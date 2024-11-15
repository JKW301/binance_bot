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
from stop_loss_related import *
from account import *
from positions import *

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
