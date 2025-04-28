#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için veritabanı yönetim modülü.
İşlem geçmişi, sinyaller ve ayarları depolar.
"""
import os
import logging
import sqlite3
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

logger = logging.getLogger("ForexTradingBot.DatabaseManager")

class DatabaseManager:
    """
    Veritabanı işlemlerini yönetmek için sınıf.
    SQLite veritabanı kullanarak veri depolama ve sorgulama.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Veritabanı yöneticisini başlat
        
        Args:
            db_path: Veritabanı dosya yolu (opsiyonel)
        """
        if db_path is None:
            # Varsayılan veritabanı yolu
            self.db_path = os.path.join(Path(__file__).resolve().parent.parent.parent, "data", "trading_bot.db")
        else:
            self.db_path = db_path
            
        # Veritabanı klasörünü oluştur
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Veritabanını oluştur/bağlan ve tabloları kontrol et
        self.connection = None
        self._init_database()
        
        logger.info(f"Veritabanı yöneticisi başlatıldı: {self.db_path}")
    
    def _init_database(self):
        """
        Veritabanı bağlantısını oluştur ve tabloları kontrol et
        """
        try:
            self.connection = sqlite3.connect(self.db_path)
            
            # Tabloları oluştur
            self._create_tables()
            logger.info("Veritabanı tabloları oluşturuldu/kontrol edildi")
        except sqlite3.Error as e:
            logger.error(f"Veritabanı başlatma hatası: {e}")
            if self.connection:
                self.connection.close()
            self.connection = None
    
    def _create_tables(self):
        """
        Gerekli tabloları oluştur
        """
        if not self.connection:
            return
            
        cursor = self.connection.cursor()
        
        # Sinyaller tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            timestamp DATETIME NOT NULL,
            probability REAL,
            risk_reward REAL,
            status TEXT DEFAULT 'pending',
            executed INTEGER DEFAULT 0,
            result TEXT,
            profit_loss REAL,
            notes TEXT,
            metadata TEXT
        )
        ''')
        
        # İşlemler tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket INTEGER,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            volume REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            open_time DATETIME NOT NULL,
            close_time DATETIME,
            status TEXT DEFAULT 'open',
            profit_loss REAL,
            commission REAL,
            swap REAL,
            signal_id INTEGER,
            notes TEXT,
            FOREIGN KEY (signal_id) REFERENCES signals (id)
        )
        ''')
        
        # Performans tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE NOT NULL,
            trades_count INTEGER DEFAULT 0,
            win_count INTEGER DEFAULT 0,
            loss_count INTEGER DEFAULT 0,
            profit_loss REAL DEFAULT 0,
            win_rate REAL DEFAULT 0,
            average_win REAL DEFAULT 0,
            average_loss REAL DEFAULT 0,
            largest_win REAL DEFAULT 0,
            largest_loss REAL DEFAULT 0,
            metadata TEXT
        )
        ''')
        
        # Model performans tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            model_name TEXT NOT NULL,
            train_date DATETIME NOT NULL,
            accuracy REAL,
            precision REAL,
            recall REAL,
            f1_score REAL,
            mse REAL,
            mae REAL,
            metadata TEXT,
            UNIQUE(symbol, model_name, train_date)
        )
        ''')
        
        # Loglar tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            source TEXT,
            metadata TEXT
        )
        ''')
        
        # Telegram mesajları tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS telegram_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            chat_id INTEGER NOT NULL,
            user_id INTEGER,
            username TEXT,
            message_text TEXT,
            timestamp DATETIME NOT NULL,
            is_command INTEGER DEFAULT 0,
            command TEXT,
            responded INTEGER DEFAULT 0,
            response_text TEXT,
            metadata TEXT
        )
        ''')
        
        self.connection.commit()
    
    def test_connection(self) -> bool:
        """
        Veritabanı bağlantısını test et
        
        Returns:
            bool: Bağlantı durumu
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if self.connection:
                cursor = self.connection.cursor()
                cursor.execute("SELECT SQLITE_VERSION()")
                version = cursor.fetchone()
                logger.info(f"SQLite veritabanı sürümü: {version[0]}")
                return True
            else:
                return False
        except sqlite3.Error as e:
            logger.error(f"Veritabanı bağlantı testi hatası: {e}")
            return False
    
    def add_signal(self, signal_data: Dict) -> int:
        """
        Yeni bir sinyal ekle
        
        Args:
            signal_data: Sinyal verileri
            
        Returns:
            int: Eklenen sinyal ID'si veya -1 (hata durumunda)
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return -1
                
            cursor = self.connection.cursor()
            
            # Metadata alanını JSON'a dönüştür
            if "metadata" in signal_data and isinstance(signal_data["metadata"], dict):
                signal_data["metadata"] = json.dumps(signal_data["metadata"])
                
            # Timestamp kontrolü
            if "timestamp" not in signal_data:
                signal_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            # Sütun adlarını ve değerleri hazırla
            columns = ', '.join(signal_data.keys())
            placeholders = ', '.join(['?' for _ in signal_data])
            values = tuple(signal_data.values())
            
            # SQL sorgusunu oluştur ve çalıştır
            query = f"INSERT INTO signals ({columns}) VALUES ({placeholders})"
            cursor.execute(query, values)
            self.connection.commit()
            
            # Eklenen kaydın ID'sini döndür
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Sinyal ekleme hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return -1
    
    def update_signal(self, signal_id: int, data: Dict) -> bool:
        """
        Mevcut bir sinyali güncelle
        
        Args:
            signal_id: Güncellenecek sinyal ID'si
            data: Güncellenecek veriler
            
        Returns:
            bool: Güncelleme başarılıysa True, aksi halde False
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return False
                
            cursor = self.connection.cursor()
            
            # Metadata alanını JSON'a dönüştür
            if "metadata" in data and isinstance(data["metadata"], dict):
                data["metadata"] = json.dumps(data["metadata"])
                
            # Update sorgusu oluştur
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            values = list(data.values())
            values.append(signal_id)  # WHERE için ID
            
            # SQL sorgusunu oluştur ve çalıştır
            query = f"UPDATE signals SET {set_clause} WHERE id = ?"
            cursor.execute(query, values)
            self.connection.commit()
            
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Sinyal güncelleme hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_signal(self, signal_id: int) -> Optional[Dict]:
        """
        Belirli bir sinyali getir
        
        Args:
            signal_id: Sinyal ID'si
            
        Returns:
            Optional[Dict]: Sinyal verileri sözlüğü veya None
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return None
                
            cursor = self.connection.cursor()
            
            # SQL sorgusunu çalıştır
            cursor.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
            row = cursor.fetchone()
            
            if row:
                # Sütun adlarını al
                columns = [description[0] for description in cursor.description]
                
                # Satırı sözlüğe dönüştür
                signal = dict(zip(columns, row))
                
                # Metadata alanını JSON'dan çöz
                if "metadata" in signal and signal["metadata"]:
                    try:
                        signal["metadata"] = json.loads(signal["metadata"])
                    except json.JSONDecodeError:
                        pass
                
                return signal
            else:
                return None
        except sqlite3.Error as e:
            logger.error(f"Sinyal getirme hatası: {e}")
            return None
    
    def get_signals(self, filters: Optional[Dict] = None, limit: int = 100) -> List[Dict]:
        """
        Filtrelere göre sinyalleri getir
        
        Args:
            filters: Filtre kriterleri (opsiyonel)
            limit: Maksimum kayıt sayısı
            
        Returns:
            List[Dict]: Sinyal verileri listesi
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return []
                
            cursor = self.connection.cursor()
            
            # SQL sorgusunu oluştur
            query = "SELECT * FROM signals"
            values = []
            
            # Filtreler varsa WHERE koşulunu ekle
            if filters:
                where_clauses = []
                for key, value in filters.items():
                    where_clauses.append(f"{key} = ?")
                    values.append(value)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
            
            # Sıralama ve limit ekle
            query += " ORDER BY timestamp DESC LIMIT ?"
            values.append(limit)
            
            # SQL sorgusunu çalıştır
            cursor.execute(query, values)
            rows = cursor.fetchall()
            
            # Sonuçları listede topla
            result = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                # Satırı sözlüğe dönüştür
                signal = dict(zip(columns, row))
                
                # Metadata alanını JSON'dan çöz
                if "metadata" in signal and signal["metadata"]:
                    try:
                        signal["metadata"] = json.loads(signal["metadata"])
                    except json.JSONDecodeError:
                        pass
                
                result.append(signal)
            
            return result
        except sqlite3.Error as e:
            logger.error(f"Sinyal listesi getirme hatası: {e}")
            return []
    
    def add_trade(self, trade_data: Dict) -> int:
        """
        Yeni bir işlem ekle
        
        Args:
            trade_data: İşlem verileri
            
        Returns:
            int: Eklenen işlem ID'si veya -1 (hata durumunda)
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return -1
                
            cursor = self.connection.cursor()
            
            # Open time kontrolü
            if "open_time" not in trade_data:
                trade_data["open_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            # Sütun adlarını ve değerleri hazırla
            columns = ', '.join(trade_data.keys())
            placeholders = ', '.join(['?' for _ in trade_data])
            values = tuple(trade_data.values())
            
            # SQL sorgusunu oluştur ve çalıştır
            query = f"INSERT INTO trades ({columns}) VALUES ({placeholders})"
            cursor.execute(query, values)
            self.connection.commit()
            
            # Eklenen kaydın ID'sini döndür
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"İşlem ekleme hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return -1
    
    def update_trade(self, trade_id: int, data: Dict) -> bool:
        """
        Mevcut bir işlemi güncelle
        
        Args:
            trade_id: Güncellenecek işlem ID'si
            data: Güncellenecek veriler
            
        Returns:
            bool: Güncelleme başarılıysa True, aksi halde False
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return False
                
            cursor = self.connection.cursor()
            
            # Update sorgusu oluştur
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            values = list(data.values())
            values.append(trade_id)  # WHERE için ID
            
            # SQL sorgusunu oluştur ve çalıştır
            query = f"UPDATE trades SET {set_clause} WHERE id = ?"
            cursor.execute(query, values)
            self.connection.commit()
            
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"İşlem güncelleme hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_trade(self, trade_id: int) -> Optional[Dict]:
        """
        Belirli bir işlemi getir
        
        Args:
            trade_id: İşlem ID'si
            
        Returns:
            Optional[Dict]: İşlem verileri sözlüğü veya None
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return None
                
            cursor = self.connection.cursor()
            
            # SQL sorgusunu çalıştır
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            
            if row:
                # Sütun adlarını al
                columns = [description[0] for description in cursor.description]
                
                # Satırı sözlüğe dönüştür
                return dict(zip(columns, row))
            else:
                return None
        except sqlite3.Error as e:
            logger.error(f"İşlem getirme hatası: {e}")
            return None
    
    def get_trades(self, filters: Optional[Dict] = None, limit: int = 100) -> List[Dict]:
        """
        Filtrelere göre işlemleri getir
        
        Args:
            filters: Filtre kriterleri (opsiyonel)
            limit: Maksimum kayıt sayısı
            
        Returns:
            List[Dict]: İşlem verileri listesi
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return []
                
            cursor = self.connection.cursor()
            
            # SQL sorgusunu oluştur
            query = "SELECT * FROM trades"
            values = []
            
            # Filtreler varsa WHERE koşulunu ekle
            if filters:
                where_clauses = []
                for key, value in filters.items():
                    where_clauses.append(f"{key} = ?")
                    values.append(value)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
            
            # Sıralama ve limit ekle
            query += " ORDER BY open_time DESC LIMIT ?"
            values.append(limit)
            
            # SQL sorgusunu çalıştır
            cursor.execute(query, values)
            rows = cursor.fetchall()
            
            # Sonuçları listede topla
            result = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                # Satırı sözlüğe dönüştür
                result.append(dict(zip(columns, row)))
            
            return result
        except sqlite3.Error as e:
            logger.error(f"İşlem listesi getirme hatası: {e}")
            return []
    
    def update_performance(self, date: str, data: Dict) -> bool:
        """
        Performans verilerini güncelle
        
        Args:
            date: Tarih (YYYY-MM-DD formatında)
            data: Güncellenecek veriler
            
        Returns:
            bool: Güncelleme başarılıysa True, aksi halde False
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return False
                
            cursor = self.connection.cursor()
            
            # Metadata alanını JSON'a dönüştür
            if "metadata" in data and isinstance(data["metadata"], dict):
                data["metadata"] = json.dumps(data["metadata"])
                
            # Tarih için kayıt var mı kontrol et
            cursor.execute("SELECT id FROM performance WHERE date = ?", (date,))
            existing = cursor.fetchone()
            
            if existing:
                # Güncelleme yap
                set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
                values = list(data.values())
                values.append(date)  # WHERE için tarih
                
                query = f"UPDATE performance SET {set_clause} WHERE date = ?"
                cursor.execute(query, values)
            else:
                # Yeni kayıt ekle
                data["date"] = date
                
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                values = tuple(data.values())
                
                query = f"INSERT INTO performance ({columns}) VALUES ({placeholders})"
                cursor.execute(query, values)
                
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Performans güncelleme hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_performance(self, start_date: Optional[str] = None, 
                       end_date: Optional[str] = None) -> List[Dict]:
        """
        Belirli bir tarih aralığı için performans verilerini getir
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında)
            
        Returns:
            List[Dict]: Performans verileri listesi
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return []
                
            cursor = self.connection.cursor()
            
            # SQL sorgusunu oluştur
            query = "SELECT * FROM performance"
            values = []
            
            # Tarih filtresi varsa WHERE koşulunu ekle
            if start_date or end_date:
                where_clauses = []
                
                if start_date:
                    where_clauses.append("date >= ?")
                    values.append(start_date)
                
                if end_date:
                    where_clauses.append("date <= ?")
                    values.append(end_date)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
            
            # Sıralama ekle
            query += " ORDER BY date ASC"
            
            # SQL sorgusunu çalıştır
            cursor.execute(query, values)
            rows = cursor.fetchall()
            
            # Sonuçları listede topla
            result = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                # Satırı sözlüğe dönüştür
                perf = dict(zip(columns, row))
                
                # Metadata alanını JSON'dan çöz
                if "metadata" in perf and perf["metadata"]:
                    try:
                        perf["metadata"] = json.loads(perf["metadata"])
                    except json.JSONDecodeError:
                        pass
                
                result.append(perf)
            
            return result
        except sqlite3.Error as e:
            logger.error(f"Performans verileri getirme hatası: {e}")
            return []
    
    def add_log(self, level: str, message: str, source: Optional[str] = None, 
               metadata: Optional[Dict] = None) -> int:
        """
        Yeni bir log kaydı ekle
        
        Args:
            level: Log seviyesi
            message: Log mesajı
            source: Log kaynağı (opsiyonel)
            metadata: Ek bilgiler (opsiyonel)
            
        Returns:
            int: Eklenen log ID'si veya -1 (hata durumunda)
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return -1
                
            cursor = self.connection.cursor()
            
            # Log verilerini hazırla
            log_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": level,
                "message": message
            }
            
            if source:
                log_data["source"] = source
                
            if metadata:
                log_data["metadata"] = json.dumps(metadata)
                
            # Sütun adlarını ve değerleri hazırla
            columns = ', '.join(log_data.keys())
            placeholders = ', '.join(['?' for _ in log_data])
            values = tuple(log_data.values())
            
            # SQL sorgusunu oluştur ve çalıştır
            query = f"INSERT INTO logs ({columns}) VALUES ({placeholders})"
            cursor.execute(query, values)
            self.connection.commit()
            
            # Eklenen kaydın ID'sini döndür
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Log ekleme hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return -1
    
    def get_logs(self, level: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Logları getir
        
        Args:
            level: Log seviyesi filtresi (opsiyonel)
            limit: Maksimum kayıt sayısı
            
        Returns:
            List[Dict]: Log kayıtları listesi
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return []
                
            cursor = self.connection.cursor()
            
            # SQL sorgusunu oluştur
            query = "SELECT * FROM logs"
            values = []
            
            # Seviye filtresi varsa WHERE koşulunu ekle
            if level:
                query += " WHERE level = ?"
                values.append(level)
            
            # Sıralama ve limit ekle
            query += " ORDER BY timestamp DESC LIMIT ?"
            values.append(limit)
            
            # SQL sorgusunu çalıştır
            cursor.execute(query, values)
            rows = cursor.fetchall()
            
            # Sonuçları listede topla
            result = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                # Satırı sözlüğe dönüştür
                log = dict(zip(columns, row))
                
                # Metadata alanını JSON'dan çöz
                if "metadata" in log and log["metadata"]:
                    try:
                        log["metadata"] = json.loads(log["metadata"])
                    except json.JSONDecodeError:
                        pass
                
                result.append(log)
            
            return result
        except sqlite3.Error as e:
            logger.error(f"Log kayıtları getirme hatası: {e}")
            return []
    
    def add_telegram_message(self, message_data: Dict) -> int:
        """
        Yeni bir Telegram mesajı ekle
        
        Args:
            message_data: Mesaj verileri
            
        Returns:
            int: Eklenen mesaj ID'si veya -1 (hata durumunda)
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return -1
                
            cursor = self.connection.cursor()
            
            # Timestamp kontrolü
            if "timestamp" not in message_data:
                message_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            # Metadata alanını JSON'a dönüştür
            if "metadata" in message_data and isinstance(message_data["metadata"], dict):
                message_data["metadata"] = json.dumps(message_data["metadata"])
                
            # Sütun adlarını ve değerleri hazırla
            columns = ', '.join(message_data.keys())
            placeholders = ', '.join(['?' for _ in message_data])
            values = tuple(message_data.values())
            
            # SQL sorgusunu oluştur ve çalıştır
            query = f"INSERT INTO telegram_messages ({columns}) VALUES ({placeholders})"
            cursor.execute(query, values)
            self.connection.commit()
            
            # Eklenen kaydın ID'sini döndür
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Telegram mesajı ekleme hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return -1
    
    def update_telegram_message(self, message_id: int, data: Dict) -> bool:
        """
        Mevcut bir Telegram mesajını güncelle
        
        Args:
            message_id: Güncellenecek mesaj ID'si
            data: Güncellenecek veriler
            
        Returns:
            bool: Güncelleme başarılıysa True, aksi halde False
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return False
                
            cursor = self.connection.cursor()
            
            # Metadata alanını JSON'a dönüştür
            if "metadata" in data and isinstance(data["metadata"], dict):
                data["metadata"] = json.dumps(data["metadata"])
                
            # Update sorgusu oluştur
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            values = list(data.values())
            values.append(message_id)  # WHERE için ID
            
            # SQL sorgusunu oluştur ve çalıştır
            query = f"UPDATE telegram_messages SET {set_clause} WHERE id = ?"
            cursor.execute(query, values)
            self.connection.commit()
            
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Telegram mesajı güncelleme hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_telegram_messages(self, chat_id: Optional[int] = None, 
                             limit: int = 100) -> List[Dict]:
        """
        Telegram mesajlarını getir
        
        Args:
            chat_id: Sohbet ID'si filtresi (opsiyonel)
            limit: Maksimum kayıt sayısı
            
        Returns:
            List[Dict]: Telegram mesajları listesi
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return []
                
            cursor = self.connection.cursor()
            
            # SQL sorgusunu oluştur
            query = "SELECT * FROM telegram_messages"
            values = []
            
            # Chat ID filtresi varsa WHERE koşulunu ekle
            if chat_id is not None:
                query += " WHERE chat_id = ?"
                values.append(chat_id)
            
            # Sıralama ve limit ekle
            query += " ORDER BY timestamp DESC LIMIT ?"
            values.append(limit)
            
            # SQL sorgusunu çalıştır
            cursor.execute(query, values)
            rows = cursor.fetchall()
            
            # Sonuçları listede topla
            result = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                # Satırı sözlüğe dönüştür
                message = dict(zip(columns, row))
                
                # Metadata alanını JSON'dan çöz
                if "metadata" in message and message["metadata"]:
                    try:
                        message["metadata"] = json.loads(message["metadata"])
                    except json.JSONDecodeError:
                        pass
                
                result.append(message)
            
            return result
        except sqlite3.Error as e:
            logger.error(f"Telegram mesajları getirme hatası: {e}")
            return []
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Optional[List[tuple]]:
        """
        Özel SQL sorgusu çalıştır
        
        Args:
            query: SQL sorgusu
            params: Sorgu parametreleri (opsiyonel)
            
        Returns:
            Optional[List[tuple]]: Sorgu sonuçları veya None (hata durumunda)
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return None
                
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            # DML sorgusu ise commit et
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                self.connection.commit()
                return None
            
            # SELECT sorgusu ise sonuçları döndür
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"SQL sorgusu çalıştırma hatası: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    def get_data_as_dataframe(self, table: str, filters: Optional[Dict] = None, 
                             limit: Optional[int] = None) -> pd.DataFrame:
        """
        Veritabanı tablosunu pandas DataFrame'e dönüştür
        
        Args:
            table: Tablo adı
            filters: Filtre kriterleri (opsiyonel)
            limit: Maksimum kayıt sayısı (opsiyonel)
            
        Returns:
            pd.DataFrame: Tablo verileri DataFrame'i
        """
        try:
            if self.connection is None:
                self._init_database()
                
            if not self.connection:
                logger.error("Veritabanı bağlantısı yok")
                return pd.DataFrame()
                
            # SQL sorgusunu oluştur
            query = f"SELECT * FROM {table}"
            params = []
            
            # Filtreler varsa WHERE koşulunu ekle
            if filters:
                where_clauses = []
                for key, value in filters.items():
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
            
            # Limit ekle
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            # Pandas ile sorguyu çalıştır
            return pd.read_sql_query(query, self.connection, params=tuple(params))
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"DataFrame dönüştürme hatası: {e}")
            return pd.DataFrame()
    
    def close(self):
        """
        Veritabanı bağlantısını kapat
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Veritabanı bağlantısı kapatıldı")
    
    def __del__(self):
        """
        Yıkıcı metod, nesne silindiğinde bağlantıyı kapat
        """
        self.close()