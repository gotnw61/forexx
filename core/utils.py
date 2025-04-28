#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için yardımcı fonksiyon modülü.
"""
import os
import logging
import json
import pytz
import time
import math
import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Any

logger = logging.getLogger("ForexTradingBot.Utils")

def generate_uuid() -> str:
    """
    Benzersiz ID oluştur
    
    Returns:
        str: Benzersiz ID
    """
    return str(uuid.uuid4())

def timestamp_to_datetime(timestamp: int, timezone: str = "Europe/Istanbul") -> datetime:
    """
    Unix zaman damgasını datetime nesnesine dönüştür
    
    Args:
        timestamp: Unix zaman damgası (saniye)
        timezone: Zaman dilimi
        
    Returns:
        datetime: Datetime nesnesi
    """
    tz = pytz.timezone(timezone)
    return datetime.fromtimestamp(timestamp, tz=tz)

def datetime_to_timestamp(dt: datetime) -> int:
    """
    Datetime nesnesini Unix zaman damgasına dönüştür
    
    Args:
        dt: Datetime nesnesi
        
    Returns:
        int: Unix zaman damgası (saniye)
    """
    return int(dt.timestamp())

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Datetime nesnesini belirli bir formatta stringe dönüştür
    
    Args:
        dt: Datetime nesnesi
        format_str: Format string
        
    Returns:
        str: Formatlanmış tarih-saat string'i
    """
    return dt.strftime(format_str)

