import math
import time
import sys
import pandas as pd
from binance.client import Client
from binance.enums import *
import csv
from colorama import Fore, Style, init
init(autoreset=True)

from ux_load_idle import *
from strategy_ichimoku import *
from timeframes import *

from threading import Event

stop_event = Event()  # Importé dans le script principal


MAX_POSITIONS = 2  # Limite du nombre maximal de positions simultanées
CSV_FILE = "trading_operations.csv"  # Nom du fichier pour l'enregistrement
# Clés API pour le Testnet Binance Futures
API_KEY = '363fb2d8ce63c950476fcbd02ceca08f6375c7d4d720585d65f195fa60cd1893'
API_SECRET = '033f6910e69b1ea63a2fc24f1a66df9e304bf2050160d531e3dda5802fb6bd4c' 

# Initialisation de l'API Binance Futures Testnet
def initialize_binance():
    client = Client(API_KEY, API_SECRET, testnet=True)
    client.FAPI_URL = 'https://testnet.binancefuture.com/fapi/v1'
    return client

# Fonction pour récupérer le solde USDT en temps réel
def get_balance(client):
    """
    Récupère le solde disponible en USDT pour le compte Binance Futures.
    """
    try:
        account_info = client.futures_account()
        for asset in account_info['assets']:
            if asset['asset'] == 'USDT':
                return float(asset['availableBalance'])  # Solde disponible
        print("[ERREUR] Impossible de trouver le solde en USDT.")
        return 0.0
    except Exception as e:
        print(f"[ERREUR] Erreur lors de la récupération du solde : {e}")
        return 0.0


def get_position_details(client, symbol):
    """
    Interroge Binance pour récupérer les informations des positions ouvertes pour un symbole.
    """
    positions = client.futures_position_information()
    for position in positions:
        if position['symbol'] == symbol:
            qty = float(position['positionAmt'])
            entry_price = float(position['entryPrice'])
            
            # Récupérer l'effet de levier configuré
            leverage = get_leverage(client, symbol)
            if leverage is None:
                print(f"{Fore.RED}[ERREUR]{Style.RESET_ALL} Impossible de récupérer l'effet de levier pour {symbol}. Valeur par défaut : 1")
                leverage = 1
            
            # Vérifier si un stop-loss existe pour cette position
            has_stop_loss = check_stop_loss_order(client, symbol, {"quantity": qty})
            
            return {
                "quantity": qty,
                "entry_price": entry_price,
                "leverage": leverage,
                "is_long": qty > 0,
                "is_short": qty < 0,
                "has_stop_loss": has_stop_loss
            }
    return None

def count_open_positions_count(client):
    """Retourne le nombre total de positions ouvertes sur le compte."""
    positions = client.futures_position_information()
    open_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
    return len(open_positions)

def get_leverage(client, symbol):
    """
    Récupère l'effet de levier configuré pour un symbole donné dans Binance Futures.
    """
    account_info = client.futures_account()
    for asset in account_info['positions']:
        if asset['symbol'] == symbol:
            return int(asset['leverage'])
    return None

def get_symbol_constraints(client, symbol):
    """
    Récupère les contraintes spécifiques (tickSize, minPrice, etc.) pour un symbole donné.
    """
    try:
        exchange_info = client.futures_exchange_info()
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                constraints = {}
                for f in s['filters']:
                    if f['filterType'] == 'PRICE_FILTER':
                        constraints['tickSize'] = float(f['tickSize'])
                    if f['filterType'] == 'MIN_NOTIONAL':
                        constraints['minNotional'] = float(f['notional'])
                return constraints
    except Exception as e:
        print(f"[ERREUR] Impossible de récupérer les contraintes du symbole {symbol} : {e}")
        return None
"""
    print ("capital : ", capital)
    print("risk percent : ", risk_percent)
    print("risk amount : ", risk_amount)
    print("position size : ", position_size)
    print("leverage : ", leverage)
    print("entry price : ", entry_price)
    print("loss per unit : ", loss_per_unit)
    print("stop price : ", stop_price)
"""

