from binance.client import Client
from binance.enums import *
import time
import pandas as pd
import ta  # Utilisez ta-lib ou ta pour calculer l'indicateur RSI

# Clés API pour le Testnet Binance Futures
API_KEY = "363fb2d8ce63c950476fcbd02ceca08f6375c7d4d720585d65f195fa60cd1893"
API_SECRET = "033f6910e69b1ea63a2fc24f1a66df9e304bf2050160d531e3dda5802fb6bd4c"

# Initialisation de l'API Binance Futures Testnet
def initialize_binance():
    client = Client(API_KEY, API_SECRET, testnet=True)
    client.FAPI_URL = 'https://testnet.binancefuture.com/fapi/v1'
    return client

# Fonction pour récupérer les données de chandeliers et calculer le RSI
def fetch_data(client, symbol, interval='15m', lookback=100):
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=lookback)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                       'close_time', 'quote_asset_volume', 'number_of_trades',
                                       'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = pd.to_numeric(df['close'])
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)  # Calculer le RSI sur 14 périodes
    return df

# Fonction pour ouvrir un ordre
def open_order(client, side, quantity=0.01):
    order = client.futures_create_order(
        symbol='BTCUSDT',
        side=side,
        type=ORDER_TYPE_MARKET,
        quantity=quantity
    )
    return order

# Stratégie basée sur le RSI
def rsi_strategy(client):
    position_open = False

    while True:
        df = fetch_data(client, 'BTCUSDT')
        current_rsi = df['rsi'].iloc[-1]
        print(f"RSI actuel : {current_rsi}")

        if current_rsi < 30 and not position_open:
            print("RSI indique une survente. Ouverture d'un ordre d'achat.")
            order = open_order(client, SIDE_BUY)
            print("Ordre d'achat ouvert:", order)
            position_open = True

        elif current_rsi > 70 and position_open:
            print("RSI indique une surachat. Fermeture de la position.")
            order = open_order(client, SIDE_SELL)
            print("Ordre de vente pour clôturer la position:", order)
            position_open = False

        # Attendre avant de vérifier les conditions de trading à nouveau
        time.sleep(60)  # Vérifie les conditions toutes les 60 secondes

# Script principal
if __name__ == "__main__":
    client = initialize_binance()
    rsi_strategy(client)
