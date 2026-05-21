import os
import io
import base64
import time
from flask import Flask, jsonify
import pandas as pd
import numpy as np
import mplfinance as mpf
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.collections as mcollections
from matplotlib.patches import Rectangle
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# tvDatafeed
try:
    from tvDatafeed import TvDatafeed, Interval
    tv_user = os.environ.get('TV_USERNAME')
    tv_pass = os.environ.get('TV_PASSWORD')
    if tv_user and tv_pass:
        tv = TvDatafeed(tv_user, tv_pass)
        print("✅ tvDatafeed OK (ログイン)")
    else:
        tv = TvDatafeed()
        print("⚠️ tvDatafeed OK (ログインなし・データ制限あり)")
    TV_AVAILABLE = True
except Exception as e:
    TV_AVAILABLE = False
    print(f"⚠️ tvDatafeed NG: {e}")

app = Flask(__name__)

SYMBOLS = [
    'TONX', 'FRSH', 'PAYC', 'GCTS', 'PXLW',
    'FSLR', 'SIDU', 'VRNS', 'TRVG', 'TZOO',
    'MAKO', 'HLP'
]

INDEX_SYMBOLS = ['NQ1!', 'ES1!', 'NI225']

CALC_PERIOD = 'max'
DISPLAY_PERIOD = 90
BG_COLOR = '#131722'
TEXT_COLOR = 'white'
GRID_COLOR = '#444444'
CACHE_SECONDS = 3600

chart_cache = {}


def get_wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def fetch_and_calculate(symbol, period='max'):
    try:
        df = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = df.columns.str.lower()
        df = df.loc[:, ~df.columns.duplicated()].copy()
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        if df.empty or len(df) < 2:
            return None
        if 'close' not in df.columns:
            if 'adj close' in df.columns:
                df['close'] = df['adj close']
            else:
                return None
    except Exception:
        return None

    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['prev_close'] = df['close'].shift(1)
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['uvol'] = np.where(df['close'] > df['prev_close'], df['volume'], 0)
    df['dvol'] = np.where(df['close'] < df['prev_close'], df['volume'], 0)
    df['total_uvol_sma'] = get_wma(df['uvol'], 10)
    df['total_dvol_sma'] = get_wma(df['dvol'], 10)
    df['discrepancyPercent'] = (df['close'] - df['ema_21']) / df['ema_21'] * 100
    df['discrepancyScore'] = df['discrepancyPercent'] / 2
    df['volDiff'] = df['total_uvol_sma'] - df['total_dvol_sma']
    df['volDiff_avg'] = df['volDiff'].rolling(window=50).mean()
    df['volDiff_std'] = df['volDiff'].rolling(window=50).std(ddof=0)
    df['volDiffScore'] = np.where(
        df['volDiff_std'] != 0,
        (df['volDiff'] - df['volDiff_avg']) / df['volDiff_std'] * 3,
        0
    )
    df['totalScore'] = df['discrepancyScore'] + df['volDiffScore']
    return df


