#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için MetaTrader 5 bağlantı modülü.
MT5 ile emir gönderme, veri alma ve hesap bilgilerine erişim sağlar.
"""
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
import pandas as pd
import numpy as np
import pytz

# MetaTrader 5 modülünü koşullu olarak içe aktar
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

logger = logging.getLogger("ForexTradingBot.BrokerConnector")

class BrokerConnector:
    """
    MetaTrader 5 ile iletişim ve emirleri yönetmek için broker bağlantı sınıfı
    """
    
    def __init__(self, settings_manager):
        """
        Broker bağlantısını başlat
        
        Args:
            settings_manager: Ayarlar yöneticisi veya ayarlar sözlüğü
        """
        # settings_manager bir SettingsManager mı yoksa doğrudan ayarlar sözlüğü mü?
        if hasattr(settings_manager, 'settings'):
            # SettingsManager nesnesi
            self.settings_manager = settings_manager
            self.settings = settings_manager.settings
            self.api_keys = settings_manager.api_keys
        else:
            # Doğrudan ayarlar sözlüğü
            self.settings_manager = None
            self.settings = settings_manager
            self.api_keys = settings_manager.get('api_keys', {})
        
        self.connected = False
        self.timezone = pytz.timezone(self.settings.get("timezone", "Europe/Istanbul"))
        
        # Zaman dilimi haritalaması
        self.timeframe_map = {
            "M1": mt5.TIMEFRAME_M1 if mt5 else 1,
            "M5": mt5.TIMEFRAME_M5 if mt5 else 5,
            "M15": mt5.TIMEFRAME_M15 if mt5 else 15,
            "M30": mt5.TIMEFRAME_M30 if mt5 else 30, 
            "H1": mt5.TIMEFRAME_H1 if mt5 else 60,
            "H4": mt5.TIMEFRAME_H4 if mt5 else 240,
            "D1": mt5.TIMEFRAME_D1 if mt5 else 1440,
            "W1": mt5.TIMEFRAME_W1 if mt5 else 10080,
            "MN1": mt5.TIMEFRAME_MN1 if mt5 else 43200
        }
        
        logger.info("Broker bağlantısı başlatıldı")
    
    def connect(self) -> bool:
        """
        MetaTrader 5'e bağlan
        
        Returns:
            bool: Bağlantı başarılıysa True, aksi halde False
        """
        if self.connected:
            logger.info("Zaten MT5'e bağlı")
            return True
            
        if mt5 is None:
            logger.error("MetaTrader5 modülü yüklü değil. Demo modunda çalışılacak.")
            # MT5 yüklü değilse bile UI'ın çalışmasına izin ver
            self.connected = False
            return False
            
        try:
            # Ayarları al
            mt5_settings = self.settings.get("mt5", {})
            mt5_path = mt5_settings.get("path", "C:/Program Files/FTMO Global Markets MT5 Terminal/terminal64.exe")
            
            # API anahtarlarını al
            api_keys = (self.api_keys if hasattr(self, 'api_keys') 
                        else self.settings.get('api_keys', {}).get('mt5', {}))
            
            login = api_keys.get("login")
            password = api_keys.get("password")
            server = api_keys.get("server")
            
            # MT5'e bağlan
            if not mt5.initialize(path=mt5_path):
                logger.error(f"MT5 başlatma hatası: {mt5.last_error()}")
                return False
            
            # Hesaba giriş yap
            if login and password and server:
                login = int(login) if isinstance(login, (str, int)) else None
                
                if login and not mt5.login(login=login, password=str(password), server=str(server)):
                    logger.error(f"MT5 hesap girişi başarısız: {mt5.last_error()}")
                    self.connected = False
                    return False
                    
                logger.info(f"MT5 hesabına giriş yapıldı ({login}@{server})")
            
            self.connected = True
            logger.info("MT5 bağlantısı başarılı")
            
            return True
        except Exception as e:
            logger.error(f"MT5 bağlantı hatası: {e}", exc_info=True)
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        MetaTrader 5 bağlantısını kapat
        
        Returns:
            bool: İşlem başarılıysa True, aksi halde False
        """
        if not self.connected:
            logger.info("Zaten bağlantı kesilmiş")
            return True
            
        try:
            if mt5:
                mt5.shutdown()
                
            self.connected = False
            logger.info("MT5 bağlantısı kapatıldı")
            return True
        except Exception as e:
            logger.error(f"MT5 bağlantısı kapatılırken hata: {e}")
            return False
    
    def get_account_info(self) -> Dict:
        """
        Hesap bilgilerini al
        
        Returns:
            Dict: Hesap bilgileri sözlüğü
        """
        if not self._ensure_connection():
            return {}
            
        try:
            account_info = mt5.account_info()
            if account_info:
                # NamedTuple'ı sözlüğe dönüştür
                return {
                    "login": account_info.login,
                    "server": account_info.server,
                    "balance": account_info.balance,
                    "equity": account_info.equity,
                    "margin": account_info.margin,
                    "free_margin": account_info.margin_free,
                    "margin_level": account_info.margin_level,
                    "currency": account_info.currency,
                    "profit": account_info.profit,
                    "leverage": account_info.leverage,
                    "trade_mode": "Gerçek" if account_info.trade_mode == 0 else "Demo"
                }
            else:
                logger.error(f"Hesap bilgileri alınamadı: {mt5.last_error()}")
                return {}
        except Exception as e:
            logger.error(f"Hesap bilgileri alınırken hata: {e}")
            return {}
    
    def get_positions(self) -> pd.DataFrame:
        """
        Açık pozisyonları al
        
        Returns:
            pd.DataFrame: Açık pozisyonlar DataFrame'i
        """
        if not self._ensure_connection():
            return pd.DataFrame()
            
        try:
            positions = mt5.positions_get()
            if positions:
                # Pozisyonları DataFrame'e dönüştür
                df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
                
                # İşlem yönünü metin olarak ekle
                df['direction'] = df['type'].apply(lambda x: 'BUY' if x == 0 else 'SELL')
                
                # Zaman damgasını datetime'a dönüştür
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df['time_update'] = pd.to_datetime(df['time_update'], unit='s')
                
                return df
            else:
                if mt5.last_error()[0] != 0:
                    logger.warning(f"Açık pozisyonlar alınamadı: {mt5.last_error()}")
                # Açık pozisyon yoksa boş DataFrame döndür
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Açık pozisyonlar alınırken hata: {e}")
            return pd.DataFrame()
    
    def get_position(self, position_id: int) -> Dict:
        """
        Belirli bir pozisyonun bilgilerini al
        
        Args:
            position_id: Pozisyon kimliği
            Returns:
            Dict: Pozisyon bilgileri sözlüğü veya boş sözlük
        """
        if not self._ensure_connection():
            return {}
            
        try:
            positions = mt5.positions_get(ticket=position_id)
            if positions:
                # NamedTuple'ı sözlüğe dönüştür
                position = positions[0]._asdict()
                
                # İşlem yönünü metin olarak ekle
                position['direction'] = 'BUY' if position['type'] == 0 else 'SELL'
                
                # Zaman damgasını datetime'a dönüştür
                position['time'] = datetime.fromtimestamp(position['time'], tz=self.timezone)
                position['time_update'] = datetime.fromtimestamp(position['time_update'], tz=self.timezone)
                
                return position
            else:
                logger.warning(f"Pozisyon bulunamadı (ID: {position_id}): {mt5.last_error()}")
                return {}
        except Exception as e:
            logger.error(f"Pozisyon bilgileri alınırken hata: {e}")
            return {}
    
    def get_orders(self) -> pd.DataFrame:
        """
        Bekleyen emirleri al
        
        Returns:
            pd.DataFrame: Bekleyen emirler DataFrame'i
        """
        if not self._ensure_connection():
            return pd.DataFrame()
            
        try:
            orders = mt5.orders_get()
            if orders:
                # Emirleri DataFrame'e dönüştür
                df = pd.DataFrame(list(orders), columns=orders[0]._asdict().keys())
                
                # İşlem yönünü metin olarak ekle
                df['direction'] = df['type'].apply(lambda x: 'BUY' if x in [0, 2, 4, 6] else 'SELL')
                
                # Emir tipini metin olarak ekle
                order_types = {
                    0: 'BUY',
                    1: 'SELL',
                    2: 'BUY_LIMIT',
                    3: 'SELL_LIMIT',
                    4: 'BUY_STOP',
                    5: 'SELL_STOP',
                    6: 'BUY_STOP_LIMIT',
                    7: 'SELL_STOP_LIMIT'
                }
                df['order_type'] = df['type'].apply(lambda x: order_types.get(x, 'UNKNOWN'))
                
                # Zaman damgasını datetime'a dönüştür
                df['time_setup'] = pd.to_datetime(df['time_setup'], unit='s')
                
                return df
            else:
                if mt5.last_error()[0] != 0:
                    logger.warning(f"Bekleyen emirler alınamadı: {mt5.last_error()}")
                # Bekleyen emir yoksa boş DataFrame döndür
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Bekleyen emirler alınırken hata: {e}")
            return pd.DataFrame()
    
    def get_order_history(self, start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Emir geçmişini al
        
        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            Returns:
            pd.DataFrame: Emir geçmişi DataFrame'i
        """
        if not self._ensure_connection():
            return pd.DataFrame()
            
        try:
            # Bitiş tarihi belirtilmemişse şu anki zamanı kullan
            if end_date is None:
                end_date = datetime.now(self.timezone)
                
            # Başlangıç tarihi belirtilmemişse son 7 günü kullan
            if start_date is None:
                start_date = end_date - timedelta(days=7)
            
            # Zaman aralığını belirle
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            # Emir geçmişini al
            history = mt5.history_orders_get(start_timestamp, end_timestamp)
            
            if history:
                # Emirleri DataFrame'e dönüştür
                df = pd.DataFrame(list(history), columns=history[0]._asdict().keys())
                
                # İşlem yönünü metin olarak ekle
                df['direction'] = df['type'].apply(lambda x: 'BUY' if x in [0, 2, 4, 6] else 'SELL')
                
                # Emir tipini metin olarak ekle
                order_types = {
                    0: 'BUY',
                    1: 'SELL',
                    2: 'BUY_LIMIT',
                    3: 'SELL_LIMIT',
                    4: 'BUY_STOP',
                    5: 'SELL_STOP',
                    6: 'BUY_STOP_LIMIT',
                    7: 'SELL_STOP_LIMIT'
                }
                df['order_type'] = df['type'].apply(lambda x: order_types.get(x, 'UNKNOWN'))
                
                # Zaman damgasını datetime'a dönüştür
                for col in ['time_setup', 'time_done']:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], unit='s')
                
                return df
            else:
                if mt5.last_error()[0] != 0:
                    logger.warning(f"Emir geçmişi alınamadı: {mt5.last_error()}")
                # Geçmiş emir yoksa boş DataFrame döndür
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Emir geçmişi alınırken hata: {e}")
            return pd.DataFrame()
    
    def get_trade_history(self, start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        İşlem geçmişini al
        
        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            Returns:
            pd.DataFrame: İşlem geçmişi DataFrame'i
        """
        if not self._ensure_connection():
            return pd.DataFrame()
            
        try:
            # Bitiş tarihi belirtilmemişse şu anki zamanı kullan
            if end_date is None:
                end_date = datetime.now(self.timezone)
                
            # Başlangıç tarihi belirtilmemişse son 7 günü kullan
            if start_date is None:
                start_date = end_date - timedelta(days=7)
            
            # Zaman aralığını belirle
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            # İşlem geçmişini al
            history = mt5.history_deals_get(start_timestamp, end_timestamp)
            
            if history:
                # İşlemleri DataFrame'e dönüştür
                df = pd.DataFrame(list(history), columns=history[0]._asdict().keys())
                
                # İşlem yönünü metin olarak ekle
                df['direction'] = df['type'].apply(lambda x: 'BUY' if x == 0 else 'SELL')
                
                # İşlem giriş tipini metin olarak ekle
                entry_types = {
                    0: 'IN',     # Giriş
                    1: 'OUT',    # Çıkış
                    2: 'INOUT',  # Ter yön
                    3: 'OUTBY'   # Kapat
                }
                df['entry_type'] = df['entry'].apply(lambda x: entry_types.get(x, 'UNKNOWN'))
                
                # Zaman damgasını datetime'a dönüştür
                df['time'] = pd.to_datetime(df['time'], unit='s')
                
                return df
            else:
                if mt5.last_error()[0] != 0:
                    logger.warning(f"İşlem geçmişi alınamadı: {mt5.last_error()}")
                # Geçmiş işlem yoksa boş DataFrame döndür
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"İşlem geçmişi alınırken hata: {e}")
            return pd.DataFrame()
    
    def get_historical_data(self, symbol: str, timeframe: str, 
                           start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Belirli bir sembol ve zaman dilimi için tarihsel veriyi al
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            timeframe: Zaman dilimi (örn. "H1", "D1")
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            Returns:
            pd.DataFrame: Tarihsel veri DataFrame'i
        """
        if not self._ensure_connection():
            return pd.DataFrame()
            
        try:
            # Bitiş tarihi belirtilmemişse şu anki zamanı kullan
            if end_date is None:
                end_date = datetime.now(self.timezone)
                
            # Başlangıç tarihi belirtilmemişse son 1000 çubuğu kullan
            if start_date is None:
                # Zaman dilimini dakika cinsine çevir
                tf_minutes = self._get_timeframe_minutes(timeframe)
                start_date = end_date - timedelta(minutes=tf_minutes * 1000)
            
            # Zaman aralığını belirle
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            # MT5 zaman dilimini al
            mt5_timeframe = self.timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)
            
            # Tarihsel veriyi al
            rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_timestamp, end_timestamp)
            
            if rates is not None and len(rates) > 0:
                # Numpy dizisini DataFrame'e dönüştür
                df = pd.DataFrame(rates)
                
                # Zaman damgasını datetime'a dönüştür
                df['time'] = pd.to_datetime(df['time'], unit='s')
                
                # datetime'ı indeks olarak ayarla
                df.set_index('time', inplace=True)
                
                return df
            else:
                error = mt5.last_error()
                if error[0] != 0:
                    logger.warning(f"Tarihsel veri alınamadı ({symbol}, {timeframe}): {error}")
                # Veri yoksa boş DataFrame döndür
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Tarihsel veri alınırken hata ({symbol}, {timeframe}): {e}")
            return pd.DataFrame()
    
    def get_last_tick(self, symbol: str) -> Dict:
        """
        Belirli bir sembol için en son tick verisini al
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            Returns:
            Dict: Tick verisi sözlüğü
        """
        if not self._ensure_connection():
            return {}
            
        try:
            # Son tick verisini al
            tick = mt5.symbol_info_tick(symbol)
            
            if tick:
                # NamedTuple'ı sözlüğe dönüştür
                tick_dict = tick._asdict()
                
                # Zaman damgasını datetime'a dönüştür
                tick_dict['time'] = datetime.fromtimestamp(tick_dict['time'], tz=self.timezone)
                
                return tick_dict
            else:
                logger.warning(f"Tick verisi alınamadı ({symbol}): {mt5.last_error()}")
                return {}
        except Exception as e:
            logger.error(f"Tick verisi alınırken hata ({symbol}): {e}")
            return {}
    
    def get_symbols_info(self) -> pd.DataFrame:
        """
        Tüm sembollerin bilgilerini al
        
        Returns:
            pd.DataFrame: Sembol bilgileri DataFrame'i
        """
        if not self._ensure_connection():
            return pd.DataFrame()
            
        try:
            # Tüm sembolleri al
            symbols = mt5.symbols_get()
            
            if symbols:
                # Sembolleri DataFrame'e dönüştür
                df = pd.DataFrame([s._asdict() for s in symbols])
                
                # Sadece gerekli sütunları seç
                if not df.empty:
                    columns = ['name', 'description', 'path', 'currency_base', 'currency_profit', 
                              'trade_mode', 'digits', 'point', 'tick_size', 'tick_value', 
                              'contract_size', 'volume_min', 'volume_max', 'volume_step']
                    df = df[[c for c in columns if c in df.columns]]
                
                return df
            else:
                logger.warning(f"Sembol bilgileri alınamadı: {mt5.last_error()}")
                return pd.DataFrame()
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
        if not self._ensure_connection():
            return {}
            
        try:
            # Sembol bilgilerini al
            info = mt5.symbol_info(symbol)
            
            if info:
                # NamedTuple'ı sözlüğe dönüştür
                return info._asdict()
            else:
                logger.warning(f"Sembol bilgisi alınamadı ({symbol}): {mt5.last_error()}")
                return {}
        except Exception as e:
            logger.error(f"Sembol bilgisi alınırken hata ({symbol}): {e}")
            return {}
    
    def open_position(self, symbol: str, order_type: str, volume: float, 
                     price: Optional[float] = None, stop_loss: Optional[float] = None, 
                     take_profit: Optional[float] = None, comment: str = "",
                     magic: int = 0) -> Dict:
        """
        Yeni bir pozisyon aç
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            order_type: İşlem tipi ("BUY" veya "SELL")
            volume: İşlem hacmi (lot)
            price: İşlem fiyatı (market işleminde None)
            stop_loss: Stop Loss seviyesi
            take_profit: Take Profit seviyesi
            comment: İşlem yorumu
            magic: Sihirli numara (expert identifier)
            Returns:
            Dict: İşlem sonucu sözlüğü
        """
        if not self._ensure_connection():
            return {"error": "MT5 bağlantısı yok"}
            
        # Gerçek hesapta işlem kontrolü
        if self.settings.get("mt5", {}).get("enable_real_trading", False) is False:
            account_info = self.get_account_info()
            if account_info.get("trade_mode") == "Gerçek":
                logger.warning("Gerçek hesapta işlem yapma devre dışı")
                return {"error": "Gerçek hesapta işlem yapma devre dışı"}
        
        try:
            # İşlem tipini belirle
            if order_type.upper() == "BUY":
                mt5_order_type = mt5.ORDER_TYPE_BUY
            elif order_type.upper() == "SELL":
                mt5_order_type = mt5.ORDER_TYPE_SELL
            else:
                logger.error(f"Geçersiz işlem tipi: {order_type}")
                return {"error": f"Geçersiz işlem tipi: {order_type}"}
            
            # Sembol bilgilerini al
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Sembol bulunamadı: {symbol}")
                return {"error": f"Sembol bulunamadı: {symbol}"}
            
            # Sembolün ticaret için uygun olup olmadığını kontrol et
            if not symbol_info.visible:
                # Sembolü piyasa gözlemine ekle
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"Sembol seçilemedi: {symbol}")
                    return {"error": f"Sembol seçilemedi: {symbol}"}
            
            # Son tick fiyatını al
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Tick verisi alınamadı: {symbol}")
                return {"error": f"Tick verisi alınamadı: {symbol}"}
            
            # İşlem fiyatını belirle (market işleminde son fiyat)
            if price is None:
                price = tick.ask if mt5_order_type == mt5.ORDER_TYPE_BUY else tick.bid
            
            # İşlem parametrelerini oluştur
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_order_type,
                "price": price,
                "deviation": 10,  # Fiyat sapma toleransı (pip)
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancelled
                "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate Or Cancel
            }
            
            # Stop Loss ve Take Profit ekle (varsa)
            if stop_loss is not None:
                request["sl"] = stop_loss
            if take_profit is not None:
                request["tp"] = take_profit
            
            # İşlemi gönder
            result = mt5.order_send(request)
            
            # Sonucu kontrol et
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"İşlem başarıyla açıldı: {symbol} {order_type} {volume} lot")
                
                # Başarılı işlem bilgilerini döndür
                return {
                    "ticket": result.order,
                    "symbol": symbol,
                    "volume": volume,
                    "price": result.price,
                    "type": order_type,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "comment": comment,
                    "time": datetime.now(self.timezone)
                }
            else:
                logger.error(f"İşlem açma hatası: {result.retcode} - {self._get_error_description(result.retcode)}")
                return {
                    "error": f"İşlem açma hatası: {result.retcode} - {self._get_error_description(result.retcode)}"
                }
        except Exception as e:
            logger.error(f"İşlem açma sırasında hata: {e}")
            return {"error": f"İşlem açma sırasında hata: {e}"}
    
    def close_position(self, ticket: int, volume: Optional[float] = None, comment: str = "") -> Dict:
        """
        Mevcut bir pozisyonu kapat
        
        Args:
            ticket: Pozisyon bileti (ID)
            volume: Kapatılacak hacim (lot) (None ise tamamı kapatılır)
            comment: İşlem yorumu
            Returns:
            Dict: İşlem sonucu sözlüğü
        """
        if not self._ensure_connection():
            return {"error": "MT5 bağlantısı yok"}
            
        try:
            # Pozisyon bilgilerini al
            position = mt5.positions_get(ticket=ticket)
            if not position:
                logger.error(f"Pozisyon bulunamadı (Ticket: {ticket})")
                return {"error": f"Pozisyon bulunamadı (Ticket: {ticket})"}
            
            position = position[0]
            
            # Kapatılacak hacmi belirle
            if volume is None or volume >= position.volume:
                volume = position.volume
                
            # Ters işlem tipini belirle
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
            else:
                order_type = mt5.ORDER_TYPE_BUY
            
            # Son tick fiyatını al
            tick = mt5.symbol_info_tick(position.symbol)
            if tick is None:
                logger.error(f"Tick verisi alınamadı: {position.symbol}")
                return {"error": f"Tick verisi alınamadı: {position.symbol}"}
            
            # İşlem fiyatını belirle
            price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask
            
            # İşlem parametrelerini oluştur
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 10,  # Fiyat sapma toleransı (pip)
                "magic": position.magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancelled
                "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate Or Cancel
            }
            
            # İşlemi gönder
            result = mt5.order_send(request)
            
            # Sonucu kontrol et
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Pozisyon başarıyla kapatıldı: Ticket {ticket}, {volume} lot")
                
                # Başarılı işlem bilgilerini döndür
                return {
                    "ticket": result.order,
                    "symbol": position.symbol,
                    "volume": volume,
                    "price": result.price,
                    "profit": position.profit,
                    "time": datetime.now(self.timezone)
                }
            else:
                logger.error(f"Pozisyon kapatma hatası: {result.retcode} - {self._get_error_description(result.retcode)}")
                return {
                    "error": f"Pozisyon kapatma hatası: {result.retcode} - {self._get_error_description(result.retcode)}"
                }
        except Exception as e:
            logger.error(f"Pozisyon kapatma sırasında hata: {e}")
            return {"error": f"Pozisyon kapatma sırasında hata: {e}"}
    
    def modify_position(self, ticket: int, stop_loss: Optional[float] = None, 
                       take_profit: Optional[float] = None) -> Dict:
        """
        Mevcut bir pozisyonun Stop Loss ve Take Profit seviyelerini değiştir
        
        Args:
            ticket: Pozisyon bileti (ID)
            stop_loss: Yeni Stop Loss seviyesi
            take_profit: Yeni Take Profit seviyesi
            Returns:
            Dict: İşlem sonucu sözlüğü
        """
        if not self._ensure_connection():
            return {"error": "MT5 bağlantısı yok"}
            
        try:
            # Pozisyon bilgilerini al
            position = mt5.positions_get(ticket=ticket)
            if not position:
                logger.error(f"Pozisyon bulunamadı (Ticket: {ticket})")
                return {"error": f"Pozisyon bulunamadı (Ticket: {ticket})"}
            
            position = position[0]
            
            # Değiştirilecek değerleri kontrol et
            if stop_loss is None and take_profit is None:
                logger.warning("Değiştirilecek değer belirtilmedi")
                return {"error": "Değiştirilecek değer belirtilmedi"}
            
            # Mevcut değerleri koru (değiştirilmeyenler için)
            if stop_loss is None:
                stop_loss = position.sl
            if take_profit is None:
                take_profit = position.tp
            
            # İşlem parametrelerini oluştur
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": ticket,
                "sl": stop_loss,
                "tp": take_profit
            }
            
            # İşlemi gönder
            result = mt5.order_send(request)
            
            # Sonucu kontrol et
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Pozisyon başarıyla değiştirildi: Ticket {ticket}, SL: {stop_loss}, TP: {take_profit}")
                
                # Başarılı işlem bilgilerini döndür
                return {
                    "ticket": ticket,
                    "symbol": position.symbol,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "time": datetime.now(self.timezone)
                }
            else:
                logger.error(f"Pozisyon değiştirme hatası: {result.retcode} - {self._get_error_description(result.retcode)}")
                return {
                    "error": f"Pozisyon değiştirme hatası: {result.retcode} - {self._get_error_description(result.retcode)}"
                }
        except Exception as e:
            logger.error(f"Pozisyon değiştirme sırasında hata: {e}")
            return {"error": f"Pozisyon değiştirme sırasında hata: {e}"}
    
    def place_pending_order(self, symbol: str, order_type: str, volume: float, 
                           price: float, stop_loss: Optional[float] = None, 
                           take_profit: Optional[float] = None, 
                           expiration: Optional[datetime] = None,
                           comment: str = "", magic: int = 0) -> Dict:
        """
        Bekleyen emir oluştur
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            order_type: Emir tipi ("BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP")
            volume: İşlem hacmi (lot)
            price: Emir fiyatı
            stop_loss: Stop Loss seviyesi
            take_profit: Take Profit seviyesi
            expiration: Emir geçerlilik süresi
            comment: İşlem yorumu
            magic: Sihirli numara (expert identifier)
            Returns:
            Dict: İşlem sonucu sözlüğü
        """
        if not self._ensure_connection():
            return {"error": "MT5 bağlantısı yok"}
            
        # Gerçek hesapta işlem kontrolü
        if self.settings.get("mt5", {}).get("enable_real_trading", False) is False:
            account_info = self.get_account_info()
            if account_info.get("trade_mode") == "Gerçek":
                logger.warning("Gerçek hesapta işlem yapma devre dışı")
                return {"error": "Gerçek hesapta işlem yapma devre dışı"}
        
        try:
            # Emir tipini belirle
            order_type_map = {
                "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
                "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
                "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
                "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
                "BUY_STOP_LIMIT": mt5.ORDER_TYPE_BUY_STOP_LIMIT,
                "SELL_STOP_LIMIT": mt5.ORDER_TYPE_SELL_STOP_LIMIT
            }
            
            mt5_order_type = order_type_map.get(order_type.upper())
            if mt5_order_type is None:
                logger.error(f"Geçersiz emir tipi: {order_type}")
                return {"error": f"Geçersiz emir tipi: {order_type}"}
            
            # Sembol bilgilerini al
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Sembol bulunamadı: {symbol}")
                return {"error": f"Sembol bulunamadı: {symbol}"}
            
            # Sembolün ticaret için uygun olup olmadığını kontrol et
            if not symbol_info.visible:
                # Sembolü piyasa gözlemine ekle
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"Sembol seçilemedi: {symbol}")
                    return {"error": f"Sembol seçilemedi: {symbol}"}
            
            # İşlem parametrelerini oluştur
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_order_type,
                "price": price,
                "deviation": 10,  # Fiyat sapma toleransı (pip)
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancelled
                "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate Or Cancel
            }
            
            # Stop Loss ve Take Profit ekle (varsa)
            if stop_loss is not None:
                request["sl"] = stop_loss
            if take_profit is not None:
                request["tp"] = take_profit
            
            # Geçerlilik süresi ekle (varsa)
            if expiration is not None:
                request["type_time"] = mt5.ORDER_TIME_SPECIFIED
                request["expiration"] = int(expiration.timestamp())
            
            # İşlemi gönder
            result = mt5.order_send(request)
            
            # Sonucu kontrol et
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Bekleyen emir başarıyla oluşturuldu: {symbol} {order_type} {volume} lot, Fiyat: {price}")
                
                # Başarılı işlem bilgilerini döndür
                return {
                    "ticket": result.order,
                    "symbol": symbol,
                    "volume": volume,
                    "price": price,
                    "type": order_type,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "expiration": expiration,
                    "comment": comment,
                    "time": datetime.now(self.timezone)
                }
            else:
                logger.error(f"Bekleyen emir oluşturma hatası: {result.retcode} - {self._get_error_description(result.retcode)}")
                return {
                    "error": f"Bekleyen emir oluşturma hatası: {result.retcode} - {self._get_error_description(result.retcode)}"
                }
        except Exception as e:
            logger.error(f"Bekleyen emir oluşturma sırasında hata: {e}")
            return {"error": f"Bekleyen emir oluşturma sırasında hata: {e}"}
    
    def cancel_order(self, ticket: int) -> Dict:
        """
        Bekleyen bir emri iptal et
        
        Args:
            ticket: Emir bileti (ID)
            Returns:
            Dict: İşlem sonucu sözlüğü
        """
        if not self._ensure_connection():
            return {"error": "MT5 bağlantısı yok"}
            
        try:
            # Emir bilgilerini al
            order = mt5.orders_get(ticket=ticket)
            if not order:
                logger.error(f"Emir bulunamadı (Ticket: {ticket})")
                return {"error": f"Emir bulunamadı (Ticket: {ticket})"}
            
            # İşlem parametrelerini oluştur
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket
            }
            
            # İşlemi gönder
            result = mt5.order_send(request)
            
            # Sonucu kontrol et
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Emir başarıyla iptal edildi: Ticket {ticket}")
                
                # Başarılı işlem bilgilerini döndür
                return {
                    "ticket": ticket,
                    "status": "cancelled",
                    "time": datetime.now(self.timezone)
                }
            else:
                logger.error(f"Emir iptal hatası: {result.retcode} - {self._get_error_description(result.retcode)}")
                return {
                    "error": f"Emir iptal hatası: {result.retcode} - {self._get_error_description(result.retcode)}"
                }
        except Exception as e:
            logger.error(f"Emir iptal sırasında hata: {e}")
            return {"error": f"Emir iptal sırasında hata: {e}"}
    
    def calculate_margin(self, symbol: str, order_type: str, volume: float) -> Dict:
        """
        Belirli bir işlem için gerekli marjin miktarını hesapla
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            order_type: İşlem tipi ("BUY" veya "SELL")
            volume: İşlem hacmi (lot)
            Returns:
            Dict: Marjin bilgileri sözlüğü
        """
        if not self._ensure_connection():
            return {"error": "MT5 bağlantısı yok"}
            
        try:
            # İşlem tipini belirle
            if order_type.upper() == "BUY":
                mt5_order_type = mt5.ORDER_TYPE_BUY
            elif order_type.upper() == "SELL":
                mt5_order_type = mt5.ORDER_TYPE_SELL
            else:
                logger.error(f"Geçersiz işlem tipi: {order_type}")
                return {"error": f"Geçersiz işlem tipi: {order_type}"}
            
            # Son tick fiyatını al
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Tick verisi alınamadı: {symbol}")
                return {"error": f"Tick verisi alınamadı: {symbol}"}
            
            # İşlem fiyatını belirle
            price = tick.ask if mt5_order_type == mt5.ORDER_TYPE_BUY else tick.bid
            
            # Marjin hesapla
            margin = mt5.order_calc_margin(mt5_order_type, symbol, volume, price)
            
            if margin is not None:
                return {
                    "symbol": symbol,
                    "volume": volume,
                    "type": order_type,
                    "price": price,
                    "margin": margin
                }
            else:
                logger.error(f"Marjin hesaplama hatası: {mt5.last_error()}")
                return {"error": f"Marjin hesaplama hatası: {mt5.last_error()}"}
        except Exception as e:
            logger.error(f"Marjin hesaplama sırasında hata: {e}")
            return {"error": f"Marjin hesaplama sırasında hata: {e}"}
    
    def _ensure_connection(self) -> bool:
        """
        MT5 bağlantısını kontrol et, bağlı değilse bağlanmayı dene
        
        Returns:
            bool: Bağlantı durumu
        """
        if self.connected:
            return True
        
        # Bağlantıyı yeniden dene
        logger.info("MT5 bağlantısı yeniden deneniyor...")
        return self.connect()
    
    def _get_timeframe_minutes(self, timeframe: str) -> int:
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
    
    def _get_error_description(self, retcode: int) -> str:
        """
        MT5 hata koduna göre açıklama döndür
        
        Args:
            retcode: MT5 hata kodu
            Returns:
            str: Hata açıklaması
        """
        error_descriptions = {
            mt5.TRADE_RETCODE_REQUOTE: "Fiyat değişti",
            mt5.TRADE_RETCODE_REJECT: "İstek reddedildi",
            mt5.TRADE_RETCODE_CANCEL: "İstek trader tarafından iptal edildi",
            mt5.TRADE_RETCODE_PLACED: "Emir yerleştirildi",
            mt5.TRADE_RETCODE_DONE: "İstek tamamlandı",
            mt5.TRADE_RETCODE_DONE_PARTIAL: "İstek kısmen tamamlandı",
            mt5.TRADE_RETCODE_ERROR: "İstek işleme hatası",
            mt5.TRADE_RETCODE_TIMEOUT: "İstek zaman aşımına uğradı",
            mt5.TRADE_RETCODE_INVALID: "Geçersiz istek",
            mt5.TRADE_RETCODE_INVALID_VOLUME: "Geçersiz hacim",
            mt5.TRADE_RETCODE_INVALID_PRICE: "Geçersiz fiyat",
            mt5.TRADE_RETCODE_INVALID_STOPS: "Geçersiz stop seviyeleri",
            mt5.TRADE_RETCODE_TRADE_DISABLED: "Ticaret devre dışı",
            mt5.TRADE_RETCODE_MARKET_CLOSED: "Piyasa kapalı",
            mt5.TRADE_RETCODE_NO_MONEY: "Yetersiz bakiye",
            mt5.TRADE_RETCODE_PRICE_CHANGED: "Fiyat değişti",
            mt5.TRADE_RETCODE_PRICE_OFF: "Fiyat kotasyonları yok",
            mt5.TRADE_RETCODE_INVALID_EXPIRATION: "Geçersiz emir geçerlilik süresi",
            mt5.TRADE_RETCODE_ORDER_CHANGED: "Emir durumu değişti",
            mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "Çok fazla istek",
            mt5.TRADE_RETCODE_NO_CHANGES: "İstekte değişiklik yok",
            mt5.TRADE_RETCODE_SERVER_DISABLES_AT: "Sunucu otomatik işlemi devre dışı bıraktı",
            mt5.TRADE_RETCODE_CLIENT_DISABLES_AT: "İstemci otomatik işlemi devre dışı bıraktı",
            mt5.TRADE_RETCODE_LOCKED: "İstek kilitlendi",
            mt5.TRADE_RETCODE_FROZEN: "Emir veya pozisyon donduruldu",
            mt5.TRADE_RETCODE_INVALID_FILL: "Geçersiz doldurma türü",
            mt5.TRADE_RETCODE_CONNECTION: "Sunucu ile bağlantı yok",
            mt5.TRADE_RETCODE_ONLY_REAL: "Sadece gerçek hesaplar için",
            mt5.TRADE_RETCODE_LIMIT_ORDERS: "Bekleyen emirlerin sayısı limitine ulaşıldı",
            mt5.TRADE_RETCODE_LIMIT_VOLUME: "Sembol için emirlerin ve pozisyonların hacim limitine ulaşıldı",
            mt5.TRADE_RETCODE_INVALID_ORDER: "Yanlış veya yasaklanmış emir tipi",
            mt5.TRADE_RETCODE_POSITION_CLOSED: "Belirtilen POSITION_IDENTIFIER ile pozisyon zaten kapalı"
        }
        
        return error_descriptions.get(retcode, f"Bilinmeyen hata kodu: {retcode}")