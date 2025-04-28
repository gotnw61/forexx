#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için SMC (Smart Money Concepts) strateji modülü.
Arz-talep bölgeleri, piyasa yapısı analizi ve akıllı para konseptlerini kullanarak
teknik analiz yapar.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger("ForexTradingBot.SMCStrategy")

class SMCStrategy:
    """
    SMC teknik analiz stratejisi uygulayan sınıf.
    """
    
    def __init__(self, data_manager):
        """
        SMC strateji modülünü başlat
        
        Args:
            data_manager: Veri yöneticisi
        """
        self.data_manager = data_manager
        logger.info("SMC strateji modülü başlatıldı")
    
    def analyze(self, symbol: str, timeframe: str) -> Dict:
        """
        Belirli bir sembol ve zaman dilimi için SMC analizi yap
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            timeframe: Zaman dilimi (örn. "H1", "D1")
            
        Returns:
            Dict: SMC analiz sonuçları
        """
        try:
            # Veriyi al
            df = self.data_manager.get_historical_data(symbol, timeframe)
            
            if df.empty:
                logger.warning(f"SMC analizi için veri bulunamadı: {symbol} {timeframe}")
                return {"error": "Veri bulunamadı"}
            
            # Sonuçları topla
            results = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.now()
            }
            
            # Piyasa yapısını analiz et
            market_structure = self._analyze_market_structure(df)
            results["market_structure"] = market_structure
            
            # Arz-talep bölgelerini belirle
            supply_demand = self._find_supply_demand_zones(df)
            results["supply_zones"] = supply_demand["supply"]
            results["demand_zones"] = supply_demand["demand"]
            
            # Premium/Rabat bölgelerini belirle
            premium_discount = self._find_premium_discount_areas(df, market_structure)
            results["premium_areas"] = premium_discount["premium"]
            results["discount_areas"] = premium_discount["discount"]
            
            # Dalgalanma (Impulse/Corrective) analizini yap
            impulse_analysis = self._analyze_impulse_corrective(df, market_structure)
            results["impulse_moves"] = impulse_analysis["impulse"]
            results["corrective_moves"] = impulse_analysis["corrective"]
            
            # Smart Money yapıları belirle
            smart_money_concepts = self._identify_smart_money_concepts(df, results)
            results["patterns"] = smart_money_concepts
            
            # Destek ve direnç seviyelerini belirle
            support_resistance = self._find_support_resistance(df, results)
            results["support_levels"] = support_resistance["support"]
            results["resistance_levels"] = support_resistance["resistance"]
            
            # İşlem sinyali oluştur
            signal, strength = self._generate_signal(df, results)
            results["signal"] = signal
            results["strength"] = strength
            
            return results
            
        except Exception as e:
            logger.error(f"SMC analizi sırasında hata: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """
        Piyasa yapısını analiz et (HH/HL, LH/LL yapıları)
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Piyasa yapısı analizi
        """
        results = {
            "trend": "sideways",  # Genel trend
            "current_phase": "accumulation",  # Birikim, dağıtım veya trendsiz
            "swing_highs": [],  # Salınım yüksekleri
            "swing_lows": [],   # Salınım düşükleri
            "transitions": [],  # Yapı geçişleri
            "key_levels": []    # Kilit seviyeler
        }
        
        try:
            # En az 30 çubuk gerekir
            if len(df) < 30:
                return results
            
            # Tüm swing high/low noktalarını bul
            swing_highs = []
            swing_lows = []
            
            for i in range(5, len(df) - 5):
                # Swing high
                if (df.iloc[i]['high'] > df.iloc[i-1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i-2]['high'] and
                    df.iloc[i]['high'] > df.iloc[i+1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i+2]['high']):
                    
                    swing_highs.append({
                        "index": i,
                        "price": df.iloc[i]['high'],
                        "datetime": df.index[i]
                    })
                
                # Swing low
                if (df.iloc[i]['low'] < df.iloc[i-1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i-2]['low'] and
                    df.iloc[i]['low'] < df.iloc[i+1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i+2]['low']):
                    
                    swing_lows.append({
                        "index": i,
                        "price": df.iloc[i]['low'],
                        "datetime": df.index[i]
                    })
            
            # Yapı geçişlerini belirle
            # Önce kronolojik sırala
            all_swings = sorted(swing_highs + swing_lows, key=lambda x: x["index"])
            
            # HH/HL ve LH/LL yapılarını belirle
            transitions = []
            
            for i in range(2, len(all_swings)):
                current = all_swings[i]
                prev = all_swings[i-2]  # Aynı tip (high/low) için 2 geriye git
                
                if current in swing_highs and prev in swing_highs:
                    # Higher High (HH) veya Lower High (LH)
                    if current["price"] > prev["price"]:
                        transitions.append({
                            "index": current["index"],
                            "type": "HH",  # Higher High
                            "prev_index": prev["index"],
                            "price": current["price"],
                            "prev_price": prev["price"],
                            "datetime": current["datetime"]
                        })
                    else:
                        transitions.append({
                            "index": current["index"],
                            "type": "LH",  # Lower High
                            "prev_index": prev["index"],
                            "price": current["price"],
                            "prev_price": prev["price"],
                            "datetime": current["datetime"]
                        })
                
                elif current in swing_lows and prev in swing_lows:
                    # Higher Low (HL) veya Lower Low (LL)
                    if current["price"] > prev["price"]:
                        transitions.append({
                            "index": current["index"],
                            "type": "HL",  # Higher Low
                            "prev_index": prev["index"],
                            "price": current["price"],
                            "prev_price": prev["price"],
                            "datetime": current["datetime"]
                        })
                    else:
                        transitions.append({
                            "index": current["index"],
                            "type": "LL",  # Lower Low
                            "prev_index": prev["index"],
                            "price": current["price"],
                            "prev_price": prev["price"],
                            "datetime": current["datetime"]
                        })
            
            # Son yapı geçişleri (son 5 geçiş)
            recent_transitions = transitions[-5:] if len(transitions) >= 5 else transitions
            
            # Genel trend ve faz belirle
            if len(recent_transitions) >= 3:
                # Yukarı trend: HH ve HL'ler baskın
                hh_hl_count = sum(1 for t in recent_transitions if t["type"] in ["HH", "HL"])
                lh_ll_count = sum(1 for t in recent_transitions if t["type"] in ["LH", "LL"])
                
                if hh_hl_count >= 3 and hh_hl_count > lh_ll_count:
                    results["trend"] = "uptrend"
                    # Son geçiş LH ise, dağıtım fazında olabilir
                    if recent_transitions[-1]["type"] == "LH":
                        results["current_phase"] = "distribution"
                    else:
                        results["current_phase"] = "markup"
                
                # Aşağı trend: LH ve LL'ler baskın
                elif lh_ll_count >= 3 and lh_ll_count > hh_hl_count:
                    results["trend"] = "downtrend"
                    # Son geçiş HL ise, birikim fazında olabilir
                    if recent_transitions[-1]["type"] == "HL":
                        results["current_phase"] = "accumulation"
                    else:
                        results["current_phase"] = "markdown"
                
                # Karışık yapı: Yatay piyasa
                else:
                    results["trend"] = "sideways"
                    results["current_phase"] = "consolidation"
            
            # Kilit seviyeleri belirle
            # Önemli yapı kırılmaları (trendin başlangıcı veya sonu)
            if len(transitions) >= 3:
                for i in range(1, len(transitions)):
                    current = transitions[i]
                    prev = transitions[i-1]
                    
                    # Trend değişimi işareti
                    if (prev["type"] in ["HH", "HL"] and current["type"] in ["LH", "LL"]) or \
                       (prev["type"] in ["LH", "LL"] and current["type"] in ["HH", "HL"]):
                        results["key_levels"].append({
                            "price": current["price"],
                            "type": "structure_change",
                            "description": f"Trend change signal: {prev['type']} to {current['type']}",
                            "index": current["index"],
                            "datetime": current["datetime"],
                            "importance": "high"
                        })
            
            # Son 10 swing high/low'u sakla
            results["swing_highs"] = swing_highs[-10:] if len(swing_highs) >= 10 else swing_highs
            results["swing_lows"] = swing_lows[-10:] if len(swing_lows) >= 10 else swing_lows
            results["transitions"] = transitions[-10:] if len(transitions) >= 10 else transitions
            
            return results
            
        except Exception as e:
            logger.error(f"Piyasa yapısı analizi sırasında hata: {e}")
            return results
    
    def _find_supply_demand_zones(self, df: pd.DataFrame) -> Dict:
        """
        Arz ve talep bölgelerini belirle
        
        Args:
            df: OHLC verileri içeren DataFrame
            
        Returns:
            Dict: Arz ve talep bölgeleri
        """
        results = {
            "supply": [],  # Arz bölgeleri
            "demand": []   # Talep bölgeleri
        }
        
        try:
            # En az 30 çubuk gerekir
            if len(df) < 30:
                return results
            
            # Ortalama aralık hesapla
            avg_range = np.mean(df['high'] - df['low'])
            
            # Güçlü hareketi belirle (ortalama hareketin 1.5 katı)
            strong_move_threshold = 1.5 * avg_range
            
            # Tüm çubuklar için kontrol et
            for i in range(5, len(df) - 5):
                # İleri hareket (i -> i+3 arasında)
                forward_move = df.iloc[i+3]['close'] - df.iloc[i]['close']
                forward_range = abs(forward_move)
                
                # Hareket güçlü mü?
                if forward_range > strong_move_threshold:
                    # Aşağı yönlü güçlü hareket
                    if forward_move < 0:
                        # Hareket öncesi potansiyel arz bölgesi
                        zone_top = max(df.iloc[i-2:i+1]['high'])
                        zone_bottom = min(df.iloc[i-2:i+1]['close'])
                        
                        # Bölge genişliği çok büyük değilse
                        if (zone_top - zone_bottom) < 2 * avg_range:
                            # Arz bölgesi
                            zone = {
                                "top": zone_top,
                                "bottom": zone_bottom,
                                "index": i,
                                "datetime": df.index[i],
                                "strength": forward_range / avg_range,  # Hareketin gücü
                                "touched": False,  # Bölgeye dokunuldu mu
                                "broken": False    # Bölge kırıldı mı
                            }
                            
                            results["supply"].append(zone)
                    
                    # Yukarı yönlü güçlü hareket
                    else:
                        # Hareket öncesi potansiyel talep bölgesi
                        zone_top = max(df.iloc[i-2:i+1]['open'])
                        zone_bottom = min(df.iloc[i-2:i+1]['low'])
                        
                        # Bölge genişliği çok büyük değilse
                        if (zone_top - zone_bottom) < 2 * avg_range:
                            # Talep bölgesi
                            zone = {
                                "top": zone_top,
                                "bottom": zone_bottom,
                                "index": i,
                                "datetime": df.index[i],
                                "strength": forward_range / avg_range,  # Hareketin gücü
                                "touched": False,  # Bölgeye dokunuldu mu
                                "broken": False    # Bölge kırıldı mı
                            }
                            
                            results["demand"].append(zone)
            
            # Bölgeleri güncelle (sonraki fiyat hareketleriyle etkileşim)
            for zone in results["supply"] + results["demand"]:
                zone_index = zone["index"]
                
                # Bölgeden sonraki çubukları kontrol et
                for i in range(zone_index + 5, len(df)):
                    # Fiyat bölgeye dokundu mu?
                    if zone["bottom"] <= df.iloc[i]['high'] <= zone["top"] or \
                       zone["bottom"] <= df.iloc[i]['low'] <= zone["top"]:
                        zone["touched"] = True
                    
                    # Bölge kırıldı mı?
                    if (zone in results["supply"] and df.iloc[i]['close'] > zone["top"]) or \
                       (zone in results["demand"] and df.iloc[i]['close'] < zone["bottom"]):
                        zone["broken"] = True
                        break
            
            # Kullanılmamış bölgeleri filtrele
            results["supply"] = [z for z in results["supply"] if not z["broken"]]
            results["demand"] = [z for z in results["demand"] if not z["broken"]]
            
            # Güce göre sırala
            results["supply"] = sorted(results["supply"], key=lambda x: x["strength"], reverse=True)
            results["demand"] = sorted(results["demand"], key=lambda x: x["strength"], reverse=True)
            
            # En güçlü 5 bölgeyi tut
            results["supply"] = results["supply"][:5]
            results["demand"] = results["demand"][:5]
            
            return results
            
        except Exception as e:
            logger.error(f"Arz-talep bölgeleri belirlenirken hata: {e}")
            return results
    
    def _find_premium_discount_areas(self, df: pd.DataFrame, market_structure: Dict) -> Dict:
        """
        Premium ve discount (rabatlı) alanları belirle
        
        Args:
            df: OHLC verileri içeren DataFrame
            market_structure: Piyasa yapısı analizi
            
        Returns:
            Dict: Premium ve discount alanları
        """
        results = {
            "premium": [],
            "discount": []
        }
        
        try:
            # En az 30 çubuk ve yapı geçişleri gerekir
            if len(df) < 30 or not market_structure["transitions"]:
                return results
            
            # Trendlerle ayrık çalışacak faz düzeyleri belirle
            
            # Trend yukarı ise
            if market_structure["trend"] == "uptrend":
                # Son 5 yapı geçişini kontrol et
                transitions = market_structure["transitions"][-5:]
                
                # HH ve HL'leri bul
                hh_points = [t for t in transitions if t["type"] == "HH"]
                hl_points = [t for t in transitions if t["type"] == "HL"]
                
                if hh_points and hl_points:
                    # En yüksek HH (trend yüksek)
                    highest_hh = max(hh_points, key=lambda x: x["price"])
                    # En son HL (trend düşük)
                    latest_hl = hl_points[-1]
                    
                    # Premium alan (HH'nin üstü)
                    premium_zone = {
                        "top": highest_hh["price"] * 1.005,  # %0.5 üstü
                        "bottom": highest_hh["price"],
                        "index": highest_hh["index"],
                        "datetime": highest_hh["datetime"],
                        "type": "uptrend_premium"
                    }
                    results["premium"].append(premium_zone)
                    
                    # Discount alan (HL'nin altı, HH'nin çok altında)
                    discount_zone = {
                        "top": latest_hl["price"],
                        "bottom": latest_hl["price"] * 0.995,  # %0.5 altı
                        "index": latest_hl["index"],
                        "datetime": latest_hl["datetime"],
                        "type": "uptrend_discount"
                    }
                    results["discount"].append(discount_zone)
            
            # Trend aşağı ise
            elif market_structure["trend"] == "downtrend":
                # Son 5 yapı geçişini kontrol et
                transitions = market_structure["transitions"][-5:]
                
                # LH ve LL'leri bul
                lh_points = [t for t in transitions if t["type"] == "LH"]
                ll_points = [t for t in transitions if t["type"] == "LL"]
                
                if lh_points and ll_points:
                    # En düşük LL (trend düşük)
                    lowest_ll = min(ll_points, key=lambda x: x["price"])
                    # En son LH (trend yüksek)
                    latest_lh = lh_points[-1]
                    
                    # Premium alan (LL'nin altı)
                    premium_zone = {
                        "top": lowest_ll["price"],
                        "bottom": lowest_ll["price"] * 0.995,  # %0.5 altı
                        "index": lowest_ll["index"],
                        "datetime": lowest_ll["datetime"],
                        "type": "downtrend_premium"
                    }
                    results["premium"].append(premium_zone)
                    
                    # Discount alan (LH'nin üstü, LL'nin çok üstünde)
                    discount_zone = {
                        "top": latest_lh["price"] * 1.005,  # %0.5 üstü
                        "bottom": latest_lh["price"],
                        "index": latest_lh["index"],
                        "datetime": latest_lh["datetime"],
                        "type": "downtrend_discount"
                    }
                    results["discount"].append(discount_zone)
            
            # Trendsiz (yatay) ise
            else:
                # Swing high/low'ları kullan
                if market_structure["swing_highs"] and market_structure["swing_lows"]:
                    # Son 3 swing high/low'u al
                    highs = market_structure["swing_highs"][-3:]
                    lows = market_structure["swing_lows"][-3:]
                    
                    if highs and lows:
                        # En yüksek swing high
                        highest_high = max(highs, key=lambda x: x["price"])
                        # En düşük swing low
                        lowest_low = min(lows, key=lambda x: x["price"])
                        
                        # Premium alan (En yüksek noktanın üstü)
                        premium_zone = {
                            "top": highest_high["price"] * 1.005,  # %0.5 üstü
                            "bottom": highest_high["price"],
                            "index": highest_high["index"],
                            "datetime": highest_high["datetime"],
                            "type": "range_premium"
                        }
                        results["premium"].append(premium_zone)
                        
                        # Discount alan (En düşük noktanın altı)
                        discount_zone = {
                            "top": lowest_low["price"],
                            "bottom": lowest_low["price"] * 0.995,  # %0.5 altı
                            "index": lowest_low["index"],
                            "datetime": lowest_low["datetime"],
                            "type": "range_discount"
                        }
                        results["discount"].append(discount_zone)
            
            return results
            
        except Exception as e:
            logger.error(f"Premium/Discount alanları belirlenirken hata: {e}")
            return results
    
    def _analyze_impulse_corrective(self, df: pd.DataFrame, market_structure: Dict) -> Dict:
        """
        Dürtü (Impulse) ve düzeltme (Corrective) hareketlerini analiz et
        
        Args:
            df: OHLC verileri içeren DataFrame
            market_structure: Piyasa yapısı analizi
            
        Returns:
            Dict: Dürtü ve düzeltme hareketleri
        """
        results = {
            "impulse": [],
            "corrective": []
        }
        
        try:
            # En az 30 çubuk ve swing noktaları gerekir
            if len(df) < 30 or not market_structure["swing_highs"] or not market_structure["swing_lows"]:
                return results
            
            # Tüm swing noktalarını kronolojik sırala
            all_swings = sorted(
                market_structure["swing_highs"] + market_structure["swing_lows"],
                key=lambda x: x["index"]
            )
            
            # En az 3 swing noktası gerekir
            if len(all_swings) < 3:
                return results
            
            # Ortalama salınım büyüklüğü hesapla
            avg_swing = 0
            for i in range(1, len(all_swings)):
                avg_swing += abs(all_swings[i]["price"] - all_swings[i-1]["price"])
            avg_swing /= (len(all_swings) - 1)
            
            # Hareketleri belirle
            for i in range(1, len(all_swings) - 1):
                start = all_swings[i-1]
                middle = all_swings[i]
                end = all_swings[i+1]
                
                # Fiyat hareketleri
                first_leg = middle["price"] - start["price"]
                second_leg = end["price"] - middle["price"]
                
                # Hareket büyüklükleri
                first_size = abs(first_leg)
                second_size = abs(second_leg)
                
                # Mum sayıları
                first_length = middle["index"] - start["index"]
                second_length = end["index"] - middle["index"]
                
                # Dürtü (Impulse) hareketi
                if first_size > avg_swing * 1.5 and first_length < 15:
                    move = {
                        "start_index": start["index"],
                        "end_index": middle["index"],
                        "start_price": start["price"],
                        "end_price": middle["price"],
                        "size": first_size,
                        "bars": first_length,
                        "direction": "up" if first_leg > 0 else "down",
                        "speed": first_size / first_length  # Hız (fiyat/çubuk)
                    }
                    results["impulse"].append(move)
                
                # Düzeltme (Corrective) hareketi
                if second_size < first_size * 0.618 and second_length > first_length:
                    move = {
                        "start_index": middle["index"],
                        "end_index": end["index"],
                        "start_price": middle["price"],
                        "end_price": end["price"],
                        "size": second_size,
                        "bars": second_length,
                        "direction": "up" if second_leg > 0 else "down",
                        "depth": second_size / first_size,  # Düzeltme derinliği
                        "speed": second_size / second_length  # Hız (fiyat/çubuk)
                    }
                    results["corrective"].append(move)
            
            # En son 5 hareketi tut
            results["impulse"] = results["impulse"][-5:]
            results["corrective"] = results["corrective"][-5:]
            
            return results
            
        except Exception as e:
            logger.error(f"Dürtü/Düzeltme analizi sırasında hata: {e}")
            return results
    
    def _identify_smart_money_concepts(self, df: pd.DataFrame, analysis_results: Dict) -> List[str]:
        """
        Smart Money konseptlerini ve formasyonlarını belirle
        
        Args:
            df: OHLC verileri içeren DataFrame
            analysis_results: SMC analiz sonuçları
            
        Returns:
            List[str]: Smart Money formasyonları
        """
        patterns = []
        
        try:
            # Son fiyat
            last_price = df['close'].iloc[-1]
            
            # Trend belirle
            trend = analysis_results.get("market_structure", {}).get("trend", "sideways")
            
            # Son birikim/dağıtım fazını kontrol et
            phase = analysis_results.get("market_structure", {}).get("current_phase", "")
            
            if phase == "accumulation" and trend != "uptrend":
                patterns.append("Accumulation Phase (Smart Money Buying)")
            elif phase == "distribution" and trend != "downtrend":
                patterns.append("Distribution Phase (Smart Money Selling)")
            
            # Arz bölgelerini kontrol et
            supply_zones = analysis_results.get("supply_zones", [])
            active_supply = [z for z in supply_zones if z["bottom"] <= last_price * 1.01]
            
            if active_supply:
                if trend == "uptrend" and phase == "distribution":
                    patterns.append("Bearish Supply Zone at Distribution Phase")
                elif trend == "downtrend" and len(active_supply) >= 2:
                    patterns.append("Strong Bearish Supply Zone Confluence")
            
            # Talep bölgelerini kontrol et
            demand_zones = analysis_results.get("demand_zones", [])
            active_demand = [z for z in demand_zones if z["top"] >= last_price * 0.99]
            
            if active_demand:
                if trend == "downtrend" and phase == "accumulation":
                    patterns.append("Bullish Demand Zone at Accumulation Phase")
                elif trend == "uptrend" and len(active_demand) >= 2:
                    patterns.append("Strong Bullish Demand Zone Confluence")
            
            # Premium/Discount alanlarını kontrol et
            premium_areas = analysis_results.get("premium_areas", [])
            discount_areas = analysis_results.get("discount_areas", [])
            
            # Fiyat premium alanda mı?
            for area in premium_areas:
                if area["bottom"] <= last_price <= area["top"]:
                    if trend == "uptrend":
                        patterns.append("Price in Premium Zone (Caution for Longs)")
                    elif trend == "downtrend":
                        patterns.append("Price in Premium Zone (Good for Shorts)")
            
            # Fiyat discount alanda mı?
            for area in discount_areas:
                if area["bottom"] <= last_price <= area["top"]:
                    if trend == "uptrend":
                        patterns.append("Price in Discount Zone (Good for Longs)")
                    elif trend == "downtrend":
                        patterns.append("Price in Discount Zone (Caution for Shorts)")
            
            # Dürtü ve düzeltme hareketlerini kontrol et
            impulse_moves = analysis_results.get("impulse_moves", [])
            corrective_moves = analysis_results.get("corrective_moves", [])
            
            if impulse_moves and corrective_moves:
                last_impulse = impulse_moves[-1]
                last_corrective = corrective_moves[-1]
                
                # Yeni bir dürtü hareketinin başlangıcı mı?
                if last_corrective["end_index"] > last_impulse["end_index"]:
                    if last_corrective["depth"] <= 0.5:  # Sığ düzeltme
                        if last_corrective["direction"] == "down" and trend == "uptrend":
                            patterns.append("Shallow Pullback in Uptrend (Potential Continuation)")
                        elif last_corrective["direction"] == "up" and trend == "downtrend":
                            patterns.append("Shallow Pullback in Downtrend (Potential Continuation)")
            
            # Özel SMC formasyonları
            # BOS (Break of Structure) ve OTE (Optimal Trade Entry)
            market_structure = analysis_results.get("market_structure", {})
            transitions = market_structure.get("transitions", [])
            
            if transitions and len(transitions) >= 2:
                last_transition = transitions[-1]
                prev_transition = transitions[-2]
                
                # BOS (Up) - Lower Low sonrası Higher High
                if prev_transition["type"] == "LL" and last_transition["type"] == "HH":
                    patterns.append("Bullish Break of Structure (BOS)")
                
                # BOS (Down) - Higher High sonrası Lower Low
                elif prev_transition["type"] == "HH" and last_transition["type"] == "LL":
                    patterns.append("Bearish Break of Structure (BOS)")
                
                # OB (Order Block) - Trend değişimi öncesi son blok
                if "order_blocks" in df.columns:
                    last_block_idx = df['order_blocks'].last_valid_index()
                    if last_block_idx is not None and last_block_idx > transitions[-1]["index"]:
                        if trend == "uptrend":
                            patterns.append("Bullish Order Block after BOS")
                        elif trend == "downtrend":
                            patterns.append("Bearish Order Block after BOS")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Smart Money konseptleri belirlenirken hata: {e}")
            return patterns
    
    def _find_support_resistance(self, df: pd.DataFrame, analysis_results: Dict) -> Dict:
        """
        SMC bileşenlerine göre destek ve direnç seviyelerini belirle
        
        Args:
            df: OHLC verileri içeren DataFrame
            analysis_results: SMC analiz sonuçları
            
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
            
            # Swing high/low noktaları
            market_structure = analysis_results.get("market_structure", {})
            
            for high in market_structure.get("swing_highs", []):
                if high["price"] > last_price:
                    results["resistance"].append(high["price"])
                else:
                    results["support"].append(high["price"])
            
            for low in market_structure.get("swing_lows", []):
                if low["price"] < last_price:
                    results["support"].append(low["price"])
                else:
                    results["resistance"].append(low["price"])
            
            # Arz-talep bölgeleri
            for zone in analysis_results.get("supply_zones", []):
                if zone["bottom"] > last_price:
                    results["resistance"].append(zone["bottom"])
                    results["resistance"].append(zone["top"])
            
            for zone in analysis_results.get("demand_zones", []):
                if zone["top"] < last_price:
                    results["support"].append(zone["bottom"])
                    results["support"].append(zone["top"])
            
            # Premium/Discount alanları
            for area in analysis_results.get("premium_areas", []):
                if area["bottom"] > last_price:
                    results["resistance"].append(area["bottom"])
            
            for area in analysis_results.get("discount_areas", []):
                if area["top"] < last_price:
                    results["support"].append(area["top"])
            
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
        SMC analizi sonuçlarına göre işlem sinyali oluştur
        
        Args:
            df: OHLC verileri içeren DataFrame
            analysis_results: SMC analiz sonuçları
            
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
            
            # Piyasa yapısını değerlendir
            market_structure = analysis_results.get("market_structure", {})
            trend = market_structure.get("trend", "sideways")
            phase = market_structure.get("current_phase", "")
            
            # Trend bazlı başlangıç puanları
            if trend == "uptrend":
                buy_score += 2
            elif trend == "downtrend":
                sell_score += 2
            
            # Faz bazlı puanlar
            if phase == "accumulation":
                buy_score += 1
            elif phase == "distribution":
                sell_score += 1
            elif phase == "markup":
                buy_score += 2
            elif phase == "markdown":
                sell_score += 2
            
            # Arz-talep bölgelerini değerlendir
            for zone in analysis_results.get("demand_zones", []):
                # Fiyat talep bölgesinde veya üstünde mi?
                if zone["bottom"] <= last_price <= zone["top"] * 1.01:
                    buy_score += 3
                elif last_price < zone["bottom"] and (zone["bottom"] - last_price) / last_price < 0.003:
                    buy_score += 2  # Fiyat talep bölgesine yaklaşıyor
            
            for zone in analysis_results.get("supply_zones", []):
                # Fiyat arz bölgesinde veya altında mı?
                if zone["bottom"] * 0.99 <= last_price <= zone["top"]:
                    sell_score += 3
                elif last_price > zone["top"] and (last_price - zone["top"]) / last_price < 0.003:
                    sell_score += 2  # Fiyat arz bölgesine yaklaşıyor
            
            # Premium/Discount alanlarını değerlendir
            for area in analysis_results.get("premium_areas", []):
                if area["bottom"] <= last_price <= area["top"]:
                    if "uptrend" in area.get("type", ""):
                        sell_score += 2  # Yükseliş trendinde premium alan = satış fırsatı
                    elif "downtrend" in area.get("type", ""):
                        sell_score += 3  # Düşüş trendinde premium alan = güçlü satış
            
            for area in analysis_results.get("discount_areas", []):
                if area["bottom"] <= last_price <= area["top"]:
                    if "uptrend" in area.get("type", ""):
                        buy_score += 3  # Yükseliş trendinde discount alan = güçlü alış
                    elif "downtrend" in area.get("type", ""):
                        buy_score += 2  # Düşüş trendinde discount alan = alış fırsatı
            
            # Dürtü/Düzeltme hareketleri
            impulse_moves = analysis_results.get("impulse_moves", [])
            corrective_moves = analysis_results.get("corrective_moves", [])
            
            if impulse_moves and corrective_moves:
                last_impulse = impulse_moves[-1]
                last_corrective = corrective_moves[-1]
                
                # Son düzeltme hareketi son dürtü hareketinden sonra mı?
                if last_corrective["end_index"] > last_impulse["end_index"]:
                    if last_impulse["direction"] == "up" and last_corrective["direction"] == "down":
                        # Yükseliş dürtüsü sonrası düşüş düzeltmesi
                        if last_corrective["depth"] < 0.618:  # %61.8'den az geri çekilme
                            buy_score += 3  # Güçlü yükseliş devamı sinyali
                    
                    elif last_impulse["direction"] == "down" and last_corrective["direction"] == "up":
                        # Düşüş dürtüsü sonrası yükseliş düzeltmesi
                        if last_corrective["depth"] < 0.618:  # %61.8'den az geri çekilme
                            sell_score += 3  # Güçlü düşüş devamı sinyali
            
            # Smart Money formasyonları değerlendir
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
            logger.error(f"SMC sinyali oluşturulurken hata: {e}")
            return "neutral", 0