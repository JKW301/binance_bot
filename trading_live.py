import time
import pandas as pd
from binance.client import Client
from binance.enums import *
#from combined_BTC import ichimoku, is_bullish_convergence, is_bearish_convergence

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

# Fonction pour passer un ordre
def place_order(client, symbol, side, quantity, leverage):
    try:
        client.futures_change_leverage(symbol=symbol, leverage=leverage)
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        print(f"[ORDRE] Ordre {side} exécuté pour {quantity} {symbol}. Détails : {order}")
    except Exception as e:
        print(f"[ERREUR] Erreur lors de l'exécution de l'ordre : {e}")

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

# Fonction principale de trading en temps réel
def run_live_trading(symbol='BTCUSDT', leverage=10):
    client = initialize_binance()
    position_size = 0.01
    positions = {"long": None, "short": None, "stop_loss": None}

    # Initialiser les DataFrames avec des données historiques pour les calculs Ichimoku
    df_15m, df_1h, df_1d = initialize_dataframes(client, symbol)

    print("[INFO] Début du trading en direct en utilisant les données OHLC avec historique.")
    while True:
        # Obtenez les dernières données OHLC pour chaque intervalle
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

        # Affichage des indicateurs pour le suivi
        print(f"[INDICATEURS] Tenkan-sen (15m): {df_15m['tenkan_sen'].iloc[-1]}, Kijun-sen (15m): {df_15m['kijun_sen'].iloc[-1]}")
        print(f"[INDICATEURS] Senkou Span A (15m): {df_15m['senkou_span_a'].iloc[-1]}, Senkou Span B (15m): {df_15m['senkou_span_b'].iloc[-1]}")

        print(f"[INDICATEURS] Tenkan-sen (1h): {df_1h['tenkan_sen'].iloc[-1]}, Kijun-sen (1h): {df_1h['kijun_sen'].iloc[-1]}")
        print(f"[INDICATEURS] Senkou Span A (1h): {df_1h['senkou_span_a'].iloc[-1]}, Senkou Span B (1h): {df_1h['senkou_span_b'].iloc[-1]}")

        print(f"[INDICATEURS] Tenkan-sen (1d): {df_1d['tenkan_sen'].iloc[-1]}, Kijun-sen (1d): {df_15m['kijun_sen'].iloc[-1]}")
        print(f"[INDICATEURS] Senkou Span A (1d): {df_1d['senkou_span_a'].iloc[-1]}, Senkou Span B (1d): {df_1d['senkou_span_b'].iloc[-1]}")

        # Calcul du capital et du risque en temps réel
        capital = get_balance(client)
        risk_amount = capital * 0.02
        print(f"[CAPITAL] Solde actuel: {capital} USDT, montant à risque: {risk_amount} USDT")

        # Signaux d'achat et de vente
        if not positions["long"] and is_bullish_convergence(df_15m, df_1h, df_1d, -1):
            print("[SIGNAL] Signal d'achat détecté. Ouverture d'une position longue.")
            place_order(client, symbol, SIDE_BUY, position_size, leverage)
            positions["long"] = position_size
            positions["stop_loss"] = ohlc_15m['close'] - (risk_amount / (position_size * leverage))

        elif not positions["short"] and is_bearish_convergence(df_15m, df_1h, df_1d, -1):
            print("[SIGNAL] Signal de vente détecté. Ouverture d'une position courte.")
            place_order(client, symbol, SIDE_SELL, position_size, leverage)
            positions["short"] = position_size
            positions["stop_loss"] = ohlc_15m['close'] + (risk_amount / (position_size * leverage))

        # Attente de 60 secondes avant la prochaine vérification
        print("[ATTENTE] Attente de 60 secondes avant la prochaine vérification...")
        for _ in range(60):
            for cursor in "|/-\\":
                print(f"\b{cursor}", end="", flush=True)
                time.sleep(0.25)
        print("\n")
        """
        while True:
            update_and_plot(client, symbol)
            print("[ATTENTE] Attente de 60 secondes avant la prochaine mise à jour...")
            time.sleep(60)
        """

def get_historical_data(client, symbol, interval, limit):
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                       'quote_asset_volume', 'number_of_trades',
                                       'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[['open', 'high', 'low', 'close']].astype(float)
    return df

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

# Exécution du trading en direct
if __name__ == "__main__":
    run_live_trading()
