#!/usr/bin/env python3
from imports import *
from colorama import Fore, Style, init
init(autoreset=True)


MAX_POSITIONS = 2  # Limite du nombre maximal de positions simultanées
CSV_FILE = "trading_operations.csv"  # Nom du fichier pour l'enregistrement
# Clés API pour le Testnet Binance Futures
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
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
