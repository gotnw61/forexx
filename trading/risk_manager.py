#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için risk yönetim modülü.
Hesap bakiyesine göre pozisyon boyutu hesaplaması ve risk kontrolleri yapar.
"""
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta
import math

logger = logging.getLogger("ForexTradingBot.RiskManager")

class RiskManager:
    """
    Risk yönetimi ve pozisyon boyutu hesaplaması yapan sınıf.
    """
    
    def __init__(self, broker_connector, settings):
        """
        Risk yöneticisini başlat
        
        Args:
            broker_connector: MT5 bağlantısı için broker connector
            settings: Uygulama ayarları
        """
        self.broker = broker_connector
        self.settings = settings
        
        # Risk yönetim geçmişi ve günlük/haftalık takip
        self.risk_history = []
        self.daily_risk = 0.0
        self.weekly_risk = 0.0
        self.last_reset_day = datetime.now().date()
        self.last_reset_week = self._get_week_number(datetime.now())
        
        logger.info("Risk yöneticisi başlatıldı")
    
    def calculate_risk_params(self, signal: Dict) -> Dict:
        """
        İşlem sinyaline göre risk parametrelerini hesapla
        
        Args:
            signal: İşlem sinyali
            
        Returns:
            Dict: Risk parametreleri
        """
        params = {
            "lot_size": 0.01,              # Varsayılan minimum lot
            "risk_amount": 0.0,            # Risk edilen tutar
            "risk_percent": 0.0,           # Hesap bakiyesinin yüzdesi
            "max_allowed": True,           # İzin verilen maksimum riski aşıyor mu
            "sl_pips": 0,                  # Stop loss mesafesi (pip)
            "tp_pips": 0,                  # Take profit mesafesi (pip)
            "pip_value": 0.0,              # Pip başına değer
            "risk_reward_ratio": 0.0,      # Risk/Ödül oranı
            "margin_required": 0.0,        # Gerekli marjin
            "max_lot_allowed": 0.0         # İzin verilen maksimum lot
        }
        
        try:
            # Hesap bilgilerini al
            account_info = self.broker.get_account_info()
            
            if not account_info:
                logger.error("Hesap bilgileri alınamadı, varsayılan risk parametreleri kullanılıyor")
                return params
            
            # Hesap bakiyesi ve para birimi
            balance = account_info.get("balance", 0.0)
            currency = account_info.get("currency", "USD")
            
            # Sembol bilgilerini al
            symbol = signal.get("symbol", "")
            symbol_info = self.broker.get_symbol_info(symbol)
            
            if not symbol_info:
                logger.error(f"Sembol bilgileri alınamadı: {symbol}")
                return params
            
            # Pip değerini hesapla
            contract_size = symbol_info.get("contract_size", 100000)
            digits = symbol_info.get("digits", 5)
            
            # JPY çiftleri için pip değeri farklıdır
            pip_factor = 0.01 if symbol.endswith("JPY") else 0.0001
            
            # Bir pip'in değeri (hesap para birimi cinsinden)
            pip_value = (pip_factor * contract_size) / 10**digits
            
            # SL/TP mesafelerini pip cinsinden hesapla
            entry_price = signal.get("entry_price", 0.0)
            stop_loss = signal.get("stop_loss", 0.0)
            take_profit = signal.get("take_profit", 0.0)
            
            if signal.get("signal") == "buy":
                sl_distance = entry_price - stop_loss
                tp_distance = take_profit - entry_price
            else:  # sell
                sl_distance = stop_loss - entry_price
                tp_distance = entry_price - take_profit
            
            sl_pips = int(sl_distance / pip_factor)
            tp_pips = int(tp_distance / pip_factor)
            
            # Risk/Ödül oranı
            risk_reward = tp_distance / sl_distance if sl_distance > 0 else 0
            
            # Risk ayarları
            risk_settings = self.settings.get("risk_management", {})
            max_risk_percent = risk_settings.get("max_risk_percent", 2.0)
            max_daily_risk_percent = risk_settings.get("max_daily_risk_percent", 5.0)
            max_weekly_risk_percent = risk_settings.get("max_weekly_risk_percent", 10.0)
            
            # Günlük ve haftalık risk takibini güncelle
            self._update_risk_tracking()
            
            # Başarı olasılığına göre risk yüzdesini ayarla
            success_probability = signal.get("success_probability", 0.0)
            
            if success_probability >= 80:
                risk_percent = max_risk_percent  # Tam risk
            elif success_probability >= 70:
                risk_percent = max_risk_percent * 0.8  # %80 risk
            elif success_probability >= 60:
                risk_percent = max_risk_percent * 0.6  # %60 risk
            else:
                risk_percent = max_risk_percent * 0.5  # %50 risk
            
            # Günlük/haftalık risk limitlerini kontrol et
            remaining_daily_risk = (max_daily_risk_percent - self.daily_risk) / 100 * balance
            remaining_weekly_risk = (max_weekly_risk_percent - self.weekly_risk) / 100 * balance
            
            # Kullanılabilir en düşük risk
            available_risk = min(remaining_daily_risk, remaining_weekly_risk)
            
            # Risk tutarını hesapla
            risk_amount = balance * risk_percent / 100
            
            # Kullanılabilir riskten fazla ise sınırla
            if risk_amount > available_risk:
                risk_amount = available_risk
                risk_percent = risk_amount / balance * 100
            
            # Risk tutarına göre lot büyüklüğünü hesapla
            if sl_pips > 0 and pip_value > 0:
                lot_size = risk_amount / (sl_pips * pip_value)
            else:
                lot_size = 0.01  # Minimum lot
            
            # Lot büyüklüğünü yuvarla (0.01 çarpanları)
            lot_size = round(lot_size / 0.01) * 0.01
            
            # Minimum ve maksimum lot kontrolü
            min_lot = symbol_info.get("volume_min", 0.01)
            max_lot = symbol_info.get("volume_max", 100.0)
            max_allowed_lot = risk_settings.get("max_lot_size", 1.0)
            
            lot_size = max(min_lot, min(lot_size, max_lot, max_allowed_lot))
            
            # Marjin hesapla
            margin_params = self.broker.calculate_margin(
                symbol, 
                signal.get("signal", "buy"), 
                lot_size
            )
            
            margin_required = margin_params.get("margin", 0.0) if margin_params else 0.0
            
            # Parametreleri doldur
            params["lot_size"] = lot_size
            params["risk_amount"] = risk_amount
            params["risk_percent"] = risk_percent
            params["max_allowed"] = risk_amount <= available_risk
            params["sl_pips"] = sl_pips
            params["tp_pips"] = tp_pips
            params["pip_value"] = pip_value
            params["risk_reward_ratio"] = risk_reward
            params["margin_required"] = margin_required
            params["max_lot_allowed"] = max_allowed_lot
            
            return params
            
        except Exception as e:
            logger.error(f"Risk parametreleri hesaplanırken hata: {e}", exc_info=True)
            return params
    
    def check_position_limits(self) -> Dict:
        """
        Açık pozisyon limitlerini kontrol et
        
        Returns:
            Dict: Limit durumları
        """
        limits = {
            "max_positions_reached": False,
            "max_positions_per_symbol_reached": {},
            "current_open_positions": 0,
            "positions_per_symbol": {},
            "max_positions": 0,
            "max_positions_per_symbol": 0
        }
        
        try:
            # Risk ayarları
            risk_settings = self.settings.get("risk_management", {})
            max_positions = risk_settings.get("max_open_positions", 5)
            max_positions_per_symbol = risk_settings.get("max_positions_per_symbol", 2)
            
            # Açık pozisyonları al
            positions_df = self.broker.get_positions()
            
            if positions_df.empty:
                # Açık pozisyon yok
                limits["max_positions"] = max_positions
                limits["max_positions_per_symbol"] = max_positions_per_symbol
                return limits
            
            # Toplam açık pozisyon sayısı
            total_positions = len(positions_df)
            limits["current_open_positions"] = total_positions
            limits["max_positions"] = max_positions
            limits["max_positions_reached"] = total_positions >= max_positions
            
            # Sembol başına pozisyon sayısı
            positions_per_symbol = positions_df['symbol'].value_counts().to_dict()
            limits["positions_per_symbol"] = positions_per_symbol
            limits["max_positions_per_symbol"] = max_positions_per_symbol
            
            # Sembol başına limit kontrolü
            for symbol, count in positions_per_symbol.items():
                limits["max_positions_per_symbol_reached"][symbol] = count >= max_positions_per_symbol
            
            return limits
            
        except Exception as e:
            logger.error(f"Pozisyon limitleri kontrol edilirken hata: {e}")
            return limits
    
    def can_open_position(self, signal: Dict) -> Tuple[bool, str]:
        """
        Yeni bir pozisyon açılabilir mi kontrol et
        
        Args:
            signal: İşlem sinyali
            
        Returns:
            Tuple[bool, str]: (Açılabilir mi, Açılamazsa nedeni)
        """
        try:
            # Hesap bilgilerini al
            account_info = self.broker.get_account_info()
            
            if not account_info:
                return False, "Hesap bilgileri alınamadı"
            
            # Hesap bakiyesi ve marjin
            balance = account_info.get("balance", 0.0)
            free_margin = account_info.get("free_margin", 0.0)
            
            # Sembol
            symbol = signal.get("symbol", "")
            
            # Pozisyon limitlerini kontrol et
            limits = self.check_position_limits()
            
            if limits["max_positions_reached"]:
                return False, f"Maksimum açık pozisyon limitine ulaşıldı ({limits['max_positions']})"
            
            if symbol in limits["max_positions_per_symbol_reached"] and limits["max_positions_per_symbol_reached"][symbol]:
                return False, f"{symbol} için maksimum pozisyon limitine ulaşıldı ({limits['max_positions_per_symbol']})"
            
            # Risk parametrelerini hesapla
            risk_params = self.calculate_risk_params(signal)
            
            # Marjin yeterli mi kontrol et
            if risk_params["margin_required"] > free_margin:
                return False, f"Yetersiz marjin: Gereken {risk_params['margin_required']}, Mevcut {free_margin}"
            
            # Günlük/haftalık risk limitlerini kontrol et
            if not risk_params["max_allowed"]:
                return False, "Günlük veya haftalık maksimum risk limitine ulaşıldı"
            
            # Min lot kontrolü
            if risk_params["lot_size"] < 0.01:
                return False, "Hesaplanan lot büyüklüğü çok küçük (< 0.01)"
            
            # Risk/Ödül oranı kontrolü
            min_risk_reward = self.settings.get("signal", {}).get("min_risk_reward", 1.5)
            
            if risk_params["risk_reward_ratio"] < min_risk_reward:
                return False, f"Risk/Ödül oranı çok düşük: {risk_params['risk_reward_ratio']:.2f} < {min_risk_reward}"
            
            return True, "İşlem açılabilir"
            
        except Exception as e:
            logger.error(f"Pozisyon açma kontrolü sırasında hata: {e}")
            return False, f"Kontrol sırasında hata: {str(e)}"
    
    def update_risk_history(self, trade_data: Dict) -> None:
        """
        Risk geçmişini güncelle
        
        Args:
            trade_data: İşlem verileri
        """
        try:
            # Hesap bilgilerini al
            account_info = self.broker.get_account_info()
            
            if not account_info:
                logger.error("Risk geçmişi güncellenirken hesap bilgileri alınamadı")
                return
            
            # Hesap bakiyesi
            balance = account_info.get("balance", 0.0)
            
            # Risk tutarını hesapla
            risk_amount = trade_data.get("risk_amount", 0.0)
            risk_percent = (risk_amount / balance) * 100 if balance > 0 else 0
            
            # Risk geçmişine ekle
            risk_entry = {
                "timestamp": datetime.now(),
                "symbol": trade_data.get("symbol", ""),
                "direction": trade_data.get("signal", ""),
                "lot_size": trade_data.get("lot_size", 0.0),
                "risk_amount": risk_amount,
                "risk_percent": risk_percent,
                "balance": balance
            }
            
            self.risk_history.append(risk_entry)
            
            # Geçmişi son 100 girişle sınırla
            if len(self.risk_history) > 100:
                self.risk_history = self.risk_history[-100:]
            
            # Günlük ve haftalık riski güncelle
            self.daily_risk += risk_percent
            self.weekly_risk += risk_percent
            
            logger.info(f"Risk geçmişi güncellendi: {risk_entry}")
            
        except Exception as e:
            logger.error(f"Risk geçmişi güncellenirken hata: {e}")
    
    def _update_risk_tracking(self) -> None:
        """
        Günlük ve haftalık risk takibini güncelle
        """
        try:
            current_date = datetime.now().date()
            current_week = self._get_week_number(datetime.now())
            
            # Günlük takibi sıfırla
            if current_date != self.last_reset_day:
                self.daily_risk = 0.0
                self.last_reset_day = current_date
                logger.info("Günlük risk takibi sıfırlandı")
            
            # Haftalık takibi sıfırla
            if current_week != self.last_reset_week:
                self.weekly_risk = 0.0
                self.last_reset_week = current_week
                logger.info("Haftalık risk takibi sıfırlandı")
                
        except Exception as e:
            logger.error(f"Risk takibi güncellenirken hata: {e}")
    
    def _get_week_number(self, date: datetime) -> int:
        """
        Tarih için hafta numarasını döndür
        
        Args:
            date: Tarih
            
        Returns:
            int: Hafta numarası
        """
        return date.isocalendar()[1]
    
    def get_risk_history(self, days: int = 7) -> List[Dict]:
        """
        Belirli gün sayısı için risk geçmişini döndür
        
        Args:
            days: Gün sayısı
            
        Returns:
            List[Dict]: Risk geçmişi
        """
        try:
            # Başlangıç tarihini hesapla
            start_date = datetime.now() - timedelta(days=days)
            
            # Belirtilen tarihten sonraki kayıtları filtrele
            filtered_history = [
                entry for entry in self.risk_history 
                if entry.get("timestamp") >= start_date
            ]
            
            return filtered_history
            
        except Exception as e:
            logger.error(f"Risk geçmişi alınırken hata: {e}")
            return []
    
    def get_risk_summary(self) -> Dict:
        """
        Risk özet bilgilerini döndür
        
        Returns:
            Dict: Risk özeti
        """
        summary = {
            "daily_risk": self.daily_risk,
            "weekly_risk": self.weekly_risk,
            "max_daily_risk": self.settings.get("risk_management", {}).get("max_daily_risk_percent", 5.0),
            "max_weekly_risk": self.settings.get("risk_management", {}).get("max_weekly_risk_percent", 10.0),
            "total_trades_today": 0,
            "avg_risk_per_trade": 0.0
        }
        
        try:
            # Bugünkü işlem sayısını hesapla
            today = datetime.now().date()
            todays_trades = [
                entry for entry in self.risk_history 
                if entry.get("timestamp").date() == today
            ]
            
            summary["total_trades_today"] = len(todays_trades)
            
            # İşlem başına ortalama risk
            if summary["total_trades_today"] > 0:
                avg_risk = sum(entry.get("risk_percent", 0.0) for entry in todays_trades) / summary["total_trades_today"]
                summary["avg_risk_per_trade"] = avg_risk
            
            return summary
            
        except Exception as e:
            logger.error(f"Risk özeti oluşturulurken hata: {e}")
            return summary