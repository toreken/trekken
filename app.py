import os
import io
import re
import base64
import time
import threading
import xml.etree.ElementTree as ET
from flask import Flask, jsonify, request
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

SYMBOLS = [
    'TONX', 'FRSH', 'PAYC', 'GCTS', 'PXLW',
    'FSLR', 'SIDU', 'VRNS', 'TRVG', 'TZOO',
    'MAKO', 'HLP',
    # グループ2
    'KOS', 'GOOGL', 'INTC', 'NVDA', 'IONQ', 'FIGS', 'MU',
    'RKLB', 'CRWV', 'LUNR', 'ATOM', 'KLXE', 'WTI', 'ESOA'
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
    'MATIC': ('POLUSDT',  'BINANCE'),  # MATICは2024年にPOLへリブランド
    'ATOMC': ('ATOMUSDT', 'BINANCE'),  # 暗号通貨のATOM（株式のATOMと区別するためサイト上はATOMCと表記）
}


def fetch_crypto(symbol_key, n_bars=1000):
    """tvDatafeedで暗号通貨を取得し、個別株と同じスコア計算を適用する"""
    tv_local = get_tv()
    if tv_local is None:
        return None
    Interval = get_interval()
    if Interval is None:
        return None
    if symbol_key not in CRYPTO_MAP:
        return None
    tv_symbol, tv_exchange = CRYPTO_MAP[symbol_key]
    try:
        df_raw = tv_local.get_hist(symbol=tv_symbol, exchange=tv_exchange,
                                   interval=Interval.in_daily, n_bars=n_bars)
        if df_raw is None or df_raw.empty:
            return None

        # 既存の fetch_and_calculate と同じ小文字カラム名に揃える
        df = df_raw.rename(columns={'open':'open','high':'high','low':'low',
                                    'close':'close','volume':'volume'})
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.index = pd.to_datetime(df.index).normalize().tz_localize(None)

        # ↓ ここからは fetch_and_calculate と完全に同じスコア計算
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
        # SPYはAMEX/ARCAにあるためフォールバック
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

        # 表示用チャートデータ（S&P500 E-mini先物）
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


