#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için işlem sinyali oluşturucu.
Analiz ve AI tahmin sonuçlarını birleştirerek işlem sinyalleri oluşturur.
"""
import logging
import uuid
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

logger = logging.getLogger("ForexTradingBot.SignalGenerator")

class SignalGenerator:
    """
    İşlem sinyallerini oluşturan sınıf.
    """
    
    def __init__(self, analysis_engine, ai_predictor, settings):
        """
        Sinyal oluşturucuyu başlat
        
        Args:
            analysis_engine: Analiz motoru
            ai_predictor: AI tahmin motoru
            settings: Uygulama ayarları
        """
        self.analysis_engine = analysis_engine
        self.ai_predictor = ai_predictor
        self.settings = settings
        
        # Sinyal geçmişi
        self.signal_history = []
        
        logger.info("Sinyal oluşturucu başlatıldı")
    
    def generate_signal(self, symbol: str, analysis_results: Optional[Dict] = None, 
                      prediction_results: Optional[Dict] = None) -> Optional[Dict]:
        """
        Analiz ve tahmin sonuçlarını birleştirerek işlem sinyali oluştur
        
        Args:
            symbol: İşlem sembolü
            analysis_results: Analiz sonuçları (None ise yeni analiz yap)
            prediction_results: Tahmin sonuçları (None ise yeni tahmin yap)
            
        Returns:
            Optional[Dict]: İşlem sinyali veya None
        """
        try:
            # Analiz sonuçları yoksa yeni analiz yap
            if analysis_results is None:
                timeframes = self.settings.get("timeframes", ["M15", "H1", "H4", "D1"])
                analysis_results = self.analysis_engine.analyze(symbol, timeframes)
            
            # Tahmin sonuçları yoksa yeni tahmin yap
            if prediction_results is None:
                prediction_results = self.ai_predictor.predict(symbol, "H1")
            
            # Sonuçları kontrol et
            if "error" in analysis_results or "error" in prediction_results:
                logger.error(f"Sinyal oluşturulamadı: {symbol} - Analiz veya tahmin hatası")
                return None
            
            # Son fiyatı al
            last_price = self._get_last_price(symbol, analysis_results)
            
            if last_price is None:
                logger.error(f"Son fiyat alınamadı: {symbol}")
                return None
            
            # Genel analiz özetini al
            summary = analysis_results.get("summary", {})
            
            # Analiz ve tahmin sonuçlarını birleştir
            signal_data = self._combine_signals(analysis_results, prediction_results, symbol)
            
            # Sinyal yoksa boş dön
            if signal_data["signal"] == "neutral" or signal_data["strength"] < 40:
                logger.info(f"Zayıf veya nötr sinyal: {symbol} - Sinyal oluşturulmadı")
                return None
            
            # Stop Loss ve Take Profit seviyelerini hesapla
            sl_tp = self._calculate_sl_tp(
                symbol, 
                signal_data["signal"], 
                last_price, 
                analysis_results, 
                prediction_results
            )
            
            if sl_tp is None:
                logger.error(f"SL/TP hesaplanamadı: {symbol}")
                return None
            
            # Risk/Ödül oranını hesapla
            risk_reward = self._calculate_risk_reward(
                signal_data["signal"],
                last_price,
                sl_tp["stop_loss"],
                sl_tp["take_profit"]
            )
            
            # Risk/Ödül oranı çok düşükse sinyal oluşturma
            min_risk_reward = self.settings.get("signal", {}).get("min_risk_reward", 1.5)
            if risk_reward < min_risk_reward:
                logger.info(f"Düşük Risk/Ödül oranı: {symbol} - {risk_reward} < {min_risk_reward}")
                return None
            
            # Sinyal kimliği oluştur
            signal_id = str(uuid.uuid4())
            
            # İşlem sinyali oluştur
            signal = {
                "id": signal_id,
                "symbol": symbol,
                "signal": signal_data["signal"],
                "entry_price": last_price,
                "stop_loss": sl_tp["stop_loss"],
                "take_profit": sl_tp["take_profit"],
                "risk_reward": risk_reward,
                "strength": signal_data["strength"],
                "success_probability": signal_data["success_probability"],
                "timestamp": datetime.now(),
                "timeframes": signal_data["key_timeframes"],
                "analysis_summary": summary,
                "prediction": prediction_results,
                "executed": False,
                "status": "pending"
            }
            
            # Sinyali geçmişe ekle
            self.signal_history.append(signal)
            
            # Geçmişi son 100 sinyalle sınırla
            if len(self.signal_history) > 100:
                self.signal_history = self.signal_history[-100:]
            
            logger.info(f"İşlem sinyali oluşturuldu: {symbol} {signal_data['signal']} (Güven: {signal_data['success_probability']:.1f}%)")
            return signal
            
        except Exception as e:
            logger.error(f"Sinyal oluşturma hatası: {e}", exc_info=True)
            return None
    
    def _get_last_price(self, symbol: str, analysis_results: Dict) -> Optional[float]:
        """
        Son fiyatı al
        
        Args:
            symbol: İşlem sembolü
            analysis_results: Analiz sonuçları
            
        Returns:
            Optional[float]: Son fiyat veya None
        """
        try:
            # H1 veya mevcut olan herhangi bir zaman dilimini kullan
            for timeframe in ["H1", "M15", "H4", "D1"]:
                if timeframe in analysis_results.get("timeframes", {}):
                    last_price = None
                    
                    # Teknik analiz modelinden fiyat al
                    if "price_action" in analysis_results["timeframes"][timeframe].get("analysis", {}):
                        pa_data = analysis_results["timeframes"][timeframe]["analysis"]["price_action"]
                        if "last_price" in pa_data:
                            return pa_data["last_price"]
            
            # Analiz sonuçlarından fiyat alınamazsa veri yöneticisini kullan
            tick_data = self.analysis_engine.data_manager.get_latest_tick_data(symbol)
            if tick_data and "bid" in tick_data:
                return (tick_data["bid"] + tick_data["ask"]) / 2
            
            # Son çare olarak son kapanış fiyatını al
            df = self.analysis_engine.data_manager.get_historical_data(symbol, "H1")
            if not df.empty:
                return df['close'].iloc[-1]
            
            return None
            
        except Exception as e:
            logger.error(f"Son fiyat alınırken hata: {e}")
            return None
    
    def _combine_signals(self, analysis_results: Dict, prediction_results: Dict, symbol: str) -> Dict:
        """
        Analiz ve tahmin sonuçlarını birleştir
        
        Args:
            analysis_results: Analiz sonuçları
            prediction_results: Tahmin sonuçları
            symbol: İşlem sembolü
            
        Returns:
            Dict: Birleştirilmiş sinyal verileri
        """
        combined = {
            "signal": "neutral",  # buy, sell, neutral
            "strength": 0,        # 0-100 arası
            "success_probability": 0,  # 0-100 arası
            "key_timeframes": []
        }
        
        try:
            # Analiz sinyalini al
            analysis_signal = analysis_results.get("summary", {}).get("signal", "neutral")
            analysis_strength = analysis_results.get("summary", {}).get("strength", 0)
            analysis_probability = analysis_results.get("summary", {}).get("success_probability", 0)
            analysis_timeframes = analysis_results.get("summary", {}).get("key_timeframes", [])
            
            # AI tahmin sinyalini al
            prediction_signal = prediction_results.get("direction", "neutral")
            prediction_confidence = prediction_results.get("confidence", 0)
            
            # Sinyal ağırlıkları
            analysis_weight = 0.7  # Analiz %70 ağırlık
            prediction_weight = 0.3  # Tahmin %30 ağırlık
            
            # Sinyal puanları
            buy_score = 0
            sell_score = 0
            
            # Analiz sinyalini değerlendir
            if analysis_signal == "buy":
                buy_score += analysis_strength * analysis_weight
            elif analysis_signal == "sell":
                sell_score += analysis_strength * analysis_weight
            
            # Tahmin sinyalini değerlendir
            if prediction_signal == "buy":
                buy_score += prediction_confidence * prediction_weight
            elif prediction_signal == "sell":
                sell_score += prediction_confidence * prediction_weight
            
            # Sonuçları değerlendir
            if buy_score > sell_score + 10:  # En az 10 puan fark olsun
                combined["signal"] = "buy"
                combined["strength"] = buy_score
            elif sell_score > buy_score + 10:
                combined["signal"] = "sell"
                combined["strength"] = sell_score
            else:
                combined["signal"] = "neutral"
                combined["strength"] = max(buy_score, sell_score) / 2  # Kararsız durumda güç yarıya düşer
            
            # Başarı olasılığını hesapla
            if combined["signal"] == "buy":
                combined["success_probability"] = (analysis_probability * analysis_weight + 
                                                 prediction_confidence * prediction_weight)
            elif combined["signal"] == "sell":
                combined["success_probability"] = (analysis_probability * analysis_weight + 
                                                 prediction_confidence * prediction_weight)
            else:
                combined["success_probability"] = 0
            
            # Anahtar zaman dilimlerini ekle
            combined["key_timeframes"] = analysis_timeframes
            
            return combined
            
        except Exception as e:
            logger.error(f"Sinyaller birleştirilirken hata: {e}")
            return combined
    
    def _calculate_sl_tp(self, symbol: str, signal: str, entry_price: float, 
                       analysis_results: Dict, prediction_results: Dict) -> Optional[Dict]:
        """
        Stop Loss ve Take Profit seviyelerini hesapla
        
        Args:
            symbol: İşlem sembolü
            signal: İşlem sinyali (buy, sell)
            entry_price: Giriş fiyatı
            analysis_results: Analiz sonuçları
            prediction_results: Tahmin sonuçları
            
        Returns:
            Optional[Dict]: SL ve TP seviyeleri veya None
        """
        try:
            # Sonuçları başlat
            result = {
                "stop_loss": None,
                "take_profit": None
            }
            
            # Risk ayarları
            risk_params = self.settings.get("risk_management", {})
            default_sl_pips = risk_params.get("default_stop_loss_pips", 50)
            default_tp_pips = risk_params.get("default_take_profit_pips", 100)
            
            # ATR değerini al (volatiliteye göre SL/TP ayarlamak için)
            atr = self._get_atr_value(symbol, analysis_results)
            
            # ATR bulunamazsa varsayılan pip değerlerini kullan
            if atr is None:
                # Pip değerini fiyata çevir
                pip_value = self._pips_to_price(symbol, 1)
                
                if signal == "buy":
                    result["stop_loss"] = entry_price - (default_sl_pips * pip_value)
                    result["take_profit"] = entry_price + (default_tp_pips * pip_value)
                else:  # sell
                    result["stop_loss"] = entry_price + (default_sl_pips * pip_value)
                    result["take_profit"] = entry_price - (default_tp_pips * pip_value)
                
                return result
            
            # Analiz sonuçlarından destek/direnç seviyelerini al
            support_levels = []
            resistance_levels = []
            
            for tf_data in analysis_results.get("timeframes", {}).values():
                if "summary" in tf_data:
                    supports = tf_data["summary"].get("support_levels", [])
                    resistances = tf_data["summary"].get("resistance_levels", [])
                    
                    support_levels.extend(supports)
                    resistance_levels.extend(resistances)
            
            # Son fiyata en yakın destek/direnci bul
            nearest_support = None
            nearest_resistance = None
            
            if support_levels:
                # Son fiyatın altındaki en yakın destek
                supports_below = [s for s in support_levels if s < entry_price]
                if supports_below:
                    nearest_support = max(supports_below)
            
            if resistance_levels:
                # Son fiyatın üstündeki en yakın direnç
                resistances_above = [r for r in resistance_levels if r > entry_price]
                if resistances_above:
                    nearest_resistance = min(resistances_above)
            
            # ATR bazlı SL/TP hesapla
            atr_sl_multiplier = 1.5  # 1.5 * ATR
            atr_tp_multiplier = 3.0  # 3.0 * ATR
            
            # Destek/dirençler varsa, SL/TP'yi ayarla
            if signal == "buy":
                # Stop Loss: Destek seviyesi veya ATR bazlı
                if nearest_support and entry_price - nearest_support < atr * 2:
                    result["stop_loss"] = nearest_support - (0.1 * atr)  # Destek altında biraz boşluk
                else:
                    result["stop_loss"] = entry_price - (atr * atr_sl_multiplier)
                
                # Take Profit: Direnç seviyesi veya ATR bazlı
                if nearest_resistance and nearest_resistance - entry_price < atr * 4:
                    result["take_profit"] = nearest_resistance
                else:
                    result["take_profit"] = entry_price + (atr * atr_tp_multiplier)
            
            else:  # sell
                # Stop Loss: Direnç seviyesi veya ATR bazlı
                if nearest_resistance and nearest_resistance - entry_price < atr * 2:
                    result["stop_loss"] = nearest_resistance + (0.1 * atr)  # Direnç üstünde biraz boşluk
                else:
                    result["stop_loss"] = entry_price + (atr * atr_sl_multiplier)
                
                # Take Profit: Destek seviyesi veya ATR bazlı
                if nearest_support and entry_price - nearest_support < atr * 4:
                    result["take_profit"] = nearest_support
                else:
                    result["take_profit"] = entry_price - (atr * atr_tp_multiplier)
            
            # SL/TP'yi limitlere göre kontrol et
            # SL çok yakın olmamalı
            min_sl_distance = atr * 0.5
            
            if signal == "buy" and entry_price - result["stop_loss"] < min_sl_distance:
                result["stop_loss"] = entry_price - min_sl_distance
            elif signal == "sell" and result["stop_loss"] - entry_price < min_sl_distance:
                result["stop_loss"] = entry_price + min_sl_distance
            
            # TP yeterince uzak olmalı
            min_tp_distance = atr * 1.0
            
            if signal == "buy" and result["take_profit"] - entry_price < min_tp_distance:
                result["take_profit"] = entry_price + min_tp_distance
            elif signal == "sell" and entry_price - result["take_profit"] < min_tp_distance:
                result["take_profit"] = entry_price - min_tp_distance
            
            return result
            
        except Exception as e:
            logger.error(f"SL/TP hesaplanırken hata: {e}")
            return None
    
    def _get_atr_value(self, symbol: str, analysis_results: Dict) -> Optional[float]:
        """
        ATR değerini al
        
        Args:
            symbol: İşlem sembolü
            analysis_results: Analiz sonuçları
            
        Returns:
            Optional[float]: ATR değeri veya None
        """
        try:
            # Öncelikle H1 zaman dilimindeki ATR'yi kontrol et
            for timeframe in ["H1", "H4", "M15", "D1"]:
                if timeframe in analysis_results.get("timeframes", {}):
                    tf_data = analysis_results["timeframes"][timeframe]
                    
                    if "analysis" in tf_data and "price_action" in tf_data["analysis"]:
                        pa_data = tf_data["analysis"]["price_action"]
                        
                        if "atr" in pa_data:
                            return pa_data["atr"]
            
            # Analiz verilerinde ATR yoksa hesapla
            df = self.analysis_engine.data_manager.get_historical_data(symbol, "H1")
            
            if df.empty:
                return None
                
            # ATR hesapla (14 periyot)
            df['tr1'] = abs(df['high'] - df['low'])
            df['tr2'] = abs(df['high'] - df['close'].shift())
            df['tr3'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            df['atr'] = df['tr'].rolling(window=14).mean()
            
            # Son ATR değerini döndür
            return df['atr'].iloc[-1]
            
        except Exception as e:
            logger.error(f"ATR alınırken hata: {e}")
            return None
    
    def _calculate_risk_reward(self, signal: str, entry_price: float, 
                            stop_loss: float, take_profit: float) -> float:
        """
        Risk/Ödül oranını hesapla
        
        Args:
            signal: İşlem sinyali (buy, sell)
            entry_price: Giriş fiyatı
            stop_loss: Stop Loss seviyesi
            take_profit: Take Profit seviyesi
            
        Returns:
            float: Risk/Ödül oranı
        """
        try:
            # Risk ve ödül mesafelerini hesapla
            if signal == "buy":
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:  # sell
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            # Bölme hatası kontrolü
            if risk <= 0:
                return 0
                
            return reward / risk
            
        except Exception as e:
            logger.error(f"Risk/Ödül hesaplanırken hata: {e}")
            return 0
    
    def _pips_to_price(self, symbol: str, pips: float) -> float:
        """
        Pip değerini fiyata çevir
        
        Args:
            symbol: İşlem sembolü
            pips: Pip değeri
            
        Returns:
            float: Fiyat değeri
        """
        try:
            # JPY çiftleri için pip değeri 0.01, diğerleri için 0.0001
            pip_value = 0.01 if "JPY" in symbol else 0.0001
            
            # XAU (Altın) için özel değer
            if "XAU" in symbol:
                pip_value = 0.1
            
            return pips * pip_value
            
        except Exception as e:
            logger.error(f"Pip-fiyat dönüşümü hatası: {e}")
            return 0.0001 * pips  # Varsayılan değer
    
    def get_signal_history(self, limit: int = 10) -> List[Dict]:
        """
        Son sinyal geçmişini döndür
        
        Args:
            limit: Maksimum sinyal sayısı
            
        Returns:
            List[Dict]: Sinyal geçmişi
        """
        # Son limit kadar sinyali döndür
        return self.signal_history[-limit:] if self.signal_history else []
    
    def get_signal_by_id(self, signal_id: str) -> Optional[Dict]:
        """
        ID'ye göre sinyali bul
        
        Args:
            signal_id: Sinyal kimliği
            
        Returns:
            Optional[Dict]: Sinyal veya None
        """
        # ID'ye göre sinyali filtreleme
        for signal in self.signal_history:
            if signal.get("id") == signal_id:
                return signal
                
        return None
    
    def update_signal_status(self, signal_id: str, status: str, 
                           execution_details: Optional[Dict] = None) -> bool:
        """
        Sinyal durumunu güncelle
        
        Args:
            signal_id: Sinyal kimliği
            status: Yeni durum ("executed", "rejected", "expired", "completed")
            execution_details: İşlem detayları (opsiyonel)
            
        Returns:
            bool: Güncelleme başarılıysa True, aksi halde False
        """
        try:
            # Sinyali bul
            signal = self.get_signal_by_id(signal_id)
            
            if signal is None:
                logger.error(f"Güncellenecek sinyal bulunamadı: {signal_id}")
                return False
            
            # Durumu güncelle
            signal["status"] = status
            
            # İşlem detaylarını ekle
            if status == "executed" and execution_details:
                signal["executed"] = True
                signal["execution_details"] = execution_details
                signal["execution_time"] = datetime.now()
            
            logger.info(f"Sinyal durumu güncellendi: {signal_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Sinyal durumu güncellenirken hata: {e}")
            return False