#!/usr/bin/env python3
"""
GitHub Actions上で実行される S&P500 + NASDAQ100差分 + ETF + 日経225 プリフェッチスクリプト。
yfinanceでデータを取得し、サムネイル画像とprofile情報を生成して
cache/cache.json として保存する。

日経225銘柄はTSE:XXXX形式でキー管理し、yfinanceはXXXX.T形式で取得。
NASDAQ100銘柄はS&P500と多くが重複するため、差分13銘柄(ARM, ASML, CCEPなど)のみ追加。
ETF銘柄はセクター別11セクター×3ファミリー(SPDR/Vanguard/iShares)＋高配当4銘柄の計37銘柄。
"""

import os
import io
import sys
import json
import time
import base64
import traceback

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ===========================
# S&P 500 銘柄リストと業界マップ
# ===========================
# 先物・指数タブの全銘柄（3色判定：緑/黄/赤）
FUTURES_INDEX_SET = frozenset(['NQ1!', 'ES1!', 'SPY', 'RSP', 'DIA', 'QQQ', 'QQQE', 'IWM', 'VTI', 'VT'])

# 軽量プリフェッチ対象（チャート画像なし、スコアのみ取得）
# 元シンボル → yfinance形式のシンボル
LIGHT_TARGETS_MAP = {
    # 先物
    'NQ1!': 'NQ=F',
    'ES1!': 'ES=F',
    # 暗号通貨
    'BTC':   'BTC-USD',
    'ETH':   'ETH-USD',
    'SOL':   'SOL-USD',
    'XRP':   'XRP-USD',
    'ADA':   'ADA-USD',
    'DOGE':  'DOGE-USD',
    'AVAX':  'AVAX-USD',
    'LINK':  'LINK-USD',
    'MATIC': 'POL-USD',
    'ATOMC': 'ATOM-USD',
    # 為替
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X',
    'USDJPY': 'JPY=X',
    'USDCHF': 'CHF=X',
    'AUDUSD': 'AUDUSD=X',
    'NZDUSD': 'NZDUSD=X',
    'USDCAD': 'CAD=X',
    'EURJPY': 'EURJPY=X',
    'GBPJPY': 'GBPJPY=X',
    'AUDJPY': 'AUDJPY=X',
    'EURGBP': 'EURGBP=X',
}


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


# ===========================
# 日経225 銘柄リスト（TSE:XXXX形式）
# ===========================
NIKKEI225_SYMBOLS = [
    # 医薬品
    'TSE:4151','TSE:4502','TSE:4503','TSE:4506','TSE:4507','TSE:4519','TSE:4523','TSE:4568','TSE:4578',
    # 電気機器
    'TSE:285A','TSE:4062','TSE:6479','TSE:6501','TSE:6502','TSE:6504','TSE:6506','TSE:6526','TSE:6594',
    'TSE:6645','TSE:6674','TSE:6701','TSE:6702','TSE:6723','TSE:6724','TSE:6752','TSE:6753','TSE:6758',
    'TSE:6762','TSE:6770','TSE:6841','TSE:6857','TSE:6861','TSE:6902','TSE:6952','TSE:6954','TSE:6971',
    'TSE:6976','TSE:7735','TSE:7751','TSE:8035',
    # 輸送用機器
    'TSE:543A','TSE:7201','TSE:7202','TSE:7203','TSE:7205','TSE:7211','TSE:7261','TSE:7267','TSE:7269','TSE:7270','TSE:7272',
    # 化学
    'TSE:3407','TSE:4004','TSE:4005','TSE:4021','TSE:4042','TSE:4043','TSE:4061','TSE:4183','TSE:4188',
    'TSE:4208','TSE:4452','TSE:4631','TSE:6988','TSE:7912',
    # 機械
    'TSE:6103','TSE:6113','TSE:6273','TSE:6301','TSE:6302','TSE:6305','TSE:6326','TSE:6361','TSE:6367',
    'TSE:6369','TSE:6471','TSE:6472','TSE:7004','TSE:7011','TSE:7013',
    # 鉄鋼
    'TSE:5401','TSE:5406','TSE:5411',
    # 非鉄金属
    'TSE:3436','TSE:5703','TSE:5706','TSE:5711','TSE:5713','TSE:5714','TSE:5801','TSE:5802','TSE:5803',
    # 金属製品
    'TSE:5947',
    # 鉱業
    'TSE:1605',
    # 石油・石炭製品
    'TSE:5020','TSE:5101','TSE:5108',
    # ガラス・土石製品
    'TSE:4901','TSE:5201','TSE:5214','TSE:5233','TSE:5301','TSE:5332','TSE:5333',
    # 食料品
    'TSE:2002','TSE:2269','TSE:2282','TSE:2501','TSE:2502','TSE:2503','TSE:2531','TSE:2801','TSE:2802',
    'TSE:2871','TSE:2914',
    # 繊維製品
    'TSE:3001','TSE:3861','TSE:3893',
    # パルプ・紙
    'TSE:3941',
    # 銀行業
    'TSE:8304','TSE:8306','TSE:8308','TSE:8309','TSE:8316','TSE:8331','TSE:8354','TSE:8355','TSE:8411',
    # 証券・商品先物取引業
    'TSE:8601','TSE:8604','TSE:8628',
    # 保険業
    'TSE:8725','TSE:8750','TSE:8766','TSE:8795',
    # その他金融業
    'TSE:8253','TSE:8591','TSE:8697',
    # 不動産業
    'TSE:3289','TSE:8801','TSE:8802','TSE:8804','TSE:8830',
    # 卸売業
    'TSE:2768','TSE:8001','TSE:8002','TSE:8008','TSE:8015','TSE:8031','TSE:8053','TSE:8058',
    # 小売業
    'TSE:2651','TSE:2753','TSE:3086','TSE:3099','TSE:3382','TSE:7532','TSE:8267','TSE:9843','TSE:9983',
    # 情報・通信業
    'TSE:4689','TSE:4704','TSE:4716','TSE:4732','TSE:4739','TSE:9432','TSE:9433','TSE:9434','TSE:9613','TSE:9984',
    # サービス業
    'TSE:2413','TSE:2432','TSE:4324','TSE:6098','TSE:9602','TSE:9735',
    # 電気・ガス業
    'TSE:9501','TSE:9502','TSE:9503','TSE:9531','TSE:9532',
    # 陸運業
    'TSE:9001','TSE:9005','TSE:9007','TSE:9008','TSE:9009','TSE:9020','TSE:9021','TSE:9022',
    # 海運業
    'TSE:9101','TSE:9104','TSE:9107',
    # 空運業
    'TSE:9202',
    # 倉庫・運輸関連業
    'TSE:9064',
    # 建設業
    'TSE:1721','TSE:1801','TSE:1802','TSE:1803','TSE:1808','TSE:1812','TSE:1925','TSE:1928','TSE:5631',
    # ゴム製品
    'TSE:5012',
    # その他製品
    'TSE:4902','TSE:7912','TSE:7951','TSE:7974',
    # 精密機器
    'TSE:4543','TSE:7731','TSE:7733','TSE:7741','TSE:7762',
]