def make_thumbnail_image(df, symbol):
    """軽量サムネイル画像（ライン1本のみ、軸/ラベル/余白なし）。"""
    try:
        plot_len = min(DISPLAY_PERIOD, len(df))
        plot_df = df.iloc[-plot_len:].copy()
        if plot_df.empty or len(plot_df) < 2:
            return None

        # 終値のラインのみ。色は最終スコアで決定
        last_score = plot_df['totalScore'].iloc[-1] if 'totalScore' in plot_df.columns else 0
        if pd.isna(last_score): color = '#888888'
        elif last_score >= 7:    color = '#00bfff'
        elif last_score > 0:     color = '#32cd32'
        elif last_score <= -7:   color = '#ffd700'
        else:                    color = '#ff4444'

        fig = plt.figure(figsize=(2.4, 1.2), facecolor=BG_COLOR, dpi=60)
        ax = fig.add_axes([0, 0, 1, 1])  # 余白ゼロ
        ax.set_facecolor(BG_COLOR)
        ax.plot(range(len(plot_df)), plot_df['close'].values, color=color, linewidth=1.2)
        ax.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight', pad_inches=0)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_b64
    except Exception as e:
        print(f"thumbnail {symbol} error: {e}")
        return None
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
        elif symbol_upper == 'ES1!':
            df = fetch_es1()
            if df is None:
                return jsonify({'error': 'ES1! のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_nq(df, 'S&P 500 Futures')
        elif symbol_upper in CRYPTO_MAP:
            df = fetch_crypto(symbol_upper)
            if df is None:
                return jsonify({'error': f'{symbol_upper} のデータ取得に失敗しました'}), 500
            img_b64 = make_chart_image_stock(df, symbol_upper)
        elif symbol_upper in SYMBOLS or symbol_upper in SP500_SYMBOLS:
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


# =========================================
# トレンド解説と同業他社情報（/info エンドポイント）
# =========================================
info_cache = {}
profile_cache = {}  # 銘柄概要のキャッシュ（24時間）


def generate_commentary(df):
    """直近データから簡潔なトレンド解説を3行程度で生成する"""
    try:
        last = df.iloc[-1]
        # 列名は小文字（個別株）と大文字（NQ1!/ES1!）の両方に対応
        close_col = 'close' if 'close' in df.columns else 'Close'
        score_col = 'totalScore' if 'totalScore' in df.columns else None

        if score_col is None:
            return ['データから解説を生成できません']

        score = last[score_col]
        if pd.isna(score):
            return ['スコアがまだ計算できていません']

        # 色分け基準（既存のチャート色と同じ）
        if score >= 7:
            zone = '強い上昇トレンド'
            zone_emoji = '🟦'
        elif score > 0:
            zone = '上昇トレンド'
            zone_emoji = '🟢'
        elif score <= -7:
            zone = '強い下落・反発候補'
            zone_emoji = '🟡'
        else:
            zone = '下落トレンド'
            zone_emoji = '🔴'

        lines = [f'{zone_emoji} 現在: {zone}（スコア {score:+.1f}）']

        # 乖離率
        if 'discrepancyPercent' in df.columns and not pd.isna(last['discrepancyPercent']):
            disc = last['discrepancyPercent']
            if disc > 8:
                lines.append(f'📈 EMA20から +{disc:.1f}% で過熱気味')
            elif disc > 3:
                lines.append(f'📈 EMA20から +{disc:.1f}% で上方乖離')
            elif disc < -8:
                lines.append(f'📉 EMA20から {disc:.1f}% で売られすぎ圏')
            elif disc < -3:
                lines.append(f'📉 EMA20から {disc:.1f}% で下方乖離')
            else:
                lines.append(f'➡️ EMA20近辺で推移（乖離 {disc:+.1f}%）')

        # 出来高
        if 'volDiffScore' in df.columns and not pd.isna(last['volDiffScore']):
            vds = last['volDiffScore']
            if vds > 2:
                lines.append('🔊 出来高が大きく増加（買い圧力強い）')
            elif vds > 0.5:
                lines.append('🔊 出来高がやや増加')
            elif vds < -2:
                lines.append('🔇 売り出来高が優勢')
            elif vds < -0.5:
                lines.append('🔇 売り出来高がやや優勢')

        return lines[:4]
    except Exception:
        return ['解説生成中にエラーが発生しました']


def get_peers(symbol_upper):
    """S&P500銘柄について、同じGICS Sub-Industryの他銘柄を5つ取得し、1週間の変動率を返す"""
    sub_industry = SP500_SECTOR_MAP.get(symbol_upper)
    if not sub_industry:
        return None  # S&P500外の銘柄

    # 同じ業界の他銘柄を抽出
    peers = [s for s, sub in SP500_SECTOR_MAP.items()
             if sub == sub_industry and s != symbol_upper]
    if not peers:
        return {'sector': sub_industry, 'peers': []}

    # 最大5銘柄（順番固定のため先頭から）
    peers = peers[:5]

    peer_data = []
    try:
        # 一括取得（高速化のためまとめて）
        df_all = yf.download(peers, period='10d', interval='1d',
                             progress=False, auto_adjust=False, group_by='ticker')
        for p in peers:
            try:
                if len(peers) == 1:
                    sub = df_all
                else:
                    sub = df_all[p] if p in df_all.columns.get_level_values(0) else None
                if sub is None or sub.empty:
                    peer_data.append({'symbol': p, 'change': None})
                    continue
                closes = sub['Close'].dropna()
                if len(closes) < 2:
                    peer_data.append({'symbol': p, 'change': None})
                    continue
                # 約1週間前との比較（5営業日前）
                cur = float(closes.iloc[-1])
                ref = float(closes.iloc[-6]) if len(closes) >= 6 else float(closes.iloc[0])
                if ref == 0:
                    peer_data.append({'symbol': p, 'change': None})
                    continue
                change_pct = (cur - ref) / ref * 100
                peer_data.append({'symbol': p, 'change': change_pct})
            except Exception:
                peer_data.append({'symbol': p, 'change': None})
    except Exception:
        for p in peers:
            peer_data.append({'symbol': p, 'change': None})

    return {'sector': sub_industry, 'peers': peer_data}


def format_market_cap(mc):
    """時価総額を読みやすい形式に変換（例: 3.2T, 850B, 12.5M）"""
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
    # 対象外（概要が無い銘柄）
    if symbol_upper in ('NQ1!', 'ES1!') or symbol_upper in CRYPTO_MAP:
        return None

    # 個別株か S&P 500 のみ対象
    if symbol_upper not in SYMBOLS and symbol_upper not in SP500_SYMBOLS:
        return None

    try:
        ticker = yf.Ticker(symbol_upper)
        info = ticker.info or {}
        # 何も取れなかった場合
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
def info(symbol):
    symbol_upper = symbol.upper()
    now = time.time()

    if symbol_upper in info_cache:
        cached_time, cached_data = info_cache[symbol_upper]
        if now - cached_time < CACHE_SECONDS:
            return jsonify({**cached_data, 'cached': True})

    try:
        # スコア計算用のデータを取得（チャートと同じロジック）
        if symbol_upper == 'NQ1!':
            df = fetch_nq1()
        elif symbol_upper == 'ES1!':
            df = fetch_es1()
        elif symbol_upper in CRYPTO_MAP:
            df = fetch_crypto(symbol_upper)
        elif symbol_upper in SYMBOLS or symbol_upper in SP500_SYMBOLS:
            df = fetch_and_calculate(symbol_upper, period=CALC_PERIOD)
        else:
            return jsonify({'error': f'{symbol_upper} は対象外です'}), 400

        if df is None or df.empty:
            return jsonify({'error': 'データ取得に失敗しました'}), 500

        commentary = generate_commentary(df)
        peers_info = get_peers(symbol_upper)

        # 銘柄概要を取得（プロファイルキャッシュから or 新規取得）
        profile = None
        if symbol_upper in profile_cache:
            p_time, p_data = profile_cache[symbol_upper]
            if now - p_time < CACHE_SECONDS:
                profile = p_data
        if profile is None:
            profile = get_profile(symbol_upper)
            if profile is not None:
                profile_cache[symbol_upper] = (now, profile)

        result = {
            'symbol': symbol_upper,
            'commentary': commentary,
            'peers': peers_info,
            'profile': profile,
        }
        info_cache[symbol_upper] = (now, result)
        return jsonify({**result, 'cached': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =========================================
# 銘柄比較（重ね合わせラインチャート）
# =========================================
compare_cache = {}

# 比較用カラーパレット
COMPARE_COLORS = ['#ff4444', '#32cd32', '#00bfff', '#ffd700', '#ff8800', '#aa66ff']


def fetch_close_series(symbol, bars=DISPLAY_PERIOD):
    """指定銘柄の終値シリーズを取得する。チャートと同じデータ源を使う。"""
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
        if sym in SYMBOLS or sym in SP500_SYMBOLS:
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

    # 共通の日付軸に揃える（内側結合）
    df = pd.concat(series_map, axis=1, join='inner')
    if df.empty or len(df) < 2:
        return None, []

    # 各銘柄の初日を100として正規化
    base = df.iloc[0]
    norm = df.divide(base) * 100

    fig = plt.figure(figsize=(14, 8), facecolor=BG_COLOR)
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
    plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    # 凡例用の色マップを返す
    return img_b64, [{'symbol': s, 'color': color_map[s]} for s in norm.columns]


@app.route('/compare')
def compare():
    """クエリパラメータ symbols=NVDA,AMD,INTC で複数銘柄を比較"""
    symbols_param = request.args.get('symbols', '')
    symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    if not symbols:
        return jsonify({'error': '銘柄が指定されていません'}), 400
    if len(symbols) > 8:
        symbols = symbols[:8]  # 過剰防止

    cache_key = ','.join(symbols)
    now = time.time()
    if cache_key in compare_cache:
        cached_time, cached_data = compare_cache[cache_key]
        if now - cached_time < CACHE_SECONDS:
            return jsonify({**cached_data, 'cached': True})

    try:
        img_b64, legend = make_compare_chart(symbols)
        if img_b64 is None:
            return jsonify({'error': '比較チャートを生成できませんでした'}), 500
        result = {'image': img_b64, 'symbols': symbols, 'legend': legend}
        compare_cache[cache_key] = (now, result)
        return jsonify({**result, 'cached': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =========================================
# プリフェッチ機能（外部cronから1日1回呼ぶ）
# =========================================
def calculate_scores_from_ohlcv(df):
    """OHLCV DataFrameからスコアを計算する（fetch_and_calculate と同じロジック）"""
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
            # 一括取得の結果から1銘柄分を取り出す
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

            # スコア計算
            df = calculate_scores_from_ohlcv(df)

            # チャート画像生成 → chart_cacheへ
            img_b64 = make_chart_image_stock(df, sym)
            if img_b64:
                chart_cache[sym] = (now, img_b64)

            # サムネイル生成 → thumb_cacheへ
            thumb_b64 = make_thumbnail_image(df, sym)
            last_score = df['totalScore'].iloc[-1] if 'totalScore' in df.columns else None
            try:
                last_score_val = float(last_score) if last_score is not None and not pd.isna(last_score) else None
            except Exception:
                last_score_val = None
            if thumb_b64:
                thumb_cache[sym] = (now, {'thumb': thumb_b64, 'score': last_score_val})

            # 情報生成 → info_cacheへ
            commentary = generate_commentary(df)
            peers_info = get_peers(sym)  # ここは別途yfinance呼び出しが発生

            # 概要情報も取得 → profile_cacheへ
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


# プリフェッチ実行状態
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
    """別スレッドで実行されるプリフェッチ処理本体"""
    global prefetch_state

    start_time = time.time()
    all_success = []
    all_failed = []

    BATCH_SIZE = 50
    BATCH_WAIT = 3

    try:
        for i in range(0, len(SP500_SYMBOLS), BATCH_SIZE):
            batch = SP500_SYMBOLS[i:i+BATCH_SIZE]
            print(f"Prefetch batch {i // BATCH_SIZE + 1}: {len(batch)} symbols")
            res = prefetch_batch(batch)
            all_success.extend(res.get('success', []))
            all_failed.extend(res.get('failed', []))
            if i + BATCH_SIZE < len(SP500_SYMBOLS):
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


@app.route('/prefetch')
def prefetch():
    """S&P500を一括プリフェッチ。バックグラウンドで実行し、即座にレスポンスを返す。"""
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

    # 別スレッドで実行
    thread = threading.Thread(target=run_prefetch_in_background, daemon=True)
    thread.start()

    return jsonify({
        'status': 'started',
        'message': f'{len(SP500_SYMBOLS)} 銘柄のプリフェッチを開始しました。完了まで10〜20分ほどかかります。',
        'check_status_at': '/prefetch/status',
    }), 202


@app.route('/prefetch/status')
def prefetch_status():
    """プリフェッチの進捗確認用エンドポイント（トークン不要）"""
    with prefetch_lock:
        return jsonify(dict(prefetch_state))


# =========================================
# 永続キャッシュ（GitHubに保存して再起動後も復元）
# =========================================
import json as _json


def load_persistent_cache():
    """起動時にGitHubから永続キャッシュを読み込む。失敗しても起動は継続。"""
    try:
        print(f"Loading persistent cache from {PERSISTENT_CACHE_URL} ...")
        resp = http_requests.get(PERSISTENT_CACHE_URL, timeout=10,
                                 headers={'User-Agent': 'Trekken site'})
        if resp.status_code != 200:
            print(f"Persistent cache: status {resp.status_code}, skipped")
            return
        data = resp.json()
        now = time.time()
        loaded_profiles = 0
        loaded_thumbs = 0
        # profile_cache の復元
        for sym, profile in (data.get('profiles') or {}).items():
            profile_cache[sym] = (now, profile)
            loaded_profiles += 1
        # thumb_cache の復元
        for sym, thumb_data in (data.get('thumbs') or {}).items():
            thumb_cache[sym] = (now, thumb_data)
            loaded_thumbs += 1
        print(f"Persistent cache loaded: {loaded_profiles} profiles, {loaded_thumbs} thumbs")
    except Exception as e:
        print(f"Persistent cache load failed: {e}")


# 起動時に1回だけロード（gunicornワーカー起動時に呼ばれる）
load_persistent_cache()


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
def sp500_all():
    """S&P500の全銘柄のサムネイル+スコアを返す。キャッシュにある分のみ。"""
    items = []
    for sym in SP500_SYMBOLS:
        if sym in thumb_cache:
            _, data = thumb_cache[sym]
            items.append({
                'symbol': sym,
                'sector': SP500_SECTOR_MAP.get(sym, ''),
                'thumb': data.get('thumb'),
                'score': data.get('score'),
            })
        else:
            # キャッシュ未生成の銘柄は thumb=None として情報だけ返す
            items.append({
                'symbol': sym,
                'sector': SP500_SECTOR_MAP.get(sym, ''),
                'thumb': None,
                'score': None,
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
NOTE_CACHE_SECONDS = 1800  # 30分キャッシュ
NOTE_USERNAME = 'natukb'   # トレケンのNoteアカウント


def parse_note_rss(xml_text):
    """NoteのRSS(XML)から記事情報を抽出する"""
    try:
        root = ET.fromstring(xml_text)
        # RSS2.0形式: rss > channel > item
        channel = root.find('channel')
        if channel is None:
            return []
        items = []
        for item in channel.findall('item')[:3]:  # 最新3件
            title_el = item.find('title')
            link_el = item.find('link')
            pubdate_el = item.find('pubDate')
            desc_el = item.find('description')

            title = title_el.text if title_el is not None else ''
            link = link_el.text if link_el is not None else ''
            pubdate = pubdate_el.text if pubdate_el is not None else ''
            desc = desc_el.text if desc_el is not None else ''

            # サムネイル画像URLを description のHTMLから抽出
            thumb = ''
            if desc:
                m = re.search(r'<img[^>]+src="([^"]+)"', desc)
                if m:
                    thumb = m.group(1)
                # description からタグを除去して本文プレビューに
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
