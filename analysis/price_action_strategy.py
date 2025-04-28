#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için Price Action strateji modülü.
Klasik mum formasyonları, trend analizi ve destek/direnç seviyeleri kullanarak
teknik analiz yapar.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger("ForexTradingBot.PriceActionStrategy")

class PriceActionStrategy:
    """
    Price Action teknik analiz stratejisi uygulayan sınıf.
    """
    
    def __init__(self, data_manager):
        """
        Price Action strateji modülünü başlat
        
        Args:
            data_manager: Veri yöneticisi
        """
        self.data_manager = data_manager
        logger.info("Price Action strateji modülü başlatıldı")
    
    def analyze(self, symbol: str, timeframe: str) -> Dict:
        """
        Belirli bir sembol ve zaman dilimi için Price Action analizi yap
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            timeframe: Zaman dilimi (örn. "H1", "D1")
            
        Returns:
            Dict: Price Action analiz sonuçları
        """
        try:
            # Veriyi al
            df = self.data_manager.get_historical_data(symbol, timeframe)
            
            if df.empty:
                logger.warning(f"Price Action analizi için veri bulunamadı: {symbol} {timeframe}")
                return {"error": "Veri bulunamadı"}
            
            # Sonuçları topla
            results = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.now()
            }
            
            # Trendi belirle
            trend_analysis = self._analyze_trend(df)
            results["trend"] = trend_analysis["trend"]
            results["trend_strength"] = trend_analysis["strength"]
            results["trend_data"] = trend_analysis
            
            # Mum formasyonlarını belirle
            candle_patterns = self._identify_candle_patterns(df)
            results["candle_patterns"] = candle_patterns
            
            # Destek ve direnç seviyelerini belirle
            support_resistance = self._find_support_resistance(df)
            results["support_levels"] = support_resistance["support"]
            results["resistance_levels"] = support_resistance["resistance"]
            
            # Pivot seviyelerini belirle
            pivots = self._calculate_pivot_points(df)
            results["pivots"] = pivots
            
            # Momentum indikatörlerini hesapla
            momentum = self._calculate_momentum(df)
            results["momentum"] = momentum
            
            # Price Action formasyonlarını belirle
            patterns = self._identify_price_patterns(df, support_resistance, trend_analysis)
            results["patterns"] = patterns
            
            # İşlem sinyali oluştur
            signal, strength = self._generate_signal(df, results)
            results["signal"] = signal
            results["strength"] = strength
            
            return results
            
        except Exception as e:
            logger.error(f"Price Action analizi sırasında hata: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _analyze_trend(self, df: pd.DataFrame) -> Dict:
        """
        Trend analizi yap (Hareketli ortalamalar, yüksek/düşük noktalar)
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Trend analizi sonuçları
        """
        results = {
            "trend": "sideways",  # sideways, bullish, bearish
            "strength": 0,         # 0-100 arası
            "ma20_trend": "flat",  # up, down, flat
            "ma50_trend": "flat",  # up, down, flat
            "ma200_trend": "flat", # up, down, flat
            "higher_highs": False,
            "higher_lows": False,
            "lower_highs": False,
            "lower_lows": False,
            "ma_crossover": None   # golden_cross, death_cross, none
        }
        
        try:
            # En az 200 çubuk gerekir
            if len(df) < 200:
                return results
            
            # Hareketli ortalamaları hesapla
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma50'] = df['close'].rolling(window=50).mean()
            df['ma200'] = df['close'].rolling(window=200).mean()
            
            # MA eğimleri (son 10 çubuk)
            ma20_slope = df['ma20'].iloc[-1] - df['ma20'].iloc[-10]
            ma50_slope = df['ma50'].iloc[-1] - df['ma50'].iloc[-10]
            ma200_slope = df['ma200'].iloc[-1] - df['ma200'].iloc[-10]
            
            # MA eğimlerine göre trend belirle
            if ma20_slope > 0:
                results["ma20_trend"] = "up"
            elif ma20_slope < 0:
                results["ma20_trend"] = "down"
                
            if ma50_slope > 0:
                results["ma50_trend"] = "up"
            elif ma50_slope < 0:
                results["ma50_trend"] = "down"
                
            if ma200_slope > 0:
                results["ma200_trend"] = "up"
            elif ma200_slope < 0:
                results["ma200_trend"] = "down"
            
            # MA çapraz geçişleri kontrol et
            if (df['ma20'].iloc[-2] <= df['ma50'].iloc[-2] and 
                df['ma20'].iloc[-1] > df['ma50'].iloc[-1]):
                results["ma_crossover"] = "golden_cross"  # Altın çapraz (yükseliş)
            elif (df['ma20'].iloc[-2] >= df['ma50'].iloc[-2] and 
                  df['ma20'].iloc[-1] < df['ma50'].iloc[-1]):
                results["ma_crossover"] = "death_cross"   # Ölüm çaprazı (düşüş)
            
            # Son 10 yüksek/düşük noktaları kontrol et
            highs = df['high'].rolling(window=5).max()
            lows = df['low'].rolling(window=5).min()
            
            # Son 3 salınım yüksek noktası
            last_swing_highs = []
            for i in range(5, len(df)-5, 5):
                idx = len(df) - i
                if idx >= 0 and highs.iloc[idx] == df['high'].iloc[idx]:
                    last_swing_highs.append(df['high'].iloc[idx])
                    if len(last_swing_highs) >= 3:
                        break
            
            # Son 3 salınım düşük noktası
            last_swing_lows = []
            for i in range(5, len(df)-5, 5):
                idx = len(df) - i
                if idx >= 0 and lows.iloc[idx] == df['low'].iloc[idx]:
                    last_swing_lows.append(df['low'].iloc[idx])
                    if len(last_swing_lows) >= 3:
                        break
            
            # HH, HL, LH, LL kontrol et
            if len(last_swing_highs) >= 2:
                results["higher_highs"] = last_swing_highs[0] > last_swing_highs[-1]
                results["lower_highs"] = last_swing_highs[0] < last_swing_highs[-1]
                
            if len(last_swing_lows) >= 2:
                results["higher_lows"] = last_swing_lows[0] > last_swing_lows[-1]
                results["lower_lows"] = last_swing_lows[0] < last_swing_lows[-1]
            
            # Trend belirle
            # Yükselen trend: Fiyat > MA20 > MA50, HH ve HL
            if (df['close'].iloc[-1] > df['ma20'].iloc[-1] > df['ma50'].iloc[-1] and
                results["higher_highs"] and results["higher_lows"]):
                results["trend"] = "bullish"
                results["strength"] = 80
            # Zayıf yükselen trend
            elif (df['close'].iloc[-1] > df['ma20'].iloc[-1] and
                  results["ma20_trend"] == "up"):
                results["trend"] = "bullish"
                results["strength"] = 60
            # Çok zayıf yükselen trend
            elif results["ma20_trend"] == "up" and results["higher_lows"]:
                results["trend"] = "bullish"
                results["strength"] = 40
                
            # Düşen trend: Fiyat < MA20 < MA50, LH ve LL
            elif (df['close'].iloc[-1] < df['ma20'].iloc[-1] < df['ma50'].iloc[-1] and
                  results["lower_highs"] and results["lower_lows"]):
                results["trend"] = "bearish"
                results["strength"] = 80
            # Zayıf düşen trend
            elif (df['close'].iloc[-1] < df['ma20'].iloc[-1] and
                  results["ma20_trend"] == "down"):
                results["trend"] = "bearish"
                results["strength"] = 60
            # Çok zayıf düşen trend
            elif results["ma20_trend"] == "down" and results["lower_highs"]:
                results["trend"] = "bearish"
                results["strength"] = 40
                
            # Yatay trend
            else:
                results["trend"] = "sideways"
                results["strength"] = 20
            
            # MA ilişkileri ile trend gücünü ince ayarla
            if (results["trend"] == "bullish" and 
                df['ma20'].iloc[-1] > df['ma50'].iloc[-1] > df['ma200'].iloc[-1]):
                results["strength"] = min(100, results["strength"] + 20)
            elif (results["trend"] == "bearish" and 
                  df['ma20'].iloc[-1] < df['ma50'].iloc[-1] < df['ma200'].iloc[-1]):
                results["strength"] = min(100, results["strength"] + 20)
            
            return results
            
        except Exception as e:
            logger.error(f"Trend analizi sırasında hata: {e}")
            return results
    
    def _identify_candle_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        Mum formasyonlarını belirle
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            List[Dict]: Tespit edilen mum formasyonları
        """
        patterns = []
        
        try:
            # En az 10 çubuk gerekir
            if len(df) < 10:
                return patterns
            
            # Son 5 mumu incele
            for i in range(-5, 0):
                idx = len(df) + i
                if idx < 0:
                    continue
                    
                # Mevcut ve önceki mum
                curr = df.iloc[idx]
                prev = df.iloc[idx-1] if idx > 0 else None
                
                # Mum özellikleri
                curr_body = abs(curr['close'] - curr['open'])
                curr_range = curr['high'] - curr['low']
                curr_upper_shadow = curr['high'] - max(curr['close'], curr['open'])
                curr_lower_shadow = min(curr['close'], curr['open']) - curr['low']
                
                curr_is_bullish = curr['close'] > curr['open']
                
                # Temel mum formasyonları
                
                # Doji (çok küçük gövde)
                if curr_body < 0.1 * curr_range:
                    patterns.append({
                        "index": idx,
                        "pattern": "Doji",
                        "signal": "indecision",
                        "strength": 50
                    })
                
                # Çekiç (Hammer) / Asılı Adam (Hanging Man)
                elif (curr_lower_shadow > 2 * curr_body and 
                      curr_upper_shadow < 0.3 * curr_body):
                    if curr_is_bullish:
                        patterns.append({
                            "index": idx,
                            "pattern": "Hammer",
                            "signal": "bullish",
                            "strength": 70
                        })
                    else:
                        patterns.append({
                            "index": idx,
                            "pattern": "Hanging Man",
                            "signal": "bearish",
                            "strength": 70
                        })
                
                # Şahın Kuyruklu Yıldız (Shooting Star) / Ters Çekiç (Inverted Hammer)
                elif (curr_upper_shadow > 2 * curr_body and 
                      curr_lower_shadow < 0.3 * curr_body):
                    if curr_is_bullish:
                        patterns.append({
                            "index": idx,
                            "pattern": "Inverted Hammer",
                            "signal": "bullish",
                            "strength": 60
                        })
                    else:
                        patterns.append({
                            "index": idx,
                            "pattern": "Shooting Star",
                            "signal": "bearish",
                            "strength": 70
                        })
                
                # Uzun gövde (trend göstergesi)
                elif curr_body > 0.7 * curr_range:
                    if curr_is_bullish:
                        patterns.append({
                            "index": idx,
                            "pattern": "Bullish Marubozu",
                            "signal": "bullish",
                            "strength": 80
                        })
                    else:
                        patterns.append({
                            "index": idx,
                            "pattern": "Bearish Marubozu",
                            "signal": "bearish",
                            "strength": 80
                        })
                
                # İkili mum formasyonları (önceki mum gerekir)
                if prev is not None:
                    prev_body = abs(prev['close'] - prev['open'])
                    prev_is_bullish = prev['close'] > prev['open']
                    
                    # Yutan formasyon (Engulfing)
                    if (curr_body > prev_body and 
                        ((curr_is_bullish and not prev_is_bullish and 
                          curr['open'] <= prev['close'] and curr['close'] >= prev['open']) or
                         (not curr_is_bullish and prev_is_bullish and 
                          curr['open'] >= prev['close'] and curr['close'] <= prev['open']))):
                        
                        if curr_is_bullish:
                            patterns.append({
                                "index": idx,
                                "pattern": "Bullish Engulfing",
                                "signal": "bullish",
                                "strength": 90
                            })
                        else:
                            patterns.append({
                                "index": idx,
                                "pattern": "Bearish Engulfing",
                                "signal": "bearish",
                                "strength": 90
                            })
                    
                    # Harami (İçsel dönüş)
                    elif (prev_body > curr_body and 
                          ((curr_is_bullish and not prev_is_bullish and 
                            curr['high'] <= prev['open'] and curr['low'] >= prev['close']) or
                           (not curr_is_bullish and prev_is_bullish and 
                            curr['high'] <= prev['close'] and curr['low'] >= prev['open']))):
                        
                        if curr_is_bullish:
                            patterns.append({
                                "index": idx,
                                "pattern": "Bullish Harami",
                                "signal": "bullish",
                                "strength": 60
                            })
                        else:
                            patterns.append({
                                "index": idx,
                                "pattern": "Bearish Harami",
                                "signal": "bearish",
                                "strength": 60
                            })
            
            # En son tespit edilen formasyonları derecelere göre sırala
            patterns = sorted(patterns, key=lambda x: x["strength"], reverse=True)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Mum formasyonları belirlenirken hata: {e}")
            return patterns
    
    def _find_support_resistance(self, df: pd.DataFrame) -> Dict:
        """
        Destek ve direnç seviyelerini belirle (Swing high/low, kümelenme)
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Destek ve direnç seviyeleri
        """
        results = {
            "support": [],
            "resistance": []
        }
        
        try:
            # En az 50 çubuk gerekir
            if len(df) < 50:
                return results
            
            # Swing high/low noktalarını bul
            for i in range(10, len(df) - 10):
                # Swing high (5 çubuk penceresi)
                if all(df.iloc[i]['high'] > df.iloc[i-j]['high'] for j in range(1, 6)) and \
                   all(df.iloc[i]['high'] > df.iloc[i+j]['high'] for j in range(1, 6)):
                    results["resistance"].append(df.iloc[i]['high'])
                
                # Swing low (5 çubuk penceresi)
                if all(df.iloc[i]['low'] < df.iloc[i-j]['low'] for j in range(1, 6)) and \
                   all(df.iloc[i]['low'] < df.iloc[i+j]['low'] for j in range(1, 6)):
                    results["support"].append(df.iloc[i]['low'])
            
            # Fiyat kümelenme alanlarını belirle
            price_clusters = self._find_price_clusters(df)
            
            # Kümelenme alanlarını ekle
            for cluster in price_clusters:
                if cluster["type"] == "support":
                    results["support"].append(cluster["price"])
                else:
                    results["resistance"].append(cluster["price"])
            
            # Yuvarlak sayıları kontrol et (psikolojik seviyeler)
            last_price = df['close'].iloc[-1]
            price_range = 0.1 * last_price  # Fiyatın %10'u
            
            # En yakın yuvarlak sayıları belirle
            base = 10 ** (int(np.log10(last_price)) - 1)  # 1.2345 için 0.01 gibi
            
            for multiplier in range(int((last_price - price_range) / base), 
                                  int((last_price + price_range) / base) + 1):
                level = multiplier * base
                
                # 00 veya 50 ile biten seviyeler (örn. 1.1200, 1.1250)
                if multiplier % 50 == 0:
                    if level < last_price:
                        results["support"].append(level)
                    else:
                        results["resistance"].append(level)
            
            # Yakın seviyeleri birleştir
            results["support"] = self._merge_levels(results["support"])
            results["resistance"] = self._merge_levels(results["resistance"])
            
            # En yakın 7 seviyeyi tut
            results["support"] = sorted(results["support"], reverse=True)[:7]
            results["resistance"] = sorted(results["resistance"])[:7]
            
            return results
            
        except Exception as e:
            logger.error(f"Destek/direnç seviyeleri belirlenirken hata: {e}")
            return results
    
    def _find_price_clusters(self, df: pd.DataFrame) -> List[Dict]:
        """
        Fiyat kümelenme alanlarını belirle
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            List[Dict]: Fiyat kümelenme alanları
        """
        clusters = []
        
        try:
            # Histogram ile fiyat dağılımını belirle
            high_values = df['high'].values
            low_values = df['low'].values
            
            # Tüm fiyat noktalarını birleştir
            all_prices = np.concatenate([high_values, low_values])
            
            # En düşük ile en yüksek arasını böl
            min_price = np.min(all_prices)
            max_price = np.max(all_prices)
            
            # 100 bin aralığa böl
            bins = 100
            hist, bin_edges = np.histogram(all_prices, bins=bins, range=(min_price, max_price))
            
            # En yüksek frekansları bul (üst %10)
            threshold = np.percentile(hist, 90)
            high_freq_indices = np.where(hist > threshold)[0]
            
            # Kümelenme alanlarını belirle
            for idx in high_freq_indices:
                cluster_price = (bin_edges[idx] + bin_edges[idx+1]) / 2
                
                # Son fiyata göre destek mi direnç mi?
                last_price = df['close'].iloc[-1]
                cluster_type = "support" if cluster_price < last_price else "resistance"
                
                clusters.append({
                    "price": cluster_price,
                    "type": cluster_type,
                    "strength": hist[idx] / np.max(hist) * 100  # 0-100 arası güç
                })
            
            return clusters
            
        except Exception as e:
            logger.error(f"Fiyat kümelenmeleri belirlenirken hata: {e}")
            return clusters
    
    def _calculate_pivot_points(self, df: pd.DataFrame) -> Dict:
        """
        Pivot noktalarını hesapla (Floor, Fibonacci, Woodie, Camarilla)
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Pivot noktaları
        """
        results = {
            "classic": {},
            "fibonacci": {},
            "woodie": {},
            "camarilla": {}
        }
        
        try:
            # En az 1 çubuk gerekir
            if len(df) < 1:
                return results
            
            # Son çubuğun değerleri
            high = df['high'].iloc[-1]
            low = df['low'].iloc[-1]
            close = df['close'].iloc[-1]
            
            # Klasik (Floor) Pivot Noktaları
            pp = (high + low + close) / 3
            s1 = (2 * pp) - high
            s2 = pp - (high - low)
            s3 = low - 2 * (high - pp)
            r1 = (2 * pp) - low
            r2 = pp + (high - low)
            r3 = high + 2 * (pp - low)
            
            results["classic"] = {
                "pp": pp,
                "s1": s1,
                "s2": s2,
                "s3": s3,
                "r1": r1,
                "r2": r2,
                "r3": r3
            }
            
            # Fibonacci Pivot Noktaları
            results["fibonacci"] = {
                "pp": pp,
                "s1": pp - 0.382 * (high - low),
                "s2": pp - 0.618 * (high - low),
                "s3": pp - 1.0 * (high - low),
                "r1": pp + 0.382 * (high - low),
                "r2": pp + 0.618 * (high - low),
                "r3": pp + 1.0 * (high - low)
            }
            
            # Woodie Pivot Noktaları
            pp_woodie = (high + low + 2 * close) / 4
            results["woodie"] = {
                "pp": pp_woodie,
                "s1": (2 * pp_woodie) - high,
                "s2": pp_woodie - (high - low),
                "s3": s1 - (high - low),
                "r1": (2 * pp_woodie) - low,
                "r2": pp_woodie + (high - low),
                "r3": r1 + (high - low)
            }
            
            # Camarilla Pivot Noktaları
            range_cm = high - low
            results["camarilla"] = {
                "pp": pp,
                "s1": close - (range_cm * 1.1 / 12),
                "s2": close - (range_cm * 1.1 / 6),
                "s3": close - (range_cm * 1.1 / 4),
                "s4": close - (range_cm * 1.1 / 2),
                "r1": close + (range_cm * 1.1 / 12),
                "r2": close + (range_cm * 1.1 / 6),
                "r3": close + (range_cm * 1.1 / 4),
                "r4": close + (range_cm * 1.1 / 2)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Pivot noktaları hesaplanırken hata: {e}")
            return results
    
    def _calculate_momentum(self, df: pd.DataFrame) -> Dict:
        """
        Momentum indikatörlerini hesapla (RSI, Stokastik, CCI)
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Momentum göstergeleri
        """
        results = {
            "rsi": None,
            "stoch_k": None,
            "stoch_d": None,
            "cci": None,
            "signals": []
        }
        
        try:
            # En az 20 çubuk gerekir
            if len(df) < 20:
                return results
            
            # RSI hesapla (14 periyot)
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            results["rsi"] = rsi.iloc[-1]
            
            # Stokastik hesapla (14 periyot)
            low_14 = df['low'].rolling(window=14).min()
            high_14 = df['high'].rolling(window=14).max()
            
            stoch_k = 100 * ((df['close'] - low_14) / (high_14 - low_14))
            stoch_d = stoch_k.rolling(window=3).mean()
            
            results["stoch_k"] = stoch_k.iloc[-1]
            results["stoch_d"] = stoch_d.iloc[-1]
            
            # CCI hesapla (20 periyot)
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            tp_sma = typical_price.rolling(window=20).mean()
            tp_mean_dev = abs(typical_price - tp_sma).rolling(window=20).mean()
            
            cci = (typical_price - tp_sma) / (0.015 * tp_mean_dev)
            
            results["cci"] = cci.iloc[-1]
            
            # Sinyal oluştur
            # RSI sinyalleri
            if results["rsi"] < 30:
                results["signals"].append({
                    "indicator": "RSI",
                    "value": results["rsi"],
                    "signal": "buy",
                    "strength": 70,
                    "description": "Aşırı satım (Oversold)"
                })
            elif results["rsi"] > 70:
                results["signals"].append({
                    "indicator": "RSI",
                    "value": results["rsi"],
                    "signal": "sell",
                    "strength": 70,
                    "description": "Aşırı alım (Overbought)"
                })
            
            # Stokastik sinyalleri
            if results["stoch_k"] < 20 and results["stoch_d"] < 20:
                results["signals"].append({
                    "indicator": "Stochastic",
                    "value": results["stoch_k"],
                    "signal": "buy",
                    "strength": 60,
                    "description": "Aşırı satım (Oversold)"
                })
            elif results["stoch_k"] > 80 and results["stoch_d"] > 80:
                results["signals"].append({
                    "indicator": "Stochastic",
                    "value": results["stoch_k"],
                    "signal": "sell",
                    "strength": 60,
                    "description": "Aşırı alım (Overbought)"
                })
            
            # Stokastik kesişim
            if (stoch_k.iloc[-2] < stoch_d.iloc[-2] and 
                stoch_k.iloc[-1] > stoch_d.iloc[-1]):
                results["signals"].append({
                    "indicator": "Stochastic Crossover",
                    "value": results["stoch_k"],
                    "signal": "buy",
                    "strength": 50,
                    "description": "Stokastik yukarı kesişim"
                })
            elif (stoch_k.iloc[-2] > stoch_d.iloc[-2] and 
                  stoch_k.iloc[-1] < stoch_d.iloc[-1]):
                results["signals"].append({
                    "indicator": "Stochastic Crossover",
                    "value": results["stoch_k"],
                    "signal": "sell",
                    "strength": 50,
                    "description": "Stokastik aşağı kesişim"
                })
            
            # CCI sinyalleri
            if results["cci"] < -100:
                results["signals"].append({
                    "indicator": "CCI",
                    "value": results["cci"],
                    "signal": "buy",
                    "strength": 60,
                    "description": "Aşırı satım (Oversold)"
                })
            elif results["cci"] > 100:
                results["signals"].append({
                    "indicator": "CCI",
                    "value": results["cci"],
                    "signal": "sell",
                    "strength": 60,
                    "description": "Aşırı alım (Overbought)"
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Momentum hesaplanırken hata: {e}")
            return results
    
    def _identify_price_patterns(self, df: pd.DataFrame, 
                               support_resistance: Dict, 
                               trend_analysis: Dict) -> List[str]:
        """
        Price Action formasyonlarını belirle
        
        Args:
            df: OHLC verileri içeren DataFrame
            support_resistance: Destek ve direnç seviyeleri
            trend_analysis: Trend analizi
            
        Returns:
            List[str]: Tespit edilen formasyonlar
        """
        patterns = []
        
        try:
            # En az 50 çubuk gerekir
            if len(df) < 50:
                return patterns
            
            # Son fiyat
            last_price = df['close'].iloc[-1]
            
            # Trend bilgisi
            trend = trend_analysis.get("trend", "sideways")
            
            # Destek/direnç'e yakınlık kontrolü
            support_levels = support_resistance.get("support", [])
            resistance_levels = support_resistance.get("resistance", [])
            
            # En yakın destek/direnç
            closest_support = None
            closest_resistance = None
            
            if support_levels:
                closest_support = max([s for s in support_levels if s < last_price], default=None)
                
            if resistance_levels:
                closest_resistance = min([r for r in resistance_levels if r > last_price], default=None)
            
            # Fiyatın destek/dirençe yakınlığı
            if closest_support is not None:
                support_proximity = (last_price - closest_support) / last_price
                if support_proximity < 0.005:  # %0.5'den yakın
                    patterns.append("Price at Support")
                    
                    if trend == "bullish":
                        patterns.append("Bullish Bounce from Support")
            
            if closest_resistance is not None:
                resistance_proximity = (closest_resistance - last_price) / last_price
                if resistance_proximity < 0.005:  # %0.5'den yakın
                    patterns.append("Price at Resistance")
                    
                    if trend == "bearish":
                        patterns.append("Bearish Rejection from Resistance")
            
            # Tepe ve dip formasyonlar
            # Çift tepe / çift dip
            highs = df['high'].rolling(window=5).max()
            lows = df['low'].rolling(window=5).min()
            
            # Son 50 çubukta çift tepe/dip ara
            for i in range(5, min(50, len(df) - 5)):
                # Çift tepe
                if (df.iloc[-i]['high'] == highs.iloc[-i] and 
                    any(abs(df.iloc[-j]['high'] - df.iloc[-i]['high']) / df.iloc[-i]['high'] < 0.005 
                        for j in range(5, i))):
                    
                    if trend == "bearish":
                        patterns.append("Double Top")
                        break
                
                # Çift dip
                if (df.iloc[-i]['low'] == lows.iloc[-i] and 
                    any(abs(df.iloc[-j]['low'] - df.iloc[-i]['low']) / df.iloc[-i]['low'] < 0.005 
                        for j in range(5, i))):
                    
                    if trend == "bullish":
                        patterns.append("Double Bottom")
                        break
            
            # Bayrak / Flama formasyonları
            # Önceki güçlü trend ve sonrasında konsolidasyon
            if len(df) >= 20:
                # Son 20 çubuktaki yüksek ve düşük değişimi
                high_change = (df['high'].iloc[-1] - df['high'].iloc[-20]) / df['high'].iloc[-20]
                low_change = (df['low'].iloc[-1] - df['low'].iloc[-20]) / df['low'].iloc[-20]
                
                # Son 5 çubuktaki yüksek ve düşük değişimi
                recent_high_change = (df['high'].iloc[-1] - df['high'].iloc[-5]) / df['high'].iloc[-5]
                recent_low_change = (df['low'].iloc[-1] - df['low'].iloc[-5]) / df['low'].iloc[-5]
                
                # Yükseliş trendi ve konsolidasyon
                if high_change > 0.02 and abs(recent_high_change) < 0.005 and abs(recent_low_change) < 0.005:
                    if trend == "bullish":
                        patterns.append("Bullish Flag/Pennant")
                
                # Düşüş trendi ve konsolidasyon
                elif low_change < -0.02 and abs(recent_high_change) < 0.005 and abs(recent_low_change) < 0.005:
                    if trend == "bearish":
                        patterns.append("Bearish Flag/Pennant")
            
            # Üçgen formasyonları
            if len(df) >= 20:
                # Son 20 çubuktaki yüksek ve düşük değerleri
                high_values = df['high'].iloc[-20:].values
                low_values = df['low'].iloc[-20:].values
                
                # Yüksek trend çizgisi
                high_slope, high_intercept = np.polyfit(range(len(high_values)), high_values, 1)
                
                # Düşük trend çizgisi
                low_slope, low_intercept = np.polyfit(range(len(low_values)), low_values, 1)
                
                # Simetrik üçgen (yüksekler düşüyor, düşükler yükseliyor)
                if high_slope < -0.0001 and low_slope > 0.0001:
                    patterns.append("Symmetrical Triangle")
                
                # Yükselen üçgen (yüksekler sabit, düşükler yükseliyor)
                elif abs(high_slope) < 0.0001 and low_slope > 0.0001:
                    patterns.append("Ascending Triangle")
                
                # Alçalan üçgen (yüksekler düşüyor, düşükler sabit)
                elif high_slope < -0.0001 and abs(low_slope) < 0.0001:
                    patterns.append("Descending Triangle")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Price Action formasyonları belirlenirken hata: {e}")
            return patterns
    
    def _merge_levels(self, levels: List[float], threshold: float = 0.0005) -> List[float]:
        """
        Yakın seviyeleri birleştir
        
        Args:
            levels: Seviye listesi
            threshold: Birleştirme eşiği
            
        Returns:
            List[float]: Birleştirilmiş seviyeler
        """
        if not levels:
            return []
        
        # Seviyeleri sırala
        sorted_levels = sorted(levels)
        
        # Birleştirilmiş seviyeleri tut
        merged = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Son seviye ile mevcut seviye arasındaki farkı kontrol et
            if abs(level - merged[-1]) / merged[-1] <= threshold:
                # Birleştir (ortalama al)
                merged[-1] = (merged[-1] + level) / 2
            else:
                # Yeni seviye ekle
                merged.append(level)
        
        return merged
    
    def _generate_signal(self, df: pd.DataFrame, analysis_results: Dict) -> Tuple[str, float]:
        """
        Price Action analizi sonuçlarına göre işlem sinyali oluştur
        
        Args:
            df: OHLC verileri içeren DataFrame
            analysis_results: Price Action analiz sonuçları
            
        Returns:
            Tuple[str, float]: İşlem sinyali ve sinyal gücü
        """
        signal = "neutral"
        strength = 0.0
        
        try:
            # Sinyal puanları
            buy_score = 0
            sell_score = 0
            
            # Trend değerlendirmesi
            trend = analysis_results.get("trend", "sideways")
            trend_strength = analysis_results.get("trend_strength", 0)
            
            if trend == "bullish":
                buy_score += trend_strength / 20  # 0-5 puan
            elif trend == "bearish":
                sell_score += trend_strength / 20  # 0-5 puan
            
            # Mum formasyonları
            for pattern in analysis_results.get("candle_patterns", []):
                if pattern["signal"] == "bullish":
                    buy_score += pattern["strength"] / 20  # 0-5 puan
                elif pattern["signal"] == "bearish":
                    sell_score += pattern["strength"] / 20  # 0-5 puan
            
            # Momentum göstergeleri
            for signal_data in analysis_results.get("momentum", {}).get("signals", []):
                if signal_data["signal"] == "buy":
                    buy_score += signal_data["strength"] / 20  # 0-5 puan
                elif signal_data["signal"] == "sell":
                    sell_score += signal_data["strength"] / 20  # 0-5 puan
            
            # Price Action formasyonları
            for pattern in analysis_results.get("patterns", []):
                if "Bullish" in pattern or "Support" in pattern or "Bottom" in pattern:
                    buy_score += 2.5
                elif "Bearish" in pattern or "Resistance" in pattern or "Top" in pattern:
                    sell_score += 2.5
            
            # Pivot seviyelerine yakınlık
            last_price = df['close'].iloc[-1]
            pivots = analysis_results.get("pivots", {}).get("classic", {})
            
            if pivots:
                # Desteklere yakınlık
                for level_name in ["s1", "s2", "s3"]:
                    if level_name in pivots:
                        level = pivots[level_name]
                        if 0 < (last_price - level) / last_price < 0.005:
                            buy_score += (4 - int(level_name[1])) * 0.5  # s1: 1.5, s2: 1.0, s3: 0.5
                
                # Dirençlere yakınlık
                for level_name in ["r1", "r2", "r3"]:
                    if level_name in pivots:
                        level = pivots[level_name]
                        if 0 < (level - last_price) / last_price < 0.005:
                            sell_score += (4 - int(level_name[1])) * 0.5  # r1: 1.5, r2: 1.0, r3: 0.5
            
            # Son değerlendirme
            if buy_score > sell_score + 3:  # En az 3 puanlık fark
                signal = "buy"
                strength = min(100, buy_score * 10)  # 0-100 arası
            elif sell_score > buy_score + 3:
                signal = "sell"
                strength = min(100, sell_score * 10)  # 0-100 arası
            else:
                signal = "neutral"
                strength = max(buy_score, sell_score) * 5  # Düşük güç (yarısı)
            
            return signal, strength
            
        except Exception as e:
            logger.error(f"Price Action sinyali oluşturulurken hata: {e}")
            return "neutral", 0