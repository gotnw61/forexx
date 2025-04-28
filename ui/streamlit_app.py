#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için Streamlit tabanlı kullanıcı arayüzü.
Bot'un tüm özelliklerine erişim sağlar ve görselleştirir.
"""
import os
import sys
import logging
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
import threading
import json

# Proje kök dizinini ayarla
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

# Grafik modülünü içe aktar
from ui.chart_module import ChartModule

logger = logging.getLogger("ForexTradingBot.StreamlitApp")

def run_streamlit_app(bot):
    """
    Streamlit uygulamasını başlat
    
    Args:
        bot: ForexTradingBot örneği
    """
    import os
    import sys
    import streamlit.web.cli as stcli
    
    # Streamlit config ayarları
    streamlit_port = bot.settings.get("ui", {}).get("port", 8501)
    os.environ["STREAMLIT_SERVER_PORT"] = str(streamlit_port)
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    
    # Streamlit'i doğrudan çalıştır
    sys.argv = [
        "streamlit", 
        "run", 
        os.path.abspath(__file__), 
        "--global.developmentMode=false"
    ]
    
    # Streamlit'i ana thread'de çalıştır
    stcli.main()

# Streamlit sayfasını oluştur
def main():
    """
    Ana Streamlit uygulaması
    """
    # Sayfa yapılandırması
    st.set_page_config(
        page_title="Gelişmiş Forex Trading Bot",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS stilleri
    st.markdown(""" 
    <style>
    .big-font {
        font-size:20px !important;
        font-weight: bold;
    }
    .medium-font {
        font-size:16px !important;
    }
    .buy-signal {
        color: green;
        font-weight: bold;
    }
    .sell-signal {
        color: red;
        font-weight: bold;
    }
    .neutral-signal {
        color: gray;
        font-weight: bold;
    }
    .success-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .warning-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
    }
    .error-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Başlık
    st.title("Gelişmiş Forex Trading Bot")
    
    # Bot örneği oluştur (Streamlit için global state kullan)
    if 'bot_initialized' not in st.session_state:
        # Botu başlatma fonksiyonu
        bot = initialize_bot()
        
        if bot is not None:
            st.session_state.bot = bot
            st.session_state.bot_initialized = True
            st.session_state.chart_module = ChartModule(bot.data_manager)
            
            # Bot durumu
            st.session_state.bot_running = False
            st.session_state.last_update = None
            st.session_state.signals = []
            st.session_state.open_positions = []
        else:
            st.error("Bot başlatılamadı! Lütfen ayarları kontrol edin ve yeniden deneyin.")
            return
    else:
        # Mevcut bot örneğini kullan
        bot = st.session_state.bot
    
    # Yan menü
    with st.sidebar:
        st.header("İşlemler")
        
        # Bot durumu
        bot_status = "Çalışıyor" if st.session_state.bot_running else "Durduruldu"
        st.markdown(f"**Bot Durumu:** {bot_status}")
        
        # Bot kontrolleri
        if st.session_state.bot_running:
            if st.button("Bot'u Durdur", key="stop_button"):
                stop_bot(bot)
                st.session_state.bot_running = False
                st.success("Bot durduruldu!")
                # Sayfayı yenile
                st.experimental_rerun()
        else:
            if st.button("Bot'u Başlat", key="start_button"):
                start_bot(bot)
                st.session_state.bot_running = True
                st.success("Bot başlatıldı!")
                # Sayfayı yenile
                st.experimental_rerun()
        
        # Sayfa navigasyonu
        st.markdown("---")
        st.header("Sayfalar")
        
        page = st.radio(
            "Sayfa Seçin:",
            ["Gösterge Paneli", "Canlı Grafikler", "Sinyal İzleme", "Açık Pozisyonlar", 
             "MT5 Ayarları", "Bot Ayarları", "Performans", "API Yönetimi"]
        )
        
        # En son güncelleme zamanı
        if st.session_state.last_update:
            last_update_str = st.session_state.last_update.strftime("%H:%M:%S")
            st.markdown(f"*Son güncelleme: {last_update_str}*")
        
        # Hesap Bilgileri
        st.markdown("---")
        st.header("Hesap Bilgileri")
        
        account_info = bot.broker.get_account_info()
        if account_info:
            st.markdown(f"**Bakiye:** {account_info.get('balance', 0):.2f} {account_info.get('currency', 'USD')}")
            st.markdown(f"**Varlık:** {account_info.get('equity', 0):.2f} {account_info.get('currency', 'USD')}")
            st.markdown(f"**Serbest Marjin:** {account_info.get('free_margin', 0):.2f} {account_info.get('currency', 'USD')}")
            st.markdown(f"**Marjin Seviyesi:** {account_info.get('margin_level', 0):.2f}%")
            st.markdown(f"**Hesap Tipi:** {account_info.get('trade_mode', 'Demo')}")
        else:
            st.warning("Hesap bilgileri alınamıyor!")
        
        # Yenile butonu
        if st.button("Verileri Yenile"):
            # Verileri yenile
            refresh_data(bot)
            st.success("Veriler yenilendi!")
    
    # Ana sayfa içerikleri
    if page == "Gösterge Paneli":
        show_dashboard(bot)
    elif page == "Canlı Grafikler":
        show_live_charts(bot)
    elif page == "Sinyal İzleme":
        show_signal_monitor(bot)
    elif page == "Açık Pozisyonlar":
        show_open_positions(bot)
    elif page == "MT5 Ayarları":
        show_mt5_settings(bot)
    elif page == "Bot Ayarları":
        show_bot_settings(bot)
    elif page == "Performans":
        show_performance(bot)
    elif page == "API Yönetimi":
        show_api_management(bot)

def initialize_bot():
    """
    Bot örneğini başlat
    
    Returns:
        ForexTradingBot: Bot örneği veya None
    """
    try:
        # ForexTradingBot modülünü dinamik olarak içe aktar
        sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
        
        from main import ForexTradingBot
        
        # Bot örneğini oluştur
        bot = ForexTradingBot()
        
        return bot
    except Exception as e:
        logger.error(f"Bot başlatma hatası: {e}", exc_info=True)
        st.error(f"Bot başlatılamadı: {e}")
        return None

def start_bot(bot):
    """
    Bot'u başlat
    
    Args:
        bot: ForexTradingBot örneği
    """
    try:
        # Bot'u başlatma
        bot.start()
        st.session_state.bot_running = True
        st.session_state.last_update = datetime.now()
        
        # Yenileme için thread başlat
        if not hasattr(st.session_state, 'refresh_thread') or not st.session_state.refresh_thread.is_alive():
            st.session_state.refresh_thread = threading.Thread(target=background_refresh, args=(bot,))
            st.session_state.refresh_thread.daemon = True
            st.session_state.refresh_thread.start()
    except Exception as e:
        logger.error(f"Bot başlatma hatası: {e}", exc_info=True)
        st.error(f"Bot başlatma hatası: {e}")

def stop_bot(bot):
    """
    Bot'u durdur
    
    Args:
        bot: ForexTradingBot örneği
    """
    try:
        # Bot'u durdur
        bot.stop()
        st.session_state.bot_running = False
        st.session_state.last_update = datetime.now()
    except Exception as e:
        logger.error(f"Bot durdurma hatası: {e}", exc_info=True)
        st.error(f"Bot durdurma hatası: {e}")

def refresh_data(bot):
    """
    Verileri yenile
    
    Args:
        bot: ForexTradingBot örneği
    """
    try:
        # Açık pozisyonları güncelle
        positions_df = bot.broker.get_positions()
        st.session_state.open_positions = positions_df.to_dict('records') if not positions_df.empty else []
        
        # Sinyal geçmişini güncelle
        st.session_state.signals = bot.signal_generator.get_signal_history(20)
        
        # Son güncelleme zamanını ayarla
        st.session_state.last_update = datetime.now()
    except Exception as e:
        logger.error(f"Veri yenileme hatası: {e}", exc_info=True)

def background_refresh(bot):
    """
    Arkaplan veri yenileme
    
    Args:
        bot: ForexTradingBot örneği
    """
    try:
        while st.session_state.bot_running:
            # Verileri yenile
            refresh_data(bot)
            
            # 60 saniye bekle
            time.sleep(60)
    except Exception as e:
        logger.error(f"Arkaplan yenileme hatası: {e}", exc_info=True)

