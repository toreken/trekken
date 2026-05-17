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

app = Flask(__name__)

SYMBOLS = [
    'TONX', 'FRSH', 'PAYC', 'GCTS', 'PXLW',
    'FSLR', 'SIDU', 'VRNS', 'TRVG', 'TZOO',
    'MAKO', 'HLP'
]

CALC_PERIOD = 'max'
DISPLAY_PERIOD = 90
BG_COLOR = '#131722'
TEXT_COLOR = 'white'
GRID_COLOR = '#444444'
CACHE_SECONDS = 3600  # 1時間キャッシュ

# キャッシュ用辞書
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


def make_chart_image(df, symbol):
    plot_len = min(DISPLAY_PERIOD, len(df))
    plot_df = df.iloc[-plot_len:].copy()

    hidden_marketcolors = mpf.make_marketcolors(
        up=BG_COLOR, down=BG_COLOR, edge=BG_COLOR, wick=BG_COLOR
    )
    my_style = mpf.make_mpf_style(
        base_mpf_style='nightclouds',
        marketcolors=hidden_marketcolors,
        y_on_right=True,
        rc={
            'figure.facecolor': BG_COLOR,
            'axes.facecolor': BG_COLOR,
            'savefig.facecolor': BG_COLOR,
            'axes.edgecolor': GRID_COLOR,
            'axes.labelcolor': TEXT_COLOR,
            'xtick.color': TEXT_COLOR,
            'ytick.color': TEXT_COLOR,
            'grid.color': GRID_COLOR,
            'text.color': TEXT_COLOR,
            'xtick.labelcolor': TEXT_COLOR,
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

    for artist in ax_main.get_children():
        if isinstance(artist, (mcollections.PolyCollection, mcollections.LineCollection)):
            artist.set_zorder(5)
        elif isinstance(artist, mlines.Line2D):
            artist.set_zorder(8)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_b64


@app.route('/chart/<symbol>')
def chart(symbol):
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        return jsonify({'error': f'{symbol} は対象外です'}), 400

    # キャッシュチェック
    now = time.time()
    if symbol in chart_cache:
        cached_time, cached_img = chart_cache[symbol]
        if now - cached_time < CACHE_SECONDS:
            return jsonify({'image': cached_img, 'symbol': symbol, 'cached': True})

    try:
        df = fetch_and_calculate(symbol, period=CALC_PERIOD)
        if df is None:
            return jsonify({'error': f'{symbol} のデータ取得に失敗しました'}), 500
        img_b64 = make_chart_image(df, symbol)
        if img_b64 is None:
            return jsonify({'error': f'{symbol} のチャート生成に失敗しました'}), 500

        # キャッシュに保存
        chart_cache[symbol] = (now, img_b64)

        return jsonify({'image': img_b64, 'symbol': symbol, 'cached': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()


port = int(os.environ.get('PORT', 5000))
app.run(debug=False, host='0.0.0.0', port=port)