# 重複除去（念のため）
NIKKEI225_SYMBOLS = list(dict.fromkeys(NIKKEI225_SYMBOLS))

NIKKEI225_SECTOR_MAP = {
    # 医薬品
    'TSE:4151': '医薬品', 'TSE:4502': '医薬品', 'TSE:4503': '医薬品', 'TSE:4506': '医薬品',
    'TSE:4507': '医薬品', 'TSE:4519': '医薬品', 'TSE:4523': '医薬品', 'TSE:4568': '医薬品', 'TSE:4578': '医薬品',
    # 電気機器
    'TSE:285A': '電気機器', 'TSE:4062': '電気機器', 'TSE:6479': '電気機器', 'TSE:6501': '電気機器',
    'TSE:6502': '電気機器', 'TSE:6504': '電気機器', 'TSE:6506': '電気機器', 'TSE:6526': '電気機器',
    'TSE:6594': '電気機器', 'TSE:6645': '電気機器', 'TSE:6674': '電気機器', 'TSE:6701': '電気機器',
    'TSE:6702': '電気機器', 'TSE:6723': '電気機器', 'TSE:6724': '電気機器', 'TSE:6752': '電気機器',
    'TSE:6753': '電気機器', 'TSE:6758': '電気機器', 'TSE:6762': '電気機器', 'TSE:6770': '電気機器',
    'TSE:6841': '電気機器', 'TSE:6857': '電気機器', 'TSE:6861': '電気機器', 'TSE:6902': '電気機器',
    'TSE:6952': '電気機器', 'TSE:6954': '電気機器', 'TSE:6971': '電気機器', 'TSE:6976': '電気機器',
    'TSE:7735': '電気機器', 'TSE:7751': '電気機器', 'TSE:8035': '電気機器',
    # 輸送用機器
    'TSE:543A': '自動車', 'TSE:7201': '自動車', 'TSE:7202': '自動車', 'TSE:7203': '自動車',
    'TSE:7205': '自動車', 'TSE:7211': '自動車', 'TSE:7261': '自動車', 'TSE:7267': '自動車',
    'TSE:7269': '自動車', 'TSE:7270': '自動車', 'TSE:7272': '自動車',
    # 化学
    'TSE:3407': '化学', 'TSE:4004': '化学', 'TSE:4005': '化学', 'TSE:4021': '化学',
    'TSE:4042': '化学', 'TSE:4043': '化学', 'TSE:4061': '化学', 'TSE:4183': '化学',
    'TSE:4188': '化学', 'TSE:4208': '化学', 'TSE:4452': '化学', 'TSE:4631': '化学',
    'TSE:6988': '化学', 'TSE:7912': 'その他製品',
    # 機械
    'TSE:6103': '機械', 'TSE:6113': '機械', 'TSE:6273': '機械', 'TSE:6301': '機械',
    'TSE:6302': '機械', 'TSE:6305': '機械', 'TSE:6326': '機械', 'TSE:6361': '機械',
    'TSE:6367': '機械', 'TSE:6369': '機械', 'TSE:6471': '機械', 'TSE:6472': '機械',
    'TSE:7004': '機械', 'TSE:7011': '機械', 'TSE:7013': '機械',
    # 鉄鋼
    'TSE:5401': '鉄鋼', 'TSE:5406': '鉄鋼', 'TSE:5411': '鉄鋼',
    # 非鉄金属
    'TSE:3436': '非鉄金属', 'TSE:5703': '非鉄金属', 'TSE:5706': '非鉄金属', 'TSE:5711': '非鉄金属',
    'TSE:5713': '非鉄金属', 'TSE:5714': '非鉄金属', 'TSE:5801': '非鉄金属', 'TSE:5802': '非鉄金属', 'TSE:5803': '非鉄金属',
    # 金属製品
    'TSE:5947': '金属製品',
    # 鉱業
    'TSE:1605': '鉱業',
    # 石油・石炭製品
    'TSE:5020': '石油・石炭製品', 'TSE:5101': 'ゴム製品', 'TSE:5108': 'ゴム製品',
    # ガラス・土石製品
    'TSE:4901': 'ガラス・土石製品', 'TSE:5201': 'ガラス・土石製品', 'TSE:5214': 'ガラス・土石製品',
    'TSE:5233': 'ガラス・土石製品', 'TSE:5301': 'ガラス・土石製品', 'TSE:5332': 'ガラス・土石製品', 'TSE:5333': 'ガラス・土石製品',
    # 食料品
    'TSE:2002': '食料品', 'TSE:2269': '食料品', 'TSE:2282': '食料品', 'TSE:2501': '食料品',
    'TSE:2502': '食料品', 'TSE:2503': '食料品', 'TSE:2531': '食料品', 'TSE:2801': '食料品',
    'TSE:2802': '食料品', 'TSE:2871': '食料品', 'TSE:2914': '食料品',
    # 繊維製品
    'TSE:3001': '繊維製品', 'TSE:3861': 'パルプ・紙', 'TSE:3893': 'パルプ・紙', 'TSE:3941': 'パルプ・紙',
    # 銀行業
    'TSE:8304': '銀行業', 'TSE:8306': '銀行業', 'TSE:8308': '銀行業', 'TSE:8309': '銀行業',
    'TSE:8316': '銀行業', 'TSE:8331': '銀行業', 'TSE:8354': '銀行業', 'TSE:8355': '銀行業', 'TSE:8411': '銀行業',
    # 証券
    'TSE:8601': '証券・商品先物取引業', 'TSE:8604': '証券・商品先物取引業', 'TSE:8628': '証券・商品先物取引業',
    # 保険
    'TSE:8725': '保険業', 'TSE:8750': '保険業', 'TSE:8766': '保険業', 'TSE:8795': '保険業',
    # その他金融
    'TSE:8253': 'その他金融業', 'TSE:8591': 'その他金融業', 'TSE:8697': 'その他金融業',
    # 不動産
    'TSE:3289': '不動産業', 'TSE:8801': '不動産業', 'TSE:8802': '不動産業', 'TSE:8804': '不動産業', 'TSE:8830': '不動産業',
    # 卸売
    'TSE:2768': '卸売業', 'TSE:8001': '卸売業', 'TSE:8002': '卸売業', 'TSE:8008': '卸売業',
    'TSE:8015': '卸売業', 'TSE:8031': '卸売業', 'TSE:8053': '卸売業', 'TSE:8058': '卸売業',
    # 小売
    'TSE:2651': '小売業', 'TSE:2753': '小売業', 'TSE:3086': '小売業', 'TSE:3099': '小売業',
    'TSE:3382': '小売業', 'TSE:7532': '小売業', 'TSE:8267': '小売業', 'TSE:9843': '小売業', 'TSE:9983': '小売業',
    # 情報通信
    'TSE:4689': '情報・通信業', 'TSE:4704': '情報・通信業', 'TSE:4716': '情報・通信業', 'TSE:4732': '情報・通信業',
    'TSE:4739': '情報・通信業', 'TSE:9432': '情報・通信業', 'TSE:9433': '情報・通信業', 'TSE:9434': '情報・通信業',
    'TSE:9613': '情報・通信業', 'TSE:9984': '情報・通信業',
    # サービス
    'TSE:2413': 'サービス業', 'TSE:2432': 'サービス業', 'TSE:4324': 'サービス業',
    'TSE:6098': 'サービス業', 'TSE:9602': 'サービス業', 'TSE:9735': 'サービス業',
    # 電気・ガス
    'TSE:9501': '電気・ガス業', 'TSE:9502': '電気・ガス業', 'TSE:9503': '電気・ガス業',
    'TSE:9531': '電気・ガス業', 'TSE:9532': '電気・ガス業',
    # 陸運
    'TSE:9001': '陸運業', 'TSE:9005': '陸運業', 'TSE:9007': '陸運業', 'TSE:9008': '陸運業',
    'TSE:9009': '陸運業', 'TSE:9020': '陸運業', 'TSE:9021': '陸運業', 'TSE:9022': '陸運業',
    # 海運
    'TSE:9101': '海運業', 'TSE:9104': '海運業', 'TSE:9107': '海運業',
    # 空運
    'TSE:9202': '空運業',
    # 倉庫
    'TSE:9064': '倉庫・運輸関連業',
    # 建設
    'TSE:1721': '建設業', 'TSE:1801': '建設業', 'TSE:1802': '建設業', 'TSE:1803': '建設業',
    'TSE:1808': '建設業', 'TSE:1812': '建設業', 'TSE:1925': '建設業', 'TSE:1928': '建設業', 'TSE:5631': '建設業',
    # ゴム
    'TSE:5012': 'ゴム製品',
    # その他製品
    'TSE:4902': 'その他製品', 'TSE:7951': 'その他製品', 'TSE:7974': 'その他製品',
    # 精密機器
    'TSE:4543': '精密機器', 'TSE:7731': '精密機器', 'TSE:7733': '精密機器', 'TSE:7741': '精密機器', 'TSE:7762': '精密機器',
}