def show_dashboard(bot):
    """
    Gösterge paneli sayfasını göster
    
    Args:
        bot: ForexTradingBot örneği
    """
    st.header("Gösterge Paneli")
    
    # Durum özeti
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Bot Durumu")
        
        bot_status = "Çalışıyor" if st.session_state.bot_running else "Durduruldu"
        status_color = "green" if st.session_state.bot_running else "red"
        
        st.markdown(f"<div style='padding: 10px; border-radius: 5px; background-color: {status_color}; color: white;'>"
                   f"<h3 style='margin: 0; text-align: center;'>{bot_status}</h3>"
                   f"</div>", unsafe_allow_html=True)
        
        # MT5 bağlantı durumu
        mt5_connected = bot.broker.connected
        mt5_status = "Bağlı" if mt5_connected else "Bağlı Değil"
        mt5_color = "green" if mt5_connected else "red"
        
        st.markdown(f"<div style='margin-top: 10px; padding: 10px; border-radius: 5px; "
                   f"background-color: {mt5_color}; color: white;'>"
                   f"<h4 style='margin: 0; text-align: center;'>MT5: {mt5_status}</h4>"
                   f"</div>", unsafe_allow_html=True)
        
        # Telegram bağlantı durumu
        telegram_connected = hasattr(bot.telegram_bot, 'connected') and bot.telegram_bot.connected
        telegram_status = "Bağlı" if telegram_connected else "Bağlı Değil"
        telegram_color = "green" if telegram_connected else "red"
        
        st.markdown(f"<div style='margin-top: 10px; padding: 10px; border-radius: 5px; "
                   f"background-color: {telegram_color}; color: white;'>"
                   f"<h4 style='margin: 0; text-align: center;'>Telegram: {telegram_status}</h4>"
                   f"</div>", unsafe_allow_html=True)
    
    with col2:
        st.subheader("İşlem Özeti")
        
        # Açık pozisyon sayısı
        open_count = len(st.session_state.open_positions)
        
        # Bekleyen sinyal sayısı
        pending_signals = sum(1 for s in st.session_state.signals if s.get("status") == "pending")
        
        # Günlük işlem sayısı
        today = datetime.now().date()
        daily_trades = sum(1 for p in st.session_state.open_positions 
                          if pd.to_datetime(p.get("time")).date() == today)
        
        # Kart stilinde göster
        st.markdown(f"<div style='padding: 10px; border-radius: 5px; background-color: #3498db; color: white;'>"
                   f"<h4 style='margin: 0;'>Açık Pozisyonlar: {open_count}</h4>"
                   f"</div>", unsafe_allow_html=True)
        
        st.markdown(f"<div style='margin-top: 10px; padding: 10px; border-radius: 5px; "
                   f"background-color: #f39c12; color: white;'>"
                   f"<h4 style='margin: 0;'>Bekleyen Sinyaller: {pending_signals}</h4>"
                   f"</div>", unsafe_allow_html=True)
        
        st.markdown(f"<div style='margin-top: 10px; padding: 10px; border-radius: 5px; "
                   f"background-color: #2ecc71; color: white;'>"
                   f"<h4 style='margin: 0;'>Bugünkü İşlemler: {daily_trades}</h4>"
                   f"</div>", unsafe_allow_html=True)
    
    with col3:
        st.subheader("Risk Durumu")
        
        # Risk özeti
        risk_summary = bot.risk_manager.get_risk_summary()
        
        # Günlük risk
        daily_risk = risk_summary.get("daily_risk", 0)
        max_daily_risk = risk_summary.get("max_daily_risk", 5)
        daily_risk_percent = (daily_risk / max_daily_risk) * 100 if max_daily_risk > 0 else 0
        
        # Haftalık risk
        weekly_risk = risk_summary.get("weekly_risk", 0)
        max_weekly_risk = risk_summary.get("max_weekly_risk", 10)
        weekly_risk_percent = (weekly_risk / max_weekly_risk) * 100 if max_weekly_risk > 0 else 0
        
        # İlerleme çubukları olarak göster
        st.markdown("**Günlük Risk Kullanımı:**")
        st.progress(min(daily_risk_percent / 100, 1.0))
        st.markdown(f"{daily_risk:.2f}% / {max_daily_risk:.2f}%")
        
        st.markdown("**Haftalık Risk Kullanımı:**")
        st.progress(min(weekly_risk_percent / 100, 1.0))
        st.markdown(f"{weekly_risk:.2f}% / {max_weekly_risk:.2f}%")
        
        # Ortalama işlem riski
        avg_risk = risk_summary.get("avg_risk_per_trade", 0)
        st.markdown(f"**İşlem Başına Ort. Risk:** {avg_risk:.2f}%")
    
    # Grafik ve aktivite bölümleri
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Son Fiyat Hareketleri")
        
        # Sembol seç
        default_symbol = bot.settings.get("symbols", ["EURUSD"])[0]
        selected_symbol = st.selectbox("Sembol:", bot.settings.get("symbols", ["EURUSD"]), index=0)
        
        # Grafik modülü
        chart_module = st.session_state.chart_module
        
        # Mum grafiği oluştur
        fig = chart_module.create_candlestick_chart(selected_symbol, "H1", 100)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"{selected_symbol} H1 grafiği için veri bulunamadı.")
    
    with col2:
        st.subheader("Son Aktiviteler")
        
        # Son sinyaller
        if st.session_state.signals:
            for signal in st.session_state.signals[:5]:  # Son 5 sinyal
                symbol = signal.get("symbol", "")
                signal_type = signal.get("signal", "neutral")
                timestamp = signal.get("timestamp", datetime.now())
                probability = signal.get("success_probability", 0)
                status = signal.get("status", "pending")
                
                # Renk belirle
                if signal_type == "buy":
                    color = "buy-signal"
                elif signal_type == "sell":
                    color = "sell-signal"
                else:
                    color = "neutral-signal"
                
                # Kart stilinde göster
                st.markdown(f"<div style='margin-bottom: 10px; padding: 10px; "
                           f"border-radius: 5px; border: 1px solid #ddd;'>"
                           f"<div style='display: flex; justify-content: space-between;'>"
                           f"<span><strong>{symbol}</strong></span>"
                           f"<span class='{color}'>{signal_type.upper()}</span>"
                           f"</div>"
                           f"<div style='display: flex; justify-content: space-between; margin-top: 5px;'>"
                           f"<span>{timestamp.strftime('%H:%M:%S')}</span>"
                           f"<span>Olasılık: {probability:.1f}%</span>"
                           f"</div>"
                           f"<div style='text-align: right; margin-top: 5px;'>"
                           f"<span style='background-color: #f1f1f1; padding: 2px 5px; "
                           f"border-radius: 3px;'>{status.capitalize()}</span>"
                           f"</div>"
                           f"</div>", unsafe_allow_html=True)
        else:
            st.info("Henüz sinyal yok.")
        
        # Yaklaşan önemli haberler
        st.markdown("---")
        st.subheader("Yaklaşan Önemli Haberler")
        
        # Tüm semboller için para birimlerini çıkar
        symbols = bot.settings.get("symbols", ["EURUSD"])
        currencies = set()
        
        for symbol in symbols:
            if len(symbol) >= 6:
                currencies.add(symbol[:3])
                currencies.add(symbol[3:6])
        
        # Haber verilerini al
        current_symbol = symbols[0]  # İlk sembolü kullan
        analysis_results = bot.analysis_engine.analyze(current_symbol)
        
        if "news" in analysis_results and "next_events" in analysis_results:
            upcoming_events = analysis_results["news"].get("next_events", [])
            
            if upcoming_events:
                for event in upcoming_events[:3]:  # İlk 3 olay
                    currency = event.get("currency", "")
                    event_name = event.get("event", "")
                    event_time = event.get("datetime", datetime.now())
                    impact = event.get("impact", "Low")
                    
                    # Etki rengini belirle
                    impact_color = "#28a745" if impact == "High" else "#ffc107" if impact == "Medium" else "#6c757d"
                    
                    # Kart stilinde göster
                    st.markdown(f"<div style='margin-bottom: 10px; padding: 10px; "
                               f"border-radius: 5px; border: 1px solid #ddd;'>"
                               f"<div style='display: flex; justify-content: space-between;'>"
                               f"<span><strong>{currency}</strong></span>"
                               f"<span style='color: {impact_color};'>{impact} Etki</span>"
                               f"</div>"
                               f"<div style='margin-top: 5px;'>"
                               f"{event_name}"
                               f"</div>"
                               f"<div style='text-align: right; margin-top: 5px;'>"
                               f"<span style='background-color: #f1f1f1; padding: 2px 5px; "
                               f"border-radius: 3px;'>{event_time.strftime('%d.%m.%Y %H:%M')}</span>"
                               f"</div>"
                               f"</div>", unsafe_allow_html=True)
            else:
                st.info("Yaklaşan önemli haber yok.")
        else:
            st.info("Haber verisi alınamıyor.")

