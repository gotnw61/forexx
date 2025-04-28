#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için AI tahmin motoru.
PyTorch tabanlı LSTM modeli ile fiyat tahmini yapar.
"""
import os
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import pickle
from pathlib import Path

# LSTM model sınıfını içe aktar
from prediction.lstm_model import LSTMModel

logger = logging.getLogger("ForexTradingBot.AIPredictor")

class AIPredictor:
    """
    AI tabanlı fiyat tahmini yapan sınıf.
    """
    
    def __init__(self, data_manager, settings):
        """
        AI tahmin modülünü başlat
        
        Args:
            data_manager: Veri yöneticisi
            settings: Uygulama ayarları
        """
        self.data_manager = data_manager
        self.settings = settings
        
        # Proje kök dizini
        self.model_dir = os.path.join(Path(__file__).resolve().parent.parent.parent, "models")
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Model parametreleri
        self.input_size = 20  # Giriş özellik sayısı
        self.hidden_size = 50  # Gizli katman boyutu
        self.num_layers = 2   # LSTM katman sayısı
        self.output_size = 1  # Çıkış boyutu (tahmin edilen değer)
        self.sequence_length = 60  # Tahmin için kullanılacak geçmiş veri uzunluğu
        
        # Cihaz seçimi (GPU varsa)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Model ve scaler nesneleri
        self.models = {}  # Sembol:Timeframe -> Model maplemesi
        self.scalers = {}  # Sembol:Timeframe -> Scaler maplemesi
        
        logger.info(f"AI tahmin modülü başlatıldı (Cihaz: {self.device})")
    
    def load_model(self, symbol: Optional[str] = None, 
                 timeframe: Optional[str] = "H1") -> bool:
        """
        Belirli bir sembol ve zaman dilimi için tahmin modelini yükle
        
        Args:
            symbol: İşlem sembolü (None ise tüm semboller)
            timeframe: Zaman dilimi
            
        Returns:
            bool: Yükleme başarılıysa True, aksi halde False
        """
        try:
            # Yüklenecek sembolleri belirle
            if symbol is None:
                symbols = self.settings.get("symbols", ["EURUSD", "GBPUSD", "XAUUSD"])
            else:
                symbols = [symbol]
            
            success = True
            
            for sym in symbols:
                # Model dosya yolunu oluştur
                model_key = f"{sym}_{timeframe}"
                model_path = os.path.join(self.model_dir, f"{model_key}_model.pth")
                scaler_path = os.path.join(self.model_dir, f"{model_key}_scaler.pkl")
                
                # Model dosyası var mı kontrol et
                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    # LSTM modeli oluştur
                    model = LSTMModel(
                        input_size=self.input_size,
                        hidden_size=self.hidden_size,
                        num_layers=self.num_layers,
                        output_size=self.output_size
                    )
                    
                    # Model parametrelerini yükle
                    model.load_state_dict(torch.load(model_path, map_location=self.device))
                    model.to(self.device)
                    model.eval()  # Değerlendirme modu
                    
                    # Scaler'ı yükle
                    with open(scaler_path, 'rb') as f:
                        scaler = pickle.load(f)
                    
                    # Model ve scaler'ı sakla
                    self.models[model_key] = model
                    self.scalers[model_key] = scaler
                    
                    logger.info(f"{model_key} için model başarıyla yüklendi")
                else:
                    # Model dosyası yoksa eğit
                    logger.info(f"{model_key} için model bulunamadı, eğitim başlatılıyor...")
                    model_success = self.train_model(sym, timeframe)
                    success = success and model_success
            
            return success
            
        except Exception as e:
            logger.error(f"Model yükleme hatası: {e}", exc_info=True)
            return False
    
    def train_model(self, symbol: str, timeframe: str) -> bool:
        """
        Belirli bir sembol ve zaman dilimi için tahmin modelini eğit
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            
        Returns:
            bool: Eğitim başarılıysa True, aksi halde False
        """
        try:
            logger.info(f"{symbol}_{timeframe} için model eğitimi başlatılıyor...")
            
            # Veriyi hazırla
            X, y, df, scaler = self._prepare_training_data(symbol, timeframe)
            
            if X.shape[0] == 0 or y.shape[0] == 0:
                logger.error(f"{symbol}_{timeframe} için eğitim verisi hazırlanamadı")
                return False
            
            # Eğitim ve test setlerine böl
            train_size = int(len(X) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            
            # Torch Tensor'larına dönüştür
            X_train = torch.FloatTensor(X_train).to(self.device)
            y_train = torch.FloatTensor(y_train).to(self.device)
            X_test = torch.FloatTensor(X_test).to(self.device)
            y_test = torch.FloatTensor(y_test).to(self.device)
            
            # TensorDataset ve DataLoader oluştur
            train_dataset = TensorDataset(X_train, y_train)
            test_dataset = TensorDataset(X_test, y_test)
            
            batch_size = 32
            train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
            test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
            
            # LSTM modeli oluştur
            model = LSTMModel(
                input_size=self.input_size,
                hidden_size=self.hidden_size,
                num_layers=self.num_layers,
                output_size=self.output_size
            )
            model.to(self.device)
            
            # Kayıp fonksiyonu ve optimizer
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            
            # Eğitim döngüsü
            num_epochs = 50
            best_loss = float('inf')
            patience = 5
            no_improve_count = 0
            
            for epoch in range(num_epochs):
                model.train()
                train_loss = 0
                
                for X_batch, y_batch in train_loader:
                    # Forward pass
                    outputs = model(X_batch)
                    loss = criterion(outputs, y_batch)
                    
                    # Backward ve optimize
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    
                    train_loss += loss.item()
                
                train_loss = train_loss / len(train_loader)
                
                # Değerlendirme
                model.eval()
                val_loss = 0
                
                with torch.no_grad():
                    for X_batch, y_batch in test_loader:
                        outputs = model(X_batch)
                        loss = criterion(outputs, y_batch)
                        val_loss += loss.item()
                
                val_loss = val_loss / len(test_loader)
                
                logger.info(f"Epoch {epoch+1}/{num_epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
                
                # Early stopping
                if val_loss < best_loss:
                    best_loss = val_loss
                    no_improve_count = 0
                    
                    # En iyi modeli kaydet
                    model_key = f"{symbol}_{timeframe}"
                    model_path = os.path.join(self.model_dir, f"{model_key}_model.pth")
                    scaler_path = os.path.join(self.model_dir, f"{model_key}_scaler.pkl")
                    
                    torch.save(model.state_dict(), model_path)
                    
                    with open(scaler_path, 'wb') as f:
                        pickle.dump(scaler, f)
                else:
                    no_improve_count += 1
                
                if no_improve_count >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
            
            # En iyi modeli ve scaler'ı sakla
            model_key = f"{symbol}_{timeframe}"
            model_path = os.path.join(self.model_dir, f"{model_key}_model.pth")
            
            best_model = LSTMModel(
                input_size=self.input_size,
                hidden_size=self.hidden_size,
                num_layers=self.num_layers,
                output_size=self.output_size
            )
            best_model.load_state_dict(torch.load(model_path, map_location=self.device))
            best_model.to(self.device)
            best_model.eval()
            
            self.models[model_key] = best_model
            self.scalers[model_key] = scaler
            
            logger.info(f"{symbol}_{timeframe} için model eğitimi tamamlandı")
            return True
            
        except Exception as e:
            logger.error(f"Model eğitme hatası: {e}", exc_info=True)
            return False
    
    def predict(self, symbol: str, timeframe: Optional[str] = "H1") -> Dict:
        """
        Belirli bir sembol ve zaman dilimi için fiyat tahmini yap
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            
        Returns:
            Dict: Tahmin sonuçları
        """
        results = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.now(),
            "prediction": None,
            "direction": "neutral",
            "confidence": 0.0,
            "forecast": {
                "price_1h": None,
                "price_4h": None,
                "price_24h": None
            }
        }
        
        try:
            # Model yüklü mü kontrol et
            model_key = f"{symbol}_{timeframe}"
            if model_key not in self.models or model_key not in self.scalers:
                logger.info(f"{model_key} için model yükleniyor...")
                success = self.load_model(symbol, timeframe)
                if not success:
                    logger.error(f"{model_key} için model yüklenemedi")
                    return results
            
            # Tahmin için veriyi hazırla
            X_pred, _, df, _ = self._prepare_prediction_data(symbol, timeframe)
            
            if X_pred.shape[0] == 0:
                logger.error(f"{symbol}_{timeframe} için tahmin verisi hazırlanamadı")
                return results
            
            # Son veriyi al
            last_data = X_pred[-1:].copy()
            last_price = df['close'].iloc[-1]
            
            # Torch Tensor'ına dönüştür
            X_tensor = torch.FloatTensor(last_data).to(self.device)
            
            # Tahmin yap
            model = self.models[model_key]
            model.eval()
            
            with torch.no_grad():
                prediction = model(X_tensor)
                prediction = prediction.cpu().numpy()
            
            # Sonuçları yorumla
            pred_value = prediction[0][0]
            
            # Direction ve confidence hesapla
            if pred_value > 0.01:  # %1'den fazla artış
                direction = "buy"
                confidence = min(abs(pred_value * 100), 100)
            elif pred_value < -0.01:  # %1'den fazla azalış
                direction = "sell"
                confidence = min(abs(pred_value * 100), 100)
            else:
                direction = "neutral"
                confidence = abs(pred_value * 100)
            
            # 1, 4 ve 24 saatlik tahminler
            forecast_1h = last_price * (1 + pred_value)
            forecast_4h = last_price * (1 + pred_value * 2)  # Basit çarpan
            forecast_24h = last_price * (1 + pred_value * 4)  # Basit çarpan
            
            # Sonuçları doldur
            results["prediction"] = pred_value
            results["direction"] = direction
            results["confidence"] = confidence
            results["forecast"]["price_1h"] = forecast_1h
            results["forecast"]["price_4h"] = forecast_4h
            results["forecast"]["price_24h"] = forecast_24h
            
            return results
            
        except Exception as e:
            logger.error(f"Tahmin hatası: {e}", exc_info=True)
            return results
    
    def _prepare_training_data(self, symbol: str, timeframe: str) -> Tuple:
        """
        Eğitim verilerini hazırla
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            
        Returns:
            Tuple: (X, y, df, scaler) - Eğitim özellikleri, etiketler, veri ve scaler
        """
        try:
            # Model için veriyi hazırla
            X, df = self.data_manager.prepare_data_for_model(symbol, timeframe)
            
            if X.shape[0] == 0 or df.empty:
                logger.error(f"{symbol}_{timeframe} için veri hazırlanamadı")
                return np.array([]), np.array([]), pd.DataFrame(), None
            
            # Tahmin etiketlerini hazırla (bir sonraki kapanış fiyatındaki % değişim)
            y = df['close'].pct_change(periods=1).shift(-1).fillna(0).values
            
            # Dizi yeniden şekillendirme
            # 3B tensör: [batch_size, sequence_length, input_size]
            X_sequences = []
            y_sequences = []
            
            for i in range(len(X) - self.sequence_length):
                X_sequences.append(X[i:i + self.sequence_length])
                y_sequences.append(y[i + self.sequence_length - 1])
            
            X_sequences = np.array(X_sequences)
            y_sequences = np.array(y_sequences).reshape(-1, 1)
            
            return X_sequences, y_sequences, df, None
            
        except Exception as e:
            logger.error(f"Eğitim verisi hazırlama hatası: {e}")
            return np.array([]), np.array([]), pd.DataFrame(), None
    
    def _prepare_prediction_data(self, symbol: str, timeframe: str) -> Tuple:
        """
        Tahmin verisini hazırla
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            
        Returns:
            Tuple: (X, y, df, scaler) - Tahmin özellikleri, etiketler, veri ve scaler
        """
        try:
            # Model için veriyi hazırla
            X, df = self.data_manager.prepare_data_for_model(symbol, timeframe)
            
            if X.shape[0] == 0 or df.empty:
                logger.error(f"{symbol}_{timeframe} için veri hazırlanamadı")
                return np.array([]), np.array([]), pd.DataFrame(), None
            
            # Tahmin etiketlerini hazırla (bir sonraki kapanış fiyatındaki % değişim)
            y = df['close'].pct_change(periods=1).shift(-1).fillna(0).values
            
            # Dizi yeniden şekillendirme
            # 3B tensör: [batch_size, sequence_length, input_size]
            X_sequences = []
            
            # Tahmin için sadece son sequence_length kadar veriyi al
            if len(X) >= self.sequence_length:
                X_sequences.append(X[-self.sequence_length:])
            else:
                # Yeterli veri yoksa padding yap
                padding = np.zeros((self.sequence_length - len(X), X.shape[1]))
                padded_X = np.vstack((padding, X))
                X_sequences.append(padded_X)
            
            X_sequences = np.array(X_sequences)
            
            return X_sequences, y, df, None
            
        except Exception as e:
            logger.error(f"Tahmin verisi hazırlama hatası: {e}")
            return np.array([]), np.array([]), pd.DataFrame(), None
    
    def evaluate_model(self, symbol: str, timeframe: str) -> Dict:
        """
        Model performansını değerlendir
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            
        Returns:
            Dict: Değerlendirme sonuçları
        """
        results = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.now(),
            "mse": None,
            "mae": None,
            "accuracy": None,
            "direction_accuracy": None
        }
        
        try:
            # Model yüklü mü kontrol et
            model_key = f"{symbol}_{timeframe}"
            if model_key not in self.models:
                logger.info(f"{model_key} için model yükleniyor...")
                success = self.load_model(symbol, timeframe)
                if not success:
                    logger.error(f"{model_key} için model yüklenemedi")
                    return results
            
            # Test verisi hazırla
            X, y, df, _ = self._prepare_training_data(symbol, timeframe)
            
            if X.shape[0] == 0 or y.shape[0] == 0:
                logger.error(f"{symbol}_{timeframe} için test verisi hazırlanamadı")
                return results
            
            # Eğitim ve test setlerine böl
            train_size = int(len(X) * 0.8)
            X_test = X[train_size:]
            y_test = y[train_size:]
            
            # Torch Tensor'larına dönüştür
            X_test = torch.FloatTensor(X_test).to(self.device)
            y_test = torch.FloatTensor(y_test).to(self.device)
            
            # Tahmin yap
            model = self.models[model_key]
            model.eval()
            
            with torch.no_grad():
                y_pred = model(X_test).cpu().numpy()
                y_test = y_test.cpu().numpy()
            
            # Metrikleri hesapla
            from sklearn.metrics import mean_squared_error, mean_absolute_error
            
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            
            # Yön doğruluğu (pozitif/negatif tahmin)
            y_pred_dir = np.sign(y_pred)
            y_test_dir = np.sign(y_test)
            direction_accuracy = np.mean(y_pred_dir == y_test_dir)
            
            # Eşik değeri ile doğruluk (belirli bir hata payı içinde)
            threshold = 0.001  # %0.1
            accuracy = np.mean(np.abs(y_pred - y_test) < threshold)
            
            # Sonuçları doldur
            results["mse"] = mse
            results["mae"] = mae
            results["accuracy"] = accuracy
            results["direction_accuracy"] = direction_accuracy
            
            return results
            
        except Exception as e:
            logger.error(f"Model değerlendirme hatası: {e}", exc_info=True)
            return results