#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için grafik modülü.
Plotly ile interaktif grafikler ve teknik analiz göstergeleri oluşturur.
"""
import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Tuple, Union, Any

logger = logging.getLogger("ForexTradingBot.ChartModule")

class ChartModule:
    """
    İnteraktif grafik ve gösterge çizimleri yapan sınıf.
    """
    
    def __init__(self, data_manager):
        """
        Grafik modülünü başlat
        
        Args:
            data_manager: Veri yöneticisi
        """
        self.data_manager = data_manager
        logger.info("Grafik modülü başlatıldı")
    
    def create_candlestick_chart(self, symbol: str, timeframe: str, 
                               num_periods: int = 100) -> Optional[go.Figure]:
        """
        Mum grafiği oluştur
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            num_periods: Görüntülenecek periyot sayısı
            
        Returns:
            Optional[go.Figure]: Plotly grafik nesnesi veya None
        """
        try:
            # Veriyi al
            df = self.data_manager.get_historical_data(symbol, timeframe)
            
            if df.empty:
                logger.warning(f"Grafik için veri bulunamadı: {symbol} {timeframe}")
                return None
            
            # Son num_periods kadar veriyi kullan
            df = df.tail(num_periods)
            
            # Ana grafik ve alt grafikler için subplot oluştur
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.7, 0.3],
                subplot_titles=(f"{symbol} - {timeframe}", "Hacim")
            )
            
            # Mum grafiği ekle
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name="Fiyat"
                ),
                row=1, col=1
            )
            
            # Hacim grafiği ekle
            colors = ['red' if c < o else 'green' for c, o in zip(df['close'], df['open'])]
            
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['volume'],
                    name="Hacim",
                    marker_color=colors
                ),
                row=2, col=1
            )
            
            # Hareketli ortalamalar ekle
            # 20 günlük SMA
            df['sma20'] = df['close'].rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['sma20'],
                    name="SMA 20",
                    line=dict(color='blue', width=1)
                ),
                row=1, col=1
            )
            
            # 50 günlük SMA
            df['sma50'] = df['close'].rolling(window=50).mean()
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['sma50'],
                    name="SMA 50",
                    line=dict(color='orange', width=1)
                ),
                row=1, col=1
            )
            
            # Grafik görünümünü ayarla
            fig.update_layout(
                title=f"{symbol} {timeframe} Mum Grafiği",
                xaxis_title="Tarih",
                yaxis_title="Fiyat",
                xaxis_rangeslider_visible=False,
                height=600,
                template='plotly_white',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )
            
            # X ekseni düzenlemesi
            fig.update_xaxes(
                rangeslider_visible=False,
                rangebreaks=[
                    # Haftasonları gizle
                    dict(bounds=["sat", "mon"]),
                ],
                showgrid=True
            )
            
            # Y ekseni düzenlemesi
            fig.update_yaxes(
                showgrid=True,
                zeroline=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Mum grafiği oluşturulurken hata: {e}", exc_info=True)
            return None
    
    def create_technical_chart(self, symbol: str, timeframe: str, 
                            indicators: List[str], num_periods: int = 100) -> Optional[go.Figure]:
        """
        Teknik göstergeler içeren grafik oluştur
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            indicators: Eklenecek göstergeler listesi
            num_periods: Görüntülenecek periyot sayısı
            
        Returns:
            Optional[go.Figure]: Plotly grafik nesnesi veya None
        """
        try:
            # Veriyi al
            df = self.data_manager.get_historical_data(symbol, timeframe)
            
            if df.empty:
                logger.warning(f"Grafik için veri bulunamadı: {symbol} {timeframe}")
                return None
            
            # Son num_periods kadar veriyi kullan
            df = df.tail(num_periods)
            
            # İstenen göstergelere göre alt grafik sayısını belirle
            subplot_count = 1  # Ana fiyat grafiği
            
            # RSI, MACD, Stochastic için ayrı alt grafikler
            separate_indicators = ["RSI", "MACD", "Stochastic"]
            
            for indicator in indicators:
                if indicator in separate_indicators:
                    subplot_count += 1
            
            # Ana grafik ve alt grafikler için subplot oluştur
            fig = make_subplots(
                rows=subplot_count, cols=1, 
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.5] + [0.5/max(1, subplot_count-1)] * (subplot_count-1),
                subplot_titles=tuple([f"{symbol} - {timeframe}"] + indicators)
            )
            
            # Mum grafiği ekle
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name="Fiyat"
                ),
                row=1, col=1
            )
            
            # Göstergeleri ekle
            current_row = 2
            
            for indicator in indicators:
                if indicator == "Bollinger Bands":
                    # Bollinger Bands
                    period = 20
                    std_dev = 2
                    
                    df['ma'] = df['close'].rolling(window=period).mean()
                    df['std'] = df['close'].rolling(window=period).std()
                    
                    df['upper_band'] = df['ma'] + (df['std'] * std_dev)
                    df['lower_band'] = df['ma'] - (df['std'] * std_dev)
                    
                    # Orta band
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['ma'],
                            name="BB Orta",
                            line=dict(color='blue', width=1)
                        ),
                        row=1, col=1
                    )
                    
                    # Üst band
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['upper_band'],
                            name="BB Üst",
                            line=dict(color='green', width=1, dash='dot')
                        ),
                        row=1, col=1
                    )
                    
                    # Alt band
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['lower_band'],
                            name="BB Alt",
                            line=dict(color='red', width=1, dash='dot')
                        ),
                        row=1, col=1
                    )
                
                elif indicator == "RSI":
                    # RSI hesapla
                    period = 14
                    
                    delta = df['close'].diff()
                    gain = delta.where(delta > 0, 0)
                    loss = -delta.where(delta < 0, 0)
                    
                    avg_gain = gain.rolling(window=period).mean()
                    avg_loss = loss.rolling(window=period).mean()
                    
                    rs = avg_gain / avg_loss
                    df['rsi'] = 100 - (100 / (1 + rs))
                    
                    # RSI çizgisi
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['rsi'],
                            name="RSI",
                            line=dict(color='purple', width=2)
                        ),
                        row=current_row, col=1
                    )
                    
                    # Aşırı alım/satım çizgileri
                    fig.add_shape(
                        type="line",
                        x0=df.index[0],
                        y0=70,
                        x1=df.index[-1],
                        y1=70,
                        line=dict(color="red", width=1, dash="dash"),
                        row=current_row, col=1
                    )
                    
                    fig.add_shape(
                        type="line",
                        x0=df.index[0],
                        y0=30,
                        x1=df.index[-1],
                        y1=30,
                        line=dict(color="green", width=1, dash="dash"),
                        row=current_row, col=1
                    )
                    
                    # Y ekseni aralığını ayarla
                    fig.update_yaxes(range=[0, 100], row=current_row, col=1)
                    current_row += 1
                
                elif indicator == "MACD":
                    # MACD hesapla
                    fast_period = 12
                    slow_period = 26
                    signal_period = 9
                    
                    df['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
                    df['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
                    
                    df['macd'] = df['ema_fast'] - df['ema_slow']
                    df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
                    df['macd_hist'] = df['macd'] - df['macd_signal']
                    
                    # MACD çizgisi
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['macd'],
                            name="MACD",
                            line=dict(color='blue', width=2)
                        ),
                        row=current_row, col=1
                    )
                    
                    # Sinyal çizgisi
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['macd_signal'],
                            name="Sinyal",
                            line=dict(color='red', width=1)
                        ),
                        row=current_row, col=1
                    )
                    
                    # Histogram
                    colors = ['red' if x < 0 else 'green' for x in df['macd_hist']]
                    
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df['macd_hist'],
                            name="Histogram",
                            marker_color=colors
                        ),
                        row=current_row, col=1
                    )
                    
                    # Sıfır çizgisi
                    fig.add_shape(
                        type="line",
                        x0=df.index[0],
                        y0=0,
                        x1=df.index[-1],
                        y1=0,
                        line=dict(color="black", width=1, dash="dot"),
                        row=current_row, col=1
                    )
                    
                    current_row += 1
                
                elif indicator == "Stochastic":
                    # Stochastic hesapla
                    k_period = 14
                    d_period = 3
                    
                    df['low_min'] = df['low'].rolling(window=k_period).min()
                    df['high_max'] = df['high'].rolling(window=k_period).max()
                    
                    df['stoch_k'] = 100 * ((df['close'] - df['low_min']) / 
                                         (df['high_max'] - df['low_min']))
                    df['stoch_d'] = df['stoch_k'].rolling(window=d_period).mean()
                    
                    # K çizgisi
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['stoch_k'],
                            name="%K",
                            line=dict(color='blue', width=2)
                        ),
                        row=current_row, col=1
                    )
                    
                    # D çizgisi
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['stoch_d'],
                            name="%D",
                            line=dict(color='red', width=1)
                        ),
                        row=current_row, col=1
                    )
                    
                    # Aşırı alım/satım çizgileri
                    fig.add_shape(
                        type="line",
                        x0=df.index[0],
                        y0=80,
                        x1=df.index[-1],
                        y1=80,
                        line=dict(color="red", width=1, dash="dash"),
                        row=current_row, col=1
                    )
                    
                    fig.add_shape(
                        type="line",
                        x0=df.index[0],
                        y0=20,
                        x1=df.index[-1],
                        y1=20,
                        line=dict(color="green", width=1, dash="dash"),
                        row=current_row, col=1
                    )
                    
                    # Y ekseni aralığını ayarla
                    fig.update_yaxes(range=[0, 100], row=current_row, col=1)
                    current_row += 1
                
                elif indicator == "Moving Average":
                    # Hareketli ortalamalar
                    # 20 günlük SMA
                    df['sma20'] = df['close'].rolling(window=20).mean()
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['sma20'],
                            name="SMA 20",
                            line=dict(color='blue', width=1)
                        ),
                        row=1, col=1
                    )
                    
                    # 50 günlük SMA
                    df['sma50'] = df['close'].rolling(window=50).mean()
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['sma50'],
                            name="SMA 50",
                            line=dict(color='orange', width=1)
                        ),
                        row=1, col=1
                    )
                    
                    # 200 günlük SMA
                    if len(df) >= 200:
                        df['sma200'] = df['close'].rolling(window=200).mean()
                        fig.add_trace(
                            go.Scatter(
                                x=df.index,
                                y=df['sma200'],
                                name="SMA 200",
                                line=dict(color='red', width=1)
                            ),
                            row=1, col=1
                        )
                
                elif indicator == "Ichimoku":
                    # Ichimoku hesapla
                    tenkan_period = 9
                    kijun_period = 26
                    senkou_span_b_period = 52
                    
                    # Tenkan-sen (Conversion Line)
                    tenkan_high = df['high'].rolling(window=tenkan_period).max()
                    tenkan_low = df['low'].rolling(window=tenkan_period).min()
                    df['tenkan_sen'] = (tenkan_high + tenkan_low) / 2
                    
                    # Kijun-sen (Base Line)
                    kijun_high = df['high'].rolling(window=kijun_period).max()
                    kijun_low = df['low'].rolling(window=kijun_period).min()
                    df['kijun_sen'] = (kijun_high + kijun_low) / 2
                    
                    # Senkou Span A (Leading Span A)
                    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(kijun_period)
                    
                    # Senkou Span B (Leading Span B)
                    senkou_high = df['high'].rolling(window=senkou_span_b_period).max()
                    senkou_low = df['low'].rolling(window=senkou_span_b_period).min()
                    df['senkou_span_b'] = ((senkou_high + senkou_low) / 2).shift(kijun_period)
                    
                    # Chikou Span (Lagging Span)
                    df['chikou_span'] = df['close'].shift(-kijun_period)
                    
                    # Tenkan-sen
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['tenkan_sen'],
                            name="Tenkan-sen",
                            line=dict(color='red', width=1)
                        ),
                        row=1, col=1
                    )
                    
                    # Kijun-sen
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['kijun_sen'],
                            name="Kijun-sen",
                            line=dict(color='blue', width=1)
                        ),
                        row=1, col=1
                    )
                    
                    # Senkou Span A
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['senkou_span_a'],
                            name="Senkou Span A",
                            line=dict(color='green', width=1)
                        ),
                        row=1, col=1
                    )
                    
                    # Senkou Span B
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['senkou_span_b'],
                            name="Senkou Span B",
                            line=dict(color='purple', width=1)
                        ),
                        row=1, col=1
                    )
                    
                    # Bulut (fill alanı)
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['senkou_span_a'],
                            name="Kumo Cloud",
                            line=dict(color='rgba(0,0,0,0)'),
                            showlegend=False,
                            hoverinfo='none'
                        ),
                        row=1, col=1
                    )
                    
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['senkou_span_b'],
                            name="Kumo Cloud",
                            line=dict(color='rgba(0,0,0,0)'),
                            fill='tonexty',
                            fillcolor='rgba(0,250,0,0.1)',
                            showlegend=False,
                            hoverinfo='none'
                        ),
                        row=1, col=1
                    )
            
            # Grafik görünümünü ayarla
            fig.update_layout(
                title=f"{symbol} {timeframe} Teknik Analiz",
                xaxis_title="Tarih",
                yaxis_title="Fiyat",
                xaxis_rangeslider_visible=False,
                height=800,
                template='plotly_white',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )
            
            # X ekseni düzenlemesi
            fig.update_xaxes(
                rangeslider_visible=False,
                rangebreaks=[
                    # Haftasonları gizle
                    dict(bounds=["sat", "mon"]),
                ],
                showgrid=True
            )
            
            # Y ekseni düzenlemesi
            fig.update_yaxes(
                showgrid=True,
                zeroline=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Teknik grafik oluşturulurken hata: {e}", exc_info=True)
            return None
    
    def create_analysis_chart(self, symbol: str, timeframe: str, 
                           analysis_results: Dict) -> Optional[go.Figure]:
        """
        Analiz sonuçlarını içeren grafik oluştur
        
        Args:
            symbol: İşlem sembolü
            timeframe: Zaman dilimi
            analysis_results: Analiz sonuçları
            
        Returns:
            Optional[go.Figure]: Plotly grafik nesnesi veya None
        """
        try:
            # Veriyi al
            df = self.data_manager.get_historical_data(symbol, timeframe)
            
            if df.empty:
                logger.warning(f"Grafik için veri bulunamadı: {symbol} {timeframe}")
                return None
            
            # Son 100 çubuğu al
            df = df.tail(100)
            
            # Ana grafik ve alt grafik için subplot oluştur
            fig = make_subplots(
                rows=1, cols=1,
                subplot_titles=(f"{symbol} - {timeframe} - Analiz"),
                specs=[[{"secondary_y": True}]]
            )
            
            # Mum grafiği ekle
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name="Fiyat"
                )
            )
            
            # Destek ve direnç seviyelerini ekle
            support_levels = analysis_results.get("support_levels", [])
            resistance_levels = analysis_results.get("resistance_levels", [])
            
            # Son fiyat
            last_price = df['close'].iloc[-1]
            
            # Destek seviyeleri
            for level in support_levels:
                if level < last_price:
                    fig.add_shape(
                        type="line",
                        x0=df.index[0],
                        y0=level,
                        x1=df.index[-1],
                        y1=level,
                        line=dict(color="green", width=1, dash="dash"),
                    )
                    
                    fig.add_annotation(
                        x=df.index[-1],
                        y=level,
                        text=f"Support: {level:.5f}",
                        showarrow=False,
                        xanchor="right",
                        yanchor="bottom"
                    )
            
            # Direnç seviyeleri
            for level in resistance_levels:
                if level > last_price:
                    fig.add_shape(
                        type="line",
                        x0=df.index[0],
                        y0=level,
                        x1=df.index[-1],
                        y1=level,
                        line=dict(color="red", width=1, dash="dash"),
                    )
                    
                    fig.add_annotation(
                        x=df.index[-1],
                        y=level,
                        text=f"Resistance: {level:.5f}",
                        showarrow=False,
                        xanchor="right",
                        yanchor="top"
                    )
            
            # Analiz sonucunu ekle
            signal = analysis_results.get("signal", "neutral")
            strength = analysis_results.get("strength", 0)
            
            signal_color = "gray"
            if signal == "buy":
                signal_color = "green"
            elif signal == "sell":
                signal_color = "red"
            
            fig.add_annotation(
                x=df.index[-1],
                y=df['high'].max(),
                text=f"Sinyal: {signal.upper()} (Güç: {strength:.1f}%)",
                showarrow=False,
                xanchor="right",
                yanchor="top",
                bgcolor=signal_color,
                font=dict(color="white"),
                bordercolor=signal_color,
                borderwidth=2
            )
            
            # Grafik görünümünü ayarla
            fig.update_layout(
                title=f"{symbol} {timeframe} Analiz Grafiği",
                xaxis_title="Tarih",
                yaxis_title="Fiyat",
                xaxis_rangeslider_visible=False,
                height=600,
                template='plotly_white',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )
            
            # X ekseni düzenlemesi
            fig.update_xaxes(
                rangeslider_visible=False,
                rangebreaks=[
                    # Haftasonları gizle
                    dict(bounds=["sat", "mon"]),
                ],
                showgrid=True
            )
            
            # Y ekseni düzenlemesi
            fig.update_yaxes(
                showgrid=True,
                zeroline=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Analiz grafiği oluşturulurken hata: {e}", exc_info=True)
            return None
    
    def create_multi_timeframe_chart(self, symbol: str, 
                                   timeframes: List[str]) -> Optional[Dict[str, go.Figure]]:
        """
        Çoklu zaman dilimi grafikleri oluştur
        
        Args:
            symbol: İşlem sembolü
            timeframes: Zaman dilimleri listesi
            
        Returns:
            Optional[Dict[str, go.Figure]]: Zaman dilimlerine göre grafikler sözlüğü veya None
        """
        try:
            results = {}
            
            for timeframe in timeframes:
                # Her zaman dilimi için grafik oluştur
                fig = self.create_candlestick_chart(symbol, timeframe)
                
                if fig is not None:
                    results[timeframe] = fig
            
            return results if results else None
            
        except Exception as e:
            logger.error(f"Çoklu zaman dilimi grafikleri oluşturulurken hata: {e}")
            return None
    
    def create_comparison_chart(self, symbols: List[str], 
                             timeframe: str, num_periods: int = 100) -> Optional[go.Figure]:
        """
        Sembolleri karşılaştıran grafik oluştur
        
        Args:
            symbols: İşlem sembolleri listesi
            timeframe: Zaman dilimi
            num_periods: Görüntülenecek periyot sayısı
            
        Returns:
            Optional[go.Figure]: Plotly grafik nesnesi veya None
        """
        try:
            # Grafik oluştur
            fig = go.Figure()
            
            # Her sembol için veriyi al ve çiz
            for symbol in symbols:
                df = self.data_manager.get_historical_data(symbol, timeframe)
                
                if df.empty:
                    logger.warning(f"Grafik için veri bulunamadı: {symbol} {timeframe}")
                    continue
                
                # Son num_periods kadar veriyi kullan
                df = df.tail(num_periods)
                
                # İlk değere göre normalize et
                first_value = df['close'].iloc[0]
                normalized_close = (df['close'] / first_value) * 100
                
                # Çizgi grafiği ekle
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=normalized_close,
                        name=symbol,
                        mode='lines'
                    )
                )
            
            # Grafik görünümünü ayarla
            fig.update_layout(
                title=f"Sembol Karşılaştırma - {timeframe}",
                xaxis_title="Tarih",
                yaxis_title="Normalize Değer (%)",
                height=600,
                template='plotly_white',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )
            
            # X ekseni düzenlemesi
            fig.update_xaxes(
                rangebreaks=[
                    # Haftasonları gizle
                    dict(bounds=["sat", "mon"]),
                ],
                showgrid=True
            )
            
            # Y ekseni düzenlemesi
            fig.update_yaxes(
                showgrid=True,
                zeroline=True
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Karşılaştırma grafiği oluşturulurken hata: {e}")
            return None