# ===========================
# NASDAQ100 のうち S&P500 に含まれない銘柄（差分のみ）
# (2026年6月時点、slickcharts.com 公開リスト・WMT/AZN 入れ替え反映済み)
# S&P500と重複する銘柄は既にプリフェッチされているため、ここには含めない。
# ===========================
NASDAQ100_ONLY_SYMBOLS = [
    'ARM', 'ASML', 'CCEP', 'MRVL', 'MELI', 'MSTR', 'PDD', 'SHOP', 'ZS',
    'ALNY', 'INSM', 'FER', 'TRI',
]

NASDAQ100_ONLY_SECTOR_MAP = {
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


# ===========================
# 日経シンボル変換ユーティリティ
# ===========================
def is_jp_symbol(symbol):
    """TSE: プレフィックスを持つ日経銘柄か判定"""
    return symbol.startswith("TSE:")

def tse_to_yfinance(symbol):
    """TSE:7203 → 7203.T"""
    code = symbol.replace("TSE:", "")
    return f"{code}.T"


# ===========================
# 設定
# ===========================
DISPLAY_PERIOD = 90
BG_COLOR = "#131722"
BATCH_SIZE = 25          # 日経混在のため少し小さめ
BATCH_WAIT = 15          # バッチ間の待機秒数
PROFILE_SLEEP = 0.5      # profile取得間のsleep
RETRY_WAIT = 30          # リトライ前の待機

# S&P500以外で対象にする銘柄（app.pyのSYMBOLSと同じ）
EXTRA_SYMBOLS = [
    'TONX', 'FRSH', 'PAYC', 'GCTS', 'PXLW',
    'FSLR', 'SIDU', 'VRNS', 'TRVG', 'TZOO',
    'MAKO', 'HLP',
    'KOS', 'GOOGL', 'INTC', 'NVDA', 'IONQ', 'FIGS', 'MU',
    'RKLB', 'CRWV', 'LUNR', 'ATOM', 'KLXE', 'WTI', 'ESOA',
    # 量子コンピュータ関連
    'RGTI', 'QBTS', 'QUBT', 'LAES',
    # 宇宙関連（ピュアプレイ + 防衛・航空宇宙）
    'ASTS', 'PL', 'BKSY', 'RDW', 'IRDM',
    'LMT', 'BA', 'NOC', 'LHX', 'GE',
    # 水素エネルギー関連（ピュアプレイ + 産業ガス・水素エンジン）
    'PLUG', 'BE', 'BLDP', 'FCEL', 'HYZN',
    'LIN', 'APD', 'CMI',
    # 太陽光関連（パネル・インバーター・架台・住宅リース、中国ADR）
    'ENPH', 'SEDG', 'RUN', 'NXT', 'ARRY',
    'JKS', 'CSIQ', 'DQ',
    # 量子ハイブリッド戦略（量子事業を持つ大手）
    'IBM', 'AMZN', 'MSFT', 'HON', 'MRVL',
]

# ETF銘柄（セクター別 + 高配当、37銘柄）
ETF_SYMBOLS = [
    # セクター別ETF（11セクター × 3ファミリー: SPDR / Vanguard / iShares）
    'XLK', 'VGT', 'IYW',      # テクノロジー
    'XLV', 'VHT', 'IYH',      # ヘルスケア
    'XLF', 'VFH', 'IYF',      # 金融
    'XLE', 'VDE', 'IYE',      # エネルギー
    'XLY', 'VCR', 'IYC',      # 一般消費財
    'XLP', 'VDC', 'IYK',      # 生活必需品
    'XLI', 'VIS', 'IYJ',      # 資本財
    'XLB', 'VAW', 'IYM',      # 素材
    'XLU', 'VPU', 'IDU',      # 公益事業
    'XLRE', 'VNQ', 'IYR',     # 不動産
    'XLC', 'VOX', 'IYZ',      # 通信サービス
    # 高配当ETF
    'VYM', 'HDV', 'SPYD', 'VIG',
]

# 全対象銘柄（S&P500 + Extra + NASDAQ100差分 + ETF + 日経225、重複除く）
def _build_all_targets():
    seen = set()
    out = []
    for s in SP500_SYMBOLS:
        if s not in seen:
            seen.add(s)
            out.append(s)
    for s in EXTRA_SYMBOLS:
        if s not in seen:
            seen.add(s)
            out.append(s)
    for s in NASDAQ100_ONLY_SYMBOLS:
        if s not in seen:
            seen.add(s)
            out.append(s)
    for s in ETF_SYMBOLS:
        if s not in seen:
            seen.add(s)
            out.append(s)
    for s in NIKKEI225_SYMBOLS:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

ALL_TARGETS = _build_all_targets()


# ===========================
# 計算系のヘルパー
# ===========================
def get_wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def calculate_scores(df):
    df = df.copy()
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["sma_50"] = df["close"].rolling(window=50).mean()
    df["prev_close"] = df["close"].shift(1)
    df["uvol"] = np.where(df["close"] > df["prev_close"], df["volume"], 0)
    df["dvol"] = np.where(df["close"] < df["prev_close"], df["volume"], 0)
    df["total_uvol_sma"] = get_wma(df["uvol"], 10)
    df["total_dvol_sma"] = get_wma(df["dvol"], 10)
    df["discrepancyPercent"] = (df["close"] - df["ema_20"]) / df["ema_20"] * 100
    df["discrepancyScore"] = df["discrepancyPercent"] / 2
    df["volDiff"] = df["total_uvol_sma"] - df["total_dvol_sma"]
    df["volDiff_avg"] = df["volDiff"].rolling(window=50).mean()
    df["volDiff_std"] = df["volDiff"].rolling(window=50).std(ddof=0)
    df["volDiffScore"] = np.where(
        df["volDiff_std"] != 0,
        (df["volDiff"] - df["volDiff_avg"]) / df["volDiff_std"] * 3,
        0,
    )
    df["totalScore"] = df["discrepancyScore"] + df["volDiffScore"]
    return df


def make_thumbnail_b64(df, symbol):
    # 先物・指数タブ銘柄は3色判定
    is_futures_thumb = symbol in FUTURES_INDEX_SET
    try:
        import mplfinance as mpf
        from matplotlib.patches import Rectangle

        plot_len = min(DISPLAY_PERIOD, len(df))
        plot_df = df.iloc[-plot_len:].copy()
        if plot_df.empty or len(plot_df) < 2:
            return None

        TEXT_COLOR = 'white'
        GRID_COLOR = '#444444'

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
        ax_main.set_title(f"{symbol} (Score: {int(current_score)})", fontsize=12, loc='center', pad=8, color=TEXT_COLOR)
        ax_main.xaxis.grid(False)
        xmin, xmax = ax_main.get_xlim()
        ax_main.set_xlim(xmin, xmax + 5)

        for j in range(len(plot_df)):
            row = plot_df.iloc[j]
            score = row['totalScore']
            if pd.isna(score):
                c = '#888888'
            elif is_futures_thumb:
                # 先物・指数：3色（緑/黄/赤）
                if score > 0:     c = '#32cd32'
                elif score > -7:  c = '#ffd700'
                else:             c = '#ff4444'
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
        plt.savefig(buf, format='png', facecolor=BG_COLOR, bbox_inches='tight')
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_b64
    except Exception as e:
        print(f"  thumbnail error: {e}")
        return None



def make_chart_b64(df, symbol):
    """大きいチャート画像（個別表示用、12x7サイズ）を生成。dpi=80。"""
    try:
        import mplfinance as mpf
        from matplotlib.patches import Rectangle

        plot_len = min(DISPLAY_PERIOD, len(df))
        plot_df = df.iloc[-plot_len:].copy()
        if plot_df.empty or len(plot_df) < 2:
            return None

        TEXT_COLOR = 'white'
        GRID_COLOR = '#444444'

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

        # 大きいチャート画像（個別表示用）：12x7、dpi=80 → 960x560px
        fig = plt.figure(figsize=(12, 7), facecolor=BG_COLOR, dpi=80)
        fig.subplots_adjust(top=0.93, bottom=0.10, left=0.05, right=0.93)
        ax_main = fig.add_subplot(111, facecolor=BG_COLOR)
        ax_main.tick_params(axis='x', colors=TEXT_COLOR, labelcolor=TEXT_COLOR, labelsize=10)
        ax_main.tick_params(axis='y', colors=TEXT_COLOR, labelcolor=TEXT_COLOR, labelsize=10)

        add_plots = []
        if 'ema_20' in plot_df.columns and plot_df['ema_20'].notna().any():
            add_plots.append(mpf.make_addplot(plot_df['ema_20'], color='orange', width=1.5, ax=ax_main))
        if 'sma_50' in plot_df.columns and plot_df['sma_50'].notna().any():
            add_plots.append(mpf.make_addplot(plot_df['sma_50'], color='cyan', width=1.5, ax=ax_main))

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
        ax_main.set_title(f"{symbol} (Score: {int(current_score):+d})", fontsize=14, loc='center', pad=10, color=TEXT_COLOR)
        ax_main.xaxis.grid(False)
        xmin, xmax = ax_main.get_xlim()
        ax_main.set_xlim(xmin, xmax + 5)

        # 先物・指数判定（3色判定）：先物・指数タブ全銘柄が対象
        is_futures = symbol in FUTURES_INDEX_SET

        for j in range(len(plot_df)):
            row = plot_df.iloc[j]
            score = row['totalScore']
            if pd.isna(score):
                c = '#888888'
            elif is_futures:
                # 先物・指数は3色（緑/黄/赤）
                if score > 0:     c = '#32cd32'  # 緑
                elif score > -7:  c = '#ffd700'  # 黄
                else:             c = '#ff4444'  # 赤
            else:
                # その他は4色（青/緑/赤/黄）
                if score >= 7:    c = '#00bfff'  # 青
                elif score > 0:   c = '#32cd32'  # 緑
                elif score <= -7: c = '#ffd700'  # 黄
                else:             c = '#ff4444'  # 赤
            ax_main.plot([j, j], [row['low'], row['high']], color=c, linewidth=1.2, zorder=10)
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
        print(f"  chart error: {e}")
        return None


def generate_commentary_simple(df, is_futures=False):
    """app.py の generate_commentary と同等の処理を行う（軽量版）。
    トレンド解説の文字列リストを返す。"""
    try:
        if df is None or df.empty or 'totalScore' not in df.columns:
            return ['📊 解説を生成できませんでした']

        score = df['totalScore'].iloc[-1]
        if pd.isna(score):
            return ['📊 解説を生成できませんでした']

        # 「ローソク足の色の説明」と完全に同じ文言
        if is_futures:
            if score > 0:
                zone, zone_emoji = '上昇トレンド', '🟢'
            elif score > -7:
                zone, zone_emoji = 'レンジ', '🟡'
            else:
                zone, zone_emoji = '下降トレンド', '🔴'
        elif score >= 7:
            zone, zone_emoji = '上昇トレンド', '🟦'
        elif score > 0:
            zone, zone_emoji = '上昇転換付近', '🟢'
        elif score <= -7:
            zone, zone_emoji = '下降トレンド', '🟡'
        else:
            zone, zone_emoji = '下降転換付近', '🔴'

        lines = [f'{zone_emoji} 現在: {zone}(スコア {int(score):+d})']

        # EMA20 乖離率
        try:
            last_close = float(df['close'].iloc[-1])
            if 'ema_20' in df.columns:
                last_ema20 = df['ema_20'].iloc[-1]
                if not pd.isna(last_ema20) and float(last_ema20) != 0:
                    dev = (last_close - float(last_ema20)) / float(last_ema20) * 100
                    if abs(dev) < 1:
                        lines.append(f'➡️ EMA20近辺で推移(乖離 {dev:+.0f}%)')
                    elif dev > 0:
                        lines.append(f'📈 EMA20から {dev:+.0f}% で上方乖離')
                    else:
                        lines.append(f'📉 EMA20から {dev:+.0f}% で下方乖離')
        except Exception:
            pass

        return lines
    except Exception:
        return ['📊 解説を生成できませんでした']


def format_market_cap(mc):
    if mc is None or not isinstance(mc, (int, float)) or mc <= 0:
        return None
    if mc >= 1e12:
        return f"{mc/1e12:.2f}兆ドル"
    if mc >= 1e9:
        return f"{mc/1e9:.2f}十億ドル"
    if mc >= 1e6:
        return f"{mc/1e6:.2f}百万ドル"
    return f"{mc:,.0f}ドル"


def fetch_profile(symbol):
    """
    1銘柄のprofile情報を取得。
    日経銘柄(TSE:XXXX)はyfinanceのXXXX.T形式で取得し、
    キャッシュキーはTSE:XXXX形式で保存する。
    """
    try:
        yf_sym = tse_to_yfinance(symbol) if is_jp_symbol(symbol) else symbol
        ticker = yf.Ticker(yf_sym)
        info = ticker.info or {}
        if not info or ("shortName" not in info and "longName" not in info):
            return None
        return {
            "symbol": symbol,  # TSE:XXXX形式で保存
            "name": info.get("longName") or info.get("shortName") or symbol,
            "industry": info.get("industry") or "",
            "sector": info.get("sector") or "",
            "country": info.get("country") or "Japan",
            "employees": info.get("fullTimeEmployees") or None,
            "market_cap": format_market_cap(info.get("marketCap")),
            "website": info.get("website") or "",
            "summary": info.get("longBusinessSummary") or "",
        }
    except Exception as e:
        print(f"  profile {symbol} error: {e}")
        return None


def process_batch(symbols, profiles, thumbs, charts, infos, failed):
    """
    1バッチを処理。日経銘柄はyfinance .T形式でダウンロードし、
    結果をTSE:XXXX形式のキーで保存する。
    """
    # 日経とUSを分離
    jp_symbols = [s for s in symbols if is_jp_symbol(s)]
    us_symbols = [s for s in symbols if not is_jp_symbol(s)]

    # --- US銘柄処理 ---
    if us_symbols:
        _process_us_batch(us_symbols, profiles, thumbs, charts, infos, failed)

    # --- 日経銘柄処理 ---
    if jp_symbols:
        # 少し間隔を空ける
        if us_symbols:
            time.sleep(3)
        _process_jp_batch(jp_symbols, profiles, thumbs, charts, infos, failed)


def _process_us_batch(symbols, profiles, thumbs, charts, infos, failed):
    """US銘柄バッチ処理（既存ロジックをそのまま移植）"""
    print(f"  [US] Downloading {len(symbols)} symbols...")
    try:
        df_all = yf.download(
            symbols, period="2y", interval="1d",
            progress=False, auto_adjust=False, group_by="ticker", threads=True,
        )
    except Exception as e:
        print(f"  [US] Batch download failed: {e}")
        failed.extend(symbols)
        return

    for sym in symbols:
        try:
            if len(symbols) == 1:
                sub = df_all
            else:
                if sym not in df_all.columns.get_level_values(0):
                    failed.append(sym)
                    continue
                sub = df_all[sym]
            if sub is None or sub.empty:
                failed.append(sym)
                continue

            df = _build_df(sub)
            if df is None:
                failed.append(sym)
                continue

            df = calculate_scores(df)
            thumb_b64 = make_thumbnail_b64(df, sym)
            last_score_val, week_change, ema20_dev, sma50_dev = _extract_score_and_change(df)

            if thumb_b64:
                thumbs[sym] = {
                    "thumb": thumb_b64,
                    "score": last_score_val,
                    "week_change": week_change,
                    "ema20_dev": ema20_dev,
                    "sma50_dev": sma50_dev,
                }

            # NEW: 大きいチャート画像も生成（個別表示用）
            chart_b64 = make_chart_b64(df, sym)
            if chart_b64:
                charts[sym] = chart_b64

            # NEW: トレンド解説も生成
            is_futures = sym in FUTURES_INDEX_SET
            commentary = generate_commentary_simple(df, is_futures=is_futures)
            infos[sym] = {
                'symbol': sym,
                'commentary': commentary,
                'peers': None,  # peersは別途バックエンドで補完（フロントで bulk preload）
                'profile': None,  # profile は別の profiles 辞書から取得
            }

            profile = fetch_profile(sym)
            if profile is not None:
                profiles[sym] = profile
                # infos の profile も更新
                infos[sym]['profile'] = profile
            time.sleep(PROFILE_SLEEP)

        except Exception as e:
            print(f"  {sym} processing error: {e}")
            failed.append(sym)


def _process_jp_batch(symbols, profiles, thumbs, charts, infos, failed):
    """
    日経銘柄バッチ処理。
    yfinanceはXXXX.T形式でダウンロード、キャッシュキーはTSE:XXXX形式。
    """
    # TSE:XXXX → XXXX.T の変換マップ
    sym_map = {tse_to_yfinance(s): s for s in symbols}  # {'7203.T': 'TSE:7203', ...}
    yf_syms = list(sym_map.keys())

    print(f"  [JP] Downloading {len(yf_syms)} symbols (e.g. {yf_syms[:3]})...")
    try:
        df_all = yf.download(
            yf_syms, period="2y", interval="1d",
            progress=False, auto_adjust=False, group_by="ticker", threads=True,
        )
    except Exception as e:
        print(f"  [JP] Batch download failed: {e}")
        failed.extend(symbols)
        return

    for yf_sym, tse_sym in sym_map.items():
        try:
            if len(yf_syms) == 1:
                sub = df_all
            else:
                if yf_sym not in df_all.columns.get_level_values(0):
                    print(f"  [JP] {yf_sym} not in download result, skip")
                    failed.append(tse_sym)
                    continue
                sub = df_all[yf_sym]
            if sub is None or sub.empty:
                failed.append(tse_sym)
                continue

            df = _build_df(sub)
            if df is None:
                failed.append(tse_sym)
                continue

            df = calculate_scores(df)
            # タイトルはTSE:XXXX形式で表示
            thumb_b64 = make_thumbnail_b64(df, tse_sym)
            last_score_val, week_change, ema20_dev, sma50_dev = _extract_score_and_change(df)

            if thumb_b64:
                thumbs[tse_sym] = {
                    "thumb": thumb_b64,
                    "score": last_score_val,
                    "week_change": week_change,
                    "ema20_dev": ema20_dev,
                    "sma50_dev": sma50_dev,
                }

            # NEW: 大きいチャート画像も生成
            chart_b64 = make_chart_b64(df, tse_sym)
            if chart_b64:
                charts[tse_sym] = chart_b64

            # NEW: トレンド解説も生成
            commentary = generate_commentary_simple(df, is_futures=False)
            infos[tse_sym] = {
                'symbol': tse_sym,
                'commentary': commentary,
                'peers': None,
                'profile': None,
            }

            profile = fetch_profile(tse_sym)
            if profile is not None:
                profiles[tse_sym] = profile
                infos[tse_sym]['profile'] = profile
            time.sleep(PROFILE_SLEEP)

        except Exception as e:
            print(f"  {tse_sym} processing error: {e}")
            failed.append(tse_sym)


def _build_df(sub):
    """yfinanceの生データをスコア計算用DataFrameに整形"""
    df = sub.copy()
    df.columns = [c.lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()].copy()
    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    if "close" not in df.columns or len(df) < 60:
        return None
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"])
    return df


def _extract_score_and_change(df):
    """totalScoreの最終値、1週間変動率、20EMA乖離率、50SMA乖離率を返す"""
    last_score = df["totalScore"].iloc[-1] if "totalScore" in df.columns else None
    try:
        last_score_val = float(last_score) if last_score is not None and not pd.isna(last_score) else None
    except Exception:
        last_score_val = None

    week_change = None
    try:
        closes = df["close"].dropna()
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
        last_close = float(df["close"].iloc[-1])
        if "ema_20" in df.columns:
            last_ema20 = df["ema_20"].iloc[-1]
            if not pd.isna(last_ema20) and float(last_ema20) != 0:
                ema20_dev = (last_close - float(last_ema20)) / float(last_ema20) * 100
        if "sma_50" in df.columns:
            last_sma50 = df["sma_50"].iloc[-1]
            if not pd.isna(last_sma50) and float(last_sma50) != 0:
                sma50_dev = (last_close - float(last_sma50)) / float(last_sma50) * 100
    except Exception:
        pass

    return last_score_val, week_change, ema20_dev, sma50_dev



def process_light_targets(thumbs):
    """先物・指数・暗号通貨・為替の「色情報のみ」をプリフェッチ。
    チャート画像やサムネ画像は生成せず、スコアと変動率だけを thumbs に追加する。
    フロント側で銘柄チップに色マーカーを表示するために使う。"""
    print()
    print("=" * 60)
    print(f"Light prefetch: {len(LIGHT_TARGETS_MAP)} symbols (scores only)")
    print("=" * 60)

    success = 0
    failed = []

    for original_sym, yf_sym in LIGHT_TARGETS_MAP.items():
        try:
            df = yf.download(yf_sym, period='1y', interval='1d',
                             auto_adjust=False, progress=False, threads=False)
            if df is None or df.empty or len(df) < 60:
                failed.append(original_sym)
                continue

            # MultiIndex 列のフラット化
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]

            # 必須カラム
            need_cols = {'open', 'high', 'low', 'close', 'volume'}
            if not need_cols.issubset(df.columns):
                failed.append(original_sym)
                continue

            df = df.reset_index()
            df = calculate_scores(df)

            # 最新値
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
                pass

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

            # 画像なしで thumbs に保存（フロントは score のみ使う）
            thumbs[original_sym] = {
                "thumb": None,
                "score": last_score_val,
                "week_change": week_change,
                "ema20_dev": ema20_dev,
                "sma50_dev": sma50_dev,
            }
            success += 1
            print(f"  ✓ {original_sym} (score={last_score_val}, week_change={week_change})")

            # レート制限対策
            time.sleep(0.5)

        except Exception as e:
            print(f"  ✗ {original_sym}: {e}")
            failed.append(original_sym)

    print(f"\nLight prefetch: success={success}, failed={len(failed)}")
    if failed:
        print(f"  Failed: {', '.join(failed)}")


