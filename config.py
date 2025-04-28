#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için yapılandırma sabitleri
"""

# Uygulama bilgileri
APP_NAME = "Gelişmiş Forex Trading Bot"
APP_VERSION = "1.1.0"
APP_AUTHOR = "AI Developer"

# Veritabanı yapılandırması
DATABASE = {
    "type": "sqlite",  # sqlite, mongodb
    "path": "data/trading_bot.db",
    "mongodb_uri": "mongodb://localhost:27017/",
    "mongodb_db": "forex_trading_bot"
}

# MetaTrader 5 varsayılan ayarları
MT5_DEFAULT = {
    "path": "C:/Program Files/FTMO Global Markets MT5 Terminal/terminal64.exe",
    "server": "Demo",
    "timeout": 60000,
    "enable_real_trading": False
}

# Varsayılan semboller
DEFAULT_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD"]

# Zaman dilimi
TIMEZONE = "Europe/Istanbul"

# Varsayılan grafikler için zaman dilimleri
TIMEFRAMES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
    "W1": 10080,
    "MN1": 43200
}

# Varsayılan indikatörler
DEFAULT_INDICATORS = [
    "RSI", "MACD", "Bollinger Bands", "Moving Average", 
    "Stochastic", "ATR", "Ichimoku"
]

# LSTM modeli parametreleri
LSTM_MODEL = {
    "input_size": 20,
    "hidden_size": 50,
    "num_layers": 2,
    "output_size": 1,
    "dropout": 0.2,
    "batch_size": 64,
    "learning_rate": 0.001,
    "epochs": 100,
    "sequence_length": 60,
    "train_split": 0.8
}

# Sinyal oluşturma parametreleri
SIGNAL_PARAMS = {
    "min_probability": 60,  # Minimum başarı olasılığı
    "auto_trade_threshold": 70,  # Otomatik işlem için minimum başarı olasılığı
    "min_risk_reward": 1.5,  # Minimum risk/ödül oranı
    "confirmation_timeout": 300,  # Onay için beklenecek süre (saniye)
    "max_signals_per_day": 10  # Günlük maksimum sinyal sayısı
}

# Risk yönetimi parametreleri
RISK_MANAGEMENT = {
    "max_risk_percent": 2.0,  # Maksimum risk yüzdesi (hesap bakiyesinin)
    "max_daily_risk_percent": 5.0,  # Günlük maksimum risk
    "max_weekly_risk_percent": 10.0,  # Haftalık maksimum risk
    "max_open_positions": 5,  # Maksimum açık pozisyon sayısı
    "max_positions_per_symbol": 2,  # Sembol başına maksimum pozisyon
    "default_stop_loss_pips": 50,  # Varsayılan stop loss (pip)
    "default_take_profit_pips": 100,  # Varsayılan take profit (pip)
    "max_stop_loss_pips": 100,  # Maksimum stop loss (pip)
    "min_stop_loss_pips": 10,  # Minimum stop loss (pip)
    "max_lot_size": 1.0,  # Maksimum lot büyüklüğü
    "default_lot_size": 0.1,  # Varsayılan lot büyüklüğü
}

# Telegram bot ayarları
TELEGRAM = {
    "api_id": None,
    "api_hash": None,
    "bot_token": None,
    "chat_id": None,
    "use_proxy": False,
    "proxy": {
        "server": None,
        "port": None,
        "username": None,
        "password": None
    },
    "commands": {
        "start": "Bot'u başlat ve yardım menüsünü göster",
        "durum": "Hesap durumunu görüntüle",
        "pozisyonlar": "Açık pozisyonları listele",
        "onay": "Bir işlemi onayla",
        "red": "Bir işlemi reddet",
        "kapat": "Bir pozisyonu kapat",
        "ayarlar": "Bot ayarlarını görüntüle/değiştir",
        "yardim": "Komut listesini göster"
    }
}

# Haber kaynakları
NEWS_SOURCES = {
    "forex_factory": {
        "url": "https://www.forexfactory.com/calendar.php",
        "enabled": True
    },
    "investing_com": {
        "url": "https://www.investing.com/economic-calendar/",
        "enabled": True
    },
    "twitter": {
        "enabled": False,
        "api_key": None,
        "api_secret": None,
        "access_token": None,
        "access_token_secret": None,
        "accounts_to_follow": []
    }
}

# Streamlit uygulama ayarları
STREAMLIT = {
    "port": 8501,
    "theme": {
        "primaryColor": "#1E88E5",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#F5F5F5",
        "textColor": "#212121",
        "font": "sans-serif"
    }
}

# Veri depolama ayarları
DATA_STORAGE = {
    "historical_data_path": "data/historical_data/",
    "model_checkpoint_path": "models/checkpoints/",
    "backtest_results_path": "data/backtest_results/",
    "logs_path": "logs/"
}

# Özel strateji parametreleri
STRATEGY_PARAMS = {
    "ict": {
        "enabled": True,
        "liquidity_levels": True,
        "order_blocks": True,
        "breaker_blocks": True,
        "fair_value_gaps": True,
        "mtf_analysis": True,
        "weight": 0.35  # Sinyal ağırlığı
    },
    "smc": {
        "enabled": True,
        "supply_demand_zones": True,
        "market_structure": True,
        "smart_money_concepts": True,
        "weight": 0.35  # Sinyal ağırlığı
    },
    "price_action": {
        "enabled": True,
        "candle_patterns": True,
        "support_resistance": True,
        "trend_analysis": True,
        "momentum": True,
        "weight": 0.3  # Sinyal ağırlığı
    }
}