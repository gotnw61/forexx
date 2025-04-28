#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için LSTM model tanımı.
"""
import torch
import torch.nn as nn

class LSTMModel(nn.Module):
    """
    Zaman serisi tahmini için LSTM modeli.
    """
    
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, output_size: int):
        """
        LSTM modelini başlat
        
        Args:
            input_size: Giriş özellik sayısı
            hidden_size: Gizli katman boyutu
            num_layers: LSTM katman sayısı
            output_size: Çıkış boyutu
        """
        super(LSTMModel, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM katmanı
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        
        # Tam bağlantılı çıkış katmanı
        self.fc = nn.Linear(hidden_size, output_size)
        
        # Dropout
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        """
        İleri yayılım
        
        Args:
            x: Giriş verisi [batch_size, seq_len, input_size]
            
        Returns:
            Çıkış tahmini [batch_size, output_size]
        """
        # Gizli durumları başlat
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        # LSTM ileri yayılım
        out, _ = self.lstm(x, (h0, c0))
        
        # Son zaman adımının çıkışını al
        out = self.dropout(out[:, -1, :])
        
        # Tam bağlantılı katman
        out = self.fc(out)
        
        return out