def show_live_charts(bot):
    """
    Canlı grafikler sayfasını göster
    
    Args:
        bot: ForexTradingBot örneği
    """
    st.header("Canlı Grafikler")
    
    # Sembol ve zaman dilimi seçimi
    col1, col2 = st.columns(2)
    
    with col1:
        selected_symbol = st.selectbox("Sembol:", bot.settings.get("symbols", ["EURUSD"]))
    
    with col2:
        timeframe_options = bot.settings.get("timeframes", ["M5", "M15", "H1", "H4", "D1"])
        selected_timeframe = st.selectbox("Zaman Dilimi:", timeframe_options)
    
    # Gösterge seçimi
    indicators = st.multiselect(
        "Göstergeler:",
        ["Moving Average", "Bollinger Bands", "RSI", "MACD", "Stochastic", "Ichimoku"],
        default=["Moving Average", "RSI"]
    )
    
    # Grafik oluşturma butonu
    if st.button("Grafik Oluştur"):
        with st.spinner("Grafik hazırlanıyor..."):
            chart_module = st.session_state.chart_module
            
            if indicators:
                # Teknik göstergeli grafik
                fig = chart_module.create_technical_chart(
                    selected_symbol, 
                    selected_timeframe, 
                    indicators
                )
            else:
                # Basit mum grafiği
                fig = chart_module.create_candlestick_chart(
                    selected_symbol, 
                    selected_timeframe
                )
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"{selected_symbol} {selected_timeframe} grafiği için veri bulunamadı.")
    
    # Çoklu zaman dilimi görünümü
    st.markdown("---")
    st.subheader("Çoklu Zaman Dilimi Görünümü")
    
    multi_symbol = st.selectbox("Sembol:", bot.settings.get("symbols", ["EURUSD"]), key="multi_symbol")
    
    if st.button("Çoklu Grafikler Oluştur"):
        with st.spinner("Grafikler hazırlanıyor..."):
            chart_module = st.session_state.chart_module
            
            # Çoklu zaman dilimi grafikleri
            timeframes = ["M15", "H1", "H4", "D1"]
            charts = chart_module.create_multi_timeframe_chart(multi_symbol, timeframes)
            
            if charts:
                # Grafikleri göster
                for tf, fig in charts.items():
                    st.subheader(f"{multi_symbol} - {tf}")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"{multi_symbol} için çoklu zaman dilimi grafikleri oluşturulamadı.")
    
    # Karşılaştırma grafiği
    st.markdown("---")
    st.subheader("Sembol Karşılaştırma Grafiği")
    
    compare_symbols = st.multiselect(
        "Karşılaştırılacak Semboller:",
        bot.settings.get("symbols", ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]),
        default=bot.settings.get("symbols", ["EURUSD", "GBPUSD"])[:2]
    )
    
    compare_timeframe = st.selectbox(
        "Zaman Dilimi:", 
        ["H1", "H4", "D1"], 
        index=0,
        key="compare_timeframe"
    )
    
    if st.button("Karşılaştırma Grafiği Oluştur"):
        if len(compare_symbols) >= 2:
            with st.spinner("Karşılaştırma grafiği hazırlanıyor..."):
                chart_module = st.session_state.chart_module
                
                # Karşılaştırma grafiği
                fig = chart_module.create_comparison_chart(
                    compare_symbols,
                    compare_timeframe
                )
                
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Karşılaştırma grafiği oluşturulamadı.")
        else:
            st.warning("Karşılaştırma için en az 2 sembol seçmelisiniz.")

