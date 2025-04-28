#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için ICT (Inner Circle Trader) strateji modülü.
Likidite seviyeleri, sipariş blokları, kırıcı bloklar ve adil değer boşlukları gibi
ICT kavramlarını kullanarak teknik analiz yapar.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger("ForexTradingBot.ICTStrategy")

class ICTStrategy:
    """
    ICT teknik analiz stratejisi uygulayan sınıf.
    """
    
    def __init__(self, data_manager):
        """
        ICT strateji modülünü başlat
        
        Args:
            data_manager: Veri yöneticisi
        """
        self.data_manager = data_manager
        logger.info("ICT strateji modülü başlatıldı")
    
    def analyze(self, symbol: str, timeframe: str) -> Dict:
        """
        Belirli bir sembol ve zaman dilimi için ICT analizi yap
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            timeframe: Zaman dilimi (örn. "H1", "D1")
            
        Returns:
            Dict: ICT analiz sonuçları
        """
        try:
            # Veriyi al
            df = self.data_manager.get_historical_data(symbol, timeframe)
            
            if df.empty:
                logger.warning(f"ICT analizi için veri bulunamadı: {symbol} {timeframe}")
                return {"error": "Veri bulunamadı"}
            
            # Sonuçları topla
            results = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.now()
            }
            
            # Likidite seviyelerini belirle
            liquidity_levels = self._find_liquidity_levels(df)
            results["liquidity_levels"] = liquidity_levels
            
            # Sipariş bloklarını belirle
            order_blocks = self._find_order_blocks(df)
            results["order_blocks"] = order_blocks
            
            # Kırıcı blokları belirle
            breaker_blocks = self._find_breaker_blocks(df)
            results["breaker_blocks"] = breaker_blocks
            
            # Adil değer boşluklarını belirle
            fair_value_gaps = self._find_fair_value_gaps(df)
            results["fair_value_gaps"] = fair_value_gaps
            
            # ICT formasyonları belirle
            patterns = self._identify_ict_patterns(df, liquidity_levels, order_blocks, fair_value_gaps)
            results["patterns"] = patterns
            
            # Destek ve direnç seviyelerini belirle
            support_resistance = self._find_support_resistance(df, liquidity_levels, order_blocks)
            results["support_levels"] = support_resistance["support"]
            results["resistance_levels"] = support_resistance["resistance"]
            
            # İşlem sinyali oluştur
            signal, strength = self._generate_signal(df, results)
            results["signal"] = signal
            results["strength"] = strength
            
            return results
            
        except Exception as e:
            logger.error(f"ICT analizi sırasında hata: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _find_liquidity_levels(self, df: pd.DataFrame) -> Dict:
        """
        Likidite seviyelerini belirle (Swing high/low, equal highs/lows)
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Likidite seviyeleri
        """
        results = {
            "buy_side": [],  # Alış tarafı likidite (Düşük seviyeler)
            "sell_side": []  # Satış tarafı likidite (Yüksek seviyeler)
        }
        
        try:
            # En az 30 çubuk gerekir
            if len(df) < 30:
                return results
            
            # Swing high ve low'ları bul (5 çubuk penceresi)
            for i in range(5, len(df) - 5):
                # Swing high
                if (df.iloc[i]['high'] > df.iloc[i-1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i-2]['high'] and
                    df.iloc[i]['high'] > df.iloc[i+1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i+2]['high']):
                    
                    # Equal highs kontrolü (son 50 çubuk içinde)
                    equal_highs = []
                    base_high = df.iloc[i]['high']
                    
                    for j in range(max(0, i-50), i):
                        # %0.1 tolerans ile eşit yükseklik
                        if abs(df.iloc[j]['high'] - base_high) / base_high < 0.001:
                            equal_highs.append(j)
                    
                    # Likidite seviyesini ekle
                    level = {
                        "price": df.iloc[i]['high'],
                        "index": i,
                        "datetime": df.index[i],
                        "type": "swing_high",
                        "equal_points": len(equal_highs),
                        "strength": 1 + (len(equal_highs) * 0.2)  # Her eşit nokta için güç artar
                    }
                    
                    results["sell_side"].append(level)
                
                # Swing low
                if (df.iloc[i]['low'] < df.iloc[i-1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i-2]['low'] and
                    df.iloc[i]['low'] < df.iloc[i+1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i+2]['low']):
                    
                    # Equal lows kontrolü (son 50 çubuk içinde)
                    equal_lows = []
                    base_low = df.iloc[i]['low']
                    
                    for j in range(max(0, i-50), i):
                        # %0.1 tolerans ile eşit alçaklık
                        if abs(df.iloc[j]['low'] - base_low) / base_low < 0.001:
                            equal_lows.append(j)
                    
                    # Likidite seviyesini ekle
                    level = {
                        "price": df.iloc[i]['low'],
                        "index": i,
                        "datetime": df.index[i],
                        "type": "swing_low",
                        "equal_points": len(equal_lows),
                        "strength": 1 + (len(equal_lows) * 0.2)  # Her eşit nokta için güç artar
                    }
                    
                    results["buy_side"].append(level)
            
            # Sonuçları güce göre sırala
            results["buy_side"] = sorted(results["buy_side"], key=lambda x: x["strength"], reverse=True)
            results["sell_side"] = sorted(results["sell_side"], key=lambda x: x["strength"], reverse=True)
            
            # En güçlü 5 seviyeyi tut
            results["buy_side"] = results["buy_side"][:5]
            results["sell_side"] = results["sell_side"][:5]
            
            return results
            
        except Exception as e:
            logger.error(f"Likidite seviyeleri bulunurken hata: {e}")
            return results
    
    def _find_order_blocks(self, df: pd.DataFrame) -> Dict:
        """
        Sipariş bloklarını belirle (Güçlü hareketten önce gelen ters mumlar)
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Sipariş blokları
        """
        results = {
            "bullish": [],  # Yükseliş sipariş blokları
            "bearish": []   # Düşüş sipariş blokları
        }
        
        try:
            # En az 20 çubuk gerekir
            if len(df) < 20:
                return results
            
            # Güçlü hareketleri bul (ortalama hareketin 2 katı)
            avg_range = np.mean(df['high'] - df['low'])
            strong_move_threshold = 2 * avg_range
            
            for i in range(3, len(df) - 1):
                # Yükselen hareket (güçlü yeşil mum)
                if (df.iloc[i]['close'] > df.iloc[i]['open'] and
                    df.iloc[i]['high'] - df.iloc[i]['low'] > strong_move_threshold):
                    
                    # Önceki çubuklarda düşüş sipariş bloğu ara
                    for j in range(i-3, i):
                        # Düşüş sipariş bloğu kriterleri
                        if (df.iloc[j]['close'] < df.iloc[j]['open'] and  # Kırmızı mum
                            df.iloc[j]['low'] < df.iloc[i]['low']):  # Hareket öncesi daha düşük
                            
                            # Düşüş sipariş bloğu
                            block = {
                                "top": df.iloc[j]['open'],  # Sipariş bloğu üst seviyesi
                                "bottom": df.iloc[j]['close'],  # Sipariş bloğu alt seviyesi
                                "index": j,
                                "datetime": df.index[j],
                                "strength": (df.iloc[i]['high'] - df.iloc[i]['low']) / avg_range  # Güç
                            }
                            
                            results["bearish"].append(block)
                            break  # En son sipariş bloğunu bul
                
                # Düşen hareket (güçlü kırmızı mum)
                elif (df.iloc[i]['close'] < df.iloc[i]['open'] and
                      df.iloc[i]['high'] - df.iloc[i]['low'] > strong_move_threshold):
                    
                    # Önceki çubuklarda yükseliş sipariş bloğu ara
                    for j in range(i-3, i):
                        # Yükseliş sipariş bloğu kriterleri
                        if (df.iloc[j]['close'] > df.iloc[j]['open'] and  # Yeşil mum
                            df.iloc[j]['high'] > df.iloc[i]['high']):  # Hareket öncesi daha yüksek
                            
                            # Yükseliş sipariş bloğu
                            block = {
                                "top": df.iloc[j]['close'],  # Sipariş bloğu üst seviyesi
                                "bottom": df.iloc[j]['open'],  # Sipariş bloğu alt seviyesi
                                "index": j,
                                "datetime": df.index[j],
                                "strength": (df.iloc[i]['high'] - df.iloc[i]['low']) / avg_range  # Güç
                            }
                            
                            results["bullish"].append(block)
                            break  # En son sipariş bloğunu bul
            
            # Sonuçları güce göre sırala
            results["bullish"] = sorted(results["bullish"], key=lambda x: x["strength"], reverse=True)
            results["bearish"] = sorted(results["bearish"], key=lambda x: x["strength"], reverse=True)
            
            # En güçlü 3 bloğu tut
            results["bullish"] = results["bullish"][:3]
            results["bearish"] = results["bearish"][:3]
            
            return results
            
        except Exception as e:
            logger.error(f"Sipariş blokları bulunurken hata: {e}")
            return results
    
    def _find_breaker_blocks(self, df: pd.DataFrame) -> Dict:
        """
        Kırıcı blokları belirle (Yapı kırılmasından sonraki ilk karşıt hareket)
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Kırıcı blokları
        """
        results = {
            "bullish": [],  # Yükseliş kırıcı blokları
            "bearish": []   # Düşüş kırıcı blokları
        }
        
        try:
            # En az 50 çubuk gerekir
            if len(df) < 50:
                return results
            
            # Higher highs (HH) ve lower lows (LL) bul
            highs = []
            lows = []
            
            for i in range(5, len(df) - 5):
                # Swing high
                if (df.iloc[i]['high'] > df.iloc[i-1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i-2]['high'] and
                    df.iloc[i]['high'] > df.iloc[i+1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i+2]['high']):
                    
                    highs.append((i, df.iloc[i]['high']))
                
                # Swing low
                if (df.iloc[i]['low'] < df.iloc[i-1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i-2]['low'] and
                    df.iloc[i]['low'] < df.iloc[i+1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i+2]['low']):
                    
                    lows.append((i, df.iloc[i]['low']))
            
            # Yapı kırılmalarını kontrol et
            for i in range(1, len(highs)):
                # Yüksek nokta yapı kırılması (HH -> LH)
                if highs[i][1] < highs[i-1][1]:
                    # Kırılmadan sonraki ilk yükseliş bloğunu bul
                    start_idx = highs[i][0]
                    end_idx = min(start_idx + 20, len(df) - 1)  # Sonraki 20 çubuğa bak
                    
                    for j in range(start_idx, end_idx):
                        # Yeşil mum
                        if df.iloc[j]['close'] > df.iloc[j]['open']:
                            # Kırıcı blok
                            block = {
                                "top": df.iloc[j]['close'],
                                "bottom": df.iloc[j]['open'],
                                "index": j,
                                "datetime": df.index[j],
                                "structure_break": "lower_high",
                                "strength": 1 + (highs[i-1][1] - highs[i][1]) / highs[i-1][1]  # Kırılma büyüklüğü
                            }
                            
                            results["bullish"].append(block)
                            break
            
            for i in range(1, len(lows)):
                # Düşük nokta yapı kırılması (LL -> HL)
                if lows[i][1] > lows[i-1][1]:
                    # Kırılmadan sonraki ilk düşüş bloğunu bul
                    start_idx = lows[i][0]
                    end_idx = min(start_idx + 20, len(df) - 1)  # Sonraki 20 çubuğa bak
                    
                    for j in range(start_idx, end_idx):
                        # Kırmızı mum
                        if df.iloc[j]['close'] < df.iloc[j]['open']:
                            # Kırıcı blok
                            block = {
                                "top": df.iloc[j]['open'],
                                "bottom": df.iloc[j]['close'],
                                "index": j,
                                "datetime": df.index[j],
                                "structure_break": "higher_low",
                                "strength": 1 + (lows[i][1] - lows[i-1][1]) / lows[i-1][1]  # Kırılma büyüklüğü
                            }
                            
                            results["bearish"].append(block)
                            break
            
            # Sonuçları güce göre sırala
            results["bullish"] = sorted(results["bullish"], key=lambda x: x["strength"], reverse=True)
            results["bearish"] = sorted(results["bearish"], key=lambda x: x["strength"], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Kırıcı blokları bulunurken hata: {e}")
            return results
    
    def _find_fair_value_gaps(self, df: pd.DataFrame) -> Dict:
        """
        Adil değer boşluklarını belirle (Birbirini takip eden mumlar arasındaki boşluklar)
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Adil değer boşlukları
        """
        results = {
            "bullish": [],  # Yükseliş boşlukları
            "bearish": []   # Düşüş boşlukları
        }
        
        try:
            # En az 10 çubuk gerekir
            if len(df) < 10:
                return results
            
            # Ortalama aralık hesapla (volatilite için)
            avg_range = np.mean(df['high'] - df['low'])
            min_gap_size = 0.3 * avg_range  # Minimum boşluk büyüklüğü
            
            for i in range(1, len(df) - 1):
                # Yükseliş boşluğu (Önceki mumun yüksek noktası < Sonraki mumun düşük noktası)
                if df.iloc[i-1]['high'] < df.iloc[i+1]['low']:
                    gap_size = df.iloc[i+1]['low'] - df.iloc[i-1]['high']
                    
                    if gap_size > min_gap_size:
                        # Boşluğu ekle
                        gap = {
                            "top": df.iloc[i+1]['low'],
                            "bottom": df.iloc[i-1]['high'],
                            "index": i,
                            "datetime": df.index[i],
                            "size": gap_size,
                            "strength": gap_size / avg_range  # Boşluk büyüklüğü / Ortalama aralık
                        }
                        
                        results["bullish"].append(gap)
                
                # Düşüş boşluğu (Önceki mumun düşük noktası > Sonraki mumun yüksek noktası)
                if df.iloc[i-1]['low'] > df.iloc[i+1]['high']:
                    gap_size = df.iloc[i-1]['low'] - df.iloc[i+1]['high']
                    
                    if gap_size > min_gap_size:
                        # Boşluğu ekle
                        gap = {
                            "top": df.iloc[i-1]['low'],
                            "bottom": df.iloc[i+1]['high'],
                            "index": i,
                            "datetime": df.index[i],
                            "size": gap_size,
                            "strength": gap_size / avg_range  # Boşluk büyüklüğü / Ortalama aralık
                        }
                        
                        results["bearish"].append(gap)
            
            # Sonuçları güce göre sırala
            results["bullish"] = sorted(results["bullish"], key=lambda x: x["strength"], reverse=True)
            results["bearish"] = sorted(results["bearish"], key=lambda x: x["strength"], reverse=True)
            
            # En güçlü 3 boşluğu tut
            results["bullish"] = results["bullish"][:3]
            results["bearish"] = results["bearish"][:3]
            
            return results
            
        except Exception as e:
            logger.error(f"Adil değer boşlukları bulunurken hata: {e}")
            return results
    
    def _identify_ict_patterns(self, df: pd.DataFrame, liquidity_levels: Dict, 
                              order_blocks: Dict, fair_value_gaps: Dict) -> List[str]:
        """
        ICT formasyonlarını belirle
        
        Args:
            df: OHLC verileri içeren DataFrame
            liquidity_levels: Likidite seviyeleri
            order_blocks: Sipariş blokları
            fair_value_gaps: Adil değer boşlukları
            
        Returns:
            List[str]: Tespit edilen ICT formasyonları
        """
        patterns = []
        
        try:
            # Son fiyat
            last_price = df['close'].iloc[-1]
            
            # Likidite toplama formasyonu (Swap)
            if liquidity_levels["buy_side"] and len(df) > 100:
                # Son 3 gün içindeki en düşük likidite seviyeleri
                recent_liquidity = [level for level in liquidity_levels["buy_side"] 
                                   if level["index"] > len(df) - 60]
                
                if recent_liquidity:
                    # Likidite seviyeleri arasında dar bir bölge var mı?
                    if len(recent_liquidity) >= 2:
                        ranges = []
                        for i in range(len(recent_liquidity) - 1):
                            ranges.append(abs(recent_liquidity[i]["price"] - recent_liquidity[i+1]["price"]))
                        
                        avg_range = np.mean(df['high'] - df['low'])
                        if min(ranges) < 0.5 * avg_range:
                            patterns.append("Liquidity Sweep Pattern (Buy Side)")
            
            # IPDA (Dahili Fiyat Dağıtım Alanı)
            # Son 3 yükseliş sipariş bloğu yakın mı?
            bullish_blocks = order_blocks["bullish"]
            if len(bullish_blocks) >= 2:
                avg_range = np.mean(df['high'] - df['low'])
                tops = [block["top"] for block in bullish_blocks]
                bottoms = [block["bottom"] for block in bullish_blocks]
                
                range_size = max(tops) - min(bottoms)
                if range_size < 2 * avg_range:
                    patterns.append("Internal Price Delivery Area (Bullish)")
            
            # Adil değer boşluğu ile sipariş bloğu çakışması
            for gap in fair_value_gaps["bullish"]:
                for block in order_blocks["bullish"]:
                    if (gap["bottom"] <= block["top"] and gap["top"] >= block["bottom"]):
                        patterns.append("Bullish Order Block with Fair Value Gap")
                        break
            
            for gap in fair_value_gaps["bearish"]:
                for block in order_blocks["bearish"]:
                    if (gap["bottom"] <= block["top"] and gap["top"] >= block["bottom"]):
                        patterns.append("Bearish Order Block with Fair Value Gap")
                        break
            
            # Likidite ile ilişkili sipariş bloğu
            for level in liquidity_levels["buy_side"]:
                for block in order_blocks["bullish"]:
                    if abs(level["price"] - block["bottom"]) / level["price"] < 0.002:
                        patterns.append("Bullish Order Block at Buy Side Liquidity")
                        break
            
            for level in liquidity_levels["sell_side"]:
                for block in order_blocks["bearish"]:
                    if abs(level["price"] - block["top"]) / level["price"] < 0.002:
                        patterns.append("Bearish Order Block at Sell Side Liquidity")
                        break
            
            # Güncel fiyat adil değer boşluğuna yaklaşıyor
            for gap in fair_value_gaps["bullish"]:
                if last_price < gap["bottom"] and (gap["bottom"] - last_price) / last_price < 0.005:
                    patterns.append("Price Approaching Bullish Fair Value Gap")
                    break
            
            for gap in fair_value_gaps["bearish"]:
                if last_price > gap["top"] and (last_price - gap["top"]) / last_price < 0.005:
                    patterns.append("Price Approaching Bearish Fair Value Gap")
                    break
            
            # Benzersiz formasyonları döndür
            return list(set(patterns))
            
        except Exception as e:
            logger.error(f"ICT formasyonları belirlenirken hata: {e}")
            return patterns
    
    def _find_support_resistance(self, df: pd.DataFrame, liquidity_levels: Dict, 
                                order_blocks: Dict) -> Dict:
        """
        ICT bileşenlerine göre destek ve direnç seviyelerini belirle
        
        Args:
            df: OHLC verileri içeren DataFrame
            liquidity_levels: Likidite seviyeleri
            order_blocks: Sipariş blokları
            
        Returns:
            Dict: Destek ve direnç seviyeleri
        """
        results = {
            "support": [],
            "resistance": []
        }
        
        try:
            # Son fiyat
            last_price = df['close'].iloc[-1]
            
            # Likidite seviyelerinden destek/direnç oluştur
            for level in liquidity_levels["buy_side"]:
                if level["price"] < last_price:
                    results["support"].append(level["price"])
            
            for level in liquidity_levels["sell_side"]:
                if level["price"] > last_price:
                    results["resistance"].append(level["price"])
            
            # Sipariş bloklarından destek/direnç oluştur
            for block in order_blocks["bullish"]:
                if block["top"] < last_price:
                    results["support"].append(block["top"])
                    results["support"].append(block["bottom"])
            
            for block in order_blocks["bearish"]:
                if block["bottom"] > last_price:
                    results["resistance"].append(block["top"])
                    results["resistance"].append(block["bottom"])
            
            # Yakın seviyeleri birleştir
            if results["support"]:
                results["support"] = self._merge_levels(results["support"])
            if results["resistance"]:
                results["resistance"] = self._merge_levels(results["resistance"])
            
            return results
            
        except Exception as e:
            logger.error(f"Destek/direnç seviyeleri belirlenirken hata: {e}")
            return results
    
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
        ICT analizi sonuçlarına göre işlem sinyali oluştur
        
        Args:
            df: OHLC verileri içeren DataFrame
            analysis_results: ICT analiz sonuçları
            
        Returns:
            Tuple[str, float]: İşlem sinyali ve sinyal gücü
        """
        signal = "neutral"
        strength = 0.0
        
        try:
            # Son fiyat
            last_price = df['close'].iloc[-1]
            
            # Sinyal puanları
            buy_score = 0
            sell_score = 0
            
            # Likidite seviyeleri
            for level in analysis_results["liquidity_levels"]["buy_side"]:
                # Fiyat alış tarafı likiditeye yaklaşıyor veya kırdı
                diff_pct = (last_price - level["price"]) / last_price
                if -0.005 < diff_pct < 0.002:  # Likiditeye çok yakın veya yeni kırıldı
                    buy_score += 2 * level["strength"]
                elif 0.002 <= diff_pct < 0.01:  # Likidite kırıldı ve geri çekilme
                    buy_score += 1 * level["strength"]
            
            for level in analysis_results["liquidity_levels"]["sell_side"]:
                # Fiyat satış tarafı likiditeye yaklaşıyor veya kırdı
                diff_pct = (level["price"] - last_price) / last_price
                if -0.005 < diff_pct < 0.002:  # Likiditeye çok yakın veya yeni kırıldı
                    sell_score += 2 * level["strength"]
                elif 0.002 <= diff_pct < 0.01:  # Likidite kırıldı ve geri çekilme
                    sell_score += 1 * level["strength"]
            
            # Sipariş blokları
            for block in analysis_results["order_blocks"]["bullish"]:
                # Fiyat yükseliş sipariş bloğuna yakın
                if block["bottom"] <= last_price <= block["top"]:
                    buy_score += 3 * block["strength"]
                elif 0 < (last_price - block["top"]) / last_price < 0.005:
                    buy_score += 1.5 * block["strength"]
            
            for block in analysis_results["order_blocks"]["bearish"]:
                # Fiyat düşüş sipariş bloğuna yakın
                if block["bottom"] <= last_price <= block["top"]:
                    sell_score += 3 * block["strength"]
                elif 0 < (block["bottom"] - last_price) / last_price < 0.005:
                    sell_score += 1.5 * block["strength"]
            
            # Adil değer boşlukları
            for gap in analysis_results["fair_value_gaps"]["bullish"]:
                # Fiyat yükseliş boşluğuna yakın
                if last_price < gap["bottom"] and (gap["bottom"] - last_price) / last_price < 0.005:
                    buy_score += 2 * gap["strength"]
                elif gap["bottom"] <= last_price <= gap["top"]:  # Fiyat boşluk içinde
                    buy_score += 1 * gap["strength"]
            
            for gap in analysis_results["fair_value_gaps"]["bearish"]:
                # Fiyat düşüş boşluğuna yakın
                if last_price > gap["top"] and (last_price - gap["top"]) / last_price < 0.005:
                    sell_score += 2 * gap["strength"]
                elif gap["bottom"] <= last_price <= gap["top"]:  # Fiyat boşluk içinde
                    sell_score += 1 * gap["strength"]
            
            # ICT formasyonları
            for pattern in analysis_results.get("patterns", []):
                if "Bullish" in pattern:
                    buy_score += 2
                elif "Bearish" in pattern:
                    sell_score += 2
            
            # Sonuçları değerlendir
            if buy_score > sell_score + 2:  # Minimum fark eşiği
                signal = "buy"
                strength = min(100, buy_score * 10)  # 0-100 arası
            elif sell_score > buy_score + 2:
                signal = "sell"
                strength = min(100, sell_score * 10)  # 0-100 arası
            else:
                signal = "neutral"
                strength = 0
            
            return signal, strength
            
        except Exception as e:
            logger.error(f"ICT sinyali oluşturulurken hata: {e}")
            return "neutral", 0