def calculate_stop_loss_price(entry_price, position_size, capital, risk_percent, is_short, leverage, tick_size):
    """
    Calcule un stop-loss correct basé sur le risque maximal autorisé.
    """
    # Calcul du risque maximal autorisé (en USDT)
    risk_amount = capital * (risk_percent / 100)
    print ("capital : ", capital)
    print("risk percent : ", risk_percent)
    print("risk amount : ", risk_amount)
    print("position size : ", position_size)
    print("leverage : ", leverage)
    # Calcul de la perte par unité de BTC, en tenant compte du levier
    loss_per_unit = risk_amount / (position_size * leverage)

    # Calcul du stop-loss
    if is_short:
        stop_price = entry_price + loss_per_unit  # Pour une position short
    else:
        stop_price = entry_price - loss_per_unit  # Pour une position longue

    # Ajustement du prix avec le tickSize
    stop_price = adjust_precision(stop_price, tick_size)
    print("entry price : ", entry_price)
    print("loss per unit : ", loss_per_unit)
    print("stop price : ", stop_price)
    return stop_price

def place_stop_loss_order(client, symbol, entry_price, risk_percent, is_short, leverage, capital, percentage):
    """
    Place un ordre Stop Loss sur Binance Futures en respectant un risque cible et les contraintes.
    """
    try:
        # Valider le capital
        if capital <= 0:
            print("[ERREUR] Le capital est nul ou invalide. Vérifiez votre solde.")
            return

        # Obtenir les contraintes du symbole
        constraints = get_symbol_constraints(client, symbol)
        if not constraints:
            print(f"[ERREUR] Contraintes introuvables pour le symbole {symbol}.")
            return

        tick_size = constraints.get('tickSize', 0.1)
        step_size = constraints.get('stepSize', 0.001)
        min_notional = constraints.get('minNotional', 5)

        print(f"[CONTRAINTES] tickSize={tick_size}, stepSize={step_size}, minNotional={min_notional}")

        # Calculer la quantité dynamique
        quantity = calculate_quantity(
            capital=capital,
            entry_price=entry_price,
            percentage=percentage,
            tick_size=tick_size,
            step_size=step_size,
            min_notional=min_notional
        )

        if quantity <= 0:
            print("[ERREUR] La quantité calculée est invalide.")
            return

        # Calculer le Stop Price
        stop_price = calculate_stop_loss_price(
            entry_price=entry_price,
            position_size=quantity,
            capital=capital,
            risk_percent=risk_percent,
            is_short=is_short,
            leverage=leverage,
            tick_size=tick_size
        )

        print(f"[STOP-LOSS] Calculé : stopPrice={stop_price}, quantity={quantity}")

        # Définir le type de l'ordre
        side = Client.SIDE_BUY if is_short else Client.SIDE_SELL

        print(f"[API CALL] symbol={symbol}, side={side}, stopPrice={stop_price}, quantity={quantity}")

        # Placer l'ordre Stop Loss
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='STOP_MARKET',
            stopPrice=stop_price,
            quantity=quantity,
            timeInForce='GTC'
        )
        print(f"[STOP-LOSS] Ordre placé avec succès : {order}")
        return order

    except Exception as e:
        print(f"[ERREUR] Impossible de placer l'ordre Stop Loss : {e}")
        return None



def get_existing_stop_loss(client, symbol):
    """
    Vérifie s'il existe un ordre stop-loss actif pour le symbole.
    """
    try:
        open_orders = client.futures_get_open_orders(symbol=symbol)
        for order in open_orders:
            if order['type'] == 'STOP_MARKET' and order['reduceOnly']:
                return order  # Retourne l'ordre existant
        return None
    except Exception as e:
        print(f"Erreur lors de la récupération des ordres actifs : {e}")
        return None

def get_symbol_info(client, symbol):
    exchange_info = client.futures_exchange_info()
    for s in exchange_info['symbols']:
        if s['symbol'] == symbol:
            return s
    return None

def adjust_precision(value, tick_size):
    """
    Ajuste une valeur donnée à la précision définie par le tickSize.
    """
    return round(value - (value % tick_size), len(str(tick_size).split('.')[-1]))


def check_stop_loss_order(client, symbol, position):
    orders = client.futures_get_open_orders(symbol=symbol)
    for order in orders:
        if order['type'] == 'STOP_MARKET' and float(order['origQty']) == abs(position['quantity']):
            return True
    return False

