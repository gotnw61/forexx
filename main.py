#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gelişmiş Forex Trading Bot Ana Uygulama Dosyası
"""
import os
import sys
import logging
import time
import threading
from pathlib import Path

# Proje kök dizinini ekleyelim
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

# Modülleri içe aktarma
from core.settings_manager import SettingsManager
from core.data_manager import DataManager
from core.broker_connector import BrokerConnector
from core.database_manager import DatabaseManager
from analysis.analysis_engine import AnalysisEngine
from prediction.ai_predictor import AIPredictor
from trading.signal_generator import SignalGenerator
from trading.risk_manager import RiskManager
from communication.telegram_bot import TelegramBot
from ui.streamlit_app import run_streamlit_app
import config

# Loglama yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(ROOT_DIR, "logs", "trading_bot.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ForexTradingBot")

class ForexTradingBot:
    """
    Ana Trading Bot sınıfı - tüm bileşenleri yönetir
    """
    def __init__(self):
        """Bileşenlerin başlatılması ve bağlanması"""
        logger.info("Forex Trading Bot başlatılıyor...")
        
        # Veritabanı bağlantısını oluştur
        self.db_manager = DatabaseManager()
        
        # Ayarları yükle
        self.settings_manager = SettingsManager(self.db_manager)
        self.settings = self.settings_manager.settings  # Doğrudan settings'ı kullan
        
        # MT5 bağlantısını kur
        self.broker = BrokerConnector(self.settings_manager)
        
        # Veri yöneticisini oluştur
        self.data_manager = DataManager(self.broker, self.settings)
        
        # Analiz motoru
        self.analysis_engine = AnalysisEngine(self.data_manager)
        
        # AI tahmin modülü
        self.ai_predictor = AIPredictor(self.data_manager, self.settings)
        
        # Sinyal oluşturucusu
        self.signal_generator = SignalGenerator(
            self.analysis_engine, 
            self.ai_predictor,
            self.settings
        )
        
        # Risk yöneticisi
        self.risk_manager = RiskManager(self.broker, self.settings)
        
        # Telegram botu
        self.telegram_bot = TelegramBot(
            self.settings_manager, 
            self.signal_generator, 
            self.risk_manager,
            self.broker
        )
        
        # İşlem durumu
        self.is_running = False
        
        logger.info("Forex Trading Bot başlatıldı.")
    
    def start(self):
        """
        Trading bot'u başlat
        """
        if self.is_running:
            logger.warning("Bot zaten çalışıyor!")
            return
            
        logger.info("Trading Bot başlatılıyor...")
        
        # MT5 bağlantısını kontrol et
        if not self.broker.connect():
            logger.error("MT5 bağlantısı kurulamadı. Bot başlatılamıyor.")
            return False
            
        # Telegram botunu başlat
        self.telegram_bot.start()
        
        # AI modelini yükle
        self.ai_predictor.load_model()
        
        # Ana işlem döngüsünü başlat
        self.is_running = True
        self.trading_thread = threading.Thread(target=self._trading_loop)
        self.trading_thread.daemon = True
        self.trading_thread.start()
        
        logger.info("Trading Bot başlatıldı.")
        return True
        
    def stop(self):
        """
        Trading bot'u durdur
        """
        if not self.is_running:
            logger.warning("Bot zaten durmuş durumda!")
            return
            
        logger.info("Trading Bot durduruluyor...")
        self.is_running = False
        
        # Telegram botunu durdur
        self.telegram_bot.stop()
        
        # MT5 bağlantısını kapat
        self.broker.disconnect()
        
        # Trading thread'in durmasını bekle
        if hasattr(self, 'trading_thread') and self.trading_thread.is_alive():
            self.trading_thread.join(timeout=5.0)
            
        logger.info("Trading Bot durduruldu.")
        
    def _trading_loop(self):
        """
        Ana işlem döngüsü
        """
        logger.info("İşlem döngüsü başlatıldı.")
        
        while self.is_running:
            try:
                # Piyasa verilerini güncelle
                self.data_manager.update_market_data()
                
                # Semboller üzerinde döngü
                for symbol in self.settings.get("symbols", ["EURUSD", "XAUUSD"]):
                    # Analiz yap
                    analysis_results = self.analysis_engine.analyze(symbol)
                    
                    # AI tahmini
                    prediction = self.ai_predictor.predict(symbol)
                    
                    # Sinyal oluştur
                    signal = self.signal_generator.generate_signal(
                        symbol, 
                        analysis_results, 
                        prediction
                    )
                    
                    # Sinyal varsa işle
                    if signal:
                        logger.info(f"Sinyal oluşturuldu: {signal}")
                        
                        # Risk yönetimi
                        risk_params = self.risk_manager.calculate_risk_params(signal)
                        
                        # Sinyal başarı oranı kontrol
                        if signal.success_probability >= self.settings.get("auto_trade_threshold", 70):
                            if self.settings.get("auto_trade_enabled", False):
                                # Otomatik işlem modu açıksa Telegram onayı gönder
                                self.telegram_bot.send_signal_confirmation(signal, risk_params)
                            else:
                                # Sadece bilgilendirme gönder
                                self.telegram_bot.send_signal_info(signal, risk_params)
            
                # Belirli aralıklarla çalıştır
                time.sleep(self.settings.get("scan_interval", 60))
                
            except Exception as e:
                logger.error(f"İşlem döngüsünde hata: {e}", exc_info=True)
                time.sleep(30)  # Hata durumunda biraz bekle
        
        logger.info("İşlem döngüsü durduruldu.")

def main():
    """
    Ana fonksiyon - uygulamayı başlatır
    """
    # Ana dizinleri oluştur
    os.makedirs(os.path.join(ROOT_DIR, "logs"), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, "models"), exist_ok=True)
    
    # Bot örneği oluştur
    bot = ForexTradingBot()
    
    # Streamlit'i ana thread'de başlat
    try:
        # Streamlit UI'ı ana thread'de çalıştır
        run_streamlit_app(bot)
        
        # Bot'u başlat
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu.")
        bot.stop()
    except Exception as e:
        logger.error(f"Beklenmeyen hata: {e}", exc_info=True)
        bot.stop()

if __name__ == "__main__":
    main()