def main():
    start_time = time.time()
    us_count = len([s for s in ALL_TARGETS if not is_jp_symbol(s)])
    jp_count = len([s for s in ALL_TARGETS if is_jp_symbol(s)])
    ndx_only_count = len([s for s in NASDAQ100_ONLY_SYMBOLS if s in ALL_TARGETS])
    etf_count = len([s for s in ETF_SYMBOLS if s in ALL_TARGETS])
    print(f"=== Prefetch start at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} ===")
    print(f"Target: {len(ALL_TARGETS)} symbols (US:{us_count} incl. NDX-only:{ndx_only_count}, ETF:{etf_count}, JP:{jp_count}), batch_size={BATCH_SIZE}, batch_wait={BATCH_WAIT}s")

    profiles = {}
    thumbs = {}
    charts = {}   # NEW: 大きいチャート画像
    infos = {}    # NEW: トレンド解説 + profile
    failed = []

    # ステップ1: 通常バッチ処理
    total_batches = (len(ALL_TARGETS) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(ALL_TARGETS), BATCH_SIZE):
        batch = ALL_TARGETS[i:i + BATCH_SIZE]
        batch_idx = i // BATCH_SIZE + 1
        elapsed = time.time() - start_time
        jp_in_batch = len([s for s in batch if is_jp_symbol(s)])
        print(f"[Batch {batch_idx}/{total_batches}] elapsed={elapsed:.0f}s, success={len(thumbs)}/{len(profiles)} (charts={len(charts)}), failed={len(failed)}, JP={jp_in_batch}")
        process_batch(batch, profiles, thumbs, charts, infos, failed)
        if i + BATCH_SIZE < len(ALL_TARGETS):
            time.sleep(BATCH_WAIT)

    # ステップ2: 失敗銘柄を1回リトライ
    if failed:
        print(f"\n=== Retry {len(failed)} failed symbols after {RETRY_WAIT}s wait ===")
        time.sleep(RETRY_WAIT)
        retry_failed = []
        retry_targets = list(failed)
        failed.clear()
        for i in range(0, len(retry_targets), BATCH_SIZE):
            batch = retry_targets[i:i + BATCH_SIZE]
            print(f"  Retry batch: {len(batch)} symbols")
            process_batch(batch, profiles, thumbs, charts, infos, retry_failed)
            if i + BATCH_SIZE < len(retry_targets):
                time.sleep(BATCH_WAIT)
        failed = retry_failed

    # ステップ2.5: 軽量プリフェッチ（先物・暗号通貨・為替の色情報のみ）
    process_light_targets(thumbs)

    # ステップ3: JSON出力（メモリ問題対策で分割保存）
    elapsed = time.time() - start_time

    # 3-A: 軽量 cache.json（profiles + thumbs + infos）
    # charts は除外（個別ファイルに保存）
    data = {
        "profiles": profiles,
        "thumbs": thumbs,
        "infos": infos,
        "exported_at": time.time(),
        "profile_count": len(profiles),
        "thumb_count": len(thumbs),
        "chart_count": len(charts),
        "info_count": len(infos),
        "failed": failed,
        "failed_count": len(failed),
        "elapsed_seconds": round(elapsed, 1),
    }

    os.makedirs("cache", exist_ok=True)
    with open("cache/cache.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    # 3-B: charts は 1銘柄1ファイル（メモリ展開負荷を分散）
    charts_dir = "cache/charts"
    os.makedirs(charts_dir, exist_ok=True)
    # まず既存のファイルを削除（古い銘柄を残さないため）
    import glob
    for old_file in glob.glob(os.path.join(charts_dir, "*.txt")):
        try:
            os.remove(old_file)
        except OSError:
            pass
    # 新しい charts を保存
    saved_charts = 0
    for sym, img_b64 in charts.items():
        if not img_b64:
            continue
        # ファイル名は安全化（: は _ に変換）
        safe_name = sym.replace(":", "_").replace("/", "_")
        chart_path = os.path.join(charts_dir, f"{safe_name}.txt")
        try:
            with open(chart_path, "w", encoding="utf-8") as cf:
                cf.write(img_b64)
            saved_charts += 1
        except Exception as e:
            print(f"  Failed to save chart {sym}: {e}")
    print(f"Saved {saved_charts} chart files to {charts_dir}/")

    print(f"\n=== Done in {elapsed:.0f}s ===")
    print(f"  profiles: {len(profiles)}")
    print(f"  thumbs:   {len(thumbs)}")
    print(f"  failed:   {len(failed)}")
    if failed:
        print(f"  failed list (first 20): {failed[:20]}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
