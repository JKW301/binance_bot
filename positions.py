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
#from stop_loss_related import check_stop_loss_order
from stop_loss_related import *
from account import *
from positions import *

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
