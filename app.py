import os
import io
import re
import base64
import time
import threading
import xml.etree.ElementTree as ET
from flask import Flask, jsonify, request, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests as http_requests
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

# tvDatafeed は起動時に初期化せず、必要になったとき（NQ1! 要求時）に初期化する。
# こうすることで tvDatafeed で何が起きてもサーバー起動（ポート検出）は必ず成功する。
tv = None
TV_INIT_TRIED = False


def get_tv():
    """tvDatafeed を遅延初期化する。成功すれば tv インスタンスを返し、失敗すれば None を返す。"""
    global tv, TV_INIT_TRIED
    if tv is not None:
        return tv
    if TV_INIT_TRIED:
        return None
    TV_INIT_TRIED = True
    try:
        from tvDatafeed import TvDatafeed
        tv_user = os.environ.get('TV_USERNAME')
        tv_pass = os.environ.get('TV_PASSWORD')
        if tv_user and tv_pass:
            tv = TvDatafeed(tv_user, tv_pass)
            print("✅ tvDatafeed OK (ログイン)")
        else:
            tv = TvDatafeed()
            print("⚠️ tvDatafeed OK (ログインなし・データ制限あり)")
        return tv
    except Exception as e:
        print(f"⚠️ tvDatafeed NG: {e}")
        tv = None
        return None


def get_interval():
    """Interval を安全に取り込む。"""
    try:
        from tvDatafeed import Interval
        return Interval
    except Exception:
        return None


app = Flask(__name__)


