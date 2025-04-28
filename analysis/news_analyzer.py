#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için haber ve sosyal medya analiz modülü.
Ekonomik takvim ve sosyal medya verilerini analiz eder.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import re

logger = logging.getLogger("ForexTradingBot.NewsAnalyzer")

class NewsAnalyzer:
    """
    Haber ve sosyal medya verilerini analiz eden sınıf.
    """
    
    def __init__(self, data_manager):
        """
        Haber analiz modülünü başlat
        
        Args:
            data_manager: Veri yöneticisi
        """
        self.data_manager = data_manager
        logger.info("Haber analiz modülü başlatıldı")
    
    def analyze(self, symbol: str) -> Dict:
        """
        Belirli bir sembol için haber ve sosyal medya verilerini analiz et
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            
        Returns:
            Dict: Haber ve sosyal medya analiz sonuçları
        """
        try:
            # İlgili para birimlerini çıkar
            currencies = self._extract_currencies(symbol)
            
            # Sonuçları topla
            results = {
                "symbol": symbol,
                "currencies": currencies,
                "timestamp": datetime.now(),
                "news": {},
                "social_media": {},
                "impact": 0,  # -100 ile 100 arasında toplam etki
                "next_events": []
            }
            
            # Ekonomik takvim verilerini analiz et
            news_results = self._analyze_economic_calendar(currencies)
            results["news"] = news_results
            
            # Sosyal medya verilerini analiz et
            social_results = self._analyze_social_media(symbol)
            results["social_media"] = social_results
            
            # Sonraki önemli olayları belirle
            results["next_events"] = self._find_upcoming_events(currencies)
            
            # Toplam etkiyi hesapla
            results["impact"] = self._calculate_total_impact(news_results, social_results, currencies)
            
            return results
            
        except Exception as e:
            logger.error(f"Haber analizi sırasında hata: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _extract_currencies(self, symbol: str) -> List[str]:
        """
        Sembolden para birimlerini çıkar
        
        Args:
            symbol: İşlem sembolü (örn. "EURUSD")
            
        Returns:
            List[str]: Para birimleri listesi
        """
        # Bilinen para birimi kodları
        known_currencies = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "XAU", "XAG"]
        
        # Sembolden para birimlerini çıkar
        result = []
        
        if len(symbol) == 6:
            # Standart forex çifti (örn. EURUSD)
            base = symbol[:3]
            quote = symbol[3:]
            
            if base in known_currencies:
                result.append(base)
            if quote in known_currencies:
                result.append(quote)
        elif symbol.startswith("XAU") or symbol.startswith("XAG"):
            # Altın veya gümüş
            if symbol.startswith("XAU"):
                result.append("XAU")  # Altın
            else:
                result.append("XAG")  # Gümüş
                
            # İkinci para birimi
            quote = symbol[3:]
            if quote in known_currencies:
                result.append(quote)
        
        return result
    
    def _analyze_economic_calendar(self, currencies: List[str]) -> Dict:
        """
        Ekonomik takvim verilerini analiz et
        
        Args:
            currencies: Para birimleri listesi
            
        Returns:
            Dict: Ekonomik takvim analiz sonuçları
        """
        results = {
            "recent_events": [],
            "total_events": 0,
            "high_impact_events": 0,
            "bullish_events": 0,
            "bearish_events": 0,
            "total_impact": 0  # -100 ile 100 arasında
        }
        
        try:
            # Son 24 saat ve gelecek 24 saat için tarihleri belirle
            now = datetime.now()
            start_date = now - timedelta(days=1)
            end_date = now + timedelta(days=1)
            
            # Ekonomik takvim verilerini al
            news_data = self.data_manager.get_news_data(start_date, end_date)
            
            if news_data.empty:
                logger.warning(f"Ekonomik takvim verisi bulunamadı")
                return results
            
            # İlgili para birimleri için haberleri filtrele
            relevant_news = news_data[news_data['currency'].isin(currencies)]
            
            # Özet istatistikler
            results["total_events"] = len(relevant_news)
            results["high_impact_events"] = len(relevant_news[relevant_news['impact'] == 'High'])
            
            # Son olayları işle
            for _, event in relevant_news.iterrows():
                # Olay zamanını kontrol et
                event_time = event['datetime']
                if isinstance(event_time, str):
                    event_time = pd.to_datetime(event_time)
                
                # Olay geçmişte mi?
                is_past = event_time < now
                
                # Gerçek değer beklentiden iyi mi?
                is_better = False
                is_worse = False
                
                if is_past and pd.notna(event['actual']) and pd.notna(event['forecast']):
                    # Sayısal değerleri karşılaştır
                    actual_value = self._parse_numeric(event['actual'])
                    forecast_value = self._parse_numeric(event['forecast'])
                    
                    if actual_value is not None and forecast_value is not None:
                        # Değerin yüksek olması iyi mi?
                        better_is_higher = True
                        
                        # İşsizlik gibi göstergelerde düşük değer iyidir
                        if any(term in event['event'].lower() for term in ['unemployment', 'jobless', 'deficit']):
                            better_is_higher = False
                        
                        is_better = (actual_value > forecast_value) if better_is_higher else (actual_value < forecast_value)
                        is_worse = (actual_value < forecast_value) if better_is_higher else (actual_value > forecast_value)
                
                # Olay etkisi
                event_impact = 0
                impact_factor = {'Low': 1, 'Medium': 2, 'High': 4}.get(event['impact'], 1)
                
                if is_past:
                    if is_better:
                        event_impact = impact_factor
                        results["bullish_events"] += 1
                    elif is_worse:
                        event_impact = -impact_factor
                        results["bearish_events"] += 1
                
                # Para birimi bazında etkiyi ayarla
                currency = event['currency']
                for base_currency in currencies:
                    # Para birimi çiftte ilk sırada mı ikinci sırada mı kontrol et
                    if base_currency == currency and currency == currencies[0]:
                        # İlk para birimi için olumlu etki, olumlu
                        pass
                    elif base_currency == currency and currency != currencies[0]:
                        # İkinci para birimi için olumlu etki, olumsuz
                        event_impact = -event_impact
                
                # Olay detayı
                event_detail = {
                    "datetime": event_time,
                    "currency": currency,
                    "event": event['event'],
                    "impact": event['impact'],
                    "actual": event['actual'] if pd.notna(event['actual']) else None,
                    "forecast": event['forecast'] if pd.notna(event['forecast']) else None,
                    "previous": event['previous'] if pd.notna(event['previous']) else None,
                    "is_past": is_past,
                    "is_better": is_better,
                    "is_worse": is_worse,
                    "event_impact": event_impact
                }
                
                results["recent_events"].append(event_detail)
                results["total_impact"] += event_impact
            
            # Toplam etkiyi -100 ile 100 arasına normalize et
            if results["high_impact_events"] > 0:
                max_impact = results["high_impact_events"] * 4
                results["total_impact"] = max(min(100, results["total_impact"] * 100 / max_impact), -100)
            else:
                results["total_impact"] = 0
            
            return results
            
        except Exception as e:
            logger.error(f"Ekonomik takvim analizi sırasında hata: {e}")
            return results
    
    def _analyze_social_media(self, symbol: str) -> Dict:
        """
        Sosyal medya verilerini analiz et
        
        Args:
            symbol: İşlem sembolü
            
        Returns:
            Dict: Sosyal medya analiz sonuçları
        """
        results = {
            "sentiment": 0,  # -100 ile 100 arasında duyarlılık
            "volume": 0,     # Tweet/mesaj hacmi
            "bullish_ratio": 0,  # 0-1 arası olumlu oran
            "bearish_ratio": 0,  # 0-1 arası olumsuz oran
            "neutral_ratio": 0,  # 0-1 arası nötr oran
            "trending": False,   # Trend konusu mu
            "keywords": []    # Popüler anahtar kelimeler
        }
        
        try:
            # Son 3 gün için tarihleri belirle
            now = datetime.now()
            start_date = now - timedelta(days=3)
            
            # Sosyal medya verilerini al
            social_data = self.data_manager.get_social_media_data(symbol, start_date)
            
            if social_data.empty:
                logger.warning(f"Sosyal medya verisi bulunamadı: {symbol}")
                return results
            
            # Toplam tweet sayısı
            results["volume"] = social_data['tweet_count'].sum()
            
            # Duyarlılık dağılımı
            sentiment_counts = social_data['sentiment'].value_counts()
            total_count = len(social_data)
            
            if total_count > 0:
                results["bullish_ratio"] = sentiment_counts.get('positive', 0) / total_count
                results["bearish_ratio"] = sentiment_counts.get('negative', 0) / total_count
                results["neutral_ratio"] = sentiment_counts.get('neutral', 0) / total_count
            
            # Ortalama duyarlılık puanı
            avg_sentiment = social_data['sentiment_score'].mean()
            if pd.notna(avg_sentiment):
                results["sentiment"] = int(avg_sentiment * 100)  # -100 ile 100 arasına dönüştür
            
            # Trend analizi (son 6 saat için)
            recent_cutoff = now - timedelta(hours=6)
            recent_data = social_data[social_data['datetime'] > recent_cutoff]
            
            # Son 6 saatteki tweet hacmi, toplam hacmin %30'undan fazla mı?
            if len(recent_data) > 0 and results["volume"] > 0:
                recent_ratio = len(recent_data) / results["volume"]
                results["trending"] = recent_ratio > 0.3
            
            # Popüler anahtar kelimeler (simüle edilmiş veri)
            results["keywords"] = ["forex", "trading", "market", "analysis", "trend"]
            
            return results
            
        except Exception as e:
            logger.error(f"Sosyal medya analizi sırasında hata: {e}")
            return results
    
    def _find_upcoming_events(self, currencies: List[str]) -> List[Dict]:
        """
        Gelecekteki önemli ekonomik olayları bul
        
        Args:
            currencies: Para birimleri listesi
            
        Returns:
            List[Dict]: Gelecekteki olaylar listesi
        """
        upcoming_events = []
        
        try:
            # Gelecek 48 saat için verileri al
            now = datetime.now()
            end_date = now + timedelta(days=2)
            
            # Ekonomik takvim verilerini al
            news_data = self.data_manager.get_news_data(now, end_date)
            
            if news_data.empty:
                logger.warning(f"Gelecek ekonomik takvim verisi bulunamadı")
                return upcoming_events
            
            # İlgili para birimleri için haberleri filtrele
            relevant_news = news_data[news_data['currency'].isin(currencies)]
            
            # Önemli olayları filtrele
            high_impact_news = relevant_news[relevant_news['impact'] == 'High']
            
            # Olayları zaman sırasına göre sırala
            sorted_news = high_impact_news.sort_values(by='datetime')
            
            # İlk 5 önemli olayı al
            for _, event in sorted_news.head(5).iterrows():
                event_time = event['datetime']
                if isinstance(event_time, str):
                    event_time = pd.to_datetime(event_time)
                
                event_detail = {
                    "datetime": event_time,
                    "currency": event['currency'],
                    "event": event['event'],
                    "impact": event['impact'],
                    "forecast": event['forecast'] if pd.notna(event['forecast']) else None,
                    "previous": event['previous'] if pd.notna(event['previous']) else None,
                    "time_until": (event_time - now).total_seconds() / 3600  # Saat cinsinden
                }
                
                upcoming_events.append(event_detail)
            
            return upcoming_events
            
        except Exception as e:
            logger.error(f"Gelecek olaylar listelenirken hata: {e}")
            return upcoming_events
    
    def _calculate_total_impact(self, news_results: Dict, 
                             social_results: Dict, 
                             currencies: List[str]) -> float:
        """
        Haber ve sosyal medya verilerinin toplam etkisini hesapla
        
        Args:
            news_results: Ekonomik takvim analiz sonuçları
            social_results: Sosyal medya analiz sonuçları
            currencies: Para birimleri listesi
            
        Returns:
            float: Toplam etki (-100 ile 100 arasında)
        """
        try:
            # Ekonomik takvim etkisi (%70 ağırlık)
            news_impact = news_results.get("total_impact", 0) * 0.7
            
            # Sosyal medya etkisi (%30 ağırlık)
            social_impact = social_results.get("sentiment", 0) * 0.3
            
            # Toplam etki
            total_impact = news_impact + social_impact
            
            # -100 ile 100 arasına sınırla
            total_impact = max(min(total_impact, 100), -100)
            
            return total_impact
            
        except Exception as e:
            logger.error(f"Toplam etki hesaplanırken hata: {e}")
            return 0
    
    def _parse_numeric(self, value_str: str) -> Optional[float]:
        """
        String'den sayısal değeri çıkar
        
        Args:
            value_str: Sayısal değer içeren string
            
        Returns:
            Optional[float]: Sayısal değer veya None
        """
        try:
            # String mi?
            if not isinstance(value_str, str):
                return float(value_str) if pd.notna(value_str) else None
            
            # Yüzde işaretini kaldır
            value_str = value_str.replace('%', '')
            
            # İlk sayıyı bul
            match = re.search(r'[-+]?\d*\.\d+|[-+]?\d+', value_str)
            if match:
                return float(match.group())
            
            return None
        except Exception:
            return None