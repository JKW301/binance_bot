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