def fetch_nq1(n_bars=1000):
    if not TV_AVAILABLE:
        return None
    try:
        df_qqq = tv.get_hist(symbol='QQQ', exchange='NASDAQ', interval=Interval.in_daily, n_bars=n_bars)
        df_ndtw = tv.get_hist(symbol='NDTW', exchange='INDEX', interval=Interval.in_daily, n_bars=n_bars)
        df_ndfi = tv.get_hist(symbol='NDFI', exchange='INDEX', interval=Interval.in_daily, n_bars=n_bars)
        df_ndth = tv.get_hist(symbol='NDTH', exchange='INDEX', interval=Interval.in_daily, n_bars=n_bars)
        df_uvol = tv.get_hist(symbol='UVOLQ', exchange='USI', interval=Interval.in_daily, n_bars=n_bars)
        df_dvol = tv.get_hist(symbol='DVOLQ', exchange='USI', interval=Interval.in_daily, n_bars=n_bars)
        df_chart = tv.get_hist(symbol='NQ1!', exchange='CME_MINI', interval=Interval.in_daily, n_bars=n_bars)

        if any(x is None or x.empty for x in [df_qqq, df_ndtw, df_ndfi, df_ndth, df_uvol, df_dvol, df_chart]):
            return None

        df = df_qqq.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
        df = df.join(df_ndtw[['close']].rename(columns={'close':'ndtw'}), how='inner')
        df = df.join(df_ndfi[['close']].rename(columns={'close':'ndfi'}), how='inner')
        df = df.join(df_ndth[['close']].rename(columns={'close':'ndth'}), how='inner')
        df = df.join(df_uvol[['close']].rename(columns={'close':'uVol'}), how='inner')
        df = df.join(df_dvol[['close']].rename(columns={'close':'dVol'}), how='inner')
        for col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.index = pd.to_datetime(df.index).normalize().tz_localize(None)

        df_chart = df_chart.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
        for col in df_chart.columns: df_chart[col] = pd.to_numeric(df_chart[col], errors='coerce')
        df_chart.index = pd.to_datetime(df_chart.index).normalize().tz_localize(None)

        df['QQQSMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['ndtwScore'] = df['ndtw'] / 3
        df['ndfiScore'] = df['ndfi'] / 4
        df['ndthScore'] = df['ndth'] / 6
        df['discrepancyPercent'] = (df['Close'] - df['QQQSMA20']) / df['QQQSMA20'] * 100
        df['discrepancyScore'] = df['discrepancyPercent'] * 3
        df['uVolSMA10'] = df['uVol'].rolling(window=10).mean()
        df['dVolSMA10'] = df['dVol'].rolling(window=10).mean()
        df['volDiff'] = df['uVolSMA10'] - df['dVolSMA10']
        df['volDiffScore'] = df['volDiff'] / 50000000
        df['totalScore'] = df['ndtwScore'] + df['ndfiScore'] + df['ndthScore'] + df['discrepancyScore'] + df['volDiffScore']
        df['isAboveEMA20'] = df['Close'] > df['QQQSMA20']

        colors = []
        for i in range(len(df)):
            score = df['totalScore'].iloc[i]
            is_above = df['isAboveEMA20'].iloc[i]
            if pd.isna(score): c = '#888888'
            elif score > 40 and is_above: c = '#32cd32'
            elif score <= 40 and not is_above: c = '#ff4444'
            else: c = '#ffd700'
            colors.append(c)
        df['candle_color'] = colors

        cols_map = df[['candle_color', 'totalScore']].copy()
        cols_map.index = cols_map.index - pd.Timedelta(days=1)
        df_mapped = cols_map.reindex(df_chart.index, method='ffill')
        df_plot = df_chart.join(df_mapped)

        return df_plot
    except Exception as e:
        print(f"NQ1! error: {e}")
        return None


def make_chart_image_stock(df, symbol):
    plot_len = min(DISPLAY_PERIOD, len(df))
    plot_df = df.iloc[-plot_len:].copy()

    hidden_mc = mpf.make_marketcolors(up=BG_COLOR, down=BG_COLOR, edge=BG_COLOR, wick=BG_COLOR)
    my_style = mpf.make_mpf_style(
        base_mpf_style='nightclouds', marketcolors=hidden_mc, y_on_right=True,
        rc={
            'figure.facecolor': BG_COLOR, 'axes.facecolor': BG_COLOR,
            'savefig.facecolor': BG_COLOR, 'axes.edgecolor': GRID_COLOR,
            'axes.labelcolor': TEXT_COLOR, 'xtick.color': TEXT_COLOR,
            'ytick.color': TEXT_COLOR, 'grid.color': GRID_COLOR,
            'text.color': TEXT_COLOR, 'xtick.labelcolor': TEXT_COLOR,
            'ytick.labelcolor': TEXT_COLOR,
        }
    )

    fig = plt.figure(figsize=(14, 8), facecolor=BG_COLOR)
    fig.subplots_adjust(top=0.92, bottom=0.15, left=0.05, right=0.90)
    ax_main = fig.add_subplot(111, facecolor=BG_COLOR)
    ax_main.tick_params(axis='x', colors=TEXT_COLOR, labelcolor=TEXT_COLOR)
    ax_main.tick_params(axis='y', colors=TEXT_COLOR, labelcolor=TEXT_COLOR)

    add_plots = []
    if 'ema_20' in plot_df.columns and plot_df['ema_20'].notna().any():
        add_plots.append(mpf.make_addplot(plot_df['ema_20'], color='orange', width=1.5, ax=ax_main))
    if 'sma_50' in plot_df.columns and plot_df['sma_50'].notna().any():
        add_plots.append(mpf.make_addplot(plot_df['sma_50'], color='cyan', width=1.5, ax=ax_main))

    try:
        if add_plots:
            mpf.plot(plot_df, type='candle', style=my_style, ax=ax_main,
                     addplot=add_plots, warn_too_much_data=10000, returnfig=False, datetime_format='%Y-%m')
        else:
            mpf.plot(plot_df, type='candle', style=my_style, ax=ax_main,
                     warn_too_much_data=10000, returnfig=False, datetime_format='%Y-%m')
    except Exception:
        plt.close(fig)
        return None

    current_score = plot_df['totalScore'].iloc[-1] if not pd.isna(plot_df['totalScore'].iloc[-1]) else 0
    ax_main.set_title(f"{symbol} (Score: {current_score:.1f})", fontsize=20, loc='center', pad=15, color=TEXT_COLOR)
    ax_main.xaxis.grid(False)
    xmin, xmax = ax_main.get_xlim()
    ax_main.set_xlim(xmin, xmax + 5)

    for j in range(len(plot_df)):
        row = plot_df.iloc[j]
        score = row['totalScore']
        if pd.isna(score):   c = '#888888'
        elif score >= 7:     c = '#00bfff'
        elif score > 0:      c = '#32cd32'
        elif score <= -7:    c = '#ffd700'
        else:                c = '#ff4444'
        ax_main.plot([j, j], [row['low'], row['high']], color=c, linewidth=1.5, zorder=10)
        body_bottom = min(row['open'], row['close'])
        body_height = max(abs(row['open'] - row['close']), row['close'] * 0.0005)
        rect = Rectangle((j - 0.35, body_bottom), 0.7, body_height, facecolor=c, edgecolor=c, zorder=10)
        ax_main.add_patch(rect)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_b64


def make_chart_image_nq(df, symbol):
    plot_len = min(DISPLAY_PERIOD, len(df))
    plot_df = df.iloc[-plot_len:].copy()

    hidden_mc = mpf.make_marketcolors(up=BG_COLOR, down=BG_COLOR, edge=BG_COLOR, wick=BG_COLOR)
    my_style = mpf.make_mpf_style(
        base_mpf_style='nightclouds', marketcolors=hidden_mc, y_on_right=True,
        rc={
            'figure.facecolor': BG_COLOR, 'axes.facecolor': BG_COLOR,
            'savefig.facecolor': BG_COLOR, 'axes.edgecolor': GRID_COLOR,
            'axes.labelcolor': TEXT_COLOR, 'xtick.color': TEXT_COLOR,
            'ytick.color': TEXT_COLOR, 'grid.color': GRID_COLOR,
            'text.color': TEXT_COLOR,
        }
    )

    fig = plt.figure(figsize=(14, 8), facecolor=BG_COLOR)
    fig.subplots_adjust(top=0.92, bottom=0.15, left=0.05, right=0.90)
    ax_main = fig.add_subplot(111, facecolor=BG_COLOR)
    ax_main.tick_params(axis='x', colors=TEXT_COLOR, labelcolor=TEXT_COLOR)
    ax_main.tick_params(axis='y', colors=TEXT_COLOR, labelcolor=TEXT_COLOR)

    try:
        mpf.plot(plot_df, type='candle', style=my_style, ax=ax_main,
                 warn_too_much_data=10000, returnfig=False, datetime_format='%Y-%m')
    except Exception:
        plt.close(fig)
        return None

    current_score = plot_df['totalScore'].iloc[-1] if 'totalScore' in plot_df.columns and not pd.isna(plot_df['totalScore'].iloc[-1]) else 0
    ax_main.set_title(f"{symbol} (Score: {current_score:.1f})", fontsize=20, loc='center', pad=15, color=TEXT_COLOR)
    ax_main.xaxis.grid(False)
    xmin, xmax = ax_main.get_xlim()
    ax_main.set_xlim(xmin, xmax + 5)

    for j in range(len(plot_df)):
        row = plot_df.iloc[j]
        c = row.get('candle_color', '#888888')
        if pd.isna(c): c = '#888888'
        ax_main.plot([j, j], [row['Low'], row['High']], color=c, linewidth=1.5, zorder=10)
        body_bottom = min(row['Open'], row['Close'])
        body_height = max(abs(row['Open'] - row['Close']), row['Close'] * 0.0005)
        rect = Rectangle((j - 0.35, body_bottom), 0.7, body_height, facecolor=c, edgecolor=c, zorder=10)
        ax_main.add_patch(rect)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_b64


@app.route('/chart/<symbol>')
def chart(symbol):
    symbol_upper = symbol.upper()
    now = time.time()

    if symbol_upper in chart_cache:
        cached_time, cached_img = chart_cache[symbol_upper]
        if now - cached_time < CACHE_SECONDS:
            return jsonify({'image': cached_img, 'symbol': symbol_upper, 'cached': True})

    try:
        if symbol_upper == 'NQ1!':
            df = fetch_nq1()
            if df is None:
                return jsonify({'error': 'NQ1! のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_nq(df, 'NASDAQ Futures')
        elif symbol_upper in SYMBOLS:
            df = fetch_and_calculate(symbol_upper, period=CALC_PERIOD)
            if df is None:
                return jsonify({'error': f'{symbol_upper} のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_stock(df, symbol_upper)
        else:
            return jsonify({'error': f'{symbol_upper} は対象外です'}), 400

        if img_b64 is None:
            return jsonify({'error': 'チャート生成に失敗しました'}), 500

        chart_cache[symbol_upper] = (now, img_b64)
        return jsonify({'image': img_b64, 'symbol': symbol_upper, 'cached': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()


port = int(os.environ.get('PORT', 5000))
app.run(debug=False, host='0.0.0.0', port=port)