# ===== レート制限（DDoS・大量スクレイピング対策） =====
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["300 per hour", "60 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)


# ===== シンボル名バリデーション（インジェクション対策） =====
# 許可文字: 英数字、ピリオド(.), ハイフン(-), コロン(:), 感嘆符(!), イコール(=)
# 例: AAPL, BRK.B, BRK-B, TSE:7203, NQ1!, EURUSD
SYMBOL_PATTERN = re.compile(r'^[A-Za-z0-9\.\-:!=]+$')


def is_valid_symbol(symbol):
    """シンボル名が安全かどうか判定。許可文字以外があれば False。"""
    if not symbol or not isinstance(symbol, str):
        return False
    if len(symbol) > 30:
        return False
    return bool(SYMBOL_PATTERN.match(symbol))


# ===== robots.txt（AI クローラーブロック） =====
ROBOTS_TXT_CONTENT = """User-agent: *
Allow: /

# AI/LLM 学習クローラーを全面ブロック
User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: cohere-ai
Disallow: /

User-agent: FacebookBot
Disallow: /

User-agent: Meta-ExternalAgent
Disallow: /

User-agent: Diffbot
Disallow: /

User-agent: ImagesiftBot
Disallow: /

User-agent: Omgilibot
Disallow: /

User-agent: YouBot
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: Amazonbot
Disallow: /
"""


@app.route('/ping')
def ping():
    """軽量ヘルスチェック。Renderスリープ防止用にGitHub Actions等から定期的に叩く。
    DBアクセスや外部API呼び出しを一切行わず、即座に200を返す。"""
    return jsonify({'status': 'ok', 'time': int(time.time())}), 200


@app.route('/robots.txt')
def robots_txt():
    return Response(ROBOTS_TXT_CONTENT, mimetype='text/plain')


@app.after_request
def add_security_headers(resp):
    """技術スタック情報を隠す + AIブロックヘッダー + セキュリティ強化"""
    # サーバー情報を隠す（Werkzeug/Python/Flask の表記を消す）
    resp.headers['Server'] = 'Trekken'
    # AI クローラーに学習禁止を明示
    resp.headers['X-Robots-Tag'] = 'noai, noimageai'
    # セキュリティ基本ヘッダー
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # クリックジャッキング対策（iframeに埋め込めない）
    resp.headers['X-Frame-Options'] = 'DENY'
    # XSS Protection（古いブラウザ向け）
    resp.headers['X-XSS-Protection'] = '1; mode=block'
    # Content Security Policy（XSS対策の現代版）
    resp.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    # X-Powered-By を念のため空に
    resp.headers.pop('X-Powered-By', None)
    return resp


SYMBOLS = [
    'TONX', 'FRSH', 'PAYC', 'GCTS', 'PXLW',
    'FSLR', 'SIDU', 'VRNS', 'TRVG', 'TZOO',
    'MAKO', 'HLP',
    # グループ2
    'KOS', 'GOOGL', 'INTC', 'NVDA', 'IONQ', 'FIGS', 'MU',
    'RKLB', 'CRWV', 'LUNR', 'ATOM', 'KLXE', 'WTI', 'ESOA',
    # 量子コンピュータ関連（ピュアプレイ + 量子セキュリティ）
    'RGTI', 'QBTS', 'QUBT', 'LAES',
    # 宇宙関連（ピュアプレイ + 衛星通信）
    'ASTS', 'PL', 'BKSY', 'RDW', 'IRDM',
    # 水素エネルギー関連（ピュアプレイ）
    'PLUG', 'BE', 'BLDP', 'FCEL', 'HYZN',
    # 太陽光関連（純プレイ＋中国ADR、FSLRは既出）
    'ENPH', 'SEDG', 'RUN', 'NXT', 'ARRY', 'JKS', 'CSIQ', 'DQ',
    # ETF（セクター別 + 高配当）
    'XLK', 'VGT', 'IYW',           # テクノロジー
    'XLV', 'VHT', 'IYH',           # ヘルスケア
    'XLF', 'VFH', 'IYF',           # 金融
    'XLE', 'VDE', 'IYE',           # エネルギー
    'XLY', 'VCR', 'IYC',           # 一般消費財
    'XLP', 'VDC', 'IYK',           # 生活必需品
    'XLI', 'VIS', 'IYJ',           # 資本財
    'XLB', 'VAW', 'IYM',           # 素材
    'XLU', 'VPU', 'IDU',           # 公益事業
    'XLRE', 'VNQ', 'IYR',          # 不動産
    'XLC', 'VOX', 'IYZ',           # 通信サービス
    'VYM', 'HDV', 'SPYD', 'VIG',   # 高配当
]

# S&P500 構成銘柄（yfinance形式: BRK.B → BRK-B 等に変換済み）
SP500_SYMBOLS = [
    'MMM','AOS','ABT','ABBV','ACN','ADBE','AMD','AES','AFL','A','APD','ABNB','AKAM','ALB','ARE',
    'ALGN','ALLE','LNT','ALL','GOOGL','GOOG','MO','AMZN','AMCR','AEE','AEP','AXP','AIG','AMT','AWK',
    'AMP','AME','AMGN','APH','ADI','AON','APA','APO','AAPL','AMAT','APP','APTV','ACGL','ADM','ARES',
    'ANET','AJG','AIZ','T','ATO','ADSK','ADP','AZO','AVB','AVY','AXON','BKR','BALL','BAC','BAX',
    'BDX','BRK-B','BBY','TECH','BIIB','BLK','BX','XYZ','BK','BA','BKNG','BSX','BMY','AVGO','BR',
    'BRO','BF-B','BLDR','BG','BXP','CHRW','CDNS','CPT','CPB','COF','CAH','CCL','CARR','CVNA','CASY',
    'CAT','CBOE','CBRE','CDW','COR','CNC','CNP','CF','CRL','SCHW','CHTR','CVX','CMG','CB','CHD',
    'CIEN','CI','CINF','CTAS','CSCO','C','CFG','CLX','CME','CMS','KO','CTSH','COHR','COIN','CL',
    'CMCSA','FIX','CAG','COP','ED','STZ','CEG','COO','CPRT','GLW','CPAY','CTVA','CSGP','COST','CTRA',
    'CRH','CRWD','CCI','CSX','CMI','CVS','DHR','DRI','DDOG','DVA','DECK','DE','DELL','DAL','DVN',
    'DXCM','FANG','DLR','DG','DLTR','D','DPZ','DASH','DOV','DOW','DHI','DTE','DUK','DD','ETN',
    'EBAY','SATS','ECL','EIX','EW','EA','ELV','EME','EMR','ETR','EOG','EPAM','EQT','EFX','EQIX',
    'EQR','ERIE','ESS','EL','EG','EVRG','ES','EXC','EXE','EXPE','EXPD','EXR','XOM','FFIV','FDS',
    'FICO','FAST','FRT','FDX','FIS','FITB','FSLR','FE','FISV','F','FTNT','FTV','FOXA','FOX','BEN',
    'FCX','GRMN','IT','GE','GEHC','GEV','GEN','GNRC','GD','GIS','GM','GPC','GILD','GPN','GL',
    'GDDY','GS','HAL','HIG','HAS','HCA','DOC','HSIC','HSY','HPE','HLT','HD','HON','HRL','HST',
    'HWM','HPQ','HUBB','HUM','HBAN','HII','IBM','IEX','IDXX','ITW','INCY','IR','PODD','INTC','IBKR',
    'ICE','IFF','IP','INTU','ISRG','IVZ','INVH','IQV','IRM','JBHT','JBL','JKHY','J','JNJ','JCI',
    'JPM','KVUE','KDP','KEY','KEYS','KMB','KIM','KMI','KKR','KLAC','KHC','KR','LHX','LH','LRCX',
    'LVS','LDOS','LEN','LII','LLY','LIN','LYV','LMT','L','LOW','LULU','LITE','LYB','MTB','MPC',
    'MAR','MRSH','MLM','MAS','MA','MKC','MCD','MCK','MDT','MRK','META','MET','MTD','MGM','MCHP',
    'MU','MSFT','MAA','MRNA','TAP','MDLZ','MPWR','MNST','MCO','MS','MOS','MSI','MSCI','NDAQ','NTAP',
    'NFLX','NEM','NWSA','NWS','NEE','NKE','NI','NDSN','NSC','NTRS','NOC','NCLH','NRG','NUE','NVDA',
    'NVR','NXPI','ORLY','OXY','ODFL','OMC','ON','OKE','ORCL','OTIS','PCAR','PKG','PLTR','PANW','PSKY',
    'PH','PAYX','PYPL','PNR','PEP','PFE','PCG','PM','PSX','PNW','PNC','POOL','PPG','PPL','PFG',
    'PG','PGR','PLD','PRU','PEG','PTC','PSA','PHM','PWR','QCOM','DGX','Q','RL','RJF','RTX',
    'O','REG','REGN','RF','RSG','RMD','RVTY','HOOD','ROK','ROL','ROP','ROST','RCL','SPGI','CRM',
    'SNDK','SBAC','SLB','STX','SRE','NOW','SHW','SPG','SWKS','SJM','SW','SNA','SOLV','SO','LUV',
    'SWK','SBUX','STT','STLD','STE','SYK','SMCI','SYF','SNPS','SYY','TMUS','TROW','TTWO','TPR','TRGP',
    'TGT','TEL','TDY','TER','TSLA','TXN','TPL','TXT','TMO','TJX','TKO','TTD','TSCO','TT','TDG',
    'TRV','TRMB','TFC','TYL','TSN','USB','UBER','UDR','ULTA','UNP','UAL','UPS','URI','UNH','UHS',
    'VLO','VTR','VLTO','VRSN','VRSK','VZ','VRTX','VRT','VTRS','VICI','V','VST','VMC','WRB','GWW',
    'WAB','WMT','DIS','WBD','WM','WAT','WEC','WFC','WELL','WST','WDC','WY','WSM','WMB','WTW',
    'WDAY','WYNN','XEL','XYL','YUM','ZBRA','ZBH','ZTS'
]

# SP500 Symbol → GICS Sub-Industry の対応
SP500_SECTOR_MAP = {
    'MMM': 'Industrial Conglomerates', 'AOS': 'Building Products', 'ABT': 'Health Care Equipment', 'ABBV': 'Biotechnology',
    'ACN': 'IT Consulting & Other Services', 'ADBE': 'Application Software', 'AMD': 'Semiconductors', 'AES': 'Independent Power Producers & Energy Traders',
    'AFL': 'Life & Health Insurance', 'A': 'Life Sciences Tools & Services', 'APD': 'Industrial Gases', 'ABNB': 'Hotels, Resorts & Cruise Lines',
    'AKAM': 'Internet Services & Infrastructure', 'ALB': 'Specialty Chemicals', 'ARE': 'Office REITs', 'ALGN': 'Health Care Supplies',
    'ALLE': 'Building Products', 'LNT': 'Electric Utilities', 'ALL': 'Property & Casualty Insurance', 'GOOGL': 'Interactive Media & Services',
    'GOOG': 'Interactive Media & Services', 'MO': 'Tobacco', 'AMZN': 'Broadline Retail', 'AMCR': 'Paper & Plastic Packaging Products & Materials',
    'AEE': 'Multi-Utilities', 'AEP': 'Electric Utilities', 'AXP': 'Consumer Finance', 'AIG': 'Multi-line Insurance',
    'AMT': 'Telecom Tower REITs', 'AWK': 'Water Utilities', 'AMP': 'Asset Management & Custody Banks', 'AME': 'Electrical Components & Equipment',
    'AMGN': 'Biotechnology', 'APH': 'Electronic Components', 'ADI': 'Semiconductors', 'AON': 'Insurance Brokers',
    'APA': 'Oil & Gas Exploration & Production', 'APO': 'Asset Management & Custody Banks', 'AAPL': 'Technology Hardware, Storage & Peripherals', 'AMAT': 'Semiconductor Materials & Equipment',
    'APP': 'Application Software', 'APTV': 'Automotive Parts & Equipment', 'ACGL': 'Property & Casualty Insurance', 'ADM': 'Agricultural Products & Services',
    'ARES': 'Asset Management & Custody Banks', 'ANET': 'Communications Equipment', 'AJG': 'Insurance Brokers', 'AIZ': 'Multi-line Insurance',
    'T': 'Integrated Telecommunication Services', 'ATO': 'Gas Utilities', 'ADSK': 'Application Software', 'ADP': 'Human Resource & Employment Services',
    'AZO': 'Automotive Retail', 'AVB': 'Multi-Family Residential REITs', 'AVY': 'Paper & Plastic Packaging Products & Materials', 'AXON': 'Aerospace & Defense',
    'BKR': 'Oil & Gas Equipment & Services', 'BALL': 'Metal, Glass & Plastic Containers', 'BAC': 'Diversified Banks', 'BAX': 'Health Care Equipment',
    'BDX': 'Health Care Equipment', 'BRK-B': 'Multi-Sector Holdings', 'BBY': 'Computer & Electronics Retail', 'TECH': 'Life Sciences Tools & Services',
    'BIIB': 'Biotechnology', 'BLK': 'Asset Management & Custody Banks', 'BX': 'Asset Management & Custody Banks', 'XYZ': 'Transaction & Payment Processing Services',
    'BK': 'Asset Management & Custody Banks', 'BA': 'Aerospace & Defense', 'BKNG': 'Hotels, Resorts & Cruise Lines', 'BSX': 'Health Care Equipment',
    'BMY': 'Pharmaceuticals', 'AVGO': 'Semiconductors', 'BR': 'Data Processing & Outsourced Services', 'BRO': 'Insurance Brokers',
    'BF-B': 'Distillers & Vintners', 'BLDR': 'Building Products', 'BG': 'Agricultural Products & Services', 'BXP': 'Office REITs',
    'CHRW': 'Air Freight & Logistics', 'CDNS': 'Application Software', 'CPT': 'Multi-Family Residential REITs', 'CPB': 'Packaged Foods & Meats',
    'COF': 'Consumer Finance', 'CAH': 'Health Care Distributors', 'CCL': 'Hotels, Resorts & Cruise Lines', 'CARR': 'Building Products',
    'CVNA': 'Automotive Retail', 'CASY': 'Food Retail', 'CAT': 'Construction Machinery & Heavy Transportation Equipment', 'CBOE': 'Financial Exchanges & Data',
    'CBRE': 'Real Estate Services', 'CDW': 'Technology Distributors', 'COR': 'Health Care Distributors', 'CNC': 'Managed Health Care',
    'CNP': 'Multi-Utilities', 'CF': 'Fertilizers & Agricultural Chemicals', 'CRL': 'Life Sciences Tools & Services', 'SCHW': 'Investment Banking & Brokerage',
    'CHTR': 'Cable & Satellite', 'CVX': 'Integrated Oil & Gas', 'CMG': 'Restaurants', 'CB': 'Property & Casualty Insurance',
    'CHD': 'Household Products', 'CIEN': 'Communications Equipment', 'CI': 'Health Care Services', 'CINF': 'Property & Casualty Insurance',
    'CTAS': 'Diversified Support Services', 'CSCO': 'Communications Equipment', 'C': 'Diversified Banks', 'CFG': 'Regional Banks',
    'CLX': 'Household Products', 'CME': 'Financial Exchanges & Data', 'CMS': 'Multi-Utilities', 'KO': 'Soft Drinks & Non-alcoholic Beverages',
    'CTSH': 'IT Consulting & Other Services', 'COHR': 'Electronic Components', 'COIN': 'Financial Exchanges & Data', 'CL': 'Household Products',
    'CMCSA': 'Cable & Satellite', 'FIX': 'Construction & Engineering', 'CAG': 'Packaged Foods & Meats', 'COP': 'Oil & Gas Exploration & Production',
    'ED': 'Multi-Utilities', 'STZ': 'Distillers & Vintners', 'CEG': 'Electric Utilities', 'COO': 'Health Care Supplies',
    'CPRT': 'Diversified Support Services', 'GLW': 'Electronic Components', 'CPAY': 'Transaction & Payment Processing Services', 'CTVA': 'Fertilizers & Agricultural Chemicals',
    'CSGP': 'Real Estate Services', 'COST': 'Consumer Staples Merchandise Retail', 'CTRA': 'Oil & Gas Exploration & Production', 'CRH': 'Construction Materials',
    'CRWD': 'Systems Software', 'CCI': 'Telecom Tower REITs', 'CSX': 'Rail Transportation', 'CMI': 'Construction Machinery & Heavy Transportation Equipment',
    'CVS': 'Health Care Services', 'DHR': 'Life Sciences Tools & Services', 'DRI': 'Restaurants', 'DDOG': 'Application Software',
    'DVA': 'Health Care Services', 'DECK': 'Footwear', 'DE': 'Agricultural & Farm Machinery', 'DELL': 'Technology Hardware, Storage & Peripherals',
    'DAL': 'Passenger Airlines', 'DVN': 'Oil & Gas Exploration & Production', 'DXCM': 'Health Care Equipment', 'FANG': 'Oil & Gas Exploration & Production',
    'DLR': 'Data Center REITs', 'DG': 'Consumer Staples Merchandise Retail', 'DLTR': 'Consumer Staples Merchandise Retail', 'D': 'Multi-Utilities',
    'DPZ': 'Restaurants', 'DASH': 'Specialized Consumer Services', 'DOV': 'Industrial Machinery & Supplies & Components', 'DOW': 'Commodity Chemicals',
    'DHI': 'Homebuilding', 'DTE': 'Multi-Utilities', 'DUK': 'Electric Utilities', 'DD': 'Specialty Chemicals',
    'ETN': 'Electrical Components & Equipment', 'EBAY': 'Broadline Retail', 'SATS': 'Wireless Telecommunication Services', 'ECL': 'Specialty Chemicals',
    'EIX': 'Electric Utilities', 'EW': 'Health Care Equipment', 'EA': 'Interactive Home Entertainment', 'ELV': 'Managed Health Care',
    'EME': 'Construction & Engineering', 'EMR': 'Electrical Components & Equipment', 'ETR': 'Electric Utilities', 'EOG': 'Oil & Gas Exploration & Production',
    'EPAM': 'IT Consulting & Other Services', 'EQT': 'Oil & Gas Exploration & Production', 'EFX': 'Research & Consulting Services', 'EQIX': 'Data Center REITs',
    'EQR': 'Multi-Family Residential REITs', 'ERIE': 'Insurance Brokers', 'ESS': 'Multi-Family Residential REITs', 'EL': 'Personal Care Products',
    'EG': 'Reinsurance', 'EVRG': 'Electric Utilities', 'ES': 'Electric Utilities', 'EXC': 'Electric Utilities',
    'EXE': 'Oil & Gas Exploration & Production', 'EXPE': 'Hotels, Resorts & Cruise Lines', 'EXPD': 'Air Freight & Logistics', 'EXR': 'Self-Storage REITs',
    'XOM': 'Integrated Oil & Gas', 'FFIV': 'Communications Equipment', 'FDS': 'Financial Exchanges & Data', 'FICO': 'Application Software',
    'FAST': 'Trading Companies & Distributors', 'FRT': 'Retail REITs', 'FDX': 'Air Freight & Logistics', 'FIS': 'Transaction & Payment Processing Services',
    'FITB': 'Regional Banks', 'FSLR': 'Semiconductors', 'FE': 'Electric Utilities', 'FISV': 'Transaction & Payment Processing Services',
    'F': 'Automobile Manufacturers', 'FTNT': 'Systems Software', 'FTV': 'Industrial Machinery & Supplies & Components', 'FOXA': 'Broadcasting',
    'FOX': 'Broadcasting', 'BEN': 'Asset Management & Custody Banks', 'FCX': 'Copper', 'GRMN': 'Consumer Electronics',
    'IT': 'IT Consulting & Other Services', 'GE': 'Aerospace & Defense', 'GEHC': 'Health Care Equipment', 'GEV': 'Heavy Electrical Equipment',
    'GEN': 'Systems Software', 'GNRC': 'Electrical Components & Equipment', 'GD': 'Aerospace & Defense', 'GIS': 'Packaged Foods & Meats',
    'GM': 'Automobile Manufacturers', 'GPC': 'Distributors', 'GILD': 'Biotechnology', 'GPN': 'Transaction & Payment Processing Services',
    'GL': 'Life & Health Insurance', 'GDDY': 'Internet Services & Infrastructure', 'GS': 'Investment Banking & Brokerage', 'HAL': 'Oil & Gas Equipment & Services',
    'HIG': 'Property & Casualty Insurance', 'HAS': 'Leisure Products', 'HCA': 'Health Care Facilities', 'DOC': 'Health Care REITs',
    'HSIC': 'Health Care Distributors', 'HSY': 'Packaged Foods & Meats', 'HPE': 'Technology Hardware, Storage & Peripherals', 'HLT': 'Hotels, Resorts & Cruise Lines',
    'HD': 'Home Improvement Retail', 'HON': 'Industrial Conglomerates', 'HRL': 'Packaged Foods & Meats', 'HST': 'Hotel & Resort REITs',
    'HWM': 'Aerospace & Defense', 'HPQ': 'Technology Hardware, Storage & Peripherals', 'HUBB': 'Industrial Machinery & Supplies & Components', 'HUM': 'Managed Health Care',
    'HBAN': 'Regional Banks', 'HII': 'Aerospace & Defense', 'IBM': 'IT Consulting & Other Services', 'IEX': 'Industrial Machinery & Supplies & Components',
    'IDXX': 'Health Care Equipment', 'ITW': 'Industrial Machinery & Supplies & Components', 'INCY': 'Biotechnology', 'IR': 'Industrial Machinery & Supplies & Components',
    'PODD': 'Health Care Equipment', 'INTC': 'Semiconductors', 'IBKR': 'Investment Banking & Brokerage', 'ICE': 'Financial Exchanges & Data',
    'IFF': 'Specialty Chemicals', 'IP': 'Paper & Plastic Packaging Products & Materials', 'INTU': 'Application Software', 'ISRG': 'Health Care Equipment',
    'IVZ': 'Asset Management & Custody Banks', 'INVH': 'Single-Family Residential REITs', 'IQV': 'Life Sciences Tools & Services', 'IRM': 'Other Specialized REITs',
    'JBHT': 'Cargo Ground Transportation', 'JBL': 'Electronic Manufacturing Services', 'JKHY': 'Transaction & Payment Processing Services', 'J': 'Construction & Engineering',
    'JNJ': 'Pharmaceuticals', 'JCI': 'Building Products', 'JPM': 'Diversified Banks', 'KVUE': 'Personal Care Products',
    'KDP': 'Soft Drinks & Non-alcoholic Beverages', 'KEY': 'Regional Banks', 'KEYS': 'Electronic Equipment & Instruments', 'KMB': 'Household Products',
    'KIM': 'Retail REITs', 'KMI': 'Oil & Gas Storage & Transportation', 'KKR': 'Asset Management & Custody Banks', 'KLAC': 'Semiconductor Materials & Equipment',
    'KHC': 'Packaged Foods & Meats', 'KR': 'Food Retail', 'LHX': 'Aerospace & Defense', 'LH': 'Health Care Services',
    'LRCX': 'Semiconductor Materials & Equipment', 'LVS': 'Casinos & Gaming', 'LDOS': 'Diversified Support Services', 'LEN': 'Homebuilding',
    'LII': 'Building Products', 'LLY': 'Pharmaceuticals', 'LIN': 'Industrial Gases', 'LYV': 'Movies & Entertainment',
    'LMT': 'Aerospace & Defense', 'L': 'Multi-line Insurance', 'LOW': 'Home Improvement Retail', 'LULU': 'Apparel, Accessories & Luxury Goods',
    'LITE': 'Communications Equipment', 'LYB': 'Specialty Chemicals', 'MTB': 'Regional Banks', 'MPC': 'Oil & Gas Refining & Marketing',
    'MAR': 'Hotels, Resorts & Cruise Lines', 'MRSH': 'Insurance Brokers', 'MLM': 'Construction Materials', 'MAS': 'Building Products',
    'MA': 'Transaction & Payment Processing Services', 'MKC': 'Packaged Foods & Meats', 'MCD': 'Restaurants', 'MCK': 'Health Care Distributors',
    'MDT': 'Health Care Equipment', 'MRK': 'Pharmaceuticals', 'META': 'Interactive Media & Services', 'MET': 'Life & Health Insurance',
    'MTD': 'Life Sciences Tools & Services', 'MGM': 'Casinos & Gaming', 'MCHP': 'Semiconductors', 'MU': 'Semiconductors',
    'MSFT': 'Systems Software', 'MAA': 'Multi-Family Residential REITs', 'MRNA': 'Biotechnology', 'TAP': 'Brewers',
    'MDLZ': 'Packaged Foods & Meats', 'MPWR': 'Semiconductors', 'MNST': 'Soft Drinks & Non-alcoholic Beverages', 'MCO': 'Financial Exchanges & Data',
    'MS': 'Investment Banking & Brokerage', 'MOS': 'Fertilizers & Agricultural Chemicals', 'MSI': 'Communications Equipment', 'MSCI': 'Financial Exchanges & Data',
    'NDAQ': 'Financial Exchanges & Data', 'NTAP': 'Technology Hardware, Storage & Peripherals', 'NFLX': 'Movies & Entertainment', 'NEM': 'Gold',
    'NWSA': 'Publishing', 'NWS': 'Publishing', 'NEE': 'Multi-Utilities', 'NKE': 'Apparel, Accessories & Luxury Goods',
    'NI': 'Multi-Utilities', 'NDSN': 'Industrial Machinery & Supplies & Components', 'NSC': 'Rail Transportation', 'NTRS': 'Asset Management & Custody Banks',
    'NOC': 'Aerospace & Defense', 'NCLH': 'Hotels, Resorts & Cruise Lines', 'NRG': 'Independent Power Producers & Energy Traders', 'NUE': 'Steel',
    'NVDA': 'Semiconductors', 'NVR': 'Homebuilding', 'NXPI': 'Semiconductors', 'ORLY': 'Automotive Retail',
    'OXY': 'Oil & Gas Exploration & Production', 'ODFL': 'Cargo Ground Transportation', 'OMC': 'Advertising', 'ON': 'Semiconductors',
    'OKE': 'Oil & Gas Storage & Transportation', 'ORCL': 'Application Software', 'OTIS': 'Industrial Machinery & Supplies & Components', 'PCAR': 'Construction Machinery & Heavy Transportation Equipment',
    'PKG': 'Paper & Plastic Packaging Products & Materials', 'PLTR': 'Application Software', 'PANW': 'Systems Software', 'PSKY': 'Movies & Entertainment',
    'PH': 'Industrial Machinery & Supplies & Components', 'PAYX': 'Human Resource & Employment Services', 'PYPL': 'Transaction & Payment Processing Services', 'PNR': 'Industrial Machinery & Supplies & Components',
    'PEP': 'Soft Drinks & Non-alcoholic Beverages', 'PFE': 'Pharmaceuticals', 'PCG': 'Multi-Utilities', 'PM': 'Tobacco',
    'PSX': 'Oil & Gas Refining & Marketing', 'PNW': 'Multi-Utilities', 'PNC': 'Diversified Banks', 'POOL': 'Distributors',
    'PPG': 'Specialty Chemicals', 'PPL': 'Electric Utilities', 'PFG': 'Life & Health Insurance', 'PG': 'Personal Care Products',
    'PGR': 'Property & Casualty Insurance', 'PLD': 'Industrial REITs', 'PRU': 'Life & Health Insurance', 'PEG': 'Electric Utilities',
    'PTC': 'Application Software', 'PSA': 'Self-Storage REITs', 'PHM': 'Homebuilding', 'PWR': 'Construction & Engineering',
    'QCOM': 'Semiconductors', 'DGX': 'Health Care Services', 'Q': 'Semiconductor Materials & Equipment', 'RL': 'Apparel, Accessories & Luxury Goods',
    'RJF': 'Investment Banking & Brokerage', 'RTX': 'Aerospace & Defense', 'O': 'Retail REITs', 'REG': 'Retail REITs',
    'REGN': 'Biotechnology', 'RF': 'Regional Banks', 'RSG': 'Environmental & Facilities Services', 'RMD': 'Health Care Equipment',
    'RVTY': 'Health Care Equipment', 'HOOD': 'Investment Banking & Brokerage', 'ROK': 'Electrical Components & Equipment', 'ROL': 'Environmental & Facilities Services',
    'ROP': 'Electronic Equipment & Instruments', 'ROST': 'Apparel Retail', 'RCL': 'Hotels, Resorts & Cruise Lines', 'SPGI': 'Financial Exchanges & Data',
    'CRM': 'Application Software', 'SNDK': 'Technology Hardware, Storage & Peripherals', 'SBAC': 'Telecom Tower REITs', 'SLB': 'Oil & Gas Equipment & Services',
    'STX': 'Technology Hardware, Storage & Peripherals', 'SRE': 'Multi-Utilities', 'NOW': 'Systems Software', 'SHW': 'Specialty Chemicals',
    'SPG': 'Retail REITs', 'SWKS': 'Semiconductors', 'SJM': 'Packaged Foods & Meats', 'SW': 'Paper & Plastic Packaging Products & Materials',
    'SNA': 'Industrial Machinery & Supplies & Components', 'SOLV': 'Health Care Technology', 'SO': 'Electric Utilities', 'LUV': 'Passenger Airlines',
    'SWK': 'Industrial Machinery & Supplies & Components', 'SBUX': 'Restaurants', 'STT': 'Asset Management & Custody Banks', 'STLD': 'Steel',
    'STE': 'Health Care Equipment', 'SYK': 'Health Care Equipment', 'SMCI': 'Technology Hardware, Storage & Peripherals', 'SYF': 'Consumer Finance',
    'SNPS': 'Application Software', 'SYY': 'Food Distributors', 'TMUS': 'Wireless Telecommunication Services', 'TROW': 'Asset Management & Custody Banks',
    'TTWO': 'Interactive Home Entertainment', 'TPR': 'Apparel, Accessories & Luxury Goods', 'TRGP': 'Oil & Gas Storage & Transportation', 'TGT': 'Consumer Staples Merchandise Retail',
    'TEL': 'Electronic Manufacturing Services', 'TDY': 'Electronic Equipment & Instruments', 'TER': 'Semiconductor Materials & Equipment', 'TSLA': 'Automobile Manufacturers',
    'TXN': 'Semiconductors', 'TPL': 'Oil & Gas Exploration & Production', 'TXT': 'Aerospace & Defense', 'TMO': 'Life Sciences Tools & Services',
    'TJX': 'Apparel Retail', 'TKO': 'Movies & Entertainment', 'TTD': 'Advertising', 'TSCO': 'Other Specialty Retail',
    'TT': 'Building Products', 'TDG': 'Aerospace & Defense', 'TRV': 'Property & Casualty Insurance', 'TRMB': 'Application Software',
    'TFC': 'Diversified Banks', 'TYL': 'Application Software', 'TSN': 'Packaged Foods & Meats', 'USB': 'Diversified Banks',
    'UBER': 'Passenger Ground Transportation', 'UDR': 'Multi-Family Residential REITs', 'ULTA': 'Other Specialty Retail', 'UNP': 'Rail Transportation',
    'UAL': 'Passenger Airlines', 'UPS': 'Air Freight & Logistics', 'URI': 'Trading Companies & Distributors', 'UNH': 'Managed Health Care',
    'UHS': 'Health Care Facilities', 'VLO': 'Oil & Gas Refining & Marketing', 'VTR': 'Health Care REITs', 'VLTO': 'Environmental & Facilities Services',
    'VRSN': 'Internet Services & Infrastructure', 'VRSK': 'Research & Consulting Services', 'VZ': 'Integrated Telecommunication Services', 'VRTX': 'Biotechnology',
    'VRT': 'Electrical Components & Equipment', 'VTRS': 'Pharmaceuticals', 'VICI': 'Hotel & Resort REITs', 'V': 'Transaction & Payment Processing Services',
    'VST': 'Electric Utilities', 'VMC': 'Construction Materials', 'WRB': 'Property & Casualty Insurance', 'GWW': 'Industrial Machinery & Supplies & Components',
    'WAB': 'Construction Machinery & Heavy Transportation Equipment', 'WMT': 'Consumer Staples Merchandise Retail', 'DIS': 'Movies & Entertainment', 'WBD': 'Broadcasting',
    'WM': 'Environmental & Facilities Services', 'WAT': 'Life Sciences Tools & Services', 'WEC': 'Electric Utilities', 'WFC': 'Diversified Banks',
    'WELL': 'Health Care REITs', 'WST': 'Health Care Supplies', 'WDC': 'Technology Hardware, Storage & Peripherals', 'WY': 'Timber REITs',
    'WSM': 'Homefurnishing Retail', 'WMB': 'Oil & Gas Storage & Transportation', 'WTW': 'Insurance Brokers', 'WDAY': 'Application Software',
    'WYNN': 'Casinos & Gaming', 'XEL': 'Multi-Utilities', 'XYL': 'Industrial Machinery & Supplies & Components', 'YUM': 'Restaurants',
    'ZBRA': 'Electronic Equipment & Instruments', 'ZBH': 'Health Care Equipment', 'ZTS': 'Pharmaceuticals',
}

INDEX_SYMBOLS = ['NQ1!', 'ES1!', 'NI225']

# 先物・指数タブに表示する銘柄（3色判定：緑=上昇 / 黄=レンジ / 赤=下降）
FUTURES_INDEX_SET = frozenset(['NQ1!', 'ES1!', 'SPY', 'RSP', 'DIA', 'QQQ', 'QQQE', 'IWM', 'VTI', 'VT'])

# NASDAQ100構成銘柄（2026年6月時点、slickcharts.com 公開リストより。
# 2026年1月20日のリバランスでAZNがWMTに置換済み。GOOGとGOOGLの両方を含むため101銘柄。)
NASDAQ100_SYMBOLS = [
    'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'GOOG', 'AVGO', 'META', 'TSLA', 'MU',
    'WMT', 'AMD', 'ASML', 'INTC', 'CSCO', 'COST', 'LRCX', 'ARM', 'AMAT', 'NFLX',
    'PLTR', 'TXN', 'KLAC', 'LIN', 'SNDK', 'MRVL', 'QCOM', 'PANW', 'ADI', 'PEP',
    'TMUS', 'STX', 'AMGN', 'APP', 'WDC', 'CRWD', 'GILD', 'ISRG', 'SHOP', 'HON',
    'BKNG', 'PDD', 'VRTX', 'SBUX', 'FTNT', 'CDNS', 'MAR', 'ADBE', 'ADP', 'CEG',
    'SNPS', 'MNST', 'CSX', 'CMCSA', 'DDOG', 'MELI', 'INTU', 'MDLZ', 'ABNB', 'ORLY',
    'NXPI', 'ROST', 'MPWR', 'CTAS', 'AEP', 'DASH', 'LITE', 'REGN', 'WBD', 'BKR',
    'PCAR', 'FANG', 'FAST', 'EA', 'ODFL', 'XEL', 'ADSK', 'MCHP', 'FER', 'EXC',
    'IDXX', 'MSTR', 'CCEP', 'KDP', 'ALNY', 'TTWO', 'AXON', 'TRI', 'PYPL', 'PAYX',
    'WDAY', 'ROP', 'GEHC', 'CPRT', 'DXCM', 'KHC', 'CTSH', 'VRSK', 'ZS', 'INSM',
    'CHTR',
]

# NASDAQ100にあってS&P500にない銘柄のセクター情報のみここに定義
# S&P500と重複する銘柄は SP500_SECTOR_MAP から取得する（後述の get_sector ヘルパー参照）
NASDAQ100_SECTOR_MAP = {
    'ARM':  'Semiconductors',
    'ASML': 'Semiconductor Materials & Equipment',
    'CCEP': 'Soft Drinks & Non-alcoholic Beverages',
    'MRVL': 'Semiconductors',
    'MELI': 'Broadline Retail',
    'MSTR': 'Application Software',
    'PDD':  'Broadline Retail',
    'SHOP': 'Application Software',
    'ZS':   'Systems Software',
    'ALNY': 'Biotechnology',
    'INSM': 'Biotechnology',
    'FER':  'Construction & Engineering',
    'TRI':  'Research & Consulting Services',
}


def get_sector(sym):
    """シンボルのセクター情報を取得する（為替・ETF・SP500 → NASDAQ100追加分 → 日経225 の順で参照）。"""
    if sym in FOREX_NAMES:
        return FOREX_NAMES[sym]
    if sym in ETF_SECTOR_MAP:
        return ETF_SECTOR_MAP[sym]
    return (SP500_SECTOR_MAP.get(sym)
            or NASDAQ100_SECTOR_MAP.get(sym)
            or NIKKEI225_SECTOR_MAP.get(sym)
            or '')


# 日経225構成銘柄（2026年6月4日時点・公式の日経平均プロフィルより）
NIKKEI225_SYMBOLS = [
    # 医薬品 (9)
    "TSE:4151", "TSE:4502", "TSE:4503", "TSE:4506", "TSE:4507",
    "TSE:4519", "TSE:4523", "TSE:4568", "TSE:4578",
    # 電気機器 (32)
    "TSE:285A", "TSE:4062", "TSE:6479", "TSE:6501", "TSE:6503",
    "TSE:6504", "TSE:6506", "TSE:6526", "TSE:6645", "TSE:6701",
    "TSE:6702", "TSE:6723", "TSE:6724", "TSE:6752", "TSE:6753",
    "TSE:6758", "TSE:6762", "TSE:6770", "TSE:6841", "TSE:6857",
    "TSE:6861", "TSE:6902", "TSE:6920", "TSE:6954", "TSE:6963",
    "TSE:6971", "TSE:6976", "TSE:6981", "TSE:7735", "TSE:7751",
    "TSE:7752", "TSE:8035",
    # 自動車 (10)
    "TSE:543A", "TSE:7201", "TSE:7202", "TSE:7203", "TSE:7211",
    "TSE:7261", "TSE:7267", "TSE:7269", "TSE:7270", "TSE:7272",
    # 精密機器 (6)
    "TSE:4543", "TSE:4902", "TSE:6146", "TSE:7731", "TSE:7733",
    "TSE:7741",
    # 通信 (4)
    "TSE:9432", "TSE:9433", "TSE:9434", "TSE:9984",
    # 銀行 (10)
    "TSE:5831", "TSE:7186", "TSE:8304", "TSE:8306", "TSE:8308",
    "TSE:8309", "TSE:8316", "TSE:8331", "TSE:8354", "TSE:8411",
    # その他金融 (3)
    "TSE:8253", "TSE:8591", "TSE:8697",
    # 証券 (2)
    "TSE:8601", "TSE:8604",
    # 保険 (5)
    "TSE:8630", "TSE:8725", "TSE:8750", "TSE:8766", "TSE:8795",
    # 水産 (1)
    "TSE:1332",
    # 食品 (10)
    "TSE:2002", "TSE:2269", "TSE:2282", "TSE:2501", "TSE:2502",
    "TSE:2503", "TSE:2801", "TSE:2802", "TSE:2871", "TSE:2914",
    # 小売業 (11)
    "TSE:3086", "TSE:3092", "TSE:3099", "TSE:3382", "TSE:7453",
    "TSE:7532", "TSE:8233", "TSE:8252", "TSE:8267", "TSE:9843",
    "TSE:9983",
    # サービス (19)
    "TSE:2413", "TSE:2432", "TSE:3659", "TSE:3697", "TSE:4307",
    "TSE:4324", "TSE:4385", "TSE:4661", "TSE:4689", "TSE:4704",
    "TSE:4751", "TSE:4755", "TSE:6098", "TSE:6178", "TSE:6532",
    "TSE:7974", "TSE:9602", "TSE:9735", "TSE:9766",
    # 鉱業 (1)
    "TSE:1605",
    # 繊維 (2)
    "TSE:3401", "TSE:3402",
    # パルプ・紙 (1)
    "TSE:3861",
    # 化学 (16)
    "TSE:3405", "TSE:3407", "TSE:4004", "TSE:4005", "TSE:4021",
    "TSE:4042", "TSE:4043", "TSE:4061", "TSE:4063", "TSE:4183",
    "TSE:4188", "TSE:4208", "TSE:4452", "TSE:4901", "TSE:4911",
    "TSE:6988",
    # 石油 (2)
    "TSE:5019", "TSE:5020",
    # ゴム (2)
    "TSE:5101", "TSE:5108",
    # 窯業 (6)
    "TSE:5201", "TSE:5214", "TSE:5233", "TSE:5301", "TSE:5332",
    "TSE:5333",
    # 鉄鋼 (3)
    "TSE:5401", "TSE:5406", "TSE:5411",
    # 非鉄・金属 (8)
    "TSE:3436", "TSE:5706", "TSE:5711", "TSE:5713", "TSE:5714",
    "TSE:5801", "TSE:5802", "TSE:5803",
    # 商社 (7)
    "TSE:2768", "TSE:8001", "TSE:8002", "TSE:8015", "TSE:8031",
    "TSE:8053", "TSE:8058",
    # 建設 (9)
    "TSE:1721", "TSE:1801", "TSE:1802", "TSE:1803", "TSE:1808",
    "TSE:1812", "TSE:1925", "TSE:1928", "TSE:1963",
    # 機械 (16)
    "TSE:5631", "TSE:6103", "TSE:6113", "TSE:6273", "TSE:6301",
    "TSE:6302", "TSE:6305", "TSE:6326", "TSE:6361", "TSE:6367",
    "TSE:6471", "TSE:6472", "TSE:6473", "TSE:7004", "TSE:7011",
    "TSE:7013",
    # 造船 (1)
    "TSE:7012",
    # その他製造 (4)
    "TSE:7832", "TSE:7911", "TSE:7912", "TSE:7951",
    # 不動産 (5)
    "TSE:3289", "TSE:8801", "TSE:8802", "TSE:8804", "TSE:8830",
    # 鉄道・バス (8)
    "TSE:9001", "TSE:9005", "TSE:9007", "TSE:9008", "TSE:9009",
    "TSE:9020", "TSE:9021", "TSE:9022",
    # 陸運 (2)
    "TSE:9064", "TSE:9147",
    # 海運 (3)
    "TSE:9101", "TSE:9104", "TSE:9107",
    # 空運 (2)
    "TSE:9201", "TSE:9202",
    # 電力 (3)
    "TSE:9501", "TSE:9502", "TSE:9503",
    # ガス (2)
    "TSE:9531", "TSE:9532",
]

# 日経225のセクター（業種）マップ（公式分類）
NIKKEI225_SECTOR_MAP = {
    "TSE:4151": "医薬品", "TSE:4502": "医薬品", "TSE:4503": "医薬品", "TSE:4506": "医薬品", "TSE:4507": "医薬品",
    "TSE:4519": "医薬品", "TSE:4523": "医薬品", "TSE:4568": "医薬品", "TSE:4578": "医薬品",
    "TSE:285A": "電気機器", "TSE:4062": "電気機器", "TSE:6479": "電気機器", "TSE:6501": "電気機器", "TSE:6503": "電気機器",
    "TSE:6504": "電気機器", "TSE:6506": "電気機器", "TSE:6526": "電気機器", "TSE:6645": "電気機器", "TSE:6701": "電気機器",
    "TSE:6702": "電気機器", "TSE:6723": "電気機器", "TSE:6724": "電気機器", "TSE:6752": "電気機器", "TSE:6753": "電気機器",
    "TSE:6758": "電気機器", "TSE:6762": "電気機器", "TSE:6770": "電気機器", "TSE:6841": "電気機器", "TSE:6857": "電気機器",
    "TSE:6861": "電気機器", "TSE:6902": "電気機器", "TSE:6920": "電気機器", "TSE:6954": "電気機器", "TSE:6963": "電気機器",
    "TSE:6971": "電気機器", "TSE:6976": "電気機器", "TSE:6981": "電気機器", "TSE:7735": "電気機器", "TSE:7751": "電気機器",
    "TSE:7752": "電気機器", "TSE:8035": "電気機器",
    "TSE:543A": "自動車", "TSE:7201": "自動車", "TSE:7202": "自動車", "TSE:7203": "自動車", "TSE:7211": "自動車",
    "TSE:7261": "自動車", "TSE:7267": "自動車", "TSE:7269": "自動車", "TSE:7270": "自動車", "TSE:7272": "自動車",
    "TSE:4543": "精密機器", "TSE:4902": "精密機器", "TSE:6146": "精密機器", "TSE:7731": "精密機器", "TSE:7733": "精密機器",
    "TSE:7741": "精密機器",
    "TSE:9432": "通信", "TSE:9433": "通信", "TSE:9434": "通信", "TSE:9984": "通信",
    "TSE:5831": "銀行", "TSE:7186": "銀行", "TSE:8304": "銀行", "TSE:8306": "銀行", "TSE:8308": "銀行",
    "TSE:8309": "銀行", "TSE:8316": "銀行", "TSE:8331": "銀行", "TSE:8354": "銀行", "TSE:8411": "銀行",
    "TSE:8253": "その他金融", "TSE:8591": "その他金融", "TSE:8697": "その他金融",
    "TSE:8601": "証券", "TSE:8604": "証券",
    "TSE:8630": "保険", "TSE:8725": "保険", "TSE:8750": "保険", "TSE:8766": "保険", "TSE:8795": "保険",
    "TSE:1332": "水産",
    "TSE:2002": "食品", "TSE:2269": "食品", "TSE:2282": "食品", "TSE:2501": "食品", "TSE:2502": "食品",
    "TSE:2503": "食品", "TSE:2801": "食品", "TSE:2802": "食品", "TSE:2871": "食品", "TSE:2914": "食品",
    "TSE:3086": "小売業", "TSE:3092": "小売業", "TSE:3099": "小売業", "TSE:3382": "小売業", "TSE:7453": "小売業",
    "TSE:7532": "小売業", "TSE:8233": "小売業", "TSE:8252": "小売業", "TSE:8267": "小売業", "TSE:9843": "小売業",
    "TSE:9983": "小売業",
    "TSE:2413": "サービス", "TSE:2432": "サービス", "TSE:3659": "サービス", "TSE:3697": "サービス", "TSE:4307": "サービス",
    "TSE:4324": "サービス", "TSE:4385": "サービス", "TSE:4661": "サービス", "TSE:4689": "サービス", "TSE:4704": "サービス",
    "TSE:4751": "サービス", "TSE:4755": "サービス", "TSE:6098": "サービス", "TSE:6178": "サービス", "TSE:6532": "サービス",
    "TSE:7974": "サービス", "TSE:9602": "サービス", "TSE:9735": "サービス", "TSE:9766": "サービス",
    "TSE:1605": "鉱業",
    "TSE:3401": "繊維", "TSE:3402": "繊維",
    "TSE:3861": "パルプ・紙",
    "TSE:3405": "化学", "TSE:3407": "化学", "TSE:4004": "化学", "TSE:4005": "化学", "TSE:4021": "化学",
    "TSE:4042": "化学", "TSE:4043": "化学", "TSE:4061": "化学", "TSE:4063": "化学", "TSE:4183": "化学",
    "TSE:4188": "化学", "TSE:4208": "化学", "TSE:4452": "化学", "TSE:4901": "化学", "TSE:4911": "化学",
    "TSE:6988": "化学",
    "TSE:5019": "石油", "TSE:5020": "石油",
    "TSE:5101": "ゴム", "TSE:5108": "ゴム",
    "TSE:5201": "窯業", "TSE:5214": "窯業", "TSE:5233": "窯業", "TSE:5301": "窯業", "TSE:5332": "窯業",
    "TSE:5333": "窯業",
    "TSE:5401": "鉄鋼", "TSE:5406": "鉄鋼", "TSE:5411": "鉄鋼",
    "TSE:3436": "非鉄・金属", "TSE:5706": "非鉄・金属", "TSE:5711": "非鉄・金属", "TSE:5713": "非鉄・金属", "TSE:5714": "非鉄・金属",
    "TSE:5801": "非鉄・金属", "TSE:5802": "非鉄・金属", "TSE:5803": "非鉄・金属",
    "TSE:2768": "商社", "TSE:8001": "商社", "TSE:8002": "商社", "TSE:8015": "商社", "TSE:8031": "商社",
    "TSE:8053": "商社", "TSE:8058": "商社",
    "TSE:1721": "建設", "TSE:1801": "建設", "TSE:1802": "建設", "TSE:1803": "建設", "TSE:1808": "建設",
    "TSE:1812": "建設", "TSE:1925": "建設", "TSE:1928": "建設", "TSE:1963": "建設",
    "TSE:5631": "機械", "TSE:6103": "機械", "TSE:6113": "機械", "TSE:6273": "機械", "TSE:6301": "機械",
    "TSE:6302": "機械", "TSE:6305": "機械", "TSE:6326": "機械", "TSE:6361": "機械", "TSE:6367": "機械",
    "TSE:6471": "機械", "TSE:6472": "機械", "TSE:6473": "機械", "TSE:7004": "機械", "TSE:7011": "機械",
    "TSE:7013": "機械",
    "TSE:7012": "造船",
    "TSE:7832": "その他製造", "TSE:7911": "その他製造", "TSE:7912": "その他製造", "TSE:7951": "その他製造",
    "TSE:3289": "不動産", "TSE:8801": "不動産", "TSE:8802": "不動産", "TSE:8804": "不動産", "TSE:8830": "不動産",
    "TSE:9001": "鉄道・バス", "TSE:9005": "鉄道・バス", "TSE:9007": "鉄道・バス", "TSE:9008": "鉄道・バス", "TSE:9009": "鉄道・バス",
    "TSE:9020": "鉄道・バス", "TSE:9021": "鉄道・バス", "TSE:9022": "鉄道・バス",
    "TSE:9064": "陸運", "TSE:9147": "陸運",
    "TSE:9101": "海運", "TSE:9104": "海運", "TSE:9107": "海運",
    "TSE:9201": "空運", "TSE:9202": "空運",
    "TSE:9501": "電力", "TSE:9502": "電力", "TSE:9503": "電力",
    "TSE:9531": "ガス", "TSE:9532": "ガス",
}


def _cached_json(payload, max_age=1800):
    """Cache-Control: private, max-age=XXX を付けた JSON レスポンスを返す。"""
    resp = jsonify(payload)
    # private: 各ユーザーのブラウザにのみキャッシュ。CDNなどには保存しない。
    resp.headers['Cache-Control'] = f'private, max-age={max_age}'
    return resp


def is_jp_symbol(sym):
    """日経225銘柄か判定する。'TSE:XXXX' 形式。"""
    return isinstance(sym, str) and sym.startswith('TSE:')


# ===== 色判定（フロントには露出させない内部ロジック）=====
# スコアから色を判定する関数。閾値はサーバー側だけが知っている。
# フロントへは color 文字列（'blue'|'green'|'yellow'|'red'|None）のみ返す。
_SCORE_COLOR_THRESHOLDS = (7, 0, -7)  # 内部閾値
def score_to_color(score):
    """スコアから色を判定。フロントには露出させない。"""
    if score is None:
        return None
    try:
        s = float(score)
    except (TypeError, ValueError):
        return None
    if s >= _SCORE_COLOR_THRESHOLDS[0]:
        return 'blue'
    if s > _SCORE_COLOR_THRESHOLDS[1]:
        return 'green'
    if s <= _SCORE_COLOR_THRESHOLDS[2]:
        return 'yellow'
    return 'red'


def jp_to_yfinance(sym):
    """'TSE:7203' → '7203.T'（yfinanceの日本株表記）"""
    if not is_jp_symbol(sym):
        return sym
    return sym.split(':', 1)[1] + '.T'

CALC_PERIOD = 'max'
DISPLAY_PERIOD = 90
BG_COLOR = '#131722'
TEXT_COLOR = 'white'
GRID_COLOR = '#444444'
CACHE_SECONDS = 86400  # 24時間（プリフェッチ前提のため長め）

# プリフェッチ用トークン（外部cronからの呼び出しを保護）
PREFETCH_TOKEN = os.environ.get('PREFETCH_TOKEN', '')

# 永続キャッシュのGitHub URL（GitHub Actions が毎朝ここを更新する）
PERSISTENT_CACHE_URL = 'https://raw.githubusercontent.com/toreken/trekken/main/cache/cache.json'

chart_cache = {}
thumb_cache = {}     # サムネイル画像とスコアのキャッシュ {symbol: (time, {'thumb': b64, 'score': float})}


def get_wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def fetch_and_calculate(symbol, period='max', max_retries=3):
    """yfinanceでデータ取得＆スコア計算。失敗時は指数バックオフで最大3回リトライ。
    YFRateLimitErrorは長めに待ってからリトライ。"""
    df = None
    for attempt in range(max_retries):
        try:
            df_dl = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=False)
            if isinstance(df_dl.columns, pd.MultiIndex):
                df_dl.columns = df_dl.columns.get_level_values(0)
            df_dl.columns = df_dl.columns.str.lower()
            df_dl = df_dl.loc[:, ~df_dl.columns.duplicated()].copy()
            if df_dl.index.tz is not None:
                df_dl.index = df_dl.index.tz_localize(None)
            if df_dl.empty or len(df_dl) < 2:
                if attempt < max_retries - 1:
                    time.sleep(5 * (2 ** attempt))  # 5, 10, 20秒
                    continue
                return None
            if 'close' not in df_dl.columns:
                if 'adj close' in df_dl.columns:
                    df_dl['close'] = df_dl['adj close']
                else:
                    if attempt < max_retries - 1:
                        time.sleep(5 * (2 ** attempt))
                        continue
                    return None
            df = df_dl
            break
        except Exception as e:
            err_str = str(e)
            # YFRateLimitErrorは長めの待機（30秒、60秒、120秒）
            is_rate_limit = 'RateLimit' in err_str or 'Too Many Requests' in err_str
            wait = 30 * (2 ** attempt) if is_rate_limit else 5 * (2 ** attempt)
            if attempt < max_retries - 1:
                print(f"fetch_and_calculate({symbol}) attempt {attempt+1} failed: {e}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"fetch_and_calculate({symbol}) failed after {max_retries} retries: {e}")
            return None
    if df is None:
        return None

    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['prev_close'] = df['close'].shift(1)
    df['uvol'] = np.where(df['close'] > df['prev_close'], df['volume'], 0)
    df['dvol'] = np.where(df['close'] < df['prev_close'], df['volume'], 0)
    df['total_uvol_sma'] = get_wma(df['uvol'], 10)
    df['total_dvol_sma'] = get_wma(df['dvol'], 10)
    df['discrepancyPercent'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100
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


# 暗号通貨のティッカー対応表（サイト表示名 → TradingViewでのティッカーと取引所）
CRYPTO_MAP = {
    'BTC':   ('BTCUSDT',  'BINANCE'),
    'ETH':   ('ETHUSDT',  'BINANCE'),
    'SOL':   ('SOLUSDT',  'BINANCE'),
    'XRP':   ('XRPUSDT',  'BINANCE'),
    'ADA':   ('ADAUSDT',  'BINANCE'),
    'DOGE':  ('DOGEUSDT', 'BINANCE'),
    'AVAX':  ('AVAXUSDT', 'BINANCE'),
    'LINK':  ('LINKUSDT', 'BINANCE'),
    'MATIC': ('POLUSDT',  'BINANCE'),
    'ATOMC': ('ATOMUSDT', 'BINANCE'),
}


# ===== 為替（FX）ペア =====
FOREX_PAIRS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD',
    'EURJPY', 'GBPJPY', 'AUDJPY', 'EURGBP',
]

FOREX_NAMES = {
    'EURUSD': 'ユーロ/米ドル',
    'GBPUSD': 'ポンド/米ドル',
    'USDJPY': '米ドル/円',
    'USDCHF': '米ドル/スイスフラン',
    'AUDUSD': '豪ドル/米ドル',
    'NZDUSD': 'NZドル/米ドル',
    'USDCAD': '米ドル/カナダドル',
    'EURJPY': 'ユーロ/円',
    'GBPJPY': 'ポンド/円',
    'AUDJPY': '豪ドル/円',
    'EURGBP': 'ユーロ/ポンド',
}


# ===== ETF（セクター別 + 高配当） =====
ETF_SECTOR_MAP = {
    # テクノロジー
    'XLK': 'テクノロジー(SPDR)', 'VGT': 'テクノロジー(Vanguard)', 'IYW': 'テクノロジー(iShares)',
    # ヘルスケア
    'XLV': 'ヘルスケア(SPDR)', 'VHT': 'ヘルスケア(Vanguard)', 'IYH': 'ヘルスケア(iShares)',
    # 金融
    'XLF': '金融(SPDR)', 'VFH': '金融(Vanguard)', 'IYF': '金融(iShares)',
    # エネルギー
    'XLE': 'エネルギー(SPDR)', 'VDE': 'エネルギー(Vanguard)', 'IYE': 'エネルギー(iShares)',
    # 一般消費財
    'XLY': '一般消費財(SPDR)', 'VCR': '一般消費財(Vanguard)', 'IYC': '一般消費財(iShares)',
    # 生活必需品
    'XLP': '生活必需品(SPDR)', 'VDC': '生活必需品(Vanguard)', 'IYK': '生活必需品(iShares)',
    # 資本財
    'XLI': '資本財(SPDR)', 'VIS': '資本財(Vanguard)', 'IYJ': '資本財(iShares)',
    # 素材
    'XLB': '素材(SPDR)', 'VAW': '素材(Vanguard)', 'IYM': '素材(iShares)',
    # 公益事業
    'XLU': '公益事業(SPDR)', 'VPU': '公益事業(Vanguard)', 'IDU': '公益事業(iShares)',
    # 不動産
    'XLRE': '不動産(SPDR)', 'VNQ': '不動産(Vanguard)', 'IYR': '不動産(iShares)',
    # 通信サービス
    'XLC': '通信サービス(SPDR)', 'VOX': '通信サービス(Vanguard)', 'IYZ': '通信サービス(iShares)',
    # 高配当
    'VYM': '高配当(Vanguard)', 'HDV': '高配当(iShares Core)',
    'SPYD': '高配当(SPDR S&P 500)', 'VIG': '配当成長(Vanguard)',
}


def fetch_forex(symbol_key, period=CALC_PERIOD):
    """yfinanceで為替ペアを取得しスコア計算する。
    symbol_key は 'EURUSD' 'USDJPY' 形式、内部で 'EURUSD=X' に変換する。
    為替には出来高がないため volDiffScore は実質ゼロ、20EMA乖離（discrepancyScore）が中心。
    """
    if symbol_key not in FOREX_PAIRS:
        return None
    yf_sym = symbol_key + '=X'
    try:
        ticker = yf.Ticker(yf_sym)
        df_raw = ticker.history(period=period)
        if df_raw is None or df_raw.empty:
            return None
        df = df_raw.rename(columns={'Open': 'open', 'High': 'high',
                                    'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        # 為替のvolumeは0またはNaNなので0に統一
        if 'volume' not in df.columns:
            df['volume'] = 0
        df['volume'] = df['volume'].fillna(0)
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.index = pd.to_datetime(df.index).tz_localize(None) if df.index.tz else pd.to_datetime(df.index)
        df.index = df.index.normalize()

        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['prev_close'] = df['close'].shift(1)
        df['uvol'] = np.where(df['close'] > df['prev_close'], df['volume'], 0)
        df['dvol'] = np.where(df['close'] < df['prev_close'], df['volume'], 0)
        df['total_uvol_sma'] = get_wma(df['uvol'], 10)
        df['total_dvol_sma'] = get_wma(df['dvol'], 10)
        df['discrepancyPercent'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100
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
    except Exception as e:
        print(f"{symbol_key} (forex) error: {e}")
        return None


def fetch_crypto(symbol_key, n_bars=1000):
    """tvDatafeedで暗号通貨を取得し、個別株と同じスコア計算を適用する。失敗時は最大3回リトライ。"""
    tv_local = get_tv()
    if tv_local is None:
        return None
    Interval = get_interval()
    if Interval is None:
        return None
    if symbol_key not in CRYPTO_MAP:
        return None
    tv_symbol, tv_exchange = CRYPTO_MAP[symbol_key]
    df_raw = None
    for attempt in range(3):
        try:
            df_raw = tv_local.get_hist(symbol=tv_symbol, exchange=tv_exchange,
                                       interval=Interval.in_daily, n_bars=n_bars)
            if df_raw is None or df_raw.empty:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return None
            break
        except Exception as e:
            if attempt < 2:
                print(f"fetch_crypto({symbol_key}) attempt {attempt+1} failed: {e}, retrying...")
                time.sleep(2 ** attempt)
                continue
            print(f"fetch_crypto({symbol_key}) failed after 3 retries: {e}")
            return None
    if df_raw is None:
        return None
    try:

        df = df_raw.rename(columns={'open':'open','high':'high','low':'low',
                                    'close':'close','volume':'volume'})
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.index = pd.to_datetime(df.index).normalize().tz_localize(None)

        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['prev_close'] = df['close'].shift(1)
        df['uvol'] = np.where(df['close'] > df['prev_close'], df['volume'], 0)
        df['dvol'] = np.where(df['close'] < df['prev_close'], df['volume'], 0)
        df['total_uvol_sma'] = get_wma(df['uvol'], 10)
        df['total_dvol_sma'] = get_wma(df['dvol'], 10)
        df['discrepancyPercent'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100
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
    except Exception as e:
        print(f"{symbol_key} (crypto) error: {e}")
        return None


def fetch_jp(symbol_key, n_bars=1000):
    """tvDatafeedで日経225銘柄を取得し、個別株と同じスコア計算を適用する。
    symbol_key は 'TSE:7203' 形式。失敗時は最大3回リトライ。
    """
    tv_local = get_tv()
    if tv_local is None:
        return None
    Interval = get_interval()
    if Interval is None:
        return None
    if not is_jp_symbol(symbol_key):
        return None
    parts = symbol_key.split(':', 1)
    if len(parts) != 2:
        return None
    tv_exchange, tv_symbol = parts[0], parts[1]
    df_raw = None
    for attempt in range(3):
        try:
            df_raw = tv_local.get_hist(symbol=tv_symbol, exchange=tv_exchange,
                                       interval=Interval.in_daily, n_bars=n_bars)
            if df_raw is None or df_raw.empty:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return None
            break
        except Exception as e:
            if attempt < 2:
                print(f"fetch_jp({symbol_key}) attempt {attempt+1} failed: {e}, retrying...")
                time.sleep(2 ** attempt)
                continue
            print(f"fetch_jp({symbol_key}) failed after 3 retries: {e}")
            return None
    if df_raw is None:
        return None
    try:

        df = df_raw.rename(columns={'open':'open','high':'high','low':'low',
                                    'close':'close','volume':'volume'})
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.index = pd.to_datetime(df.index).normalize().tz_localize(None)

        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['prev_close'] = df['close'].shift(1)
        df['uvol'] = np.where(df['close'] > df['prev_close'], df['volume'], 0)
        df['dvol'] = np.where(df['close'] < df['prev_close'], df['volume'], 0)
        df['total_uvol_sma'] = get_wma(df['uvol'], 10)
        df['total_dvol_sma'] = get_wma(df['dvol'], 10)
        df['discrepancyPercent'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100
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
    except Exception as e:
        print(f"{symbol_key} (jp) error: {e}")
        return None


def fetch_nq1(n_bars=1000):
    tv_local = get_tv()
    if tv_local is None:
        return None
    Interval = get_interval()
    if Interval is None:
        return None
    try:
        df_qqq = tv_local.get_hist(symbol='QQQ', exchange='NASDAQ', interval=Interval.in_daily, n_bars=n_bars)
        df_ndtw = tv_local.get_hist(symbol='NDTW', exchange='INDEX', interval=Interval.in_daily, n_bars=n_bars)
        df_ndfi = tv_local.get_hist(symbol='NDFI', exchange='INDEX', interval=Interval.in_daily, n_bars=n_bars)
        df_ndth = tv_local.get_hist(symbol='NDTH', exchange='INDEX', interval=Interval.in_daily, n_bars=n_bars)
        df_uvol = tv_local.get_hist(symbol='UVOLQ', exchange='USI', interval=Interval.in_daily, n_bars=n_bars)
        df_dvol = tv_local.get_hist(symbol='DVOLQ', exchange='USI', interval=Interval.in_daily, n_bars=n_bars)
        df_chart = tv_local.get_hist(symbol='NQ1!', exchange='CME_MINI', interval=Interval.in_daily, n_bars=n_bars)

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


def fetch_es1(n_bars=1000):
    tv_local = get_tv()
    if tv_local is None:
        return None
    Interval = get_interval()
    if Interval is None:
        return None
    try:
        df_spy = tv_local.get_hist(symbol='SPY', exchange='AMEX', interval=Interval.in_daily, n_bars=n_bars)
        if df_spy is None:
            df_spy = tv_local.get_hist(symbol='SPY', exchange='ARCA', interval=Interval.in_daily, n_bars=n_bars)

        df_ndtw = tv_local.get_hist(symbol='NDTW', exchange='INDEX', interval=Interval.in_daily, n_bars=n_bars)
        if df_ndtw is None:
            df_ndtw = tv_local.get_hist(symbol='NDTW', exchange='NASDAQ', interval=Interval.in_daily, n_bars=n_bars)

        df_ndfi = tv_local.get_hist(symbol='NDFI', exchange='INDEX', interval=Interval.in_daily, n_bars=n_bars)
        if df_ndfi is None:
            df_ndfi = tv_local.get_hist(symbol='NDFI', exchange='NASDAQ', interval=Interval.in_daily, n_bars=n_bars)

        df_ndth = tv_local.get_hist(symbol='NDTH', exchange='INDEX', interval=Interval.in_daily, n_bars=n_bars)
        if df_ndth is None:
            df_ndth = tv_local.get_hist(symbol='NDTH', exchange='NASDAQ', interval=Interval.in_daily, n_bars=n_bars)

        df_uvol = tv_local.get_hist(symbol='UVOLQ', exchange='USI', interval=Interval.in_daily, n_bars=n_bars)
        df_dvol = tv_local.get_hist(symbol='DVOLQ', exchange='USI', interval=Interval.in_daily, n_bars=n_bars)
        df_chart = tv_local.get_hist(symbol='ES1!', exchange='CME_MINI', interval=Interval.in_daily, n_bars=n_bars)

        if any(x is None or x.empty for x in [df_spy, df_ndtw, df_ndfi, df_ndth, df_uvol, df_dvol, df_chart]):
            return None

        df = df_spy.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
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

        df['SPYSMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['ndtwScore'] = df['ndtw'] / 3
        df['ndfiScore'] = df['ndfi'] / 4
        df['ndthScore'] = df['ndth'] / 6
        df['discrepancyPercent'] = (df['Close'] - df['SPYSMA20']) / df['SPYSMA20'] * 100
        df['discrepancyScore'] = df['discrepancyPercent'] * 3
        df['uVolSMA10'] = df['uVol'].rolling(window=10).mean()
        df['dVolSMA10'] = df['dVol'].rolling(window=10).mean()
        df['volDiff'] = df['uVolSMA10'] - df['dVolSMA10']
        df['volDiffScore'] = df['volDiff'] / 50000000
        df['totalScore'] = df['ndtwScore'] + df['ndfiScore'] + df['ndthScore'] + df['discrepancyScore'] + df['volDiffScore']
        df['isAboveEMA20'] = df['Close'] > df['SPYSMA20']

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
        print(f"ES1! error: {e}")
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

    fig = plt.figure(figsize=(12, 7), facecolor=BG_COLOR)
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
    ax_main.set_title(f"{symbol} (Score: {int(current_score):+d})", fontsize=20, loc='center', pad=15, color=TEXT_COLOR)
    ax_main.xaxis.grid(False)
    xmin, xmax = ax_main.get_xlim()
    ax_main.set_xlim(xmin, xmax + 5)

    # 先物・指数タブ銘柄は3色判定、その他は4色判定
    is_futures = symbol in FUTURES_INDEX_SET

    for j in range(len(plot_df)):
        row = plot_df.iloc[j]
        score = row['totalScore']
        if pd.isna(score):
            c = '#888888'
        elif is_futures:
            # 先物・指数：score>40 & close>ema20 で青、score<=40 & close<ema20 で赤、それ以外は黄
            close_v = row['close']
            ema20_v = row.get('ema_20') if hasattr(row, 'get') else (row['ema_20'] if 'ema_20' in row.index else None)
            if ema20_v is None or pd.isna(ema20_v):
                c = '#ffd700'  # EMA20 未確定は黄
            elif score > 40 and close_v > ema20_v:
                c = '#00bfff'  # 青：上昇トレンド
            elif score <= 40 and close_v < ema20_v:
                c = '#ff4444'  # 赤：下降トレンド
            else:
                c = '#ffd700'  # 黄：レンジ
        else:
            # その他：4色（青/緑/赤/黄）
            if score >= 7:    c = '#00bfff'
            elif score > 0:   c = '#32cd32'
            elif score <= -7: c = '#ffd700'
            else:             c = '#ff4444'
        ax_main.plot([j, j], [row['low'], row['high']], color=c, linewidth=1.5, zorder=10)
        body_bottom = min(row['open'], row['close'])
        body_height = max(abs(row['open'] - row['close']), row['close'] * 0.0005)
        rect = Rectangle((j - 0.35, body_bottom), 0.7, body_height, facecolor=c, edgecolor=c, zorder=10)
        ax_main.add_patch(rect)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight', dpi=80)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_b64


def make_chart_image_nq(df, symbol):
    """NQ1!/ES1! 用のチャート画像生成。大文字カラム(Open/High/Low/Close)と
    candle_color 列を使う。スコアによる色分けは fetch_nq1 / fetch_es1 が付与済み。"""
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

    fig = plt.figure(figsize=(12, 7), facecolor=BG_COLOR)
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
    ax_main.set_title(f"{symbol} (Score: {int(current_score):+d})", fontsize=20, loc='center', pad=15, color=TEXT_COLOR)
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
    plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight', dpi=80)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_b64


def make_thumbnail_image(df, symbol):
    """通常チャートと同じローソク足サムネイル（フル装備、サイズ小さめ）。一気見画面用。"""
    # 先物・指数タブ銘柄は3色判定
    is_futures = symbol in FUTURES_INDEX_SET
    try:
        plot_len = min(DISPLAY_PERIOD, len(df))
        plot_df = df.iloc[-plot_len:].copy()
        if plot_df.empty or len(plot_df) < 2:
            return None

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

        fig = plt.figure(figsize=(6, 4), facecolor=BG_COLOR, dpi=100)
        fig.subplots_adjust(top=0.90, bottom=0.15, left=0.07, right=0.90)
        ax_main = fig.add_subplot(111, facecolor=BG_COLOR)
        ax_main.tick_params(axis='x', colors=TEXT_COLOR, labelcolor=TEXT_COLOR, labelsize=8)
        ax_main.tick_params(axis='y', colors=TEXT_COLOR, labelcolor=TEXT_COLOR, labelsize=8)

        add_plots = []
        if 'ema_20' in plot_df.columns and plot_df['ema_20'].notna().any():
            add_plots.append(mpf.make_addplot(plot_df['ema_20'], color='orange', width=1.0, ax=ax_main))
        if 'sma_50' in plot_df.columns and plot_df['sma_50'].notna().any():
            add_plots.append(mpf.make_addplot(plot_df['sma_50'], color='cyan', width=1.0, ax=ax_main))

        try:
            if add_plots:
                mpf.plot(plot_df, type='candle', style=my_style, ax=ax_main,
                         addplot=add_plots, warn_too_much_data=10000,
                         returnfig=False, datetime_format='%Y-%m')
            else:
                mpf.plot(plot_df, type='candle', style=my_style, ax=ax_main,
                         warn_too_much_data=10000, returnfig=False, datetime_format='%Y-%m')
        except Exception:
            plt.close(fig)
            return None

        current_score = plot_df['totalScore'].iloc[-1] if not pd.isna(plot_df['totalScore'].iloc[-1]) else 0
        ax_main.set_title(f"{symbol} (Score: {int(current_score):+d})", fontsize=12, loc='center', pad=8, color=TEXT_COLOR)
        ax_main.xaxis.grid(False)
        xmin, xmax = ax_main.get_xlim()
        ax_main.set_xlim(xmin, xmax + 5)

        for j in range(len(plot_df)):
            row = plot_df.iloc[j]
            score = row['totalScore']
            if pd.isna(score):
                c = '#888888'
            elif is_futures:
                # 先物・指数：新ロジック（score>40 & close>ema20 で青）
                close_v = row['close']
                ema20_v = row.get('ema_20') if hasattr(row, 'get') else (row['ema_20'] if 'ema_20' in row.index else None)
                if ema20_v is None or pd.isna(ema20_v):
                    c = '#ffd700'
                elif score > 40 and close_v > ema20_v:
                    c = '#00bfff'
                elif score <= 40 and close_v < ema20_v:
                    c = '#ff4444'
                else:
                    c = '#ffd700'
            else:
                # その他：4色（青/緑/赤/黄）
                if score >= 7:    c = '#00bfff'
                elif score > 0:   c = '#32cd32'
                elif score <= -7: c = '#ffd700'
                else:             c = '#ff4444'
            ax_main.plot([j, j], [row['low'], row['high']], color=c, linewidth=1.0, zorder=10)
            body_bottom = min(row['open'], row['close'])
            body_height = max(abs(row['open'] - row['close']), row['close'] * 0.0005)
            rect = Rectangle((j - 0.35, body_bottom), 0.7, body_height, facecolor=c, edgecolor=c, zorder=10)
            ax_main.add_patch(rect)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight', dpi=80)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_b64
    except Exception as e:
        print(f"thumbnail {symbol} error: {e}")
        return None


@app.route('/chart/<symbol>')
@limiter.limit("30 per minute")
def chart(symbol):
    if not is_valid_symbol(symbol):
        return jsonify({'error': 'Invalid symbol'}), 400
    symbol_upper = symbol.upper()
    now = time.time()

    if symbol_upper in chart_cache:
        cached_time, cached_img = chart_cache[symbol_upper]
        if now - cached_time < CACHE_SECONDS:
            return _cached_json({'image': cached_img, 'symbol': symbol_upper, 'cached': True}, max_age=1800)

    # NEW: メモリキャッシュに無い場合、GitHubから個別ファイル取得を試みる（リスト内銘柄）
    if symbol_upper not in chart_cache:
        github_img = fetch_chart_from_github(symbol_upper)
        if github_img:
            chart_cache[symbol_upper] = (now, github_img)
            print(f"/chart/{symbol_upper}: loaded from GitHub on-demand")
            return _cached_json({'image': github_img, 'symbol': symbol_upper, 'cached': True, 'source': 'github'}, max_age=1800)

    def _fallback_to_stale_cache(reason):
        """新規取得に失敗した場合、期限切れキャッシュがあればそれを返す。"""
        if symbol_upper in chart_cache:
            _, cached_img = chart_cache[symbol_upper]
            print(f"/chart/{symbol_upper}: serving stale cache ({reason})")
            return _cached_json({
                'image': cached_img, 'symbol': symbol_upper,
                'cached': True, 'stale': True,
                'note': f'最新データ取得失敗のため、前回のチャートを表示中（{reason}）'
            }, max_age=300)
        return None

    try:
        if symbol_upper == 'NQ1!':
            df = fetch_nq1()
            if df is None:
                stale = _fallback_to_stale_cache('NQ1! 取得失敗')
                if stale: return stale
                return jsonify({'error': 'NQ1! のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_nq(df, 'NASDAQ Futures')
        elif symbol_upper == 'ES1!':
            df = fetch_es1()
            if df is None:
                stale = _fallback_to_stale_cache('ES1! 取得失敗')
                if stale: return stale
                return jsonify({'error': 'ES1! のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_nq(df, 'S&P 500 Futures')
        elif symbol_upper in CRYPTO_MAP:
            df = fetch_crypto(symbol_upper)
            if df is None:
                stale = _fallback_to_stale_cache(f'{symbol_upper} 取得失敗')
                if stale: return stale
                return jsonify({'error': f'{symbol_upper} のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_stock(df, symbol_upper)
        elif symbol_upper in FOREX_PAIRS:
            df = fetch_forex(symbol_upper)
            if df is None:
                stale = _fallback_to_stale_cache(f'{symbol_upper} 取得失敗')
                if stale: return stale
                return jsonify({'error': f'{symbol_upper} のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_stock(df, symbol_upper)
        elif is_jp_symbol(symbol_upper):
            df = fetch_jp(symbol_upper)
            if df is None:
                stale = _fallback_to_stale_cache(f'{symbol_upper} 取得失敗')
                if stale: return stale
                return jsonify({'error': f'{symbol_upper} のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_stock(df, symbol_upper)
        elif symbol_upper.isdigit() and len(symbol_upper) == 4:
            # 4桁数字は日本株として扱う（例: 7203 → TSE:7203）
            jp_sym = f'TSE:{symbol_upper}'
            df = fetch_jp(jp_sym)
            if df is None:
                stale = _fallback_to_stale_cache(f'{symbol_upper} 取得失敗')
                if stale: return stale
                return jsonify({'error': f'{symbol_upper} のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_stock(df, jp_sym)
            symbol_upper = jp_sym  # キャッシュキー統一
        else:
            # 登録済み銘柄 or 未登録銘柄でも yfinance で取得を試みる
            df = fetch_and_calculate(symbol_upper, period=CALC_PERIOD)
            if df is None:
                stale = _fallback_to_stale_cache(f'{symbol_upper} 取得失敗')
                if stale: return stale
                return jsonify({'error': f'{symbol_upper} のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_stock(df, symbol_upper)

        if img_b64 is None:
            stale = _fallback_to_stale_cache('チャート生成失敗')
            if stale: return stale
            return jsonify({'error': 'チャート生成に失敗しました'}), 500

        chart_cache[symbol_upper] = (now, img_b64)
        return _cached_json({'image': img_b64, 'symbol': symbol_upper, 'cached': False}, max_age=1800)
    except Exception as e:
        stale = _fallback_to_stale_cache(str(e)[:50])
        if stale: return stale
        return jsonify({'error': str(e)}), 500


# =========================================
# トレンド解説と同業他社情報（/info エンドポイント）
# =========================================
info_cache = {}
profile_cache = {}


def generate_commentary(df, is_futures=False):
    """直近データから簡潔なトレンド解説を3行程度で生成する（スコア・乖離率は整数表示）
    is_futures=True の場合は先物・指数用の3色判定（緑=上昇 / 黄=レンジ / 赤=下降）。"""
    try:
        last = df.iloc[-1]
        close_col = 'close' if 'close' in df.columns else 'Close'
        score_col = 'totalScore' if 'totalScore' in df.columns else None

        if score_col is None:
            return ['データから解説を生成できません']

        score = last[score_col]
        if pd.isna(score):
            return ['スコアがまだ計算できていません']

        # 「ローソク足の色の説明」と完全に同じ文言で表示する
        if is_futures:
            # 先物・指数：score>40 & close>ema20 で 緑、score<=40 & close<ema20 で 赤、それ以外は 黄
            try:
                last_close = float(df['close'].iloc[-1])
                last_ema20 = df['ema_20'].iloc[-1] if 'ema_20' in df.columns else None
                above_ema = (last_ema20 is not None and not pd.isna(last_ema20)
                             and last_close > float(last_ema20))
                below_ema = (last_ema20 is not None and not pd.isna(last_ema20)
                             and last_close < float(last_ema20))
            except Exception:
                above_ema = False
                below_ema = False
            if score > 40 and above_ema:
                zone = '上昇トレンド'      # 🟦 青
                zone_emoji = '🟦'
            elif score <= 40 and below_ema:
                zone = '下降トレンド'      # 🔴 赤
                zone_emoji = '🔴'
            else:
                zone = 'レンジ'            # 🟡 黄
                zone_emoji = '🟡'
        elif score >= 7:
            zone = '上昇トレンド'          # 🟦 青（強い上昇）
            zone_emoji = '🟦'
        elif score > 0:
            zone = '上昇転換付近'          # 🟢 緑
            zone_emoji = '🟢'
        elif score <= -7:
            zone = '下降トレンド'          # 🟡 黄（強い下降・反発候補）
            zone_emoji = '🟡'
        else:
            zone = '下降転換付近'          # 🔴 赤
            zone_emoji = '🔴'

        lines = [f'{zone_emoji} 現在: {zone}(スコア {int(score):+d})']

        if 'discrepancyPercent' in df.columns and not pd.isna(last['discrepancyPercent']):
            disc = last['discrepancyPercent']
            if disc > 8:
                lines.append(f'📈 EMA20から +{int(disc)}% で過熱気味')
            elif disc > 3:
                lines.append(f'📈 EMA20から +{int(disc)}% で上方乖離')
            elif disc < -8:
                lines.append(f'📉 EMA20から {int(disc)}% で売られすぎ圏')
            elif disc < -3:
                lines.append(f'📉 EMA20から {int(disc)}% で下方乖離')
            else:
                lines.append(f'➡️ EMA20近辺で推移(乖離 {int(disc):+d}%)')

        return lines[:4]
    except Exception:
        return ['解説生成中にエラーが発生しました']


def get_peers(symbol_upper):
    """同じセクターの他銘柄を5つ取得し、1週間の変動率を返す。"""
    if is_jp_symbol(symbol_upper):
        sub_industry = NIKKEI225_SECTOR_MAP.get(symbol_upper)
        if not sub_industry:
            return None
        peers = [s for s, sub in NIKKEI225_SECTOR_MAP.items()
                 if sub == sub_industry and s != symbol_upper]
        if not peers:
            return {'sector': sub_industry, 'peers': []}
        peers = peers[:5]

        peer_yf_map = {p: jp_to_yfinance(p) for p in peers}
        peer_data = []
        try:
            yf_tickers = list(peer_yf_map.values())
            df_all = yf.download(yf_tickers, period='10d', interval='1d',
                                 progress=False, auto_adjust=False, group_by='ticker')
            for p in peers:
                yf_p = peer_yf_map[p]
                try:
                    if len(peers) == 1:
                        sub = df_all
                    else:
                        sub = df_all[yf_p] if yf_p in df_all.columns.get_level_values(0) else None
                    if sub is None or sub.empty:
                        peer_data.append({'symbol': p, 'change': None, 'score': None})
                        continue
                    closes = sub['Close'].dropna()
                    if len(closes) < 2:
                        peer_data.append({'symbol': p, 'change': None, 'score': None})
                        continue
                    cur = float(closes.iloc[-1])
                    ref = float(closes.iloc[-6]) if len(closes) >= 6 else float(closes.iloc[0])
                    if ref == 0:
                        peer_data.append({'symbol': p, 'change': None, 'score': None})
                        continue
                    change_pct = (cur - ref) / ref * 100
                    peer_score = None
                    if p in thumb_cache:
                        _, thumb_data = thumb_cache[p]
                        peer_score = thumb_data.get('score')
                    peer_data.append({'symbol': p, 'change': change_pct, 'score': peer_score})
                except Exception:
                    peer_data.append({'symbol': p, 'change': None, 'score': None})
        except Exception:
            for p in peers:
                peer_score = None
                if p in thumb_cache:
                    _, thumb_data = thumb_cache[p]
                    peer_score = thumb_data.get('score')
                peer_data.append({'symbol': p, 'change': None, 'score': peer_score, 'color': score_to_color(peer_score)})

        return {'sector': sub_industry, 'peers': peer_data}

    sub_industry = get_sector(symbol_upper)
    if not sub_industry:
        return None

    # 同じ業界の他銘柄を、S&P500 と NASDAQ100 の和集合から抽出
    candidate_syms = set(SP500_SYMBOLS) | set(NASDAQ100_SYMBOLS)
    peers = [s for s in candidate_syms
             if get_sector(s) == sub_industry and s != symbol_upper]
    if not peers:
        return {'sector': sub_industry, 'peers': []}

    peers = sorted(peers)[:5]

    peer_data = []
    try:
        df_all = yf.download(peers, period='10d', interval='1d',
                             progress=False, auto_adjust=False, group_by='ticker')
        for p in peers:
            try:
                if len(peers) == 1:
                    sub = df_all
                else:
                    sub = df_all[p] if p in df_all.columns.get_level_values(0) else None
                if sub is None or sub.empty:
                    peer_data.append({'symbol': p, 'change': None, 'score': None})
                    continue
                closes = sub['Close'].dropna()
                if len(closes) < 2:
                    peer_data.append({'symbol': p, 'change': None, 'score': None})
                    continue
                cur = float(closes.iloc[-1])
                ref = float(closes.iloc[-6]) if len(closes) >= 6 else float(closes.iloc[0])
                if ref == 0:
                    peer_data.append({'symbol': p, 'change': None, 'score': None})
                    continue
                change_pct = (cur - ref) / ref * 100
                peer_score = None
                if p in thumb_cache:
                    _, thumb_data = thumb_cache[p]
                    peer_score = thumb_data.get('score')
                peer_data.append({'symbol': p, 'change': change_pct, 'score': peer_score})
            except Exception:
                peer_data.append({'symbol': p, 'change': None, 'score': None})
    except Exception:
        for p in peers:
            peer_score = None
            if p in thumb_cache:
                _, thumb_data = thumb_cache[p]
                peer_score = thumb_data.get('score')
            peer_data.append({'symbol': p, 'change': None, 'score': peer_score, 'color': score_to_color(peer_score)})

    return {'sector': sub_industry, 'peers': peer_data}


def format_market_cap(mc):
    """時価総額を読みやすい形式に変換"""
    if mc is None or not isinstance(mc, (int, float)) or mc <= 0:
        return None
    if mc >= 1e12:
        return f"{mc/1e12:.2f}兆ドル"
    if mc >= 1e9:
        return f"{mc/1e9:.2f}十億ドル"
    if mc >= 1e6:
        return f"{mc/1e6:.2f}百万ドル"
    return f"{mc:,.0f}ドル"


def get_profile(symbol_upper):
    """銘柄の概要情報を yfinance から取得する。先物・暗号通貨は対象外。"""
    if symbol_upper in ('NQ1!', 'ES1!') or symbol_upper in CRYPTO_MAP:
        return None

    # 登録銘柄優先だが、未登録でも yfinance で試す（失敗時は None を返す）

    yf_ticker = jp_to_yfinance(symbol_upper) if is_jp_symbol(symbol_upper) else symbol_upper

    try:
        ticker = yf.Ticker(yf_ticker)
        info = ticker.info or {}
        if not info or 'shortName' not in info and 'longName' not in info:
            return None

        return {
            'symbol': symbol_upper,
            'name': info.get('longName') or info.get('shortName') or symbol_upper,
            'industry': info.get('industry') or '',
            'sector': info.get('sector') or '',
            'country': info.get('country') or '',
            'employees': info.get('fullTimeEmployees') or None,
            'market_cap': format_market_cap(info.get('marketCap')),
            'website': info.get('website') or '',
            'summary': info.get('longBusinessSummary') or '',
        }
    except Exception as e:
        print(f"get_profile {symbol_upper} error: {e}")
        return None


@app.route('/info/<symbol>')
@limiter.limit("40 per minute")
def info(symbol):
    if not is_valid_symbol(symbol):
        return jsonify({'error': 'Invalid symbol'}), 400
    symbol_upper = symbol.upper()
    now = time.time()

    if symbol_upper in info_cache:
        cached_time, cached_data = info_cache[symbol_upper]
        if now - cached_time < CACHE_SECONDS:
            cached_data = dict(cached_data)
            cached_data['profile'] = apply_translation(cached_data.get('profile'))
            return _cached_json({**cached_data, 'cached': True}, max_age=1800)

    try:
        if symbol_upper == 'NQ1!':
            df = fetch_nq1()
        elif symbol_upper == 'ES1!':
            df = fetch_es1()
        elif symbol_upper in CRYPTO_MAP:
            df = fetch_crypto(symbol_upper)
        elif symbol_upper in FOREX_PAIRS:
            df = fetch_forex(symbol_upper)
        elif is_jp_symbol(symbol_upper):
            df = fetch_jp(symbol_upper)
        elif symbol_upper.isdigit() and len(symbol_upper) == 4:
            # 4桁数字 → 日本株として扱う
            symbol_upper = f'TSE:{symbol_upper}'
            df = fetch_jp(symbol_upper)
        else:
            # 登録済み銘柄 or 未登録銘柄でも yfinance で取得を試みる
            df = fetch_and_calculate(symbol_upper, period=CALC_PERIOD)

        if df is None or df.empty:
            return jsonify({'error': 'データ取得に失敗しました'}), 500

        is_futures_symbol = symbol_upper in FUTURES_INDEX_SET
        commentary = generate_commentary(df, is_futures=is_futures_symbol)
        peers_info = get_peers(symbol_upper)

        profile = None
        if symbol_upper in profile_cache:
            p_time, p_data = profile_cache[symbol_upper]
            if now - p_time < CACHE_SECONDS:
                profile = p_data
        if profile is None:
            profile = get_profile(symbol_upper)
            if profile is not None:
                profile_cache[symbol_upper] = (now, profile)

        profile = apply_translation(profile)

        result = {
            'symbol': symbol_upper,
            'commentary': commentary,
            'peers': peers_info,
            'profile': profile,
        }
        info_cache[symbol_upper] = (now, result)
        return _cached_json({**result, 'cached': False}, max_age=1800)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =========================================
# 一括 info 取得エンドポイント
# SP500 / NASDAQ100 の全銘柄の info（commentary + profile）を一括で返す。
# フロントエンドが起動時に取得して localStorage にキャッシュし、銘柄を開いた瞬間に
# トレンド解説と企業概要を瞬時表示できるようにする。peers は省略（重複多いため）。
# =========================================
@app.route('/info-bulk/<group>')
@limiter.limit("10 per minute")
def info_bulk(group):
    if group == 'SP500':
        symbols = SP500_SYMBOLS
    elif group == 'NASDAQ100':
        symbols = NASDAQ100_SYMBOLS
    else:
        return jsonify({'error': 'Invalid group. Use SP500 or NASDAQ100.'}), 400

    items = []
    for sym in symbols:
        # info_cache から取得（プリフェッチで埋まっている）
        if sym in info_cache:
            _, data = info_cache[sym]
            items.append({
                'symbol': sym,
                'commentary': data.get('commentary'),
                'profile': data.get('profile'),
            })
    # 1時間ブラウザキャッシュ
    return _cached_json({'group': group, 'items': items, 'total': len(items)}, max_age=3600)


# =========================================
# 合体エンドポイント：1リクエストでチャート＋トレンド解説＋ピア＋プロフィールを返す
# /chart と /info を別々に呼ぶより、HTTP 往復・データ取得が半減して大幅高速化
# =========================================
@app.route('/api/load/<symbol>')
@limiter.limit("60 per minute")
def load_chart_and_info(symbol):
    if not is_valid_symbol(symbol):
        return jsonify({'error': 'Invalid symbol'}), 400
    symbol_upper = symbol.upper()
    now = time.time()

    # 完全合体キャッシュ（24時間）：両方揃ってる場合は即返す
    chart_cached = symbol_upper in chart_cache and (now - chart_cache[symbol_upper][0]) < CACHE_SECONDS
    info_cached  = symbol_upper in info_cache  and (now - info_cache[symbol_upper][0])  < CACHE_SECONDS

    if chart_cached and info_cached:
        c_img = chart_cache[symbol_upper][1]
        i_data = dict(info_cache[symbol_upper][1])
        i_data['profile'] = apply_translation(i_data.get('profile'))
        return jsonify({
            'symbol': symbol_upper,
            'image': c_img,
            'commentary': i_data.get('commentary'),
            'peers': i_data.get('peers'),
            'profile': i_data.get('profile'),
            'cached': True,
        })

    try:
        # データ取得（1回だけ）
        if symbol_upper == 'NQ1!':
            df = fetch_nq1()
        elif symbol_upper == 'ES1!':
            df = fetch_es1()
        elif symbol_upper in CRYPTO_MAP:
            df = fetch_crypto(symbol_upper)
        elif symbol_upper in FOREX_PAIRS:
            df = fetch_forex(symbol_upper)
        elif is_jp_symbol(symbol_upper):
            df = fetch_jp(symbol_upper)
        elif symbol_upper.isdigit() and len(symbol_upper) == 4:
            symbol_upper = f'TSE:{symbol_upper}'
            df = fetch_jp(symbol_upper)
        else:
            df = fetch_and_calculate(symbol_upper, period=CALC_PERIOD)

        if df is None or df.empty:
            stale = _fallback_to_stale_cache(f'{symbol_upper} 取得失敗')
            if stale:
                # 古いキャッシュからチャートだけ返す（info は欠ける）
                return stale
            return jsonify({'error': f'{symbol_upper} のデータ取得に失敗しました'}), 500

        # チャート画像生成（既存キャッシュがあればそれを使う）
        if chart_cached:
            img_b64 = chart_cache[symbol_upper][1]
        else:
            if symbol_upper in ('NQ1!', 'ES1!'):
                img_b64 = make_chart_image_nq(df, symbol_upper)
            else:
                img_b64 = make_chart_image_stock(df, symbol_upper)
            chart_cache[symbol_upper] = (now, img_b64)

        # トレンド解説 ＋ ピア（info_cache を使う or 新規計算）
        if info_cached:
            i_data = dict(info_cache[symbol_upper][1])
            commentary = i_data.get('commentary')
            peers_info = i_data.get('peers')
            profile = i_data.get('profile')
        else:
            is_futures_symbol = symbol_upper in FUTURES_INDEX_SET
            commentary = generate_commentary(df, is_futures=is_futures_symbol)
            peers_info = get_peers(symbol_upper)
            profile = None
            if symbol_upper in profile_cache:
                p_time, p_data = profile_cache[symbol_upper]
                if now - p_time < CACHE_SECONDS:
                    profile = p_data
            if profile is None:
                profile = get_profile(symbol_upper)
                if profile is not None:
                    profile_cache[symbol_upper] = (now, profile)
            info_cache[symbol_upper] = (now, {
                'symbol': symbol_upper,
                'commentary': commentary,
                'peers': peers_info,
                'profile': profile,
            })

        profile = apply_translation(profile)

        return jsonify({
            'symbol': symbol_upper,
            'image': img_b64,
            'commentary': commentary,
            'peers': peers_info,
            'profile': profile,
            'cached': False,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =========================================
# 銘柄比較（重ね合わせラインチャート）
# =========================================
compare_cache = {}
COMPARE_COLORS = ['#ff4444', '#32cd32', '#00bfff', '#ffd700', '#ff8800', '#aa66ff']


def fetch_close_series(symbol, bars=DISPLAY_PERIOD):
    """指定銘柄の終値シリーズを取得する。"""
    sym = symbol.upper()
    try:
        if sym == 'NQ1!':
            df = fetch_nq1()
            if df is None or df.empty:
                return None
            return df['Close'].dropna().tail(bars)
        if sym == 'ES1!':
            df = fetch_es1()
            if df is None or df.empty:
                return None
            return df['Close'].dropna().tail(bars)
        if sym in CRYPTO_MAP:
            df = fetch_crypto(sym)
            if df is None or df.empty:
                return None
            return df['close'].dropna().tail(bars)
        if is_jp_symbol(sym):
            df = fetch_jp(sym)
            if df is None or df.empty:
                return None
            return df['close'].dropna().tail(bars)
        if sym in SYMBOLS or sym in SP500_SYMBOLS or sym in NASDAQ100_SYMBOLS:
            df = fetch_and_calculate(sym, period=CALC_PERIOD)
            if df is None or df.empty:
                return None
            return df['close'].dropna().tail(bars)
    except Exception:
        pass
    return None


def make_compare_chart(symbols):
    """複数銘柄の終値を正規化（初日=100）して重ね合わせたチャート画像を作る"""
    series_map = {}
    for s in symbols:
        cs = fetch_close_series(s, bars=DISPLAY_PERIOD)
        if cs is not None and len(cs) >= 2:
            series_map[s] = cs

    if not series_map:
        return None, []

    df = pd.concat(series_map, axis=1, join='inner')
    if df.empty or len(df) < 2:
        return None, []

    base = df.iloc[0]
    norm = df.divide(base) * 100

    fig = plt.figure(figsize=(12, 7), facecolor=BG_COLOR)
    fig.subplots_adjust(top=0.92, bottom=0.15, left=0.06, right=0.92)
    ax = fig.add_subplot(111, facecolor=BG_COLOR)
    ax.tick_params(axis='x', colors=TEXT_COLOR, labelcolor=TEXT_COLOR)
    ax.tick_params(axis='y', colors=TEXT_COLOR, labelcolor=TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    ax.grid(True, color=GRID_COLOR, alpha=0.4, linestyle='--', linewidth=0.5)
    ax.axhline(100, color='#888', linewidth=0.8, linestyle=':', alpha=0.6)

    color_map = {}
    for i, sym in enumerate(norm.columns):
        color = COMPARE_COLORS[i % len(COMPARE_COLORS)]
        color_map[sym] = color
        ax.plot(norm.index, norm[sym], color=color, linewidth=2.0, label=sym)

    legend = ax.legend(loc='upper left', facecolor=BG_COLOR, edgecolor=GRID_COLOR,
                       labelcolor=TEXT_COLOR, fontsize=11, framealpha=0.85)
    if legend:
        for text in legend.get_texts():
            text.set_color(TEXT_COLOR)

    ax.set_title(f"比較チャート（初日=100 で正規化）", fontsize=18, color=TEXT_COLOR, pad=14)
    ax.set_ylabel('正規化価格', color=TEXT_COLOR)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight', dpi=80)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    return img_b64, [{'symbol': s, 'color': color_map[s]} for s in norm.columns]


@app.route('/compare')
@limiter.limit("20 per minute")
def compare():
    """クエリパラメータ symbols=NVDA,AMD,INTC で複数銘柄を比較"""
    symbols_param = request.args.get('symbols', '')
    symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    if not symbols:
        return jsonify({'error': '銘柄が指定されていません'}), 400
    if len(symbols) > 8:
        symbols = symbols[:8]
    # 全銘柄のバリデーション
    for s in symbols:
        if not is_valid_symbol(s):
            return jsonify({'error': 'Invalid symbol in list'}), 400

    cache_key = ','.join(symbols)
    now = time.time()
    if cache_key in compare_cache:
        cached_time, cached_data = compare_cache[cache_key]
        if now - cached_time < CACHE_SECONDS:
            return _cached_json({**cached_data, 'cached': True}, max_age=1800)

    try:
        img_b64, legend = make_compare_chart(symbols)
        if img_b64 is None:
            return jsonify({'error': '比較チャートを生成できませんでした'}), 500
        result = {'image': img_b64, 'symbols': symbols, 'legend': legend}
        compare_cache[cache_key] = (now, result)
        return _cached_json({**result, 'cached': False}, max_age=1800)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =========================================
# プリフェッチ機能（外部cronから1日1回呼ぶ）
# =========================================
def calculate_scores_from_ohlcv(df):
    """OHLCV DataFrameからスコアを計算する"""
    df = df.copy()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['prev_close'] = df['close'].shift(1)
    df['uvol'] = np.where(df['close'] > df['prev_close'], df['volume'], 0)
    df['dvol'] = np.where(df['close'] < df['prev_close'], df['volume'], 0)
    df['total_uvol_sma'] = get_wma(df['uvol'], 10)
    df['total_dvol_sma'] = get_wma(df['dvol'], 10)
    df['discrepancyPercent'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100
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


def prefetch_batch(symbols_batch):
    """50銘柄程度をまとめて取得し、各銘柄のチャート画像と情報をキャッシュに格納する"""
    results = {'success': [], 'failed': []}
    try:
        df_all = yf.download(
            symbols_batch, period='2y', interval='1d',
            progress=False, auto_adjust=False, group_by='ticker', threads=True
        )
    except Exception as e:
        return {'success': [], 'failed': symbols_batch, 'error': str(e)}

    now = time.time()
    for sym in symbols_batch:
        try:
            if len(symbols_batch) == 1:
                sub = df_all
            else:
                if sym not in df_all.columns.get_level_values(0):
                    results['failed'].append(sym)
                    continue
                sub = df_all[sym]

            if sub is None or sub.empty:
                results['failed'].append(sym)
                continue

            df = sub.copy()
            df.columns = df.columns.str.lower() if hasattr(df.columns, 'str') else [c.lower() for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()].copy()
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            if 'close' not in df.columns or len(df) < 60:
                results['failed'].append(sym)
                continue
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna(subset=['close'])

            df = calculate_scores_from_ohlcv(df)

            img_b64 = make_chart_image_stock(df, sym)
            if img_b64:
                chart_cache[sym] = (now, img_b64)

            thumb_b64 = make_thumbnail_image(df, sym)
            last_score = df['totalScore'].iloc[-1] if 'totalScore' in df.columns else None
            try:
                last_score_val = float(last_score) if last_score is not None and not pd.isna(last_score) else None
            except Exception:
                last_score_val = None

            week_change = None
            try:
                closes = df['close'].dropna()
                if len(closes) >= 6:
                    cur = float(closes.iloc[-1])
                    ref = float(closes.iloc[-6])
                    if ref != 0:
                        week_change = (cur - ref) / ref * 100
            except Exception:
                week_change = None

            # 20EMA乖離率・50SMA乖離率
            ema20_dev = None
            sma50_dev = None
            try:
                last_close = float(df['close'].iloc[-1])
                if 'ema_20' in df.columns:
                    last_ema20 = df['ema_20'].iloc[-1]
                    if not pd.isna(last_ema20) and float(last_ema20) != 0:
                        ema20_dev = (last_close - float(last_ema20)) / float(last_ema20) * 100
                if 'sma_50' in df.columns:
                    last_sma50 = df['sma_50'].iloc[-1]
                    if not pd.isna(last_sma50) and float(last_sma50) != 0:
                        sma50_dev = (last_close - float(last_sma50)) / float(last_sma50) * 100
            except Exception:
                pass

            if thumb_b64:
                thumb_cache[sym] = (now, {
                    'thumb': thumb_b64,
                    'score': last_score_val,
                    'week_change': week_change,
                    'ema20_dev': ema20_dev,
                    'sma50_dev': sma50_dev,
                })

            commentary = generate_commentary(df)
            peers_info = get_peers(sym)

            profile = get_profile(sym)
            if profile is not None:
                profile_cache[sym] = (now, profile)

            info_cache[sym] = (now, {
                'symbol': sym, 'commentary': commentary, 'peers': peers_info,
                'profile': profile,
            })

            results['success'].append(sym)
        except Exception as e:
            print(f"prefetch {sym} error: {e}")
            results['failed'].append(sym)
    return results


def prefetch_jp_batch(symbols_batch):
    """日経225銘柄を tvDatafeed 経由で取得し、キャッシュに保存。
    tvDatafeed は逐次取得なので並列化せず、各銘柄を順に処理する。"""
    results = {'success': [], 'failed': []}
    now = time.time()

    for sym in symbols_batch:
        try:
            df = fetch_jp(sym, n_bars=600)
            if df is None or df.empty or len(df) < 60:
                results['failed'].append(sym)
                continue

            df = calculate_scores_from_ohlcv(df)

            img_b64 = make_chart_image_stock(df, sym)
            if img_b64:
                chart_cache[sym] = (now, img_b64)

            thumb_b64 = make_thumbnail_image(df, sym)
            last_score = df['totalScore'].iloc[-1] if 'totalScore' in df.columns else None
            try:
                last_score_val = float(last_score) if last_score is not None and not pd.isna(last_score) else None
            except Exception:
                last_score_val = None

            week_change = None
            try:
                closes = df['close'].dropna()
                if len(closes) >= 6:
                    cur = float(closes.iloc[-1])
                    ref = float(closes.iloc[-6])
                    if ref != 0:
                        week_change = (cur - ref) / ref * 100
            except Exception:
                week_change = None

            ema20_dev = None
            sma50_dev = None
            try:
                last_close = float(df['close'].iloc[-1])
                if 'ema_20' in df.columns:
                    last_ema20 = df['ema_20'].iloc[-1]
                    if not pd.isna(last_ema20) and float(last_ema20) != 0:
                        ema20_dev = (last_close - float(last_ema20)) / float(last_ema20) * 100
                if 'sma_50' in df.columns:
                    last_sma50 = df['sma_50'].iloc[-1]
                    if not pd.isna(last_sma50) and float(last_sma50) != 0:
                        sma50_dev = (last_close - float(last_sma50)) / float(last_sma50) * 100
            except Exception:
                pass

            if thumb_b64:
                thumb_cache[sym] = (now, {
                    'thumb': thumb_b64,
                    'score': last_score_val,
                    'week_change': week_change,
                    'ema20_dev': ema20_dev,
                    'sma50_dev': sma50_dev,
                })

            commentary = generate_commentary(df)
            peers_info = None  # 日経225 のピアは別管理（簡略化）

            info_cache[sym] = (now, {
                'symbol': sym, 'commentary': commentary, 'peers': peers_info,
                'profile': None,  # 日経225 の profile は別ロジック
            })

            results['success'].append(sym)
        except Exception as e:
            print(f"prefetch_jp {sym} error: {e}")
            results['failed'].append(sym)
    return results


prefetch_state = {
    'running': False,
    'started_at': None,
    'finished_at': None,
    'success_count': 0,
    'failed_count': 0,
    'failed_symbols': [],
    'elapsed_seconds': None,
}
prefetch_lock = threading.Lock()


def run_prefetch_in_background():
    """別スレッドで実行されるプリフェッチ処理本体。
    S&P500 を全件処理した後、NASDAQ100 のうち S&P500 にない差分のみ追加で処理する。"""
    global prefetch_state

    start_time = time.time()
    all_success = []
    all_failed = []

    BATCH_SIZE = 3    # workers=2 体制でメモリ余裕を確保
    BATCH_WAIT = 18   # ワーカー間でメモリピーク重複を避ける

    # NASDAQ100のうち S&P500 に含まれない銘柄（追加で取得が必要な銘柄）
    nasdaq_only = [s for s in NASDAQ100_SYMBOLS if s not in set(SP500_SYMBOLS)]
    targets = list(SP500_SYMBOLS) + nasdaq_only

    try:
        for i in range(0, len(targets), BATCH_SIZE):
            batch = targets[i:i+BATCH_SIZE]
            print(f"Prefetch batch {i // BATCH_SIZE + 1}: {len(batch)} symbols")
            res = prefetch_batch(batch)
            all_success.extend(res.get('success', []))
            all_failed.extend(res.get('failed', []))
            if i + BATCH_SIZE < len(targets):
                time.sleep(BATCH_WAIT)
    except Exception as e:
        print(f"Prefetch background error: {e}")

    elapsed = time.time() - start_time
    with prefetch_lock:
        prefetch_state['running'] = False
        prefetch_state['finished_at'] = time.time()
        prefetch_state['success_count'] = len(all_success)
        prefetch_state['failed_count'] = len(all_failed)
        prefetch_state['failed_symbols'] = all_failed
        prefetch_state['elapsed_seconds'] = round(elapsed, 1)
    print(f"Prefetch done: success={len(all_success)} failed={len(all_failed)} elapsed={elapsed:.1f}s")


def run_startup_prefetch():
    """起動時に自動で走るプリフェッチ（Render Starter プラン最適化版）。
    フェーズ1: ETF + テーマ別（水素・太陽光）+ FX + 先物 + 暗号通貨（軽量・最優先）
    フェーズ2: S&P500 + NASDAQ100差分
    フェーズ3: 日経225（プリフェッチ済みでなければ）
    tvDatafeedの初回ログイン待ちのため30秒待機してから開始。"""
    global prefetch_state

    # tvDatafeedの初回ログイン完了 + ユーザー操作優先のため60秒待機
    time.sleep(60)

    with prefetch_lock:
        if prefetch_state['running']:
            print("Startup prefetch: skipped (already running)")
            return
        prefetch_state['running'] = True
        prefetch_state['started_at'] = time.time()
        prefetch_state['finished_at'] = None

    print("=" * 60)
    print("STARTUP PREFETCH (Starter optimized): starting")
    print("=" * 60)

    start_time = time.time()
    all_success = []
    all_failed = []

    BATCH_SIZE = 3    # workers=2 体制、各ワーカーのメモリ余裕確保
    BATCH_WAIT = 18   # ピーク重複回避

    # ---------- フェーズ1: ETF + テーマ別（量子・宇宙・水素・太陽光）----------
    # ※FX / 先物 / 暗号通貨 / HYZN は yfinance では取得できないためプリフェッチ対象外。
    #   これらはユーザーが開いた時に専用関数（fetch_fx, fetch_nq1等）で取得される。
    etf_symbols = list(ETF_SECTOR_MAP.keys())
    # HYZN は yfinance で取得不可なので除外
    hydrogen_us = ['PLUG', 'BE', 'BLDP', 'FCEL', 'LIN', 'APD', 'CMI']
    solar_us = ['FSLR', 'ENPH', 'SEDG', 'RUN', 'NXT', 'ARRY', 'JKS', 'CSIQ', 'DQ']

    extras = list(set(hydrogen_us + solar_us) - set(etf_symbols))
    phase1_targets = etf_symbols + extras
    print(f"[Phase 1/3] ETF + Theme prefetch: {len(phase1_targets)} symbols")
    try:
        res = prefetch_batch(phase1_targets)
        all_success.extend(res.get('success', []))
        all_failed.extend(res.get('failed', []))
        print(f"[Phase 1/3] done: success={len(res.get('success', []))}, failed={len(res.get('failed', []))}")
    except Exception as e:
        print(f"[Phase 1/3] error: {e}")

    # Phase間の休憩（ユーザー操作優先）
    print("[Inter-Phase 1-2] cooldown 30s")
    time.sleep(30)

    # ---------- フェーズ2: S&P500 + NASDAQ100差分 ----------
    nasdaq_only = [s for s in NASDAQ100_SYMBOLS if s not in set(SP500_SYMBOLS)]
    phase2_targets = list(SP500_SYMBOLS) + nasdaq_only
    print(f"[Phase 2/3] S&P500+NASDAQ100diff prefetch: {len(phase2_targets)} symbols")

    try:
        for i in range(0, len(phase2_targets), BATCH_SIZE):
            batch = phase2_targets[i:i+BATCH_SIZE]
            print(f"[Phase 2/3] batch {i // BATCH_SIZE + 1}: {len(batch)} symbols")
            res = prefetch_batch(batch)
            all_success.extend(res.get('success', []))
            all_failed.extend(res.get('failed', []))
            if i + BATCH_SIZE < len(phase2_targets):
                time.sleep(BATCH_WAIT)
    except Exception as e:
        print(f"[Phase 2/3] error: {e}")

    # Phase2-3 間の休憩
    print("[Inter-Phase 2-3] cooldown 30s")
    time.sleep(30)

    # ---------- フェーズ3: 日経225（tvDatafeed専用関数で取得）----------
    jp_targets = list(NIKKEI225_SYMBOLS)
    JP_BATCH = 3      # tvDatafeed、ユーザー操作優先のため小さく
    JP_WAIT  = 10     # API レート制限 + ユーザー操作優先
    print(f"[Phase 3/3] Nikkei225 prefetch (tvDatafeed): {len(jp_targets)} symbols")
    try:
        for i in range(0, len(jp_targets), JP_BATCH):
            batch = jp_targets[i:i+JP_BATCH]
            print(f"[Phase 3/3] batch {i // JP_BATCH + 1}: {len(batch)} symbols")
            res = prefetch_jp_batch(batch)
            all_success.extend(res.get('success', []))
            all_failed.extend(res.get('failed', []))
            if i + JP_BATCH < len(jp_targets):
                time.sleep(JP_WAIT)
    except Exception as e:
        print(f"[Phase 3/3] error: {e}")

    elapsed = time.time() - start_time
    with prefetch_lock:
        prefetch_state['running'] = False
        prefetch_state['finished_at'] = time.time()
        prefetch_state['success_count'] = len(all_success)
        prefetch_state['failed_count'] = len(all_failed)
        prefetch_state['failed_symbols'] = all_failed
        prefetch_state['elapsed_seconds'] = round(elapsed, 1)
    print("=" * 60)
    print(f"STARTUP PREFETCH DONE: success={len(all_success)} failed={len(all_failed)} elapsed={elapsed:.1f}s")
    print("=" * 60)


@app.route('/prefetch')
def prefetch():
    """S&P500 + NASDAQ100差分 を一括プリフェッチ。バックグラウンドで実行し、即座にレスポンスを返す。"""
    token = request.args.get('token', '')
    if not PREFETCH_TOKEN or token != PREFETCH_TOKEN:
        return jsonify({'error': 'unauthorized'}), 401

    with prefetch_lock:
        if prefetch_state['running']:
            return jsonify({
                'status': 'already_running',
                'started_at': prefetch_state['started_at'],
            }), 200
        prefetch_state['running'] = True
        prefetch_state['started_at'] = time.time()
        prefetch_state['finished_at'] = None

    thread = threading.Thread(target=run_prefetch_in_background, daemon=True)
    thread.start()

    nasdaq_only_count = len([s for s in NASDAQ100_SYMBOLS if s not in set(SP500_SYMBOLS)])
    total = len(SP500_SYMBOLS) + nasdaq_only_count
    return jsonify({
        'status': 'started',
        'message': f'{total} 銘柄（S&P500 + NASDAQ100差分）のプリフェッチを開始しました。完了まで10〜20分ほどかかります。',
        'check_status_at': '/prefetch/status',
    }), 202


@app.route('/prefetch/status')
def prefetch_status():
    """プリフェッチの進捗確認用エンドポイント"""
    with prefetch_lock:
        return jsonify(dict(prefetch_state))


# =========================================
# 永続キャッシュ（GitHubに保存して再起動後も復元）
# =========================================
import json as _json

translations = {}
PERSISTENT_TRANSLATIONS_URL = 'https://raw.githubusercontent.com/toreken/trekken/main/cache/translations.json'


# 個別チャートファイルのGitHub URL（1銘柄1ファイル方式）
PERSISTENT_CHARTS_BASE_URL = 'https://raw.githubusercontent.com/toreken/trekken/main/cache/charts'

def load_persistent_cache():
    """起動時にGitHubから永続キャッシュを読み込む。失敗しても起動は継続。
    対応データ：profiles, thumbs, infos（トレンド解説+peers）。
    chartsは個別ファイル方式（リクエスト時に遅延ロード）。"""
    try:
        print(f"Loading persistent cache from {PERSISTENT_CACHE_URL} ...")
        resp = http_requests.get(PERSISTENT_CACHE_URL, timeout=30,
                                 headers={'User-Agent': 'Trekken site'})
        if resp.status_code != 200:
            print(f"Persistent cache: status {resp.status_code}, skipped")
            return
        data = resp.json()
        now = time.time()
        loaded_profiles = 0
        loaded_thumbs = 0
        loaded_infos = 0
        for sym, profile in (data.get('profiles') or {}).items():
            profile_cache[sym] = (now, profile)
            loaded_profiles += 1
        for sym, thumb_data in (data.get('thumbs') or {}).items():
            thumb_cache[sym] = (now, thumb_data)
            loaded_thumbs += 1
        for sym, info_data in (data.get('infos') or {}).items():
            if info_data:
                info_cache[sym] = (now, info_data)
                loaded_infos += 1
        chart_count = data.get('chart_count', 0)
        print(f"Persistent cache loaded: {loaded_profiles} profiles, {loaded_thumbs} thumbs, "
              f"{loaded_infos} infos ({chart_count} charts available on-demand)")
    except Exception as e:
        print(f"Persistent cache load failed: {e}")


def fetch_chart_from_github(symbol):
    """GitHubから個別チャートファイルを取得（リスト内銘柄のオンデマンドロード）。
    成功時はBase64文字列、失敗時はNoneを返す。"""
    try:
        # ファイル名安全化（コロンをアンダースコアに）
        safe_name = symbol.replace(":", "_").replace("/", "_")
        url = f"{PERSISTENT_CHARTS_BASE_URL}/{safe_name}.txt"
        resp = http_requests.get(url, timeout=8,
                                 headers={'User-Agent': 'Trekken site'})
        if resp.status_code != 200:
            return None
        img_b64 = resp.text.strip()
        if not img_b64 or len(img_b64) < 100:
            return None
        return img_b64
    except Exception as e:
        print(f"  fetch_chart_from_github {symbol} failed: {e}")
        return None


def load_translations():
    """起動時にGitHubから日本語訳辞書を読み込む。"""
    global translations
    try:
        print(f"Loading translations from {PERSISTENT_TRANSLATIONS_URL} ...")
        resp = http_requests.get(PERSISTENT_TRANSLATIONS_URL, timeout=10,
                                 headers={'User-Agent': 'Trekken site'})
        if resp.status_code != 200:
            print(f"Translations: status {resp.status_code}, skipped")
            return
        data = resp.json()
        if isinstance(data, dict):
            translations = data
            print(f"Translations loaded: {len(translations)} entries")
    except Exception as e:
        print(f"Translations load failed: {e}")


def apply_translation(profile):
    """profileのsummaryに日本語訳があれば差し替える。"""
    if not profile:
        return profile
    sym = profile.get('symbol', '')
    if sym in translations and translations[sym]:
        profile = dict(profile)
        profile['summary'] = translations[sym]
        profile['summary_translated'] = True
    return profile


load_persistent_cache()
load_translations()


# ===== 起動時自動プリフェッチ =====
# Renderコールドスタート対策：起動時にバックグラウンドでチャートをプリフェッチする
# 環境変数 STARTUP_PREFETCH=0 で無効化可能
# workers=2 以上の場合、ファイルロックで「最初のワーカー」だけが実行する
ENABLE_STARTUP_PREFETCH = os.environ.get('STARTUP_PREFETCH', '1') == '1'

def _try_acquire_prefetch_lock():
    """ワーカー間で1つだけがプリフェッチを実行するためのファイルロック。
    ロック取得成功 → このワーカーがプリフェッチ実行担当。
    ロック取得失敗 → 別のワーカーが実行中なのでスキップ。"""
    try:
        import fcntl
        # /tmp は Render の ephemeral storage で、全ワーカーから見える
        lock_fd = open('/tmp/trekken_prefetch.lock', 'w')
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # ロック取得成功 - ファイルディスクリプタをグローバルに保持（GC回避）
        globals()['_prefetch_lock_fd'] = lock_fd
        return True
    except (IOError, OSError, ImportError):
        return False

if ENABLE_STARTUP_PREFETCH:
    if _try_acquire_prefetch_lock():
        startup_prefetch_thread = threading.Thread(target=run_startup_prefetch, daemon=True)
        startup_prefetch_thread.start()
        print(f"Startup prefetch scheduled (worker pid={os.getpid()} is leader)")
    else:
        print(f"Startup prefetch skipped (worker pid={os.getpid()} is follower)")
else:
    print("Startup prefetch disabled by STARTUP_PREFETCH=0")


@app.route('/cache-export')
def cache_export():
    """現在の永続キャッシュ対象データをJSONで返す。トークン保護。"""
    token = request.args.get('token', '')
    if not PREFETCH_TOKEN or token != PREFETCH_TOKEN:
        return jsonify({'error': 'unauthorized'}), 401

    profiles = {sym: data for sym, (_, data) in profile_cache.items()}
    thumbs = {sym: data for sym, (_, data) in thumb_cache.items()}

    return jsonify({
        'profiles': profiles,
        'thumbs': thumbs,
        'exported_at': time.time(),
        'profile_count': len(profiles),
        'thumb_count': len(thumbs),
    })


@app.route('/sp500-all')
@limiter.limit("10 per minute")
def sp500_all():
    """S&P500の全銘柄のサムネイル+スコア+変動率を返す。キャッシュにある分のみ。"""
    items = []
    for sym in SP500_SYMBOLS:
        if sym in thumb_cache:
            _, data = thumb_cache[sym]
            items.append({
                'symbol': sym,
                'sector': SP500_SECTOR_MAP.get(sym, ''),
                'thumb': data.get('thumb'),
                'score': data.get('score'),
                'color': score_to_color(data.get('score')),
                'week_change': data.get('week_change'),
            })
        else:
            items.append({
                'symbol': sym,
                'sector': SP500_SECTOR_MAP.get(sym, ''),
                'thumb': None,
                'score': None,
                'week_change': None,
            })

    cached_count = sum(1 for it in items if it['thumb'] is not None)
    return jsonify({
        'total': len(items),
        'cached_count': cached_count,
        'items': items,
    })


# 先物・指数タブの全銘柄（フロント側と同じ）
FUTURES_INDEX_TAB_SYMBOLS = ['NQ1!', 'ES1!', 'SPY', 'RSP', 'DIA', 'QQQ', 'QQQE', 'IWM', 'VTI', 'VT']

@app.route('/symbols-meta')
def symbols_meta():
    """検索フィルタ用に、全グループの銘柄メタ情報を返す。サムネイル画像は含まないので軽量。"""
    all_syms = []
    seen = set()
    # 通常銘柄
    for s in SYMBOLS + SP500_SYMBOLS + NASDAQ100_SYMBOLS + NIKKEI225_SYMBOLS:
        if s not in seen:
            seen.add(s)
            all_syms.append(s)
    # 先物・指数タブの追加銘柄（NQ1!, ES1!, SPY, RSP, DIA, QQQ, QQQE, IWM, VTI, VT）
    for s in FUTURES_INDEX_TAB_SYMBOLS:
        if s not in seen:
            seen.add(s)
            all_syms.append(s)
    # 暗号通貨
    for s in CRYPTO_MAP.keys():
        if s not in seen:
            seen.add(s)
            all_syms.append(s)
    # 為替
    for s in FOREX_PAIRS:
        if s not in seen:
            seen.add(s)
            all_syms.append(s)

    items = []
    for sym in all_syms:
        score = None
        week_change = None
        ema20_dev = None
        sma50_dev = None
        if sym in thumb_cache:
            _, data = thumb_cache[sym]
            score = data.get('score')
            week_change = data.get('week_change')
            ema20_dev = data.get('ema20_dev')
            sma50_dev = data.get('sma50_dev')
        items.append({
            'symbol': sym,
            'sector': get_sector(sym),
            'score': score,
            'color': score_to_color(score),
            'week_change': week_change,
            'ema20_dev': ema20_dev,
            'sma50_dev': sma50_dev,
        })

    cached_count = sum(1 for it in items if it['score'] is not None)
    return jsonify({
        'total': len(items),
        'cached_count': cached_count,
        'items': items,
    })


@app.route('/nasdaq100-all')
@limiter.limit("10 per minute")
def nasdaq100_all():
    """NASDAQ100 の全銘柄のサムネイル+スコア+変動率を返す。キャッシュにある分のみ。
    S&P500と重複する銘柄も、同じ thumb_cache から共有して表示する。"""
    items = []
    for sym in NASDAQ100_SYMBOLS:
        if sym in thumb_cache:
            _, data = thumb_cache[sym]
            items.append({
                'symbol': sym,
                'sector': get_sector(sym),
                'thumb': data.get('thumb'),
                'score': data.get('score'),
                'color': score_to_color(data.get('score')),
                'week_change': data.get('week_change'),
            })
        else:
            items.append({
                'symbol': sym,
                'sector': get_sector(sym),
                'thumb': None,
                'score': None,
                'week_change': None,
            })

    cached_count = sum(1 for it in items if it['thumb'] is not None)
    return jsonify({
        'total': len(items),
        'cached_count': cached_count,
        'items': items,
    })


@app.route('/jp225-all')
@limiter.limit("10 per minute")
def jp225_all():
    """日経225 の全銘柄のサムネイル+スコア+変動率を返す。キャッシュにある分のみ。"""
    items = []
    for sym in NIKKEI225_SYMBOLS:
        if sym in thumb_cache:
            _, data = thumb_cache[sym]
            items.append({
                'symbol': sym,
                'sector': NIKKEI225_SECTOR_MAP.get(sym, ''),
                'thumb': data.get('thumb'),
                'score': data.get('score'),
                'color': score_to_color(data.get('score')),
                'week_change': data.get('week_change'),
            })
        else:
            items.append({
                'symbol': sym,
                'sector': NIKKEI225_SECTOR_MAP.get(sym, ''),
                'thumb': None,
                'score': None,
                'week_change': None,
            })

    cached_count = sum(1 for it in items if it['thumb'] is not None)
    return jsonify({
        'total': len(items),
        'cached_count': cached_count,
        'items': items,
    })


# =========================================
# Note 記事取得（RSSフィード経由）
# =========================================
note_cache = {'time': 0, 'items': []}
NOTE_CACHE_SECONDS = 1800
NOTE_USERNAME = 'natukb'


def parse_note_rss(xml_text):
    """NoteのRSS(XML)から記事情報を抽出する"""
    try:
        root = ET.fromstring(xml_text)
        channel = root.find('channel')
        if channel is None:
            return []
        # Media RSS の名前空間
        ns = {
            'media': 'http://search.yahoo.com/mrss/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
        }
        items = []
        for item in channel.findall('item')[:12]:
            title_el = item.find('title')
            link_el = item.find('link')
            pubdate_el = item.find('pubDate')
            desc_el = item.find('description')

            title = title_el.text if title_el is not None else ''
            link = link_el.text if link_el is not None else ''
            pubdate = pubdate_el.text if pubdate_el is not None else ''
            desc = desc_el.text if desc_el is not None else ''

            # ===== サムネイル取得（優先順位順に4箇所試す） =====
            thumb = ''
            # 1. <media:thumbnail url="..."/>（Media RSS、最優先）
            try:
                mt = item.find('media:thumbnail', ns)
                if mt is not None and mt.get('url'):
                    thumb = mt.get('url')
            except Exception:
                pass
            # 2. <media:content url="..." medium="image"/>
            if not thumb:
                try:
                    mc = item.find('media:content', ns)
                    if mc is not None and mc.get('url'):
                        thumb = mc.get('url')
                except Exception:
                    pass
            # 3. <enclosure url="..." type="image/..."/>
            if not thumb:
                enc = item.find('enclosure')
                if enc is not None and enc.get('url'):
                    enc_type = (enc.get('type') or '').lower()
                    if enc_type.startswith('image') or not enc_type:
                        thumb = enc.get('url')
            # 4. content:encoded 内のimg
            if not thumb:
                try:
                    ce = item.find('content:encoded', ns)
                    if ce is not None and ce.text:
                        m = re.search(r'<img[^>]+src="([^"]+)"', ce.text)
                        if m:
                            thumb = m.group(1)
                except Exception:
                    pass
            # 5. description内のimg（フォールバック）
            if not thumb and desc:
                m = re.search(r'<img[^>]+src="([^"]+)"', desc)
                if m:
                    thumb = m.group(1)

            # 本文プレビュー
            if desc:
                desc_text = re.sub(r'<[^>]+>', '', desc).strip()[:80]
            else:
                desc_text = ''

            items.append({
                'title': title,
                'link': link,
                'pubdate': pubdate,
                'thumb': thumb,
                'preview': desc_text,
            })
        return items
    except Exception as e:
        print(f"Note RSS parse error: {e}")
        return []


@app.route('/note-articles')
def note_articles():
    """Noteの最新記事3件を返す。30分キャッシュ。"""
    now = time.time()
    if now - note_cache['time'] < NOTE_CACHE_SECONDS and note_cache['items']:
        return jsonify({'items': note_cache['items'], 'cached': True})

    try:
        url = f'https://note.com/{NOTE_USERNAME}/rss'
        resp = http_requests.get(url, timeout=10,
                                 headers={'User-Agent': 'Mozilla/5.0 (Trekken site)'})
        if resp.status_code != 200:
            return jsonify({'items': [], 'error': f'status {resp.status_code}'}), 200
        items = parse_note_rss(resp.text)
        note_cache['time'] = now
        note_cache['items'] = items
        return jsonify({'items': items, 'cached': False})
    except Exception as e:
        return jsonify({'items': [], 'error': str(e)}), 200


@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
