#!/usr/bin/env python3
import math
import time
import sys
import pandas as pd
from binance.client import Client
from binance.enums import *
import csv
from colorama import Fore, Style, init
init(autoreset=True)
from threading import Event

from imports import *


stop_event = Event()  # Importé dans le script principal

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