#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için ana analiz motoru.
ICT, SMC ve Price Action stratejilerini birleştirir.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple  # Tuple'ı buraya ekledim
import pandas as pd
import numpy as np

# Proje modüllerini içe aktar
from analysis.ict_strategy import ICTStrategy
from analysis.smc_strategy import SMCStrategy
from analysis.price_action_strategy import PriceActionStrategy
from analysis.news_analyzer import NewsAnalyzer

logger = logging.getLogger("ForexTradingBot.AnalysisEngine")

class AnalysisEngine:
    """
    Farklı analiz modüllerini birleştiren ana analiz motoru.
    """
    
    def __init__(self, data_manager):
        """
        Analiz motorunu başlat
        
        Args:
            data_manager: Veri yöneticisi
        """
        self.data_manager = data_manager
        
        # Analiz stratejilerini başlat
        self.ict_strategy = ICTStrategy(data_manager)
        self.smc_strategy = SMCStrategy(data_manager)
        self.price_action_strategy = PriceActionStrategy(data_manager)
        self.news_analyzer = NewsAnalyzer(data_manager)
        
        logger.info("Analiz motoru başlatıldı")
    
    def analyze(self, symbol: str, timeframes: Optional[List[str]] = None) -> Dict:
        """
        Belirli bir sembol için tüm analiz stratejilerini çalıştır
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            timeframes: Analiz edilecek zaman dilimleri (None ise tümü)
            
        Returns:
            Dict: Tüm analizlerin sonuçları
        """
        # Varsayılan zaman dilimleri
        if timeframes is None:
            timeframes = ["M5", "M15", "H1", "H4", "D1"]
            
        logger.info(f"{symbol} için analiz başlatılıyor")
        
        # Analiz sonuçlarını topla
        results = {
            "symbol": symbol,
            "timestamp": datetime.now(),
            "timeframes": {},
            "ict": {},
            "smc": {},
            "price_action": {},
            "news": {},
            "summary": {}
        }
        
        try:
            # Her zaman dilimi için analiz yap
            for timeframe in timeframes:
                # Veriyi al
                df = self.data_manager.get_historical_data(symbol, timeframe)
                
                if df.empty:
                    logger.warning(f"{symbol} {timeframe} için veri bulunamadı")
                    continue
                
                # Zaman dilimi sonuçları
                timeframe_results = {
                    "ict": self.ict_strategy.analyze(symbol, timeframe),
                    "smc": self.smc_strategy.analyze(symbol, timeframe),
                    "price_action": self.price_action_strategy.analyze(symbol, timeframe)
                }
                
                # Zaman dilimi özetini oluştur
                timeframe_summary = self._create_timeframe_summary(timeframe_results)
                
                # Sonuçları ekle
                results["timeframes"][timeframe] = {
                    "data_points": len(df),
                    "analysis": timeframe_results,
                    "summary": timeframe_summary
                }
                
                # Her strateji için zaman dilimi sonuçlarını topla
                for strategy in ["ict", "smc", "price_action"]:
                    if strategy not in results:
                        results[strategy] = {}
                    
                    results[strategy][timeframe] = timeframe_results[strategy]
            
            # Haber analizini ekle
            results["news"] = self.news_analyzer.analyze(symbol)
            
            # Genel özet oluştur
            results["summary"] = self._create_summary(results)
            
            logger.info(f"{symbol} için analiz tamamlandı")
            return results
            
        except Exception as e:
            logger.error(f"{symbol} için analiz sırasında hata: {e}", exc_info=True)
            # Hata durumunda boş sonuç döndür
            return {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "error": str(e)
            }
    
    def _create_timeframe_summary(self, timeframe_results: Dict) -> Dict:
        """
        Tek bir zaman dilimi için analiz özetini oluştur
        
        Args:
            timeframe_results: Zaman dilimi analiz sonuçları
            
        Returns:
            Dict: Zaman dilimi özeti
        """
        # Her stratejinin sinyalini al
        ict_signal = timeframe_results["ict"].get("signal", "neutral")
        smc_signal = timeframe_results["smc"].get("signal", "neutral")
        pa_signal = timeframe_results["price_action"].get("signal", "neutral")
        
        # Sinyal sayılarını say
        buy_count = sum(1 for signal in [ict_signal, smc_signal, pa_signal] if signal == "buy")
        sell_count = sum(1 for signal in [ict_signal, smc_signal, pa_signal] if signal == "sell")
        
        # Ağırlıklı sinyal belirle
        if buy_count > sell_count:
            final_signal = "buy"
        elif sell_count > buy_count:
            final_signal = "sell"
        else:
            final_signal = "neutral"
        
        # Sinyal güvenilirliği
        if buy_count == 3 or sell_count == 3:
            confidence = "high"
        elif buy_count == 2 or sell_count == 2:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Her stratejinin güç değerini al (0-100 arası)
        ict_strength = timeframe_results["ict"].get("strength", 0)
        smc_strength = timeframe_results["smc"].get("strength", 0)
        pa_strength = timeframe_results["price_action"].get("strength", 0)
        
        # Ortalama güç
        avg_strength = (ict_strength + smc_strength + pa_strength) / 3
        
        # Önemli destek/direnç seviyelerini birleştir
        support_levels = []
        resistance_levels = []
        
        for strategy in ["ict", "smc", "price_action"]:
            support = timeframe_results[strategy].get("support_levels", [])
            resistance = timeframe_results[strategy].get("resistance_levels", [])
            
            if support:
                support_levels.extend(support)
            if resistance:
                resistance_levels.extend(resistance)
        
        # Yakın seviyeleri birleştir
        if support_levels:
            support_levels = self._merge_levels(support_levels)
        if resistance_levels:
            resistance_levels = self._merge_levels(resistance_levels)
        
        # Özet sözlüğünü oluştur
        summary = {
            "signal": final_signal,
            "confidence": confidence,
            "strength": avg_strength,
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "key_patterns": self._extract_key_patterns(timeframe_results)
        }
        
        return summary
    
    def _create_summary(self, results: Dict) -> Dict:
        """
        Tüm analiz sonuçları için genel özet oluştur
        
        Args:
            results: Tüm analiz sonuçları
            
        Returns:
            Dict: Genel özet
        """
        # Zaman dilimlerine göre ağırlıkları belirle
        timeframe_weights = {
            "M5": 0.05,
            "M15": 0.10,
            "H1": 0.20,
            "H4": 0.30,
            "D1": 0.35
        }
        
        # Toplam ağırlık
        total_weight = sum(timeframe_weights.get(tf, 0.0) for tf in results["timeframes"].keys())
        
        # Ağırlıkları normalize et
        if total_weight > 0:
            for tf in timeframe_weights:
                if tf in results["timeframes"]:
                    timeframe_weights[tf] /= total_weight
        
        # Her zaman dilimi için sinyalleri topla
        buy_weight = 0.0
        sell_weight = 0.0
        
        for tf, tf_data in results["timeframes"].items():
            if "summary" in tf_data:
                signal = tf_data["summary"].get("signal", "neutral")
                tf_weight = timeframe_weights.get(tf, 0.0)
                
                if signal == "buy":
                    buy_weight += tf_weight
                elif signal == "sell":
                    sell_weight += tf_weight
        
        # Haber etkisini ekle
        news_impact = 0.0
        
        if "news" in results and "impact" in results["news"]:
            news_impact = results["news"]["impact"]
            
            # Haber etkisi pozitifse alış, negatifse satış ağırlığı artar
            if news_impact > 0:
                buy_weight += 0.1 * min(news_impact, 1.0)
            elif news_impact < 0:
                sell_weight += 0.1 * min(abs(news_impact), 1.0)
        
        # Genel sinyal belirle
        if buy_weight > sell_weight + 0.1:  # 0.1 eşik değeri
            final_signal = "buy"
            signal_strength = buy_weight
        elif sell_weight > buy_weight + 0.1:
            final_signal = "sell"
            signal_strength = sell_weight
        else:
            final_signal = "neutral"
            signal_strength = max(buy_weight, sell_weight)
        
        # Sinyal gücünü 0-100 arasına normalize et
        signal_strength = min(signal_strength * 100, 100)
        
        # Güven seviyesi
        if signal_strength > 70:
            confidence = "high"
        elif signal_strength > 40:
            confidence = "medium"
        else:
            confidence = "low"
        
        # En yakın destek/direnç seviyelerini belirle
        nearest_support, nearest_resistance = self._find_nearest_levels(results)
        
        # Sinyal başarı olasılığını hesapla
        success_probability = self._calculate_success_probability(
            results, final_signal, signal_strength
        )
        
        # Özet sözlüğünü oluştur
        summary = {
            "signal": final_signal,
            "confidence": confidence,
            "strength": signal_strength,
            "success_probability": success_probability,
            "buy_weight": buy_weight * 100,  # Yüzdeye çevir
            "sell_weight": sell_weight * 100,  # Yüzdeye çevir
            "news_impact": news_impact,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "key_timeframes": self._identify_key_timeframes(results)
        }
        
        return summary
    
    def _merge_levels(self, levels: List[float], threshold: float = 0.0005) -> List[float]:
        """
        Yakın destek/direnç seviyelerini birleştir
        
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
    
    def _extract_key_patterns(self, timeframe_results: Dict) -> List[str]:
        """
        Analiz sonuçlarından önemli formasyonları çıkar
        
        Args:
            timeframe_results: Zaman dilimi analiz sonuçları
            
        Returns:
            List[str]: Önemli formasyon listesi
        """
        key_patterns = []
        
        # ICT formasyonları
        if "patterns" in timeframe_results["ict"]:
            for pattern in timeframe_results["ict"]["patterns"]:
                key_patterns.append(f"ICT: {pattern}")
        
        # SMC formasyonları
        if "patterns" in timeframe_results["smc"]:
            for pattern in timeframe_results["smc"]["patterns"]:
                key_patterns.append(f"SMC: {pattern}")
        
        # Price Action formasyonları
        if "patterns" in timeframe_results["price_action"]:
            for pattern in timeframe_results["price_action"]["patterns"]:
                key_patterns.append(f"PA: {pattern}")
        
        return key_patterns
    
    def _find_nearest_levels(self, results: Dict) -> Tuple[Optional[float], Optional[float]]:
        """
        En yakın destek/direnç seviyelerini bul
        
        Args:
            results: Tüm analiz sonuçları
            
        Returns:
            Tuple[Optional[float], Optional[float]]: En yakın destek ve direnç seviyeleri
        """
        # Mevcut fiyatı al (son değer)
        symbol = results["symbol"]
        current_price = None
        
        try:
            # H1 veya mevcut olan en yüksek timeframe'i kullan
            for tf in ["H1", "M15", "M5", "H4", "D1"]:
                if tf in results["timeframes"]:
                    df = self.data_manager.get_historical_data(symbol, tf)
                    if not df.empty:
                        current_price = df["close"].iloc[-1]
                        break
            
            if current_price is None:
                return None, None
                
            # Tüm destek ve direnç seviyelerini topla
            all_supports = []
            all_resistances = []
            
            for tf_data in results["timeframes"].values():
                if "summary" in tf_data:
                    supports = tf_data["summary"].get("support_levels", [])
                    resistances = tf_data["summary"].get("resistance_levels", [])
                    
                    all_supports.extend(supports)
                    all_resistances.extend(resistances)
            
            # Destek seviyelerini filtrele (fiyatın altındakiler)
            supports_below = [s for s in all_supports if s < current_price]
            
            # Direnç seviyelerini filtrele (fiyatın üstündekiler)
            resistances_above = [r for r in all_resistances if r > current_price]
            
            # En yakın destek ve direnç
            nearest_support = max(supports_below) if supports_below else None
            nearest_resistance = min(resistances_above) if resistances_above else None
            
            return nearest_support, nearest_resistance
            
        except Exception as e:
            logger.error(f"En yakın seviyeler bulunurken hata: {e}")
            return None, None
    
    def _identify_key_timeframes(self, results: Dict) -> List[str]:
        """
        En güçlü sinyalleri veren zaman dilimlerini belirle
        
        Args:
            results: Tüm analiz sonuçları
            
        Returns:
            List[str]: Anahtar zaman dilimleri listesi
        """
        key_timeframes = []
        
        # Her zaman dilimi için sinyal gücünü kontrol et
        for tf, tf_data in results["timeframes"].items():
            if "summary" in tf_data:
                signal = tf_data["summary"].get("signal", "neutral")
                confidence = tf_data["summary"].get("confidence", "low")
                
                if signal != "neutral" and confidence in ["medium", "high"]:
                    key_timeframes.append(tf)
        
        return key_timeframes
    
    def _calculate_success_probability(self, results: Dict, signal: str, 
                                     signal_strength: float) -> float:
        """
        Sinyal başarı olasılığını hesapla
        
        Args:
            results: Tüm analiz sonuçları
            signal: Genel sinyal ("buy", "sell", "neutral")
            signal_strength: Sinyal gücü (0-100)
            
        Returns:
            float: Başarı olasılığı (0-100)
        """
        # Baz olasılık (sinyal gücüne dayanır)
        base_probability = signal_strength
        
        # Çoklu zaman dilimi onayı için bonus
        timeframe_confirmations = 0
        
        for tf_data in results["timeframes"].values():
            if "summary" in tf_data:
                if tf_data["summary"].get("signal", "neutral") == signal:
                    timeframe_confirmations += 1
        
        # Her onay için %5 bonus
        confirmation_bonus = min(timeframe_confirmations * 5, 20)
        
        # Haber etkisi için düzeltme
        news_correction = 0
        
        if "news" in results:
            news_impact = results["news"].get("impact", 0)
            
            if (signal == "buy" and news_impact > 0) or (signal == "sell" and news_impact < 0):
                news_correction = min(abs(news_impact) * 10, 10)  # Max %10 bonus
            elif (signal == "buy" and news_impact < 0) or (signal == "sell" and news_impact > 0):
                news_correction = -min(abs(news_impact) * 10, 15)  # Max -%15 penalty
        
        # Trend gücü için düzeltme
        trend_correction = 0
        
        # H4 veya D1 zaman dilimindeki trend bilgisini kullan
        for tf in ["D1", "H4"]:
            if tf in results["timeframes"]:
                tf_data = results["timeframes"][tf]
                if "analysis" in tf_data and "price_action" in tf_data["analysis"]:
                    pa_data = tf_data["analysis"]["price_action"]
                    
                    trend = pa_data.get("trend", "sideways")
                    trend_strength = pa_data.get("trend_strength", 0)
                    
                    if (signal == "buy" and trend == "bullish") or (signal == "sell" and trend == "bearish"):
                        trend_correction = min(trend_strength * 0.15, 15)  # Max %15 bonus
                    elif (signal == "buy" and trend == "bearish") or (signal == "sell" and trend == "bullish"):
                        trend_correction = -min(trend_strength * 0.2, 20)  # Max -%20 penalty
                    
                    break
        
        # Toplam olasılık
        total_probability = base_probability + confirmation_bonus + news_correction + trend_correction
        
        # 0-100 arasına sınırla
        return max(0, min(total_probability, 100))