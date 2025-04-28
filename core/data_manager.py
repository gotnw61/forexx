#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için veri yönetim modülü.
Piyasa verilerini, haber ve sosyal medya verilerini toplar ve yönetir.
"""
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
import pytz
from pathlib import Path
import pickle
import json

# Proje kök dizinini ekleyelim
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger("ForexTradingBot.DataManager")

class DataManager:
    """
    Piyasa verilerini, haber verilerini ve sosyal medya verilerini toplama ve yönetme sınıfı.
    """
    
    def __init__(self, broker_connector, settings):
        """
        Veri yöneticisini başlat
        
        Args:
            broker_connector: MT5 bağlantısı için broker connector
            settings: Uygulama ayarları
        """
        self.broker = broker_connector
        self.settings = settings
        
        # Veri depolama klasörü
        self.data_dir = os.path.join(ROOT_DIR, "data")
        self.historical_data_dir = os.path.join(self.data_dir, "historical_data")
        self.news_data_dir = os.path.join(self.data_dir, "news_data")
        self.social_data_dir = os.path.join(self.data_dir, "social_media_data")
        
        # Veri klasörlerini oluştur
        for directory in [self.data_dir, self.historical_data_dir, 
                         self.news_data_dir, self.social_data_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Veri önbelleği
        self.market_data_cache = {}
        self.news_data_cache = {}
        self.social_data_cache = {}
        
        # Zaman dilimi ayarı
        self.timezone = pytz.timezone(settings.get("timezone", "Europe/Istanbul"))
        
        logger.info("Veri yöneticisi başlatıldı")
    
    def get_historical_data(self, symbol: str, timeframe: str, 
                           start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None,
                           use_cache: bool = True) -> pd.DataFrame:
        """
        Belirli bir sembol ve zaman dilimi için tarihsel veriyi al
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            timeframe: Zaman dilimi (örn. "H1", "D1")
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            use_cache: Önbellek kullan
            
        Returns:
            pd.DataFrame: Tarihsel veri DataFrame'i
        """
        # Bitiş tarihi belirtilmemişse şu anki zamanı kullan
        if end_date is None:
            end_date = datetime.now(self.timezone)
            
        # Başlangıç tarihi belirtilmemişse son 100 çubuk için hesapla
        if start_date is None:
            # Zaman dilimini dakika cinsine çevir
            timeframe_minutes = self._timeframe_to_minutes(timeframe)
            start_date = end_date - timedelta(minutes=timeframe_minutes * 1000)
        
        # Önbellek anahtarı oluştur
        cache_key = f"{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        # Önbellekten veriyi kontrol et
        if use_cache and cache_key in self.market_data_cache:
            return self.market_data_cache[cache_key]
        
        try:
            # Broker'dan veriyi al
            df = self.broker.get_historical_data(symbol, timeframe, start_date, end_date)
            
            # Veriyi önbelleğe ekle
            self.market_data_cache[cache_key] = df
            
            return df
        except Exception as e:
            logger.error(f"Tarihsel veri alınırken hata: {e}")
            # Boş DataFrame döndür
            return pd.DataFrame()
    
    def get_latest_tick_data(self, symbol: str) -> Dict:
        """
        Belirli bir sembol için en son tick verisini al
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            
        Returns:
            Dict: Tick verisi sözlüğü
        """
        try:
            return self.broker.get_last_tick(symbol)
        except Exception as e:
            logger.error(f"Tick verisi alınırken hata: {e}")
            return {}
    
    def get_symbols_info(self) -> pd.DataFrame:
        """
        Tüm sembollerin bilgilerini al
        
        Returns:
            pd.DataFrame: Sembol bilgileri DataFrame'i
        """
        try:
            return self.broker.get_symbols_info()
        except Exception as e:
            logger.error(f"Sembol bilgileri alınırken hata: {e}")
            return pd.DataFrame()
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        Belirli bir sembolün bilgilerini al
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            
        Returns:
            Dict: Sembol bilgileri sözlüğü
        """
        try:
            return self.broker.get_symbol_info(symbol)
        except Exception as e:
            logger.error(f"Sembol bilgisi alınırken hata: {e}")
            return {}
    
    def save_historical_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> bool:
        """
        Tarihsel veriyi dosyaya kaydet
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            timeframe: Zaman dilimi (örn. "H1", "D1")
            data: Tarihsel veri DataFrame'i
            
        Returns:
            bool: Kayıt başarılıysa True, aksi halde False
        """
        try:
            filename = f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d')}.csv"
            filepath = os.path.join(self.historical_data_dir, filename)
            
            # CSV'ye kaydet
            data.to_csv(filepath, index=True)
            logger.info(f"Tarihsel veri kaydedildi: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Tarihsel veri kaydedilirken hata: {e}")
            return False
    
    def load_historical_data(self, symbol: str, timeframe: str, 
                            date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Tarihsel veriyi dosyadan yükle
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            timeframe: Zaman dilimi (örn. "H1", "D1")
            date: Veri tarihi (belirtilmezse en son tarih)
            
        Returns:
            pd.DataFrame: Tarihsel veri DataFrame'i
        """
        try:
            if date is None:
                # En son dosyayı bul
                pattern = f"{symbol}_{timeframe}_*.csv"
                files = [f for f in os.listdir(self.historical_data_dir) 
                        if f.startswith(f"{symbol}_{timeframe}_") and f.endswith(".csv")]
                
                if not files:
                    logger.warning(f"Kayıtlı veri bulunamadı: {symbol}_{timeframe}")
                    return pd.DataFrame()
                
                # En son dosyayı seç
                files.sort(reverse=True)
                filepath = os.path.join(self.historical_data_dir, files[0])
            else:
                # Belirli tarih için dosyayı bul
                filename = f"{symbol}_{timeframe}_{date.strftime('%Y%m%d')}.csv"
                filepath = os.path.join(self.historical_data_dir, filename)
                
                if not os.path.exists(filepath):
                    logger.warning(f"Belirtilen tarih için kayıtlı veri bulunamadı: {filename}")
                    return pd.DataFrame()
            
            # CSV'den oku
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            return df
        except Exception as e:
            logger.error(f"Tarihsel veri yüklenirken hata: {e}")
            return pd.DataFrame()
    
    def update_market_data(self) -> Dict[str, bool]:
        """
        Tüm sembollerin piyasa verilerini güncelle
        
        Returns:
            Dict[str, bool]: Her sembol için güncelleme başarı durumu
        """
        results = {}
        symbols = self.settings.get("symbols", ["EURUSD", "GBPUSD", "XAUUSD"])
        timeframes = self.settings.get("timeframes", ["M5", "M15", "H1", "H4", "D1"])
        
        for symbol in symbols:
            try:
                symbol_results = {}
                for timeframe in timeframes:
                    # Son 1000 çubuğu al
                    df = self.get_historical_data(symbol, timeframe, use_cache=False)
                    
                    # Veriyi önbelleğe ekle (son durumu)
                    cache_key = f"{symbol}_{timeframe}_latest"
                    self.market_data_cache[cache_key] = df
                    
                    # Veriyi diske kaydet (opsiyonel)
                    if self.settings.get("save_historical_data", False):
                        self.save_historical_data(symbol, timeframe, df)
                    
                    symbol_results[timeframe] = not df.empty
                
                results[symbol] = symbol_results
                logger.info(f"{symbol} için piyasa verileri güncellendi")
            except Exception as e:
                logger.error(f"{symbol} piyasa verileri güncellenirken hata: {e}")
                results[symbol] = {"error": str(e)}
                
        return results
    
    def get_news_data(self, start_date: Optional[datetime] = None, 
                     end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Belirli bir tarih aralığı için haber verilerini al
        
        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            
        Returns:
            pd.DataFrame: Haber verileri DataFrame'i
        """
        # Bitiş tarihi belirtilmemişse şu anki zamanı kullan
        if end_date is None:
            end_date = datetime.now(self.timezone)
            
        # Başlangıç tarihi belirtilmemişse son 7 günü kullan
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        try:
            # Önbellek anahtarı oluştur
            cache_key = f"news_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
            
            # Önbellekten kontrol et
            if cache_key in self.news_data_cache:
                return self.news_data_cache[cache_key]
            
            # Forex Factory'den haber verilerini çek (örnek)
            # Gerçek uygulamada bu kısım farklı haber kaynaklarına bağlanabilir
            news_data = self._scrape_forex_factory(start_date, end_date)
            
            # Veriyi önbelleğe ekle
            self.news_data_cache[cache_key] = news_data
            
            return news_data
        except Exception as e:
            logger.error(f"Haber verileri alınırken hata: {e}")
            return pd.DataFrame()
    
    def get_social_media_data(self, symbol: str, 
                             start_date: Optional[datetime] = None, 
                             end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Belirli bir sembol ve tarih aralığı için sosyal medya verilerini al
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            
        Returns:
            pd.DataFrame: Sosyal medya verileri DataFrame'i
        """
        # Bitiş tarihi belirtilmemişse şu anki zamanı kullan
        if end_date is None:
            end_date = datetime.now(self.timezone)
            
        # Başlangıç tarihi belirtilmemişse son 3 günü kullan
        if start_date is None:
            start_date = end_date - timedelta(days=3)
        
        try:
            # Önbellek anahtarı oluştur
            cache_key = f"social_{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
            
            # Önbellekten kontrol et
            if cache_key in self.social_data_cache:
                return self.social_data_cache[cache_key]
            
            # Twitter verilerini çek (örnek)
            # Gerçek uygulamada bu kısım Twitter API'ye bağlanır
            social_data = self._fetch_twitter_data(symbol, start_date, end_date)
            
            # Veriyi önbelleğe ekle
            self.social_data_cache[cache_key] = social_data
            
            return social_data
        except Exception as e:
            logger.error(f"Sosyal medya verileri alınırken hata: {e}")
            return pd.DataFrame()
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Zaman dilimini dakika cinsine çevir
        
        Args:
            timeframe: Zaman dilimi (örn. "M5", "H1", "D1")
            
        Returns:
            int: Dakika cinsinden değer
        """
        timeframe_map = {
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
        
        return timeframe_map.get(timeframe, 60)  # Varsayılan H1

    def _scrape_forex_factory(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Forex Factory'den haber verilerini çek
        
        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            
        Returns:
            pd.DataFrame: Haber verileri DataFrame'i
        """
        # Bu örnekte gerçek bir çekme işlemi yapılmıyor
        # Gerçek uygulamada requests ve BeautifulSoup kullanarak veri çekilir
        
        # Örnek veri oluştur
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        data = []
        
        for date in dates:
            # Her gün için örnek veri ekle
            impact_values = ['High', 'Medium', 'Low']
            currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'NZD', 'CAD', 'CHF']
            
            for _ in range(np.random.randint(0, 5)):  # Her gün için 0-5 arası haber
                hour = np.random.randint(0, 24)
                minute = np.random.randint(0, 60)
                event_datetime = date.replace(hour=hour, minute=minute)
                
                event = {
                    'datetime': event_datetime,
                    'currency': np.random.choice(currencies),
                    'impact': np.random.choice(impact_values),
                    'event': f"Örnek Ekonomik Gösterge {np.random.randint(1, 100)}",
                    'actual': f"{np.random.uniform(-10, 10):.1f}%",
                    'forecast': f"{np.random.uniform(-5, 5):.1f}%",
                    'previous': f"{np.random.uniform(-5, 5):.1f}%"
                }
                
                data.append(event)
        
        # DataFrame oluştur
        df = pd.DataFrame(data)
        if not df.empty:
            df.sort_values('datetime', inplace=True)
            
        return df
    
    def _fetch_twitter_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Twitter'dan belirli bir sembolle ilgili verileri çek
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            
        Returns:
            pd.DataFrame: Twitter verileri DataFrame'i
        """
        # Bu örnekte gerçek bir çekme işlemi yapılmıyor
        # Gerçek uygulamada tweepy kütüphanesi kullanarak Twitter API'den veri çekilir
        
        # Örnek veri oluştur
        dates = pd.date_range(start=start_date, end=end_date, freq='H')
        data = []
        
        for date in dates:
            # Her saat için örnek veri ekle
            sentiment_values = ['positive', 'neutral', 'negative']
            
            # Bazı saatlerde tweet olmayabilir, rastgele atlama
            if np.random.random() < 0.7:  # %70 ihtimalle tweet ekle
                tweet_count = np.random.randint(1, 10)
                sentiment = np.random.choice(sentiment_values, p=[0.3, 0.4, 0.3])
                
                event = {
                    'datetime': date,
                    'symbol': symbol,
                    'tweet_count': tweet_count,
                    'sentiment': sentiment,
                    'sentiment_score': np.random.uniform(-1, 1)
                }
                
                data.append(event)
        
        # DataFrame oluştur
        df = pd.DataFrame(data)
        if not df.empty:
            df.sort_values('datetime', inplace=True)
            
        return df

    def prepare_data_for_model(self, symbol: str, timeframe: str, 
                              lookback_periods: int = 60) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        AI modeli için veri hazırla
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            lookback_periods: Geriye dönük dönem sayısı
            
        Returns:
            Tuple[np.ndarray, pd.DataFrame]: Model için hazırlanan veri ve orijinal DataFrame
        """
        try:
            # Veriyi al
            df = self.get_historical_data(symbol, timeframe)
            
            if df.empty:
                logger.error(f"Model için veri hazırlanamıyor: {symbol}_{timeframe} verisi boş")
                return np.array([]), df
            
            # Teknik indikatörler ekle
            from ta.trend import SMAIndicator, EMAIndicator, MACD
            from ta.momentum import RSIIndicator, StochasticOscillator
            from ta.volatility import BollingerBands
            from ta.volume import VolumeWeightedAveragePrice
            
            # SMA
            df['sma_5'] = SMAIndicator(close=df['close'], window=5).sma_indicator()
            df['sma_20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
            df['sma_50'] = SMAIndicator(close=df['close'], window=50).sma_indicator()
            
            # EMA
            df['ema_5'] = EMAIndicator(close=df['close'], window=5).ema_indicator()
            df['ema_20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()
            df['ema_50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
            
            # MACD
            macd = MACD(close=df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_diff'] = macd.macd_diff()
            
            # RSI
            df['rsi'] = RSIIndicator(close=df['close']).rsi()
            
            # Stochastic
            stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            # Bollinger Bands
            bb = BollingerBands(close=df['close'])
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            
            # NaN'ları doldur
            df.fillna(method='bfill', inplace=True)
            
            # Özellikleri çıkar
            features = ['open', 'high', 'low', 'close', 'volume',
                       'sma_5', 'sma_20', 'sma_50',
                       'ema_5', 'ema_20', 'ema_50',
                       'macd', 'macd_signal', 'macd_diff',
                       'rsi', 'stoch_k', 'stoch_d',
                       'bb_upper', 'bb_middle', 'bb_lower']
            
            # Normalizasyon
            from sklearn.preprocessing import MinMaxScaler
            scaler = MinMaxScaler()
            df_scaled = pd.DataFrame(
                scaler.fit_transform(df[features]),
                columns=features,
                index=df.index
            )
            
            # Dizilere dönüştür
            data_array = df_scaled.values
            
            # Geri döndür
            return data_array, df
        
        except Exception as e:
            logger.error(f"Model için veri hazırlanırken hata: {e}")
            return np.array([]), pd.DataFrame()