def show_signal_monitor(bot):
    """
    Sinyal izleme sayfasını göster
    
    Args:
        bot: ForexTradingBot örneği
    """
    st.header("Sinyal İzleme")
    
    # Manuel sinyal oluşturma
    with st.expander("Manuel Sinyal Analizi", expanded=False):
        st.subheader("Manuel Sinyal Analizi")
        
        # Sembol seçimi
        col1, col2 = st.columns(2)
        
        with col1:
            selected_symbol = st.selectbox("Sembol:", bot.settings.get("symbols", ["EURUSD"]))
        
        with col2:
            timeframe_options = ["M15", "H1", "H4", "D1"]
            selected_timeframes = st.multiselect(
                "Zaman Dilimleri:",
                timeframe_options,
                default=["H1", "H4"]
            )
        
        if st.button("Analiz Et"):
            if not selected_timeframes:
                st.warning("En az bir zaman dilimi seçin.")
            else:
                with st.spinner("Analiz yapılıyor..."):
                    try:
                        # Analiz yap
                        analysis_results = bot.analysis_engine.analyze(selected_symbol, selected_timeframes)
                        
                        # AI tahmin yap
                        prediction_results = bot.ai_predictor.predict(selected_symbol)
                        
                        # Sinyal oluştur
                        signal = bot.signal_generator.generate_signal(
                            selected_symbol,
                            analysis_results,
                            prediction_results
                        )
                        
                        if signal:
                            # Sinyal detaylarını göster
                            st.success("Sinyal başarıyla oluşturuldu!")
                            
                            # Sinyal detayları
                            signal_type = signal.get("signal", "neutral")
                            signal_color = "green" if signal_type == "buy" else "red" if signal_type == "sell" else "gray"
                            
                            st.markdown(f"<div style='padding: 15px; background-color: {signal_color}; "
                                      f"color: white; border-radius: 5px; margin-bottom: 20px;'>"
                                      f"<h3 style='margin: 0;'>{selected_symbol}: {signal_type.upper()}</h3>"
                                      f"</div>", unsafe_allow_html=True)
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Giriş Fiyatı", f"{signal.get('entry_price', 0):.5f}")
                            
                            with col2:
                                st.metric("Stop Loss", f"{signal.get('stop_loss', 0):.5f}")
                            
                            with col3:
                                st.metric("Take Profit", f"{signal.get('take_profit', 0):.5f}")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Başarı Olasılığı", f"{signal.get('success_probability', 0):.1f}%")
                            
                            with col2:
                                st.metric("Risk/Ödül", f"{signal.get('risk_reward', 0):.2f}")
                            
                            with col3:
                                st.metric("Sinyal Gücü", f"{signal.get('strength', 0):.1f}%")
                            
                            # Risk hesapla
                            risk_params = bot.risk_manager.calculate_risk_params(signal)
                            
                            st.markdown("---")
                            st.subheader("Risk Parametreleri")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Lot", f"{risk_params.get('lot_size', 0.01):.2f}")
                            
                            with col2:
                                st.metric("Risk Tutarı", f"{risk_params.get('risk_amount', 0):.2f}")
                            
                            with col3:
                                st.metric("Risk Yüzdesi", f"{risk_params.get('risk_percent', 0):.2f}%")
                            
                            with col4:
                                st.metric("SL Mesafesi", f"{risk_params.get('sl_pips', 0)} pip")
                            
                            # Grafik göster
                            st.markdown("---")
                            st.subheader("Analiz Grafiği")
                            
                            chart_module = st.session_state.chart_module
                            fig = chart_module.create_analysis_chart(
                                selected_symbol,
                                "H1",
                                analysis_results["timeframes"]["H1"]["summary"] if "H1" in analysis_results["timeframes"] else {}
                            )
                            
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # İşlem onayı
                            st.markdown("---")
                            
                            if st.button("İşlemi Onayla"):
                                # Pozisyon açılabilir mi kontrol et
                                can_open, reason = bot.risk_manager.can_open_position(signal)
                                
                                if can_open:
                                    with st.spinner("İşlem açılıyor..."):
                                        # İşlemi aç
                                        result = bot.broker.open_position(
                                            symbol=signal.get("symbol"),
                                            order_type=signal.get("signal"),
                                            volume=risk_params.get("lot_size", 0.01),
                                            stop_loss=signal.get("stop_loss"),
                                            take_profit=signal.get("take_profit"),
                                            comment="Manuel sinyal"
                                        )
                                        
                                        if "error" in result:
                                            st.error(f"İşlem açılamadı: {result['error']}")
                                        else:
                                            st.success(f"İşlem başarıyla açıldı! Ticket: {result.get('ticket')}")
                                            
                                            # Sinyali güncelle
                                            bot.signal_generator.update_signal_status(
                                                signal.get("id"),
                                                "executed",
                                                execution_details=result
                                            )
                                            
                                            # Risk geçmişini güncelle
                                            trade_data = {
                                                "symbol": signal.get("symbol"),
                                                "signal": signal.get("signal"),
                                                "lot_size": risk_params.get("lot_size", 0.01),
                                                "risk_amount": risk_params.get("risk_amount", 0)
                                            }
                                            bot.risk_manager.update_risk_history(trade_data)
                                            
                                            # Verileri yenile
                                            refresh_data(bot)
                                else:
                                    st.error(f"İşlem açılamıyor: {reason}")
                        else:
                            st.warning("Sinyal oluşturulamadı. Yetersiz analiz sonuçları veya nötr sinyal.")
                    except Exception as e:
                        st.error(f"Analiz sırasında hata: {str(e)}")
    
    # Sinyal geçmişi
    st.markdown("---")
    st.subheader("Sinyal Geçmişi")
    
    if "signals" in st.session_state and st.session_state.signals:
        # Tablo başlıkları
        columns = st.columns([1.5, 0.8, 1, 0.8, 0.8, 1, 1])
        columns[0].markdown("<strong>Sembol</strong>", unsafe_allow_html=True)
        columns[1].markdown("<strong>Sinyal</strong>", unsafe_allow_html=True)
        columns[2].markdown("<strong>Zaman</strong>", unsafe_allow_html=True)
        columns[3].markdown("<strong>Giriş</strong>", unsafe_allow_html=True)
        columns[4].markdown("<strong>R/Ö</strong>", unsafe_allow_html=True)
        columns[5].markdown("<strong>Olasılık</strong>", unsafe_allow_html=True)
        columns[6].markdown("<strong>Durum</strong>", unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 5px 0; padding: 0;'>", unsafe_allow_html=True)
        
        # Sinyalleri listele
        for signal in st.session_state.signals:
            cols = st.columns([1.5, 0.8, 1, 0.8, 0.8, 1, 1])
            
            # Sinyal detayları
            symbol = signal.get("symbol", "")
            signal_type = signal.get("signal", "neutral")
            timestamp = signal.get("timestamp", datetime.now())
            entry_price = signal.get("entry_price", 0)
            risk_reward = signal.get("risk_reward", 0)
            probability = signal.get("success_probability", 0)
            status = signal.get("status", "pending")
            
            # Renkleri belirle
            signal_color = "green" if signal_type == "buy" else "red" if signal_type == "sell" else "gray"
            status_color = "green" if status == "executed" else "red" if status == "rejected" else "orange"
            
            # Sütunlara verileri ekle
            cols[0].write(symbol)
            cols[1].markdown(f"<span style='color: {signal_color}; font-weight: bold;'>{signal_type.upper()}</span>", unsafe_allow_html=True)
            cols[2].write(timestamp.strftime("%d.%m %H:%M"))
            cols[3].write(f"{entry_price:.5f}")
            cols[4].write(f"{risk_reward:.2f}")
            cols[5].write(f"{probability:.1f}%")
            cols[6].markdown(f"<span style='color: {status_color};'>{status.capitalize()}</span>", unsafe_allow_html=True)
            
            st.markdown("<hr style='margin: 5px 0; padding: 0;'>", unsafe_allow_html=True)
            
            # Sinyal detayları (tıklama ile açılan)
            with st.expander(f"Detaylar - {symbol} ({timestamp.strftime('%d.%m.%Y %H:%M')})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Sinyal Detayları**")
                    st.write(f"Stop Loss: {signal.get('stop_loss', 0):.5f}")
                    st.write(f"Take Profit: {signal.get('take_profit', 0):.5f}")
                    st.write(f"Sinyal Gücü: {signal.get('strength', 0):.1f}%")
                    st.write(f"Anahtar Zaman Dilimleri: {', '.join(signal.get('timeframes', []))}")
                
                with col2:
                    st.markdown("**İşlem Detayları**" if status == "executed" else "**Sinyal Durumu**")
                    
                    if status == "executed" and "execution_details" in signal:
                        execution = signal.get("execution_details", {})
                        st.write(f"Ticket: {execution.get('ticket', 'N/A')}")
                        st.write(f"İşlem Fiyatı: {execution.get('price', 0):.5f}")
                        st.write(f"Lot: {execution.get('volume', 0):.2f}")
                        st.write(f"İşlem Zamanı: {execution.get('time', 'N/A')}")
                    else:
                        st.write(f"Durum: {status.capitalize()}")
                        st.write(f"Oluşturulma: {timestamp.strftime('%d.%m.%Y %H:%M:%S')}")
    else:
        st.info("Henüz sinyal yok.")

def show_open_positions(bot):
    """
    Açık pozisyonlar sayfasını göster
    
    Args:
        bot: ForexTradingBot örneği
    """
    st.header("Açık Pozisyonlar")
    
    # Pozisyonları yenile
    if st.button("Pozisyonları Yenile"):
        with st.spinner("Pozisyonlar yenileniyor..."):
            refresh_data(bot)
            st.success("Pozisyonlar yenilendi!")
    
    # Açık pozisyonları göster
    if "open_positions" in st.session_state and st.session_state.open_positions:
        # Tablo başlıkları
        columns = st.columns([1.5, 0.8, 1, 0.8, 0.8, 0.8, 0.8, 1])
        columns[0].markdown("<strong>Sembol</strong>", unsafe_allow_html=True)
        columns[1].markdown("<strong>Yön</strong>", unsafe_allow_html=True)
        columns[2].markdown("<strong>Lot</strong>", unsafe_allow_html=True)
        columns[3].markdown("<strong>Açılış</strong>", unsafe_allow_html=True)
        columns[4].markdown("<strong>SL</strong>", unsafe_allow_html=True)
        columns[5].markdown("<strong>TP</strong>", unsafe_allow_html=True)
        columns[6].markdown("<strong>Kar/Zarar</strong>", unsafe_allow_html=True)
        columns[7].markdown("<strong>İşlemler</strong>", unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 5px 0; padding: 0;'>", unsafe_allow_html=True)
        
        # Pozisyonları listele
        for position in st.session_state.open_positions:
            position_id = st.container()
            
            with position_id:
                cols = st.columns([1.5, 0.8, 1, 0.8, 0.8, 0.8, 0.8, 1])
                
                # Pozisyon detayları
                symbol = position.get("symbol", "")
                direction = position.get("direction", "")
                volume = position.get("volume", 0)
                open_price = position.get("price_open", 0)
                sl = position.get("sl", 0)
                tp = position.get("tp", 0)
                profit = position.get("profit", 0)
                ticket = position.get("ticket", 0)
                
                # Renkleri belirle
                direction_color = "green" if direction == "BUY" else "red"
                profit_color = "green" if profit > 0 else "red" if profit < 0 else "gray"
                
                # Sütunlara verileri ekle
                cols[0].write(symbol)
                cols[1].markdown(f"<span style='color: {direction_color}; font-weight: bold;'>{direction}</span>", unsafe_allow_html=True)
                cols[2].write(f"{volume:.2f}")
                cols[3].write(f"{open_price:.5f}")
                cols[4].write(f"{sl:.5f}" if sl > 0 else "---")
                cols[5].write(f"{tp:.5f}" if tp > 0 else "---")
                cols[6].markdown(f"<span style='color: {profit_color}; font-weight: bold;'>{profit:.2f}</span>", unsafe_allow_html=True)
                
                # İşlem butonları
                close_button = cols[7].button("Kapat", key=f"close_{ticket}")
                
                if close_button:
                    with st.spinner(f"Pozisyon kapatılıyor ({ticket})..."):
                        result = bot.broker.close_position(ticket)
                        
                        if "error" in result:
                            st.error(f"Pozisyon kapatılamadı: {result['error']}")
                        else:
                            st.success(f"Pozisyon başarıyla kapatıldı! Kar/Zarar: {result.get('profit', 0):.2f}")
                            
                            # Pozisyonları yenile
                            refresh_data(bot)
                
                st.markdown("<hr style='margin: 5px 0; padding: 0;'>", unsafe_allow_html=True)
                
                # Pozisyon detayları (tıklama ile açılan)
                with st.expander(f"Detaylar - {symbol} (Ticket: {ticket})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Pozisyon Detayları**")
                        st.write(f"Ticket: {ticket}")
                        st.write(f"Açılış Zamanı: {pd.to_datetime(position.get('time')).strftime('%d.%m.%Y %H:%M:%S')}")
                        st.write(f"Komisyon: {position.get('commission', 0):.2f}")
                        st.write(f"Swap: {position.get('swap', 0):.2f}")
                    
                    with col2:
                        st.markdown("**Pozisyon Değiştir**")
                        
                        # SL/TP değiştirme formu
                        new_sl = st.number_input("Yeni Stop Loss:", value=float(sl) if sl > 0 else 0.0, format="%.5f", key=f"sl_{ticket}")
                        new_tp = st.number_input("Yeni Take Profit:", value=float(tp) if tp > 0 else 0.0, format="%.5f", key=f"tp_{ticket}")
                        
                        if st.button("Değişiklikleri Uygula", key=f"modify_{ticket}"):
                            with st.spinner("Pozisyon değiştiriliyor..."):
                                result = bot.broker.modify_position(ticket, new_sl, new_tp)
                                
                                if "error" in result:
                                    st.error(f"Pozisyon değiştirilemedi: {result['error']}")
                                else:
                                    st.success("Pozisyon başarıyla değiştirildi!")
                                    
                                    # Pozisyonları yenile
                                    refresh_data(bot)
    else:
        st.info("Açık pozisyon yok.")
    
    # İşlem limitleri
    st.markdown("---")
    st.subheader("İşlem Limitleri")
    
    # Pozisyon limitlerini kontrol et
    limits = bot.risk_manager.check_position_limits()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Toplam açık pozisyon sayısı
        max_positions = limits.get("max_positions", 0)
        current_positions = limits.get("current_open_positions", 0)
        
        st.markdown(f"**Açık Pozisyonlar:** {current_positions} / {max_positions}")
        st.progress(min(current_positions / max_positions, 1.0) if max_positions > 0 else 0.0)
    
    with col2:
        # Risk durumu
        risk_summary = bot.risk_manager.get_risk_summary()
        
        daily_risk = risk_summary.get("daily_risk", 0)
        max_daily_risk = risk_summary.get("max_daily_risk", 5)
        
        st.markdown(f"**Günlük Risk:** {daily_risk:.2f}% / {max_daily_risk:.2f}%")
        st.progress(min(daily_risk / max_daily_risk, 1.0) if max_daily_risk > 0 else 0.0)
    
    with col3:
        # Sembol başına pozisyon sayısı
        positions_per_symbol = limits.get("positions_per_symbol", {})
        max_per_symbol = limits.get("max_positions_per_symbol", 0)
        
        if positions_per_symbol:
            highest_symbol = max(positions_per_symbol, key=positions_per_symbol.get)
            highest_count = positions_per_symbol[highest_symbol]
            
            st.markdown(f"**En çok: {highest_symbol}** {highest_count} / {max_per_symbol}")
            st.progress(min(highest_count / max_per_symbol, 1.0) if max_per_symbol > 0 else 0.0)
        else:
            st.markdown(f"**Sembol Başına Pozisyon:** 0 / {max_per_symbol}")
            st.progress(0.0)
    
    # Hesap özeti
    st.markdown("---")
    st.subheader("Hesap Özeti")
    
    account_info = bot.broker.get_account_info()
    
    if account_info:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Bakiye", f"{account_info.get('balance', 0):.2f} {account_info.get('currency', 'USD')}")
        
        with col2:
            equity = account_info.get('equity', 0)
            balance = account_info.get('balance', 0)
            profit_loss = equity - balance
            
            st.metric("Varlık", f"{equity:.2f}", f"{profit_loss:+.2f}")
        
        with col3:
            st.metric("Serbest Marjin", f"{account_info.get('free_margin', 0):.2f}")
        
        with col4:
            st.metric("Marjin Seviyesi", f"{account_info.get('margin_level', 0):.2f}%")
    else:
        st.warning("Hesap bilgileri alınamıyor!")

def show_mt5_settings(bot):
    """
    MT5 ayarları sayfasını göster
    
    Args:
        bot: ForexTradingBot örneği
    """
    st.header("MetaTrader 5 Ayarları")
    
    # MT5 bağlantı durumu
    mt5_connected = bot.broker.connected
    mt5_status = "Bağlı" if mt5_connected else "Bağlı Değil"
    mt5_color = "success-box" if mt5_connected else "error-box"
    
    st.markdown(f"<div class='{mt5_color}'>MT5 Durumu: {mt5_status}</div>", unsafe_allow_html=True)
    
    # MT5 ayarları formu
    with st.form("mt5_settings_form"):
        st.subheader("MT5 Bağlantı Ayarları")
        
        # Mevcut ayarları al
        mt5_settings = bot.settings.get("mt5", {})
        mt5_credentials = bot.settings.api_keys.get("mt5", {})
        
        # MT5 yolu
        mt5_path = st.text_input(
            "MT5 Yolu:",
            value=mt5_settings.get("path", "C:/Program Files/MetaTrader 5/terminal64.exe")
        )
        
        # Hesap bilgileri
        col1, col2, col3 = st.columns(3)
        
        with col1:
            mt5_login = st.text_input("Hesap Numarası:", value=mt5_credentials.get("login", ""))
        
        with col2:
            mt5_password = st.text_input("Şifre:", type="password", value=mt5_credentials.get("password", ""))
        
        with col3:
            mt5_server = st.text_input("Sunucu:", value=mt5_credentials.get("server", ""))
        
        # Bağlantı zaman aşımı
        mt5_timeout = st.number_input(
            "Bağlantı Zaman Aşımı (ms):",
            min_value=1000,
            max_value=60000,
            value=mt5_settings.get("timeout", 60000),
            step=1000
        )
        
        # Gerçek işlem izni
        mt5_real_trading = st.checkbox(
            "Gerçek Hesapta İşlem İzni",
            value=mt5_settings.get("enable_real_trading", False)
        )
        
        if not mt5_real_trading:
            st.markdown(
                "<div class='warning-box'>Bu seçenek devre dışı bırakıldığında, "
                "bot gerçek hesaplarda işlem yapmayacaktır.</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div class='warning-box'><strong>DİKKAT:</strong> Bu seçenek etkinleştirildiğinde, "
                "bot gerçek hesabınızda işlem yapabilir!</div>",
                unsafe_allow_html=True
            )
        
        # Bağlan/Bağlantıyı Kes butonları
        col1, col2 = st.columns(2)
        
        with col1:
            connect_button = st.form_submit_button("Bağlan")
        
        with col2:
            disconnect_button = st.form_submit_button("Bağlantıyı Kes")
    
    # Form işlemleri
    if connect_button:
        with st.spinner("MT5'e bağlanılıyor..."):
            # Ayarları güncelle
            bot.settings.set_setting("mt5.path", mt5_path)
            bot.settings.set_setting("mt5.timeout", mt5_timeout)
            bot.settings.set_setting("mt5.enable_real_trading", mt5_real_trading)
            
            # API anahtarlarını güncelle
            bot.settings.set_api_key("mt5.login", mt5_login)
            bot.settings.set_api_key("mt5.password", mt5_password)
            bot.settings.set_api_key("mt5.server", mt5_server)
            
            # Bağlantıyı dene
            success = bot.broker.connect()
            
            if success:
                st.success("MT5'e başarıyla bağlandı!")
                # Sayfayı yenile
                st.experimental_rerun()
            else:
                st.error("MT5 bağlantısı başarısız. Ayarları kontrol edin.")
    
    if disconnect_button:
        with st.spinner("MT5 bağlantısı kesiliyor..."):
            success = bot.broker.disconnect()
            
            if success:
                st.success("MT5 bağlantısı kesildi!")
                # Sayfayı yenile
                st.experimental_rerun()
            else:
                st.error("MT5 bağlantısını kesme başarısız.")
    
    # Semboller ve özellikleri
    st.markdown("---")
    st.subheader("Sembol Ayarları")
    
    # Sembol ayarları formu
    with st.form("symbol_settings_form"):
        # Mevcut semboller
        current_symbols = bot.settings.get("symbols", ["EURUSD", "GBPUSD", "XAUUSD"])
        symbols_str = ", ".join(current_symbols)
        
        new_symbols = st.text_input(
            "İşlem Sembolleri (virgülle ayrılmış):",
            value=symbols_str
        )
        
        # Kaydet butonu
        save_symbols = st.form_submit_button("Sembolleri Kaydet")
    
    # Sembol ayarlarını kaydet
    if save_symbols:
        try:
            # Sembolleri ayır ve temizle
            symbols_list = [s.strip() for s in new_symbols.split(",") if s.strip()]
            
            if not symbols_list:
                st.error("En az bir sembol belirtmelisiniz!")
            else:
                # Sembolleri güncelle
                bot.settings.set_setting("symbols", symbols_list)
                st.success("Semboller başarıyla güncellendi!")
        except Exception as e:
            st.error(f"Semboller güncellenirken hata: {str(e)}")
    
    # Sembol bilgilerini göster
    if mt5_connected:
        try:
            # Sembol bilgilerini al
            symbols_info = bot.broker.get_symbols_info()
            
            if not symbols_info.empty:
                # Mevcut sembolleri filtrele
                current_symbols = bot.settings.get("symbols", [])
                filtered_info = symbols_info[symbols_info['name'].isin(current_symbols)]
                
                if not filtered_info.empty:
                    st.markdown("---")
                    st.subheader("Aktif Semboller")
                    
                    # Tablo olarak göster
                    st.dataframe(
                        filtered_info[['name', 'description', 'digits', 'trade_mode', 'volume_min', 'volume_max']],
                        use_container_width=True
                    )
        except Exception as e:
            st.error(f"Sembol bilgileri alınırken hata: {str(e)}")
    
    # Son işlemler
    st.markdown("---")
    st.subheader("Son İşlemler")
    
    if mt5_connected:
        try:
            # Son işlemleri al
            trade_history = bot.broker.get_trade_history()
            
            if not trade_history.empty:
                # Son 10 işlemi göster
                st.dataframe(
                    trade_history.tail(10)[['time', 'symbol', 'direction', 'volume', 'price', 'profit']],
                    use_container_width=True
                )
            else:
                st.info("Henüz işlem geçmişi yok.")
        except Exception as e:
            st.error(f"İşlem geçmişi alınırken hata: {str(e)}")

def show_bot_settings(bot):
    """
    Bot ayarları sayfasını göster
    
    Args:
        bot: ForexTradingBot örneği
    """
    st.header("Bot Ayarları")
    
    # Ayarlar tabları
    tab1, tab2, tab3, tab4 = st.tabs(["Genel Ayarlar", "Sinyal Ayarları", "Risk Ayarları", "Telegram Ayarları"])
    
    with tab1:
        st.subheader("Genel Bot Ayarları")
        
        # Genel ayarlar formu
        with st.form("general_settings_form"):
            # Mevcut ayarları al
            timezone = bot.settings.get("timezone", "Europe/Istanbul")
            scan_interval = bot.settings.get("scan_interval", 60)
            auto_trade_enabled = bot.settings.get("auto_trade_enabled", False)
            auto_trade_threshold = bot.settings.get("auto_trade_threshold", 70)
            news_scanner_enabled = bot.settings.get("news_scanner_enabled", True)
            
            # Zaman dilimi
            timezone_options = [
                "Europe/Istanbul", "Europe/London", "America/New_York", 
                "Asia/Tokyo", "Australia/Sydney", "UTC"
            ]
            timezone = st.selectbox("Zaman Dilimi:", timezone_options, index=timezone_options.index(timezone))
            
            # Tarama aralığı
            scan_interval = st.slider(
                "Tarama Aralığı (saniye):",
                min_value=30,
                max_value=300,
                value=scan_interval,
                step=10
            )
            
            # Otomatik işlem modu
            auto_trade_enabled = st.checkbox("Otomatik İşlem Modu", value=auto_trade_enabled)
            
            # Otomatik işlem eşiği
            auto_trade_threshold = st.slider(
                "Otomatik İşlem için Minimum Başarı Olasılığı (%):",
                min_value=50,
                max_value=95,
                value=auto_trade_threshold,
                step=5
            )
            
            # Haber tarayıcı
            news_scanner_enabled = st.checkbox("Haber Tarayıcı", value=news_scanner_enabled)
            
            # Zaman dilimleri
            timeframe_options = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"]
            current_timeframes = bot.settings.get("timeframes", ["M5", "M15", "H1", "H4", "D1"])
            
            selected_timeframes = st.multiselect(
                "Kullanılacak Zaman Dilimleri:",
                timeframe_options,
                default=current_timeframes
            )
            
            # Kaydet butonu
            save_general = st.form_submit_button("Genel Ayarları Kaydet")
        
        # Genel ayarları kaydet
        if save_general:
            with st.spinner("Ayarlar kaydediliyor..."):
                try:
                    # Ayarları güncelle
                    bot.settings.set_setting("timezone", timezone)
                    bot.settings.set_setting("scan_interval", scan_interval)
                    bot.settings.set_setting("auto_trade_enabled", auto_trade_enabled)
                    bot.settings.set_setting("auto_trade_threshold", auto_trade_threshold)
                    bot.settings.set_setting("news_scanner_enabled", news_scanner_enabled)
                    
                    if selected_timeframes:
                        bot.settings.set_setting("timeframes", selected_timeframes)
                    
                    st.success("Genel ayarlar başarıyla kaydedildi!")
                except Exception as e:
                    st.error(f"Ayarlar kaydedilirken hata: {str(e)}")
    
    with tab2:
        st.subheader("Sinyal Ayarları")
        
        # Sinyal ayarları formu
        with st.form("signal_settings_form"):
            # Mevcut ayarları al
            signal_settings = bot.settings.get("signal", {})
            
            min_probability = signal_settings.get("min_probability", 60)
            auto_trade_threshold = signal_settings.get("auto_trade_threshold", 70)
            min_risk_reward = signal_settings.get("min_risk_reward", 1.5)
            confirmation_timeout = signal_settings.get("confirmation_timeout", 300)
            max_signals_per_day = signal_settings.get("max_signals_per_day", 10)
            
            # Minimum başarı olasılığı
            min_probability = st.slider(
                "Minimum Başarı Olasılığı (%):",
                min_value=30,
                max_value=90,
                value=min_probability,
                step=5
            )
            
            # Otomatik işlem eşiği
            auto_trade_threshold = st.slider(
                "Otomatik İşlem Eşiği (%):",
                min_value=50,
                max_value=95,
                value=auto_trade_threshold,
                step=5
            )
            
            # Minimum risk/ödül oranı
            min_risk_reward = st.slider(
                "Minimum Risk/Ödül Oranı:",
                min_value=1.0,
                max_value=3.0,
                value=min_risk_reward,
                step=0.1
            )
            
            # Onay zaman aşımı
            confirmation_timeout = st.slider(
                "Onay Zaman Aşımı (saniye):",
                min_value=60,
                max_value=600,
                value=confirmation_timeout,
                step=30
            )
            
            # Günlük maksimum sinyal
            max_signals_per_day = st.slider(
                "Günlük Maksimum Sinyal Sayısı:",
                min_value=1,
                max_value=20,
                value=max_signals_per_day,
                step=1
            )
            
            # Analiz stratejileri
            st.subheader("Analiz Stratejileri")
            
            # ICT stratejisi
            ict_enabled = st.checkbox(
                "ICT Stratejisi",
                value=bot.settings.get("analysis", {}).get("ict", {}).get("enabled", True)
            )
            
            # SMC stratejisi
            smc_enabled = st.checkbox(
                "SMC Stratejisi",
                value=bot.settings.get("analysis", {}).get("smc", {}).get("enabled", True)
            )
            
            # Price Action stratejisi
            pa_enabled = st.checkbox(
                "Price Action Stratejisi",
                value=bot.settings.get("analysis", {}).get("price_action", {}).get("enabled", True)
            )
            
            # Kaydet butonu
            save_signal = st.form_submit_button("Sinyal Ayarlarını Kaydet")
        
        # Sinyal ayarlarını kaydet
        if save_signal:
            with st.spinner("Ayarlar kaydediliyor..."):
                try:
                    # Sinyal ayarlarını güncelle
                    signal_settings = {
                        "min_probability": min_probability,
                        "auto_trade_threshold": auto_trade_threshold,
                        "min_risk_reward": min_risk_reward,
                        "confirmation_timeout": confirmation_timeout,
                        "max_signals_per_day": max_signals_per_day
                    }
                    
                    bot.settings.set_setting("signal", signal_settings)
                    
                    # Analiz stratejilerini güncelle
                    bot.settings.set_setting("analysis.ict.enabled", ict_enabled)
                    bot.settings.set_setting("analysis.smc.enabled", smc_enabled)
                    bot.settings.set_setting("analysis.price_action.enabled", pa_enabled)
                    
                    st.success("Sinyal ayarları başarıyla kaydedildi!")
                except Exception as e:
                    st.error(f"Ayarlar kaydedilirken hata: {str(e)}")
    
    with tab3:
        st.subheader("Risk Yönetim Ayarları")
        
        # Risk ayarları formu
        with st.form("risk_settings_form"):
            # Mevcut ayarları al
            risk_settings = bot.settings.get("risk_management", {})
            
            max_risk_percent = risk_settings.get("max_risk_percent", 2.0)
            max_daily_risk_percent = risk_settings.get("max_daily_risk_percent", 5.0)
            max_weekly_risk_percent = risk_settings.get("max_weekly_risk_percent", 10.0)
            max_open_positions = risk_settings.get("max_open_positions", 5)
            max_positions_per_symbol = risk_settings.get("max_positions_per_symbol", 2)
            default_stop_loss_pips = risk_settings.get("default_stop_loss_pips", 50)
            default_take_profit_pips = risk_settings.get("default_take_profit_pips", 100)
            max_lot_size = risk_settings.get("max_lot_size", 1.0)
            
            # İşlem başına maksimum risk
            max_risk_percent = st.slider(
                "İşlem Başına Maksimum Risk (%):",
                min_value=0.1,
                max_value=5.0,
                value=max_risk_percent,
                step=0.1
            )
            
            # Günlük maksimum risk
            max_daily_risk_percent = st.slider(
                "Günlük Maksimum Risk (%):",
                min_value=1.0,
                max_value=20.0,
                value=max_daily_risk_percent,
                step=0.5
            )
            
            # Haftalık maksimum risk
            max_weekly_risk_percent = st.slider(
                "Haftalık Maksimum Risk (%):",
                min_value=2.0,
                max_value=30.0,
                value=max_weekly_risk_percent,
                step=1.0
            )
            
            # Maksimum açık pozisyon sayısı
            max_open_positions = st.slider(
                "Maksimum Açık Pozisyon Sayısı:",
                min_value=1,
                max_value=20,
                value=max_open_positions,
                step=1
            )
            
            # Sembol başına maksimum pozisyon
            max_positions_per_symbol = st.slider(
                "Sembol Başına Maksimum Pozisyon:",
                min_value=1,
                max_value=5,
                value=max_positions_per_symbol,
                step=1
            )
            
            # Varsayılan SL/TP
            col1, col2 = st.columns(2)
            
            with col1:
                default_stop_loss_pips = st.number_input(
                    "Varsayılan Stop Loss (pip):",
                    min_value=10,
                    max_value=200,
                    value=default_stop_loss_pips,
                    step=5
                )
            
            with col2:
                default_take_profit_pips = st.number_input(
                    "Varsayılan Take Profit (pip):",
                    min_value=20,
                    max_value=400,
                    value=default_take_profit_pips,
                    step=10
                )
            
            # Maksimum lot büyüklüğü
            max_lot_size = st.number_input(
                "Maksimum Lot Büyüklüğü:",
                min_value=0.01,
                max_value=10.0,
                value=max_lot_size,
                step=0.01
            )
            
            # Kaydet butonu
            save_risk = st.form_submit_button("Risk Ayarlarını Kaydet")
        
        # Risk ayarlarını kaydet
        if save_risk:
            with st.spinner("Ayarlar kaydediliyor..."):
                try:
                    # Risk ayarlarını güncelle
                    risk_settings = {
                        "max_risk_percent": max_risk_percent,
                        "max_daily_risk_percent": max_daily_risk_percent,
                        "max_weekly_risk_percent": max_weekly_risk_percent,
                        "max_open_positions": max_open_positions,
                        "max_positions_per_symbol": max_positions_per_symbol,
                        "default_stop_loss_pips": default_stop_loss_pips,
                        "default_take_profit_pips": default_take_profit_pips,
                        "max_lot_size": max_lot_size
                    }
                    
                    bot.settings.set_setting("risk_management", risk_settings)
                    
                    st.success("Risk ayarları başarıyla kaydedildi!")
                except Exception as e:
                    st.error(f"Ayarlar kaydedilirken hata: {str(e)}")
    
    with tab4:
        st.subheader("Telegram Ayarları")
        
        # Telegram ayarları formu
        with st.form("telegram_settings_form"):
            # Mevcut ayarları al
            telegram_settings = bot.settings.get("telegram", {})
            telegram_credentials = bot.settings.api_keys.get("telegram", {})
            
            telegram_enabled = telegram_settings.get("enabled", False)
            bot_token = telegram_credentials.get("bot_token", "")
            chat_id = telegram_credentials.get("chat_id", "")
            
            # Telegram bot aktif
            telegram_enabled = st.checkbox("Telegram Bot Aktif", value=telegram_enabled)
            
            # Bot token
            bot_token = st.text_input("Bot Token:", value=bot_token)
            
            # Chat ID
            chat_id = st.text_input("Chat ID:", value=chat_id)
            
            st.markdown(
                "<div class='info-box'>Telegram bot oluşturmak için BotFather'ı kullanın. "
                "Chat ID'nizi öğrenmek için bot ile sohbet başlatın ve "
                "'getUpdates' API'sini kullanın.</div>",
                unsafe_allow_html=True
            )
            
            # Onay ayarları
            confirmation_required = telegram_settings.get("confirmation_required", True)
            confirmation_timeout = telegram_settings.get("confirmation_timeout", 300)
            
            confirmation_required = st.checkbox("İşlem Onayı Gerekli", value=confirmation_required)
            
            confirmation_timeout = st.slider(
                "Onay Zaman Aşımı (saniye):",
                min_value=60,
                max_value=600,
                value=confirmation_timeout,
                step=30
            )
            
            # Kaydet butonu
            save_telegram = st.form_submit_button("Telegram Ayarlarını Kaydet")
        
        # Telegram ayarlarını kaydet
        if save_telegram:
            with st.spinner("Ayarlar kaydediliyor..."):
                try:
                    # Telegram ayarlarını güncelle
                    bot.settings.set_setting("telegram.enabled", telegram_enabled)
                    bot.settings.set_setting("telegram.confirmation_required", confirmation_required)
                    bot.settings.set_setting("telegram.confirmation_timeout", confirmation_timeout)
                    
                    # API anahtarlarını güncelle
                    bot.settings.set_api_key("telegram.bot_token", bot_token)
                    bot.settings.set_api_key("telegram.chat_id", chat_id)
                    
                    st.success("Telegram ayarları başarıyla kaydedildi!")
                    
                    # Telegram botunu yeniden başlat
                    if telegram_enabled:
                        # Bot çalışıyorsa Telegram botunu yeniden başlat
                        if st.session_state.bot_running:
                            bot.telegram_bot.stop()
                            bot.telegram_bot.start()
                except Exception as e:
                    st.error(f"Ayarlar kaydedilirken hata: {str(e)}")
    
    # Ayarları dışa/içe aktar
    st.markdown("---")
    st.subheader("Ayarları Dışa/İçe Aktar")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Ayarları dışa aktar
        if st.button("Ayarları Dışa Aktar"):
            with st.spinner("Ayarlar dışa aktarılıyor..."):
                try:
                    # Ayarları JSON'a dönüştür
                    settings_json = json.dumps(bot.settings.settings, indent=4)
                    
                    # İndirme butonu oluştur
                    st.download_button(
                        label="Ayarları İndir",
                        data=settings_json,
                        file_name="forex_bot_settings.json",
                        mime="application/json"
                    )
                except Exception as e:
                    st.error(f"Ayarlar dışa aktarılırken hata: {str(e)}")
    
    with col2:
        # Ayarları içe aktar
        uploaded_file = st.file_uploader("Ayarları İçe Aktar", type=["json"])
        
        if uploaded_file is not None:
            if st.button("Yüklenmiş Ayarları Uygula"):
                with st.spinner("Ayarlar içe aktarılıyor..."):
                    try:
                        # Dosyadan JSON oku
                        settings_json = json.load(uploaded_file)
                        
                        # Ayarları güncelle
                        bot.settings.settings = settings_json
                        bot.settings.save_settings()
                        
                        st.success("Ayarlar başarıyla içe aktarıldı!")
                    except Exception as e:
                        st.error(f"Ayarlar içe aktarılırken hata: {str(e)}")

def show_performance(bot):
    """
    Performans sayfasını göster
    
    Args:
        bot: ForexTradingBot örneği
    """
    st.header("Performans Analizi")
    
    # İşlem geçmişi
    try:
        # Son 7 günlük işlemleri al
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        trade_history = bot.broker.get_trade_history(start_date, end_date)
        
        if not trade_history.empty:
            # İşlem istatistiklerini hesapla
            total_trades = len(trade_history)
            winning_trades = len(trade_history[trade_history['profit'] > 0])
            losing_trades = len(trade_history[trade_history['profit'] < 0])
            
            total_profit = trade_history['profit'].sum()
            avg_profit = trade_history[trade_history['profit'] > 0]['profit'].mean() if winning_trades > 0 else 0
            avg_loss = trade_history[trade_history['profit'] < 0]['profit'].mean() if losing_trades > 0 else 0
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Metrikleri göster
            st.subheader("İşlem İstatistikleri (Son 7 Gün)")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Toplam İşlem", f"{total_trades}")
            
            with col2:
                st.metric("Kazanç Oranı", f"{win_rate:.1f}%")
            
            with col3:
                st.metric("Toplam Kar/Zarar", f"{total_profit:.2f}")
            
            with col4:
                st.metric("Ortalama Kar", f"{avg_profit:.2f}")
            
            # İşlem grafiği
            st.markdown("---")
            st.subheader("İşlem Geçmişi")
            
            # İşlemleri göster
            trade_history['time'] = pd.to_datetime(trade_history['time'])
            trade_history = trade_history.sort_values('time')
            
            # Kar/zarar grafiği
            fig = go.Figure()
            
            # Kümülatif kar/zarar
            cumulative_profit = trade_history['profit'].cumsum()
            
            fig.add_trace(
                go.Scatter(
                    x=trade_history['time'],
                    y=cumulative_profit,
                    mode='lines+markers',
                    name='Kümülatif Kar/Zarar',
                    line=dict(color='blue', width=2)
                )
            )
            
            # Grafik görünümünü ayarla
            fig.update_layout(
                title="Kümülatif Kar/Zarar",
                xaxis_title="Tarih",
                yaxis_title="Kar/Zarar",
                height=400,
                template='plotly_white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # İşlem tablosu
            st.subheader("Son İşlemler")
            
            # Tabloyu göster
            st.dataframe(
                trade_history[['time', 'symbol', 'direction', 'volume', 'price', 'profit']],
                use_container_width=True
            )
        else:
            st.info("Son 7 günde tamamlanan işlem yok.")
    except Exception as e:
        st.error(f"İşlem geçmişi alınırken hata: {str(e)}")
    
    # Sinyal performansı
    st.markdown("---")
    st.subheader("Sinyal Performansı")
    
    # Sinyal geçmişinden istatistikler
    signals = st.session_state.signals
    executed_signals = [s for s in signals if s.get("status") == "executed"]
    
    if executed_signals:
        total_signals = len(executed_signals)
        
        # Tamamlanan işlemleri bul
        completed_trades = []
        
        for signal in executed_signals:
            if "execution_details" in signal:
                ticket = signal["execution_details"].get("ticket")
                
                if ticket:
                    # İşlemi ara
                    trade = None
                    
                    if not trade_history.empty:
                        trades = trade_history[trade_history['ticket'] == ticket]
                        if not trades.empty:
                            trade = trades.iloc[0]
                    
                    if trade is not None:
                        completed_trades.append({
                            "signal": signal,
                            "trade": trade,
                            "profit": trade['profit']
                        })
        
        if completed_trades:
            # İstatistikler
            winning_signals = sum(1 for t in completed_trades if t["profit"] > 0)
            signal_win_rate = (winning_signals / len(completed_trades) * 100)
            
            st.markdown(f"**Sinyal Doğruluk Oranı:** {signal_win_rate:.1f}%")
            
            # Tahmin edilen başarı olasılıklarına göre gerçek sonuçlar
            st.markdown("**Tahmin vs Gerçek Sonuçlar**")
            
            prob_ranges = {
                "50-60": {"count": 0, "wins": 0},
                "60-70": {"count": 0, "wins": 0},
                "70-80": {"count": 0, "wins": 0},
                "80-90": {"count": 0, "wins": 0},
                "90-100": {"count": 0, "wins": 0}
            }
            
            for trade in completed_trades:
                signal = trade["signal"]
                probability = signal.get("success_probability", 0)
                won = trade["profit"] > 0
                
                # Olasılık aralığını belirle
                for prob_range, data in prob_ranges.items():
                    min_prob, max_prob = map(int, prob_range.split("-"))
                    
                    if min_prob <= probability < max_prob:
                        data["count"] += 1
                        if won:
                            data["wins"] += 1
                        break
            
            # Tablo olarak göster
            prob_data = []
            for prob_range, data in prob_ranges.items():
                if data["count"] > 0:
                    win_rate = (data["wins"] / data["count"]) * 100
                    prob_data.append({
                        "Olasılık Aralığı": prob_range,
                        "İşlem Sayısı": data["count"],
                        "Kazanan İşlem": data["wins"],
                        "Başarı Oranı": f"{win_rate:.1f}%"
                    })
            
            if prob_data:
                st.table(pd.DataFrame(prob_data))
        else:
            st.info("Tamamlanmış sinyal işlemi bulunamadı.")
    else:
        st.info("Henüz işleme alınan sinyal yok.")
    
    # Risk geçmişi
    st.markdown("---")
    st.subheader("Risk Kullanımı")
    
    risk_history = bot.risk_manager.get_risk_history(7)
    
    if risk_history:
        # Risk verilerini hazırla
        risk_df = pd.DataFrame(risk_history)
        risk_df['timestamp'] = pd.to_datetime(risk_df['timestamp'])
        risk_df = risk_df.sort_values('timestamp')
        
        # Günlük toplam risk
        daily_risk = risk_df.groupby(risk_df['timestamp'].dt.date)['risk_percent'].sum().reset_index()
        daily_risk.columns = ['date', 'total_risk']
        
        # Risk grafiği
        fig = go.Figure()
        
        fig.add_trace(
            go.Bar(
                x=daily_risk['date'],
                y=daily_risk['total_risk'],
                name='Günlük Toplam Risk (%)',
                marker_color='blue'
            )
        )
        
        # Maksimum günlük risk çizgisi
        max_daily_risk = bot.settings.get("risk_management", {}).get("max_daily_risk_percent", 5.0)
        
        fig.add_trace(
            go.Scatter(
                x=daily_risk['date'],
                y=[max_daily_risk] * len(daily_risk),
                name='Maksimum Günlük Risk',
                line=dict(color='red', width=2, dash='dash')
            )
        )
        
        # Grafik görünümünü ayarla
        fig.update_layout(
            title="Günlük Risk Kullanımı",
            xaxis_title="Tarih",
            yaxis_title="Risk Yüzdesi (%)",
            height=400,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Risk geçmişi verisi bulunamadı.")

def show_api_management(bot):
    """
    API yönetimi sayfasını göster
    
    Args:
        bot: ForexTradingBot örneği
    """
    st.header("API Yönetimi")
    
    # Api ayarları tabları
    tab1, tab2, tab3 = st.tabs(["Haber Kaynakları", "Sosyal Medya", "Diğer API'ler"])
    
    with tab1:
        st.subheader("Haber Kaynakları API Ayarları")
        
        # Forex Factory
        with st.expander("Forex Factory", expanded=True):
            st.markdown(
                "Forex Factory için API anahtarı gerekmez. "
                "Ancak web sitesinden veri çekilirken sınırlamalar olabilir."
            )
            
            # Forex Factory aktif
            forex_factory_enabled = st.checkbox(
                "Forex Factory Aktif",
                value=bot.settings.get("news_sources", {}).get("forex_factory", {}).get("enabled", True)
            )
            
            if st.button("Forex Factory Ayarlarını Kaydet"):
                try:
                    # Ayarları güncelle
                    bot.settings.set_setting("news_sources.forex_factory.enabled", forex_factory_enabled)
                    st.success("Forex Factory ayarları başarıyla kaydedildi!")
                except Exception as e:
                    st.error(f"Ayarlar kaydedilirken hata: {str(e)}")
        
        # Investing.com
        with st.expander("Investing.com", expanded=False):
            # Mevcut ayarları al
            investing_settings = bot.settings.get("news_sources", {}).get("investing_com", {})
            investing_credentials = bot.settings.api_keys.get("news_sources", {}).get("investing_com", {})
            
            # Investing.com aktif
            investing_enabled = st.checkbox(
                "Investing.com Aktif",
                value=investing_settings.get("enabled", True)
            )
            
            # Kullanıcı adı ve şifre
            investing_username = st.text_input(
                "Kullanıcı Adı:",
                value=investing_credentials.get("username", "")
            )
            
            investing_password = st.text_input(
                "Şifre:",
                type="password",
                value=investing_credentials.get("password", "")
            )
            
            if st.button("Investing.com Ayarlarını Kaydet"):
                try:
                    # Ayarları güncelle
                    bot.settings.set_setting("news_sources.investing_com.enabled", investing_enabled)
                    
                    # API anahtarlarını güncelle
                    bot.settings.set_api_key("news_sources.investing_com.username", investing_username)
                    bot.settings.set_api_key("news_sources.investing_com.password", investing_password)
                    
                    st.success("Investing.com ayarları başarıyla kaydedildi!")
                except Exception as e:
                    st.error(f"Ayarlar kaydedilirken hata: {str(e)}")
    
    with tab2:
        st.subheader("Sosyal Medya API Ayarları")
        
        # Twitter API
        with st.expander("Twitter API", expanded=True):
            # Mevcut ayarları al
            twitter_settings = bot.settings.get("news_sources", {}).get("twitter", {})
            twitter_credentials = bot.settings.api_keys.get("news_sources", {}).get("twitter", {})
            
            # Twitter API aktif
            twitter_enabled = st.checkbox(
                "Twitter API Aktif",
                value=twitter_settings.get("enabled", False)
            )
            
            # API anahtarları
            twitter_api_key = st.text_input(
                "API Key:",
                value=twitter_credentials.get("api_key", "")
            )
            
            twitter_api_secret = st.text_input(
                "API Secret:",
                type="password",
                value=twitter_credentials.get("api_secret", "")
            )
            
            twitter_access_token = st.text_input(
                "Access Token:",
                value=twitter_credentials.get("access_token", "")
            )
            
            twitter_access_token_secret = st.text_input(
                "Access Token Secret:",
                type="password",
                value=twitter_credentials.get("access_token_secret", "")
            )
            
            # Takip edilecek hesaplar
            accounts_to_follow = st.text_input(
                "Takip Edilecek Hesaplar (virgülle ayrılmış):",
                value=",".join(twitter_settings.get("accounts_to_follow", []))
            )
            
            if st.button("Twitter API Ayarlarını Kaydet"):
                try:
                    # Ayarları güncelle
                    bot.settings.set_setting("news_sources.twitter.enabled", twitter_enabled)
                    
                    accounts_list = [a.strip() for a in accounts_to_follow.split(",") if a.strip()]
                    bot.settings.set_setting("news_sources.twitter.accounts_to_follow", accounts_list)
                    
                    # API anahtarlarını güncelle
                    bot.settings.set_api_key("news_sources.twitter.api_key", twitter_api_key)
                    bot.settings.set_api_key("news_sources.twitter.api_secret", twitter_api_secret)
                    bot.settings.set_api_key("news_sources.twitter.access_token", twitter_access_token)
                    bot.settings.set_api_key("news_sources.twitter.access_token_secret", twitter_access_token_secret)
                    
                    st.success("Twitter API ayarları başarıyla kaydedildi!")
                except Exception as e:
                    st.error(f"Ayarlar kaydedilirken hata: {str(e)}")
    
    with tab3:
        st.subheader("Diğer API Ayarları")
        
        st.info("Şu anda başka API yapılandırması bulunmamaktadır.")

# Streamlit uygulamasını çalıştır
if __name__ == "__main__":
    main()