def get_stop_loss_details(client, symbol):
    """
    Récupère les détails de l'ordre Stop Loss actif pour un symbole donné.
    """
    try:
        open_orders = client.futures_get_open_orders(symbol=symbol)
        for order in open_orders:
            if order['type'] in ['STOP_MARKET', 'STOP_LOSS_LIMIT']:
                stop_price = float(order['stopPrice'])
                quantity = float(order['origQty'])
                print(f"[STOP-LOSS] Stop-loss actif pour {symbol}:")
                print(f" - Stop Price: {stop_price}")
                print(f" - Quantity: {quantity}")
                return {
                    "stop_price": stop_price,
                    "quantity": quantity
                }
        print(f"[STOP-LOSS] Aucun stop-loss actif trouvé pour {symbol}.")
        return None
    except Exception as e:
        print(f"[ERREUR] Impossible de récupérer les détails du stop-loss : {e}")
        return None

# Fonction pour passer un ordre
def place_order(client, symbol, side, quantity, leverage, reduce_only=False):
    try:
        client.futures_change_leverage(symbol=symbol, leverage=leverage)
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            reduceOnly=reduce_only  # Assure que l'ordre réduit la position
        )
        print(f"[ORDRE] Ordre {side} exécuté pour {quantity} {symbol}. Détails : {order}")
    except Exception as e:
        print(f"[ERREUR] Erreur lors de l'exécution de l'ordre : {e}")

def calculate_quantity(capital, entry_price, percentage, tick_size, step_size, min_notional):
    """
    Calcule une quantité dynamique en fonction du capital, du prix d'entrée, et des contraintes Binance.
    """
    # Capital engagé en fonction du pourcentage
    capital_engaged = capital * (percentage / 100)

    # Calcul initial de la quantité
    quantity = capital_engaged / entry_price

    # Ajustement avec stepSize (lotSize)
    quantity = math.floor(quantity / step_size) * step_size

    # Vérification de la valeur notionnelle minimale
    notional = quantity * entry_price
    if notional < min_notional:
        print(f"[ERREUR] Quantité calculée ({quantity}) est inférieure à la valeur notionnelle minimale ({min_notional}).")
        return 0.0

    return quantity

def has_active_stop_loss(client, symbol, position):
    """
    Vérifie s'il existe un ordre STOP_MARKET actif cohérent avec la position actuelle.
    """
    try:
        open_orders = client.futures_get_open_orders(symbol=symbol)
        for order in open_orders:
            if order['type'] == 'STOP_MARKET':
                # Vérifier la quantité et le stopPrice
                if float(order['origQty']) == abs(position['quantity']) and float(order['stopPrice']) == position['stop_price']:
                    print(f"[INFO] Stop-loss actif correspondant trouvé : {order}")
                    return True
        return False
    except Exception as e:
        print(f"[ERREUR] Erreur lors de la vérification des ordres actifs : {e}")
        return False


def debug_open_orders(client, symbol):
    """
    Affiche les détails des ordres ouverts pour debug.
    """
    try:
        open_orders = client.futures_get_open_orders(symbol=symbol)
        for order in open_orders:
            print(f"[DEBUG] Détails de l'ordre : {order}")
    except Exception as e:
        print(f"[ERREUR] Impossible de récupérer les détails des ordres : {e}")

def cancel_duplicate_stop_orders(client, symbol):
    """
    Annule tous les ordres STOP_MARKET ouverts pour un symbole donné.
    """
    try:
        open_orders = client.futures_get_open_orders(symbol=symbol)
        for order in open_orders:
            if order['type'] == 'STOP_MARKET':
                print(f"[INFO] Annulation de l'ordre en doublon : {order}")
                client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
    except Exception as e:
        print(f"[ERREUR] Impossible d'annuler les ordres : {e}")


