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
    account_info = client.futures_account()
    for asset in account_info['assets']:
        if asset['asset'] == 'USDT':
            return float(asset['availableBalance'])
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

def calculate_stop_loss_price(entry_price, position_size, capital, risk_percent, is_short):
    risk_amount = capital * (risk_percent / 100)
    if is_short:
        stop_price = entry_price + (risk_amount / position_size)
    else:
        stop_price = entry_price - (risk_amount / position_size)
    return stop_price

def place_stop_loss_order(client, symbol, quantity, entry_price, risk_percent, is_short):
    """
    Place un ordre Stop Loss sur Binance Futures.
    """
    try:
        # Obtenir les informations du symbole
        symbol_info = get_symbol_info(client, symbol)
        price_precision = symbol_info['pricePrecision']
        quantity_precision = symbol_info['quantityPrecision']

        # Calculer le Stop Price en fonction du risque
        risk_amount = (entry_price * risk_percent) / 100
        stop_price = entry_price + risk_amount if is_short else entry_price - risk_amount

        # Ajuster le prix et la quantité aux précisions
        stop_price = adjust_precision(stop_price, price_precision)
        quantity = adjust_precision(quantity, quantity_precision)

        # Type de l'ordre (BUY pour short, SELL pour long)
        side = Client.SIDE_BUY if is_short else Client.SIDE_SELL

        # Placer l'ordre Stop Loss
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='STOP_MARKET',
            stopPrice=stop_price,  # Assurez-vous que ce paramètre est envoyé
            quantity=quantity,
            timeInForce='GTC'  # Good Till Cancel
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

def adjust_precision(value, precision):
    return math.floor(value * 10**precision) / 10**precision

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


def run_live_trading(symbol='BTCUSDT', leverage=10):
    client = initialize_binance()
    position_size = 0.002  # Taille minimale sur Testnet Futures

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

        # Récupérer le capital disponible
        capital = float(client.futures_account_balance()[0]['balance'])

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
            risk_percentage = 0.02
            max_loss = capital * risk_percentage

            # Gestion du Stop-Loss pour une position existante
            if current_position:
                print(f"[POSITIONS] Gestion de la position actuelle : {current_position}")

                if current_position['has_stop_loss']:
                    print("[STOP-LOSS] Un ordre stop-loss est déjà actif pour cette position.")
                    stop_loss_details = get_stop_loss_details(client, symbol)
                    if stop_loss_details:
                        print(f"[INFO] Stop-loss actuel : {stop_loss_details['stop_price']} pour une quantité de {stop_loss_details['quantity']}.")
                else:
                    # Placez un nouvel ordre Stop Loss
                    place_stop_loss_order(
                        client=client,
                        symbol=symbol,
                        quantity=current_position['quantity'],
                        entry_price=current_position['entry_price'],
                        risk_percent=2,  # Risque de 2%
                        is_short=current_position['is_short']
                    )



            # Ouverture de nouvelles positions
            stop_loss_price = None  # Initialisation
            if not current_position and is_bullish_convergence(df_15m, df_1h, df_1d, -1):
                print(f"{Fore.GREEN}[SIGNAL]{Style.RESET_ALL} Signal d'achat détecté. Ouverture d'une position longue.")

                # Calcul du stop-loss pour une nouvelle position longue
                entry_price = ohlc_15m['close']
                stop_price = entry_price - (max_loss / position_size)
                limit_price = stop_price - 10

                # Passer la commande
                place_order(client, symbol, SIDE_BUY, position_size, leverage, stop_price)

                # Placer le stop-loss
                place_stop_loss_order(client, symbol, position_size, stop_price, limit_price)

                # Enregistrement de l'opération
                operation_data = {
                    "timestamp": pd.Timestamp.now(),
                    "symbol": symbol,
                    "side": "BUY",
                    "quantity": position_size,
                    "leverage": leverage,
                    "stop_loss_price": stop_price
                }
                log_operation_to_csv(CSV_FILE, operation_data)

            elif not current_position and is_bearish_convergence(df_15m, df_1h, df_1d, -1):
                print(f"{Fore.RED}[SIGNAL]{Style.RESET_ALL} Signal de vente détecté. Ouverture d'une position courte.")

                # Calcul du stop-loss pour une nouvelle position courte
                entry_price = ohlc_15m['close']
                stop_price = entry_price + (max_loss / position_size)
                limit_price = stop_price + 10

                # Passer la commande
                place_order(client, symbol, SIDE_SELL, position_size, leverage, stop_price)

                # Placer le stop-loss
                place_stop_loss_order(client, symbol, position_size, stop_price, limit_price)

                # Enregistrement de l'opération
                operation_data = {
                    "timestamp": pd.Timestamp.now(),
                    "symbol": symbol,
                    "side": "SELL",
                    "quantity": position_size,
                    "leverage": leverage,
                    "stop_loss_price": stop_price
                }
                log_operation_to_csv(CSV_FILE, operation_data)

        # Attente de 60 secondes avant la prochaine vérification
        print(f"{Fore.BLUE}[ATTENTE]{Style.RESET_ALL} Attente de 60 secondes avant la prochaine vérification...")
        progress_bar_with_sleep(60)
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


# Exécution du trading en direct
if __name__ == "__main__":
    run_live_trading()