def parse_datetime(datetime_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    String'i datetime nesnesine dönüştür
    
    Args:
        datetime_str: Tarih-saat string'i
        format_str: Format string
        
    Returns:
        datetime: Datetime nesnesi
    """
    return datetime.strptime(datetime_str, format_str)

def calculate_pips(symbol: str, price_difference: float) -> float:
    """
    İki fiyat arasındaki pip farkını hesapla
    
    Args:
        symbol: Döviz çifti
        price_difference: Fiyat farkı
        
    Returns:
        float: Pip farkı
    """
    # Pip değerini belirle
    pip_factor = 10000  # 4 ondalık basamaklı çiftler (EUR/USD, GBP/USD, vb.)
    
    if symbol.endswith("JPY"):
        pip_factor = 100  # 2 ondalık basamaklı çiftler (USD/JPY, EUR/JPY, vb.)
    
    return price_difference * pip_factor

def calculate_price_from_pips(symbol: str, pips: float, base_price: float) -> float:
    """
    Baz fiyat ve pip sayısından yeni fiyat hesapla
    
    Args:
        symbol: Döviz çifti
        pips: Pip sayısı
        base_price: Baz fiyat
        
    Returns:
        float: Hesaplanan fiyat
    """
    # Pip değerini belirle
    pip_factor = 10000  # 4 ondalık basamaklı çiftler (EUR/USD, GBP/USD, vb.)
    
    if symbol.endswith("JPY"):
        pip_factor = 100  # 2 ondalık basamaklı çiftler (USD/JPY, EUR/JPY, vb.)
    
    return base_price + (pips / pip_factor)

def calculate_lot_size(account_balance: float, risk_percentage: float, 
                     stop_loss_pips: float, symbol_value_per_pip: float) -> float:
    """
    Risk yönetimi için lot büyüklüğünü hesapla
    
    Args:
        account_balance: Hesap bakiyesi
        risk_percentage: Risk yüzdesi (0-100)
        stop_loss_pips: Stop Loss seviyesi (pip cinsinden)
        symbol_value_per_pip: Sembolün pip başına değeri
        
    Returns:
        float: Hesaplanan lot büyüklüğü
    """
    # Risk tutarını hesapla
    risk_amount = account_balance * (risk_percentage / 100)
    
    # Lot büyüklüğünü hesapla
    if stop_loss_pips <= 0 or symbol_value_per_pip <= 0:
        return 0.01  # Minimum lot
    
    lot_size = risk_amount / (stop_loss_pips * symbol_value_per_pip)
    
    # Lot büyüklüğünü 0.01'e yuvarla
    lot_size = math.floor(lot_size * 100) / 100
    
    # Minimum lot kontrolü
    if lot_size < 0.01:
        lot_size = 0.01
    
    return lot_size

def calculate_risk_reward_ratio(entry_price: float, stop_loss: float, 
                              take_profit: float) -> float:
    """
    Risk/Ödül oranını hesapla
    
    Args:
        entry_price: Giriş fiyatı
        stop_loss: Stop Loss seviyesi
        take_profit: Take Profit seviyesi
        
    Returns:
        float: Risk/Ödül oranı
    """
    if stop_loss == entry_price:
        return 0
    
    # Long pozisyon
    if take_profit > entry_price:
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
    # Short pozisyon
    else:
        risk = abs(entry_price - stop_loss)
        reward = abs(entry_price - take_profit)
    
    if risk == 0:
        return float('inf')
    
    return reward / risk

def get_candle_pattern(df: pd.DataFrame, window: int = 1) -> List[Dict]:
    """
    Mum formasyonlarını tespit et
    
    Args:
        df: OHLC verileri içeren DataFrame
        window: Tarama penceresi
        
    Returns:
        List[Dict]: Tespit edilen formasyonlar listesi
    """
    patterns = []
    
    # DataFrame'in en az 20 satır içerdiğini kontrol et
    if len(df) < 20:
        return patterns
    
    # Son window sayıda mumu incele
    for i in range(-window, 0):
        idx = len(df) + i
        if idx < 0:
            continue
            
        row = df.iloc[idx]
        prev_row = df.iloc[idx - 1] if idx > 0 else None
        
        # Mum gövdesi ve gölgelerini hesapla
        body = abs(row['close'] - row['open'])
        upper_shadow = row['high'] - max(row['open'], row['close'])
        lower_shadow = min(row['open'], row['close']) - row['low']
        
        # Mum yönünü belirle
        is_bullish = row['close'] > row['open']
        
        # Çeşitli mum formasyonlarını kontrol et
        
        # Doji (gövde çok küçük)
        if body < 0.1 * (row['high'] - row['low']):
            patterns.append({
                'index': idx,
                'pattern': 'Doji',
                'direction': 'neutral',
                'strength': 'medium'
            })
            continue
        
        # Çekiç/Asılı Adam (küçük gövde, uzun alt gölge, kısa üst gölge)
        if lower_shadow > 2 * body and upper_shadow < 0.3 * body:
            if is_bullish:
                patterns.append({
                    'index': idx,
                    'pattern': 'Hammer',
                    'direction': 'bullish',
                    'strength': 'strong'
                })
            else:
                patterns.append({
                    'index': idx,
                    'pattern': 'Hanging Man',
                    'direction': 'bearish',
                    'strength': 'strong'
                })
            continue
        
        # Yutan (Engulfing) Formasyon
        if prev_row is not None:
            prev_body = abs(prev_row['close'] - prev_row['open'])
            
            if is_bullish and not (prev_row['close'] > prev_row['open']):
                if (row['open'] <= prev_row['close'] and 
                    row['close'] >= prev_row['open'] and 
                    body > prev_body):
                    patterns.append({
                        'index': idx,
                        'pattern': 'Bullish Engulfing',
                        'direction': 'bullish',
                        'strength': 'strong'
                    })
                    continue
            elif not is_bullish and (prev_row['close'] > prev_row['open']):
                if (row['open'] >= prev_row['close'] and 
                    row['close'] <= prev_row['open'] and 
                    body > prev_body):
                    patterns.append({
                        'index': idx,
                        'pattern': 'Bearish Engulfing',
                        'direction': 'bearish',
                        'strength': 'strong'
                    })
                    continue
        
        # Kuyruklu Yıldız (Shooting Star) / Çekiç Tersi
        if upper_shadow > 2 * body and lower_shadow < 0.3 * body:
            if is_bullish:
                patterns.append({
                    'index': idx,
                    'pattern': 'Inverted Hammer',
                    'direction': 'bullish',
                    'strength': 'medium'
                })
            else:
                patterns.append({
                    'index': idx,
                    'pattern': 'Shooting Star',
                    'direction': 'bearish',
                    'strength': 'strong'
                })
            continue
    
    return patterns

def find_support_resistance(df: pd.DataFrame, window: int = 10, 
                          threshold: float = 0.0005) -> Dict[str, List[float]]:
    """
    Destek ve direnç seviyelerini bul
    
    Args:
        df: OHLC verileri içeren DataFrame
        window: Tarama penceresi
        threshold: Seviye saptama eşiği
        
    Returns:
        Dict[str, List[float]]: Destek ve direnç seviyeleri
    """
    result = {
        'support': [],
        'resistance': []
    }
    
    # DataFrame'in en az 20 satır içerdiğini kontrol et
    if len(df) < 20:
        return result
    
    # Potansiyel destek ve direnç noktalarını bul
    for i in range(window, len(df) - window):
        # Düşük değerler için destek kontrolü
        if all(df.iloc[i]['low'] <= df.iloc[i-j]['low'] for j in range(1, window+1)) and \
           all(df.iloc[i]['low'] <= df.iloc[i+j]['low'] for j in range(1, window+1)):
            result['support'].append(df.iloc[i]['low'])
        
        # Yüksek değerler için direnç kontrolü
        if all(df.iloc[i]['high'] >= df.iloc[i-j]['high'] for j in range(1, window+1)) and \
           all(df.iloc[i]['high'] >= df.iloc[i+j]['high'] for j in range(1, window+1)):
            result['resistance'].append(df.iloc[i]['high'])
    
    # Birbirine çok yakın seviyeleri birleştir
    result['support'] = merge_close_levels(result['support'], threshold)
    result['resistance'] = merge_close_levels(result['resistance'], threshold)
    
    return result

def merge_close_levels(levels: List[float], threshold: float) -> List[float]:
    """
    Birbirine yakın seviyeleri birleştir
    
    Args:
        levels: Seviye listesi
        threshold: Birleştirme eşiği
        
    Returns:
        List[float]: Birleştirilmiş seviyeler
    """
    if not levels:
        return []
    
    # Seviyeleri sırala
    levels = sorted(levels)
    
    # Birleştirilmiş seviyeleri tut
    merged = [levels[0]]
    
    for level in levels[1:]:
        # Son seviye ile mevcut seviye arasındaki farkı kontrol et
        if abs(level - merged[-1]) / merged[-1] <= threshold:
            # Birleştir (ortalama al)
            merged[-1] = (merged[-1] + level) / 2
        else:
            # Yeni seviye ekle
            merged.append(level)
    
    return merged

def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """
    Average True Range (ATR) hesapla
    
    Args:
        df: OHLC verileri içeren DataFrame
        period: Hesaplama periyodu
        
    Returns:
        float: ATR değeri
    """
    if len(df) < period:
        return 0
    
    # True Range hesapla
    df_local = df.copy()
    df_local['prev_close'] = df_local['close'].shift(1)
    
    tr1 = df_local['high'] - df_local['low']
    tr2 = abs(df_local['high'] - df_local['prev_close'])
    tr3 = abs(df_local['low'] - df_local['prev_close'])
    
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    
    # ATR hesapla
    atr = tr.rolling(window=period).mean().iloc[-1]
    
    return atr

def detect_trend(df: pd.DataFrame, period: int = 20) -> str:
    """
    Fiyat trendini tespit et
    
    Args:
        df: OHLC verileri içeren DataFrame
        period: Trend belirleme periyodu
        
    Returns:
        str: Trend yönü ('bullish', 'bearish', 'sideways')
    """
    if len(df) < period:
        return 'sideways'
    
    # Son period sayıda kapanış fiyatını al
    close_prices = df['close'].iloc[-period:]
    
    # Trend belirleme yöntemi: Doğrusal regresyon eğimi
    x = np.arange(len(close_prices))
    y = close_prices.values
    
    A = np.vstack([x, np.ones(len(x))]).T
    slope, _ = np.linalg.lstsq(A, y, rcond=None)[0]
    
    # Eğime göre trend belirle
    if slope > 0.0001:
        return 'bullish'
    elif slope < -0.0001:
        return 'bearish'
    else:
        return 'sideways'

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float:
    """
    Relative Strength Index (RSI) hesapla
    
    Args:
        df: OHLC verileri içeren DataFrame
        period: Hesaplama periyodu
        
    Returns:
        float: RSI değeri
    """
    if len(df) < period + 1:
        return 50  # Varsayılan değer
    
    # Fiyat değişimleri
    delta = df['close'].diff()
    
    # Artış ve düşüşleri ayır
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # İlk ortalama değerler
    avg_gain = gain.rolling(window=period).mean().iloc[-1]
    avg_loss = loss.rolling(window=period).mean().iloc[-1]
    
    # RS ve RSI hesapla
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def moving_average_crossover(df: pd.DataFrame, fast_period: int = 20, 
                            slow_period: int = 50) -> str:
    """
    Hareketli ortalama kesişim sinyali oluştur
    
    Args:
        df: OHLC verileri içeren DataFrame
        fast_period: Hızlı MA periyodu
        slow_period: Yavaş MA periyodu
        
    Returns:
        str: Sinyal ('buy', 'sell', 'neutral')
    """
    if len(df) < slow_period + 2:
        return 'neutral'
    
    # Hareketli ortalamaları hesapla
    df['fast_ma'] = df['close'].rolling(window=fast_period).mean()
    df['slow_ma'] = df['close'].rolling(window=slow_period).mean()
    
    # Kesişim kontrolü
    if (df['fast_ma'].iloc[-2] <= df['slow_ma'].iloc[-2] and 
        df['fast_ma'].iloc[-1] > df['slow_ma'].iloc[-1]):
        return 'buy'
        
    elif (df['fast_ma'].iloc[-2] >= df['slow_ma'].iloc[-2] and 
          df['fast_ma'].iloc[-1] < df['slow_ma'].iloc[-1]):
        return 'sell'
    
    return 'neutral'

def bollinger_bands_signal(df: pd.DataFrame, period: int = 20, 
                         std_dev: float = 2.0) -> str:
    """
    Bollinger Bantları sinyali oluştur
    
    Args:
        df: OHLC verileri içeren DataFrame
        period: Hesaplama periyodu
        std_dev: Standart sapma faktörü
        
    Returns:
        str: Sinyal ('buy', 'sell', 'neutral')
    """
    if len(df) < period:
        return 'neutral'
    
    # Hareketli ortalama (orta bant)
    df['middle_band'] = df['close'].rolling(window=period).mean()
    
    # Standart sapma
    df['std_dev'] = df['close'].rolling(window=period).std()
    
    # Üst ve alt bantlar
    df['upper_band'] = df['middle_band'] + (df['std_dev'] * std_dev)
    df['lower_band'] = df['middle_band'] - (df['std_dev'] * std_dev)
    
    # Sinyal oluştur
    if df['close'].iloc[-1] > df['upper_band'].iloc[-1]:
        return 'sell'  # Üst banttan aşırı alım
        
    elif df['close'].iloc[-1] < df['lower_band'].iloc[-1]:
        return 'buy'  # Alt banttan aşırı satım
    
    return 'neutral'

def macd_signal(df: pd.DataFrame, fast_period: int = 12, 
               slow_period: int = 26, signal_period: int = 9) -> str:
    """
    MACD sinyali oluştur
    
    Args:
        df: OHLC verileri içeren DataFrame
        fast_period: Hızlı EMA periyodu
        slow_period: Yavaş EMA periyodu
        signal_period: Sinyal çizgisi periyodu
        
    Returns:
        str: Sinyal ('buy', 'sell', 'neutral')
    """
    if len(df) < slow_period + signal_period:
        return 'neutral'
    
    # Hızlı ve yavaş EMA hesapla
    df['fast_ema'] = df['close'].ewm(span=fast_period, adjust=False).mean()
    df['slow_ema'] = df['close'].ewm(span=slow_period, adjust=False).mean()
    
    # MACD çizgisi
    df['macd'] = df['fast_ema'] - df['slow_ema']
    
    # Sinyal çizgisi
    df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
    
    # MACD Histogramı
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Kesişim kontrolü
    if (df['macd'].iloc[-2] <= df['macd_signal'].iloc[-2] and 
        df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]):
        return 'buy'
        
    elif (df['macd'].iloc[-2] >= df['macd_signal'].iloc[-2] and 
          df['macd'].iloc[-1] < df['macd_signal'].iloc[-1]):
        return 'sell'
    
    return 'neutral'

def save_json(data: Any, file_path: str) -> bool:
    """
    Veriyi JSON dosyasına kaydet
    
    Args:
        data: Kaydedilecek veri
        file_path: Dosya yolu
        
    Returns:
        bool: Kayıt başarılıysa True, aksi halde False
    """
    try:
        # Dizini oluştur
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # JSON olarak kaydet
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        return True
    except Exception as e:
        logger.error(f"JSON kaydetme hatası: {e}")
        return False

def load_json(file_path: str) -> Optional[Any]:
    """
    JSON dosyasından veri yükle
    
    Args:
        file_path: Dosya yolu
        
    Returns:
        Optional[Any]: Yüklenen veri veya None (hata durumunda)
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Dosya bulunamadı: {file_path}")
            return None
            
        # JSON'dan yükle
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON yükleme hatası: {e}")
        return None

def retry(func, max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0,
         exceptions: Optional[tuple] = None):
    """
    Fonksiyonu belirli sayıda yeniden deneme ile çalıştırmak için dekoratör
    
    Args:
        func: Çalıştırılacak fonksiyon
        max_attempts: Maksimum deneme sayısı
        delay: İlk bekleme süresi (saniye)
        backoff: Bekleme süresi çarpanı
        exceptions: Yakalanacak istisna türleri
        
    Returns:
        Fonksiyon sonucu
    """
    if exceptions is None:
        exceptions = (Exception,)
        
    def wrapper(*args, **kwargs):
        attempts = 0
        current_delay = delay
        
        while attempts < max_attempts:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                attempts += 1
                if attempts == max_attempts:
                    logger.error(f"Fonksiyon çağrısı {max_attempts} denemeden sonra başarısız: {e}")
                    raise
                
                logger.warning(f"Fonksiyon çağrısı başarısız (deneme {attempts}/{max_attempts}): {e}")
                logger.info(f"{current_delay} saniye sonra tekrar deneniyor...")
                
                time.sleep(current_delay)
                current_delay *= backoff
                
    return wrapper