def run_live_trading(symbol='BTCUSDT', leverage=10, percentage=5):
    client = initialize_binance()

    # Vérifiez les permissions de l'API key
    try:
        account_info = client.futures_account()
        print("[INFO] Connexion réussie à l'API Binance Futures.")
    except Exception as e:
        print(f"Erreur de connexion à l'API Binance Futures : {e}")
        return

    # Initialiser les DataFrames avec des données historiques pour les calculs Ichimoku
    df_15m, df_1h, df_1d = initialize_dataframes(client, symbol)

    print("[INFO] Début du trading en direct en utilisant les données OHLC avec historique.")
    while True:
        #debug_open_orders(client, symbol)

        # Récupérer le capital disponible
        capital = get_balance(client)

        if capital <= 0:
            print("[ERREUR] Capital nul ou invalide. Impossible de continuer.")
            return

        # Vérifier les positions ouvertes
        current_position = get_position_details(client, symbol)

        # Vérifier le nombre de positions ouvertes
        open_positions_count = count_open_positions_count(client)
        print(f"{Fore.YELLOW}[POSITIONS]{Style.RESET_ALL} Nombre de positions ouvertes : {open_positions_count}")

        if open_positions_count >= MAX_POSITIONS:
            print(f"{Fore.YELLOW}[POSITIONS]{Style.RESET_ALL} Nombre maximum de positions atteint. Pas de nouvelle ouverture.")
        else:
            print(f"{Fore.YELLOW}[POSITIONS]{Style.RESET_ALL} Position actuelle : {current_position}")

            # Obtenir les dernières données OHLC pour chaque intervalle
            print("[DATA] Récupération des données OHLC pour chaque intervalle...")
            ohlc_15m = get_symbol_ohlc(client, symbol, '15m')
            ohlc_1h = get_symbol_ohlc(client, symbol, '1h')
            ohlc_1d = get_symbol_ohlc(client, symbol, '1d')

            current_time = pd.Timestamp.now()
            df_15m.loc[current_time] = ohlc_15m
            df_1h.loc[current_time] = ohlc_1h
            df_1d.loc[current_time] = ohlc_1d

            # Calculer les indicateurs Ichimoku
            print("[ICHIMOKU] Calcul des indicateurs Ichimoku...")
            ichimoku(df_15m)
            ichimoku(df_1h)
            ichimoku(df_1d)

            # Supposez que vous risquez 2 % du capital total
            risk_percent = 2

            # Gestion du Stop-Loss pour une position existante
            if current_position:
                print(f"[POSITIONS] Gestion de la position actuelle : {current_position}")

                # Annuler les ordres STOP_MARKET en doublon
                cancel_duplicate_stop_orders(client, symbol)

                if has_active_stop_loss(client, symbol, current_position):
                    print("[STOP-LOSS] Un ordre stop-loss est déjà actif pour cette position.")
                else:
                    print("[STOP-LOSS] Pas de stoploss en cours. Placement d'un nouvel ordre.")
                    place_stop_loss_order(
                        client=client,
                        symbol=symbol,
                        entry_price=current_position['entry_price'],
                        risk_percent=risk_percent,
                        is_short=current_position['is_short'],
                        leverage=current_position['leverage'],
                        capital=capital,
                        percentage=percentage
                    )

            # Ouverture de nouvelles positions
            if not current_position and is_bullish_convergence(df_15m, df_1h, df_1d, -1):
                print(f"{Fore.GREEN}[SIGNAL]{Style.RESET_ALL} Signal d'achat détecté. Ouverture d'une position longue.")

                # Calcul de la quantité dynamique pour l'achat
                entry_price = ohlc_15m['close']
                constraints = get_symbol_constraints(client, symbol)
                quantity = calculate_quantity(
                    capital=capital,
                    entry_price=entry_price,
                    percentage=percentage,
                    tick_size=constraints['tickSize'],
                    step_size=constraints['stepSize'],
                    min_notional=constraints['minNotional']
                )

                if quantity > 0:
                    place_order(client, symbol, SIDE_BUY, quantity, leverage)

            elif not current_position and is_bearish_convergence(df_15m, df_1h, df_1d, -1):
                print(f"{Fore.RED}[SIGNAL]{Style.RESET_ALL} Signal de vente détecté. Ouverture d'une position courte.")

                # Calcul de la quantité dynamique pour la vente
                entry_price = ohlc_15m['close']
                constraints = get_symbol_constraints(client, symbol)
                quantity = calculate_quantity(
                    capital=capital,
                    entry_price=entry_price,
                    percentage=percentage,
                    tick_size=constraints['tickSize'],
                    step_size=constraints['stepSize'],
                    min_notional=constraints['minNotional']
                )

                if quantity > 0:
                    place_order(client, symbol, SIDE_SELL, quantity, leverage)

        # Attente de 60 secondes avant la prochaine vérification
        print(f"{Fore.BLUE}[ATTENTE]{Style.RESET_ALL} Attente de 60 secondes avant la prochaine vérification...")
        progress_bar_with_sleep(60)


# Exécution du trading en direct
if __name__ == "__main__":
    run_live_trading()