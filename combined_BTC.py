import pandas as pd
import ccxt
from datetime import datetime, timedelta
import math

# Fonction pour calculer et arrondir la taille de la position
def calculate_min_position_size(current_price, leverage, min_notional=100, precision=3):
    # Calcule la taille de position pour atteindre le min_notional requis
    min_position_size = min_notional / (current_price * leverage)
    # Arrondir à la précision requise
    return round(min_position_size, precision)


def fetch_data_historical(symbol, timeframe, since, limit=1000):
    exchange = ccxt.binance()
    all_data = []
    while since < exchange.milliseconds():
        data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not data:
            print("Aucune donnée récupérée, arrêt de la collecte.")
            break
        all_data += data
        since = data[-1][0] + 1  # Avancer pour éviter les doublons
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

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

# Fonction pour exporter les transactions dans un fichier texte
def export_transactions_to_txt(df_transactions, filename="transactions_combined.txt"):
    with open(filename, "w") as file:
        file.write("Historique des transactions\n")
        file.write("=" * 30 + "\n")
        for _, row in df_transactions.iterrows():
            file.write(f"Date : {row['date']}\nType : {row['type']}\n")
            file.write(f"Prix : {row['price']:.2f} USD\n")
            file.write(f"Capital après transaction : {row['capital_after_transaction']:.2f} USD\n")
            file.write(f"Gains/Pertes : {row['profit_loss']:.2f} USD\n")
            file.write("-" * 30 + "\n")
    print(f"Transactions exportées dans le fichier {filename}")

def backtest_BTC():
    initial_capital = 1000
    position_size = 0.01  # Taille de l'ordre fixée à 0.01 BTC
    leverage = 30
    symbol = 'BTC/USDT'
    max_positions = 3
    open_positions_count = 0

    # Obtenir les données historiques
    one_year_ago = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
    df_15m = fetch_data_historical(symbol, '15m', since=one_year_ago, limit=2000)
    df_1h = fetch_data_historical(symbol, '1h', since=one_year_ago, limit=2000)
    df_1d = fetch_data_historical(symbol, '1d', since=one_year_ago, limit=2000)

    # Vérifiez si les données sont chargées correctement
    if df_15m.empty or df_1h.empty or df_1d.empty:
        print("Erreur : Les données historiques sont insuffisantes pour exécuter le backtest.")
        return

    # Synchroniser les données des timeframes
    df_1h = df_1h.reindex(df_15m.index, method='ffill')
    df_1d = df_1d.reindex(df_15m.index, method='ffill')

    # Calculer l'Ichimoku pour chaque intervalle
    ichimoku(df_15m)
    ichimoku(df_1h)
    ichimoku(df_1d)

    # Initialiser les variables de capital et de position
    capital = initial_capital
    positions = {"long": None, "short": None}
    stop_loss_level = None
    df_15m['signal'] = 0
    transactions = []

    for i in range(1, len(df_15m)):
        print(f"Étape {i}/{len(df_15m)} : Vérification des signaux de trading.")  # Débogage
        current_price = df_15m['close'].iloc[i]
        risk_amount = capital * 0.02  # Calcul du montant à risque (2% du capital)

        if open_positions_count < max_positions:
            # Ouvrir une position longue
            if is_bullish_convergence(df_15m, df_1h, df_1d, i) and positions["long"] is None:
                df_15m.loc[df_15m.index[i], 'signal'] = 1
                positions["long"] = position_size
                capital -= position_size * current_price / leverage
                entry_price_long = current_price
                stop_loss_level = entry_price_long - (risk_amount / (positions["long"] * leverage))
                open_positions_count += 1
                transactions.append({
                    'date': df_15m.index[i], 'type': 'Achat', 'price': entry_price_long,
                    'capital_after_transaction': capital, 'profit_loss': 0
                })

            # Ouvrir une position courte
            elif is_bearish_convergence(df_15m, df_1h, df_1d, i) and positions["short"] is None:
                df_15m.loc[df_15m.index[i], 'signal'] = -1
                positions["short"] = position_size
                capital -= position_size * current_price / leverage
                entry_price_short = current_price
                stop_loss_level = entry_price_short + (risk_amount / (positions["short"] * leverage))
                open_positions_count += 1
                transactions.append({
                    'date': df_15m.index[i], 'type': 'Vente à Découvert', 'price': entry_price_short,
                    'capital_after_transaction': capital, 'profit_loss': 0
                })

        # Clôture de position long
        if positions["long"]:
            if is_bearish_convergence(df_15m, df_1h, df_1d, i) or current_price <= stop_loss_level:
                profit_long = (current_price - entry_price_long) * positions["long"] * leverage
                capital += profit_long + (position_size * current_price / leverage)
                positions["long"] = None
                open_positions_count -= 1
                transactions.append({
                    'date': df_15m.index[i], 'type': 'Clôture Achat', 'price': current_price,
                    'capital_after_transaction': capital, 'profit_loss': profit_long
                })

        # Clôture de position short
        if positions["short"]:
            if is_bullish_convergence(df_15m, df_1h, df_1d, i) or current_price >= stop_loss_level:
                profit_short = (entry_price_short - current_price) * positions["short"] * leverage
                capital += profit_short + (position_size * current_price / leverage)
                positions["short"] = None
                open_positions_count -= 1
                transactions.append({
                    'date': df_15m.index[i], 'type': 'Clôture Vente à Découvert', 'price': current_price,
                    'capital_after_transaction': capital, 'profit_loss': profit_short
                })

    # Résumé du capital final
    profit = capital - initial_capital
    print(f"Capital initial : {initial_capital} USD")
    print(f"Capital final : {capital:.2f} USD")
    print(f"Profit net : {profit:.2f} USD")

    # Export des transactions
    df_transactions = pd.DataFrame(transactions)
    export_transactions_to_txt(df_transactions)

backtest_BTC()
