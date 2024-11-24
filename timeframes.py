#!/usr/bin/env python3

from imports import *


# Fonction pour obtenir le prix actuel du symbole
def get_symbol_ohlc(client, symbol, interval):
    """Récupère les données OHLC les plus récentes."""
    kline = client.futures_klines(symbol=symbol, interval=interval, limit=1)[-1]
    return {
        'open': float(kline[1]),
        'high': float(kline[2]),
        'low': float(kline[3]),
        'close': float(kline[4])
    }

def initialize_dataframes(client, symbol):
    print("[INIT] Récupération des données historiques pour initialiser les indicateurs.")
    
    # Obtenir 100 chandeliers pour chaque intervalle afin de garantir des données complètes
    klines_15m = client.futures_klines(symbol=symbol, interval='15m', limit=100)
    klines_1h = client.futures_klines(symbol=symbol, interval='1h', limit=100)
    klines_1d = client.futures_klines(symbol=symbol, interval='1d', limit=100)

    # Transformer les données en DataFrames
    df_15m = pd.DataFrame(klines_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                               'quote_asset_volume', 'number_of_trades', 
                                               'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df_1h = pd.DataFrame(klines_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                             'quote_asset_volume', 'number_of_trades', 
                                             'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df_1d = pd.DataFrame(klines_1d, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                             'quote_asset_volume', 'number_of_trades', 
                                             'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

    for df in [df_15m, df_1h, df_1d]:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df[['open', 'high', 'low', 'close']].astype(float)

    return df_15m, df_1h, df_1d

def get_historical_data(client, symbol, interval, limit):
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                       'quote_asset_volume', 'number_of_trades', 
                                       'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[['open', 'high', 'low', 'close']].astype(float)
    return df
