#!/usr/bin/env python3
"""
GitHub Actions上で実行される S&P500プリフェッチスクリプト。
yfinanceでデータを取得し、サムネイル画像とprofile情報を生成して
cache/cache.json として保存する。
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
# 設定
# ===========================
DISPLAY_PERIOD = 90
BG_COLOR = "#131722"
BATCH_SIZE = 30          # 小さめ（レート制限対策）
BATCH_WAIT = 15          # バッチ間の待機秒数（長め）
PROFILE_SLEEP = 0.5      # profile取得間のsleep
RETRY_WAIT = 30          # リトライ前の待機

# S&P500以外で対象にする銘柄（app.pyのSYMBOLSと同じ）
EXTRA_SYMBOLS = [
    'TONX', 'FRSH', 'PAYC', 'GCTS', 'PXLW',
    'FSLR', 'SIDU', 'VRNS', 'TRVG', 'TZOO',
    'MAKO', 'HLP',
    # セクター銘柄
    'KOS', 'GOOGL', 'INTC', 'NVDA', 'IONQ', 'FIGS', 'MU',
    'RKLB', 'CRWV', 'LUNR', 'ATOM', 'KLXE', 'WTI', 'ESOA'
]

# 全対象銘柄（S&P500とEXTRAをマージ、重複は除く）
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
    """fetch_and_calculateと同じスコア計算"""
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


def make_thumbnail_b64(df):
    """ローソク足サムネイル画像（base64）"""
    try:
        plot_len = min(DISPLAY_PERIOD, len(df))
        plot_df = df.iloc[-plot_len:].copy()
        if plot_df.empty or len(plot_df) < 2:
            return None

        # ローソク足の色：スコアの色分け基準
        # 上昇日（close >= open）→ スコア色
        # 下降日（close < open）→ 暗めの灰色
        last_score = plot_df["totalScore"].iloc[-1] if "totalScore" in plot_df.columns else 0
        if pd.isna(last_score):
            up_color = "#888888"
        elif last_score >= 7:
            up_color = "#00bfff"
        elif last_score > 0:
            up_color = "#32cd32"
        elif last_score <= -7:
            up_color = "#ffd700"
        else:
            up_color = "#ff4444"
        down_color = "#555555"

        fig = plt.figure(figsize=(2.5, 1.5), facecolor=BG_COLOR, dpi=60)
        ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
        ax.set_facecolor(BG_COLOR)

        # 各日のロー足を描画
        for i, (_, row) in enumerate(plot_df.iterrows()):
            o = row.get("open")
            h = row.get("high")
            l = row.get("low")
            c = row.get("close")
            if any(pd.isna(v) for v in (o, h, l, c)):
                continue
            color = up_color if c >= o else down_color
            # ヒゲ
            ax.plot([i, i], [l, h], color=color, linewidth=0.6, solid_capstyle="round")
            # 実体
            body_low, body_high = (o, c) if c >= o else (c, o)
            body_height = max(body_high - body_low, (h - l) * 0.01)
            ax.add_patch(plt.Rectangle(
                (i - 0.35, body_low), 0.7, body_height,
                facecolor=color, edgecolor=color, linewidth=0,
            ))

        ax.set_xlim(-1, len(plot_df))
        ax.axis("off")

        buf = io.BytesIO()
        plt.savefig(buf, format="png", facecolor=BG_COLOR, bbox_inches="tight", pad_inches=0)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return img_b64
    except Exception as e:
        print(f"  thumbnail error: {e}")
        return None


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
    """1銘柄のprofile情報を取得"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        if not info or ("shortName" not in info and "longName" not in info):
            return None
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "industry": info.get("industry") or "",
            "sector": info.get("sector") or "",
            "country": info.get("country") or "",
            "employees": info.get("fullTimeEmployees") or None,
            "market_cap": format_market_cap(info.get("marketCap")),
            "website": info.get("website") or "",
            "summary": info.get("longBusinessSummary") or "",
        }
    except Exception as e:
        print(f"  profile {symbol} error: {e}")
        return None


def process_batch(symbols, profiles, thumbs, failed):
    """1バッチ（最大30銘柄）を処理"""
    print(f"  Downloading {len(symbols)} symbols...")
    try:
        df_all = yf.download(
            symbols, period="2y", interval="1d",
            progress=False, auto_adjust=False, group_by="ticker", threads=True,
        )
    except Exception as e:
        print(f"  Batch download failed: {e}")
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

            df = sub.copy()
            df.columns = [c.lower() for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()].copy()
            if hasattr(df.index, "tz") and df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            if "close" not in df.columns or len(df) < 60:
                failed.append(sym)
                continue
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=["close"])

            df = calculate_scores(df)

            # サムネイル
            thumb_b64 = make_thumbnail_b64(df)
            last_score = df["totalScore"].iloc[-1] if "totalScore" in df.columns else None
            try:
                last_score_val = float(last_score) if last_score is not None and not pd.isna(last_score) else None
            except Exception:
                last_score_val = None
            if thumb_b64:
                thumbs[sym] = {"thumb": thumb_b64, "score": last_score_val}

            # profile
            profile = fetch_profile(sym)
            if profile is not None:
                profiles[sym] = profile
            time.sleep(PROFILE_SLEEP)

        except Exception as e:
            print(f"  {sym} processing error: {e}")
            failed.append(sym)


def main():
    start_time = time.time()
    print(f"=== Prefetch start at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} ===")
    print(f"Target: {len(ALL_TARGETS)} symbols (SP500 + Extra), batch_size={BATCH_SIZE}, batch_wait={BATCH_WAIT}s")

    profiles = {}
    thumbs = {}
    failed = []

    # ステップ1: 通常バッチ処理
    total_batches = (len(ALL_TARGETS) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(ALL_TARGETS), BATCH_SIZE):
        batch = ALL_TARGETS[i:i + BATCH_SIZE]
        batch_idx = i // BATCH_SIZE + 1
        elapsed = time.time() - start_time
        print(f"[Batch {batch_idx}/{total_batches}] elapsed={elapsed:.0f}s, success={len(thumbs)}/{len(profiles)}, failed={len(failed)}")
        process_batch(batch, profiles, thumbs, failed)
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
            process_batch(batch, profiles, thumbs, retry_failed)
            if i + BATCH_SIZE < len(retry_targets):
                time.sleep(BATCH_WAIT)
        failed = retry_failed

    # ステップ3: JSON出力
    elapsed = time.time() - start_time
    data = {
        "profiles": profiles,
        "thumbs": thumbs,
        "exported_at": time.time(),
        "profile_count": len(profiles),
        "thumb_count": len(thumbs),
        "failed": failed,
        "failed_count": len(failed),
        "elapsed_seconds": round(elapsed, 1),
    }

    os.makedirs("cache", exist_ok=True)
    with open("cache/cache.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

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
