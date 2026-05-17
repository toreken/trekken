import os
import io
import base64
from flask import Flask, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.patches import Rectangle
import warnings

warnings.simplefilter('ignore')

app = Flask(__name__)

DISPLAY_PERIOD = 90
BG_COLOR = '#131722'
TEXT_COLOR = 'white'
GRID_COLOR = '#444444'

SYMBOLS = [
    'TONX', 'FRSH', 'PAYC', 'GCTS', 'PXLW',
    'FSLR', 'SIDU', 'VRNS', 'TRVG', 'TZOO',
    'MAKO', 'HLP'
]

def fetch_and_calculate(symbol):
    print(f"取得中: {symbol}")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="4y", interval="1d")
    except Exception as e:
        print(f"エラー: {e}")
        return None

    if df is None or df.empty:
        print(f"{symbol} データなし")
        return None

    df.index = pd.to_datetime(df.index).normalize().tz_localize(None)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

    df['prev_close'] = df['Close'].shift(1)
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    df['uvol'] = np.where(df['Close'] > df['prev_close'], df['Volume'], 0)
    df['dvol'] = np.where(df['Close'] < df['prev_close'], df['Volume'], 0)
    df['uVolSMA10'] = df['uvol'].rolling(window=10).mean()
    df['dVolSMA10'] = df['dvol'].rolling(window=10).mean()
    df['discrepancyPercent'] = (df['Close'] - df['EMA21']) / df['EMA21'] * 100
    df['discrepancyScore'] = df['discrepancyPercent'] * 15
    df['volDiff'] = df['uVolSMA10'] - df['dVolSMA10']
    df['volDiffScore'] = df['volDiff'] / 5000
    df['totalScore'] = df['discrepancyScore'] + df['volDiffScore']

    colors = []
    for i in range(len(df)):
        score = df['totalScore'].iloc[i]
        if pd.isna(score):
            c = '#888888'
        elif score >= 0:
            c = '#32cd32'
        else:
            c = '#ff4444'
        colors.append(c)
    df['candle_color'] = colors
    return df

def make_chart_image(df, symbol):
    plot_df = df.tail(DISPLAY_PERIOD).copy()

    mc = mpf.make_marketcolors(up=BG_COLOR, down=BG_COLOR, edge=BG_COLOR, wick=BG_COLOR)
    my_style = mpf.make_mpf_style(
        base_mpf_style='nightclouds',
        marketcolors=mc,
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
        }
    )

    fig = plt.figure(figsize=(14, 8), facecolor=BG_COLOR)
    fig.subplots_adjust(top=0.92, bottom=0.15, left=0.05, right=0.90)
    ax_main = fig.add_subplot(111, facecolor=BG_COLOR)
    ax_main.tick_params(axis='x', colors=TEXT_COLOR, labelcolor=TEXT_COLOR)
    ax_main.tick_params(axis='y', colors=TEXT_COLOR, labelcolor=TEXT_COLOR)
    ax_main.yaxis.tick_right()
    ax_main.yaxis.set_label_position("right")

    mpf.plot(plot_df, type='candle', style=my_style, ax=ax_main,
             warn_too_much_data=10000, returnfig=False, datetime_format='%Y-%m')

    current_score = plot_df['totalScore'].iloc[-1] if not pd.isna(plot_df['totalScore'].iloc[-1]) else 0
    ax_main.set_title(f"{symbol} Trend - Score: {current_score:.1f}", fontsize=20, loc='center', pad=15, color=TEXT_COLOR)
    ax_main.xaxis.grid(False)

    xmin, xmax = ax_main.get_xlim()
    ax_main.set_xlim(xmin, xmax + 5)

    for j in range(len(plot_df)):
        row = plot_df.iloc[j]
        c = row['candle_color']
        ax_main.plot([j, j], [row['Low'], row['High']], color=c, linewidth=1.5, zorder=10)
        body_bottom = min(row['Open'], row['Close'])
        body_height = max(abs(row['Open'] - row['Close']), row['Close'] * 0.001)
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
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        return jsonify({'error': f'{symbol} は対象外です'}), 400
    try:
        df = fetch_and_calculate(symbol)
        if df is None:
            return jsonify({'error': f'{symbol} のデータ取得に失敗しました'}), 500
        img_b64 = make_chart_image(df, symbol)
        return jsonify({'image': img_b64, 'symbol': symbol})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

port = int(os.environ.get('PORT', 5000))
app.run(debug=False, host='0.0.0.0', port=port)
