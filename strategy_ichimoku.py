#!/usr/bin/env python3
import math
import time
import sys
import pandas as pd
from binance.client import Client
from binance.enums import *
from ux_load_idle import *
import csv
from colorama import Fore, Style, init
init(autoreset=True)

from imports import *

def ichimoku(df, tenkan=9, kijun=26, senkou=52):
    high_tenkan = df['high'].rolling(window=tenkan).max()
    low_tenkan = df['low'].rolling(window=tenkan).min()
    df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2
    high_kijun = df['high'].rolling(window=kijun).max()
    low_kijun = df['low'].rolling(window=kijun).min()
    df['kijun_sen'] = (high_kijun + low_kijun) / 2
    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(kijun)
    high_senkou = df['high'].rolling(window=senkou).max()
    low_senkou = df['low'].rolling(window=senkou).min()
    df['senkou_span_b'] = ((high_senkou + low_senkou) / 2).shift(kijun)
    df['chikou_span'] = df['close'].shift(-kijun)

def is_bullish_convergence(df_15m, df_1h, df_1d, index):
    return all([
        df_15m['tenkan_sen'].iloc[index] > df_15m['kijun_sen'].iloc[index],
        df_15m['tenkan_sen'].iloc[index] > df_15m['senkou_span_a'].iloc[index],
        df_15m['tenkan_sen'].iloc[index] > df_15m['senkou_span_b'].iloc[index],
        df_1h['tenkan_sen'].iloc[index] > df_1h['kijun_sen'].iloc[index],
        df_1d['tenkan_sen'].iloc[index] > df_1d['kijun_sen'].iloc[index]
    ])

def is_bearish_convergence(df_15m, df_1h, df_1d, index):
    return all([
        df_15m['tenkan_sen'].iloc[index] < df_15m['kijun_sen'].iloc[index],
        df_15m['tenkan_sen'].iloc[index] < df_15m['senkou_span_a'].iloc[index],
        df_15m['tenkan_sen'].iloc[index] < df_15m['senkou_span_b'].iloc[index],
        df_1h['tenkan_sen'].iloc[index] < df_1h['kijun_sen'].iloc[index],
        df_1d['tenkan_sen'].iloc[index] < df_1d['kijun_sen'].iloc[index]
    ])

def plot_ichimoku(df, title):
    plt.figure(figsize=(10, 6))
    plt.plot(df.index, df['close'], label="Prix de clôture", color='black')
    plt.plot(df.index, df['tenkan_sen'], label="Tenkan-sen", color='blue')
    plt.plot(df.index, df['kijun_sen'], label="Kijun-sen", color='red')
    plt.plot(df.index, df['senkou_span_a'], label="Senkou Span A", color='green', linestyle='--')
    plt.plot(df.index, df['senkou_span_b'], label="Senkou Span B", color='orange', linestyle='--')
    plt.fill_between(df.index, df['senkou_span_a'], df['senkou_span_b'], 
                     where=(df['senkou_span_a'] >= df['senkou_span_b']), color='lightgreen', alpha=0.3)
    plt.fill_between(df.index, df['senkou_span_a'], df['senkou_span_b'], 
                     where=(df['senkou_span_a'] < df['senkou_span_b']), color='lightcoral', alpha=0.3)
    plt.title(title)
    plt.legend(loc="upper left")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def update_and_plot(client, symbol):
    # Récupérer les données historiques pour chaque intervalle
    df_15m = get_historical_data(client, symbol, '15m', limit=100)
    df_1h = get_historical_data(client, symbol, '1h', limit=100)
    df_1d = get_historical_data(client, symbol, '1d', limit=100)

    # Calcul des indicateurs Ichimoku
    print("[ICHIMOKU] Calcul des indicateurs Ichimoku pour chaque intervalle...")
    ichimoku(df_15m)
    ichimoku(df_1h)
    ichimoku(df_1d)

    # Afficher les graphiques pour chaque intervalle
    print("[PLOT] Affichage des graphiques Ichimoku...")
    plot_ichimoku(df_15m, "Ichimoku - Intervalle 15m")
    plot_ichimoku(df_1h, "Ichimoku - Intervalle 1h")
    plot_ichimoku(df_1d, "Ichimoku - Intervalle 1d")
    