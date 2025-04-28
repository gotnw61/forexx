#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için ayarlar yönetim modülü
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import config

logger = logging.getLogger("ForexTradingBot.SettingsManager")

class SettingsManager:
    """
    API ve kullanıcı ayarlarını yönetmek için sınıf.
    Şifreli depolama ve varsayılan ayarları yönetir.
    """
    
    def __init__(self, db_manager=None):
        """
        Ayarlar yöneticisini başlat
        
        Args:
            db_manager: Veritabanı yöneticisi örneği (opsiyonel)
        """
        self.db_manager = db_manager
        self.settings_file = os.path.join(Path(__file__).resolve().parent.parent, "data", "settings.json")
        self.encrypted_file = os.path.join(Path(__file__).resolve().parent.parent, "data", "api_keys.encrypted")
        self.key_file = os.path.join(Path(__file__).resolve().parent.parent, "data", ".key")
        
        # Dosya dizinlerini oluştur
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        
        # Şifreleme anahtarını yükle veya oluştur
        self.crypto_key = self._load_or_create_key()
        self.cipher = Fernet(self.crypto_key)
        
        # Ayarları yükle veya varsayılanları oluştur
        self.settings = self._load_or_create_settings()
        self.api_keys = self._load_encrypted_api_keys()
        
        logger.info("Ayarlar yöneticisi başlatıldı")
    
    def _load_or_create_key(self) -> bytes:
        """
        Şifreleme anahtarını yükle veya yeni bir tane oluştur
        
        Returns:
            bytes: Şifreleme anahtarı
        """
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            # Yeni bir anahtar oluştur
            key = Fernet.generate_key()
            
            # Anahtarı dosyaya kaydet
            with open(self.key_file, "wb") as f:
                f.write(key)
                
            logger.info("Yeni şifreleme anahtarı oluşturuldu")
            return key
    
    def _load_or_create_settings(self) -> Dict[str, Any]:
        """
        Ayarları yükle veya varsayılanları oluştur
        
        Returns:
            Dict[str, Any]: Ayarlar sözlüğü
        """
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                logger.info("Ayarlar başarıyla yüklendi")
                return settings
            except Exception as e:
                logger.error(f"Ayarlar yüklenirken hata oluştu: {e}")
                logger.info("Varsayılan ayarlar oluşturuluyor...")
        
        # Varsayılan ayarları oluştur
        default_settings = self._create_default_settings()
        self.save_settings(default_settings)
        return default_settings
    
    def _create_default_settings(self) -> Dict[str, Any]:
        """
        Varsayılan ayarları oluştur
        
        Returns:
            Dict[str, Any]: Varsayılan ayarlar sözlüğü
        """
        default_settings = {
            "app_name": config.APP_NAME,
            "app_version": config.APP_VERSION,
            "symbols": config.DEFAULT_SYMBOLS,
            "timeframes": list(config.TIMEFRAMES.keys()),
            
            # MetaTrader 5 ayarları
            "mt5": {
                "path": config.MT5_DEFAULT["path"],
                "server": config.MT5_DEFAULT["server"],
                "timeout": config.MT5_DEFAULT["timeout"],
                "enable_real_trading": config.MT5_DEFAULT["enable_real_trading"]
            },
            
            # Analiz ayarları
            "analysis": {
                "indicators": config.DEFAULT_INDICATORS,
                "ict": config.STRATEGY_PARAMS["ict"],
                "smc": config.STRATEGY_PARAMS["smc"],
                "price_action": config.STRATEGY_PARAMS["price_action"]
            },
            
            # Risk yönetimi ayarları
            "risk_management": config.RISK_MANAGEMENT,
            
            # Sinyal ayarları
            "signal": config.SIGNAL_PARAMS,
            
            # Telegram ayarları
            "telegram": {
                "enabled": False,
                "commands": config.TELEGRAM["commands"]
            },
            
            # Otomatik işlem ayarları
            "auto_trade_enabled": False,
            "auto_trade_threshold": 70,
            "confirmation_required": True,
            "confirmation_timeout": 300,
            
            # Tarama ayarları
            "scan_interval": 60,  # saniye
            "news_scanner_enabled": True,
            
            # UI ayarları
            "ui": config.STREAMLIT,
            
            # Genel ayarlar
            "timezone": config.TIMEZONE,
            "log_level": "INFO"
        }
        
        return default_settings
    
    def _load_encrypted_api_keys(self) -> Dict[str, Any]:
        """
        Şifrelenmiş API anahtarlarını yükle
        
        Returns:
            Dict[str, Any]: API anahtarları sözlüğü
        """
        if os.path.exists(self.encrypted_file):
            try:
                with open(self.encrypted_file, "rb") as f:
                    encrypted_data = f.read()
                
                # Şifreyi çöz
                json_str = self.cipher.decrypt(encrypted_data).decode('utf-8')
                api_keys = json.loads(json_str)
                
                logger.info("Şifrelenmiş API anahtarları başarıyla yüklendi")
                return api_keys
            except Exception as e:
                logger.error(f"API anahtarları yüklenirken hata oluştu: {e}")
        
        # Varsayılan boş API anahtarları
        return self._create_default_api_keys()
    
    def _create_default_api_keys(self) -> Dict[str, Any]:
        """
        Varsayılan boş API anahtarları oluştur
        
        Returns:
            Dict[str, Any]: Boş API anahtarları sözlüğü
        """
        default_api_keys = {
            "mt5": {
                "login": None,
                "password": None,
                "server": None
            },
            "telegram": {
                "bot_token": None,
                "api_id": None,
                "api_hash": None,
                "chat_id": None
            },
            "news_sources": {
                "investing_com": {
                    "username": None,
                    "password": None
                },
                "twitter": {
                    "api_key": None,
                    "api_secret": None,
                    "access_token": None,
                    "access_token_secret": None
                }
            }
        }
        
        return default_api_keys
    
    def save_settings(self, settings: Optional[Dict[str, Any]] = None) -> bool:
        """
        Ayarları dosyaya kaydet
        
        Args:
            settings (Dict[str, Any], optional): Kaydedilecek ayarlar. 
                                               Verilmezse mevcut ayarlar kullanılır.
        
        Returns:
            bool: Kayıt başarılıysa True, aksi halde False
        """
        if settings is not None:
            self.settings = settings
            
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            
            logger.info("Ayarlar başarıyla kaydedildi")
            return True
        except Exception as e:
            logger.error(f"Ayarlar kaydedilirken hata oluştu: {e}")
            return False
    
    def save_api_keys(self, api_keys: Optional[Dict[str, Any]] = None) -> bool:
        """
        API anahtarlarını şifreli olarak kaydet
        
        Args:
            api_keys (Dict[str, Any], optional): Kaydedilecek API anahtarları.
                                              Verilmezse mevcut anahtarlar kullanılır.
        
        Returns:
            bool: Kayıt başarılıysa True, aksi halde False
        """
        if api_keys is not None:
            self.api_keys = api_keys
            
        try:
            # JSON'a dönüştür
            json_str = json.dumps(self.api_keys, ensure_ascii=False)
            
            # Veriyi şifrele
            encrypted_data = self.cipher.encrypt(json_str.encode('utf-8'))
            
            # Dosyaya kaydet
            with open(self.encrypted_file, "wb") as f:
                f.write(encrypted_data)
                
            logger.info("API anahtarları şifrelenmiş olarak kaydedildi")
            return True
        except Exception as e:
            logger.error(f"API anahtarları kaydedilirken hata oluştu: {e}")
            return False
    
    def get_setting(self, key: str, default=None) -> Any:
        """
        Belirli bir ayarı al
        
        Args:
            key (str): Ayar anahtarı (nokta notasyonu desteklenir, örn: "mt5.server")
            default: Ayar bulunamazsa dönecek varsayılan değer
            
        Returns:
            Any: Ayar değeri veya varsayılan değer
        """
        keys = key.split(".")
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        Belirli bir ayarı ayarla
        
        Args:
            key (str): Ayar anahtarı (nokta notasyonu desteklenir, örn: "mt5.server")
            value (Any): Ayarlanacak değer
            
        Returns:
            bool: İşlem başarılıysa True, aksi halde False
        """
        keys = key.split(".")
        target = self.settings
        
        # Son anahtara kadar git
        for i, k in enumerate(keys[:-1]):
            if k not in target:
                target[k] = {}
            target = target[k]
        
        # Son anahtarı ayarla
        target[keys[-1]] = value
        
        # Ayarları kaydet
        return self.save_settings()
    
    def get_api_key(self, key: str, default=None) -> Any:
        """
        Belirli bir API anahtarını al
        
        Args:
            key (str): API anahtarı (nokta notasyonu desteklenir, örn: "telegram.bot_token")
            default: Anahtar bulunamazsa dönecek varsayılan değer
            
        Returns:
            Any: API anahtarı değeri veya varsayılan değer
        """
        keys = key.split(".")
        value = self.api_keys
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set_api_key(self, key: str, value: Any) -> bool:
        """
        Belirli bir API anahtarını ayarla
        
        Args:
            key (str): API anahtarı (nokta notasyonu desteklenir, örn: "telegram.bot_token")
            value (Any): Ayarlanacak değer
            
        Returns:
            bool: İşlem başarılıysa True, aksi halde False
        """
        keys = key.split(".")
        target = self.api_keys
        
        # Son anahtara kadar git
        for i, k in enumerate(keys[:-1]):
            if k not in target:
                target[k] = {}
            target = target[k]
        
        # Son anahtarı ayarla
        target[keys[-1]] = value
        
        # API anahtarlarını kaydet
        return self.save_api_keys()
    
    def reset_settings(self) -> bool:
        """
        Tüm ayarları varsayılanlara sıfırla
        
        Returns:
            bool: İşlem başarılıysa True, aksi halde False
        """
        self.settings = self._create_default_settings()
        return self.save_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Tüm ayarları yükleyip döndür
        
        Returns:
            Dict[str, Any]: Ayarlar sözlüğü
        """
        self.settings = self._load_or_create_settings()
        self.api_keys = self._load_encrypted_api_keys()
        
        # Ayarları ve API anahtarlarını birleştir
        combined_settings = self.settings.copy()
        
        # API anahtarlarını şifreli olarak ekle
        if self.api_keys.get("mt5", {}).get("login"):
            combined_settings["mt5"]["credentials_saved"] = True
        else:
            combined_settings["mt5"]["credentials_saved"] = False
            
        if self.api_keys.get("telegram", {}).get("bot_token"):
            combined_settings["telegram"]["credentials_saved"] = True
        else:
            combined_settings["telegram"]["credentials_saved"] = False
            
        # Diğer ayarları ekle
        
        return combined_settings
    
    def validate_connection_settings(self) -> Dict[str, bool]:
        """
        Bağlantı ayarlarını doğrula
        
        Returns:
            Dict[str, bool]: Her bağlantı için doğrulama sonuçları
        """
        results = {
            "mt5": False,
            "telegram": False,
            "database": False
        }
        
        # MT5 bağlantısını doğrula
        mt5_creds = self.api_keys.get("mt5", {})
        if mt5_creds.get("login") and mt5_creds.get("password") and mt5_creds.get("server"):
            results["mt5"] = True
        
        # Telegram bağlantısını doğrula
        telegram_creds = self.api_keys.get("telegram", {})
        if telegram_creds.get("bot_token") and telegram_creds.get("chat_id"):
            results["telegram"] = True
        
        # Veritabanı bağlantısını doğrula
        if self.db_manager and self.db_manager.test_connection():
            results["database"] = True
        
        return results

    def export_settings(self, file_path: str) -> bool:
        """
        Ayarları dışa aktar (API anahtarları hariç)
        
        Args:
            file_path (str): Dışa aktarılacak dosya yolu
            
        Returns:
            bool: İşlem başarılıysa True, aksi halde False
        """
        try:
            # API anahtarlarını içermeyen ayarları kopyala
            export_settings = self.settings.copy()
            
            # Hassas bilgileri temizle
            if "mt5" in export_settings:
                if "login" in export_settings["mt5"]:
                    del export_settings["mt5"]["login"]
                if "password" in export_settings["mt5"]:
                    del export_settings["mt5"]["password"]
            
            # Dosyaya kaydet
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_settings, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Ayarlar başarıyla dışa aktarıldı: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Ayarlar dışa aktarılırken hata oluştu: {e}")
            return False
    
    def import_settings(self, file_path: str) -> bool:
        """
        Ayarları içe aktar
        
        Args:
            file_path (str): İçe aktarılacak dosya yolu
            
        Returns:
            bool: İşlem başarılıysa True, aksi halde False
        """
        try:
            # Dosyadan ayarları oku
            with open(file_path, "r", encoding="utf-8") as f:
                imported_settings = json.load(f)
            
            # Mevcut API anahtarlarını koru
            if "mt5" in imported_settings and "mt5" in self.settings:
                if "login" in self.settings["mt5"]:
                    imported_settings["mt5"]["login"] = self.settings["mt5"]["login"]
                if "password" in self.settings["mt5"]:
                    imported_settings["mt5"]["password"] = self.settings["mt5"]["password"]
            
            # Ayarları güncelle ve kaydet
            self.settings = imported_settings
            self.save_settings()
            
            logger.info(f"Ayarlar başarıyla içe aktarıldı: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Ayarlar içe aktarılırken hata oluştu: {e}")
            return False