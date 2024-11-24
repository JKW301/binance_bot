#!/usr/bin/env python3
from dotenv import load_dotenv
import os
from imports import *
from colorama import Fore, Style, init
from binance.client import Client  # Assurez-vous que Client est bien importé ici
init(autoreset=True)

# Charger les variables d'environnement
load_dotenv()

MAX_POSITIONS = 2  # Limite du nombre maximal de positions simultanées
CSV_FILE = "trading_operations.csv"  # Nom du fichier pour l'enregistrement

# Clés API pour le Testnet Binance Futures
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

# Vérifiez si les clés API sont chargées
if not API_KEY or not API_SECRET:
    print(f"{Fore.RED}[ERREUR] Les clés API ne sont pas définies. Vérifiez votre fichier .env.{Style.RESET_ALL}")
    exit(1)

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
