#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Forex Trading Bot için Telegram bot modülü.
Uzaktan bildirim ve onay sistemi sağlar.
"""
import logging
import os
import asyncio
import threading
import time
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import re

# Telegram kütüphanesini koşullu olarak içe aktar
try:
    from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import (
        ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
        ContextTypes, filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

logger = logging.getLogger("ForexTradingBot.TelegramBot")

class TelegramBot:
    """
    Telegram bot entegrasyonu sağlayan sınıf.
    """
    
    def __init__(self, settings, signal_generator, risk_manager, broker_connector):
        """
        Telegram bot'u başlat
        
        Args:
            settings: Uygulama ayarları
            signal_generator: Sinyal oluşturucu
            risk_manager: Risk yöneticisi
            broker_connector: MT5 bağlantısı için broker connector
        """
        self.settings = settings
        self.signal_generator = signal_generator
        self.risk_manager = risk_manager
        self.broker = broker_connector
        
        # Telegram botu
        self.bot = None
        self.application = None
        self.connected = False
        self.thread = None
        self.running = False
        
        # Bekleyen sinyaller
        self.pending_signals = {}
        
        # Komut listesi
        self.commands = {
            "start": self._cmd_start,
            "help": self._cmd_help,
            "durum": self._cmd_status,
            "pozisyonlar": self._cmd_positions,
            "ayarlar": self._cmd_settings,
            "sinyaller": self._cmd_signals
        }
        
        # Bot kimliği
        self.bot_username = "forex_trading_bot"
        
        logger.info("Telegram bot oluşturuldu")
    
    def start(self) -> bool:
        """
        Telegram botunu başlat
        
        Returns:
            bool: Başlatma başarılıysa True, aksi halde False
        """
        try:
            # Telegram kütüphanesi kullanılabilir mi kontrol et
            if not TELEGRAM_AVAILABLE:
                logger.error("python-telegram-bot kütüphanesi yüklü değil")
                return False
            
            # Bot aktif mi kontrol et
            if not self.settings.get("telegram", {}).get("enabled", False):
                logger.info("Telegram bot devre dışı (ayarlardan aktif edilebilir)")
                return False
            
            # Bot token'ını al
            bot_token = self.settings.get_api_key("telegram.bot_token")
            
            if not bot_token:
                logger.error("Telegram bot token'ı ayarlanmamış")
                return False
            
            # Zaten çalışıyor mu kontrol et
            if self.running:
                logger.info("Telegram bot zaten çalışıyor")
                return True
            
            # Thread oluştur ve başlat
            self.thread = threading.Thread(target=self._run_bot)
            self.thread.daemon = True
            self.thread.start()
            
            # Botun başlamasını bekle
            timeout = 10
            start_time = time.time()
            
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.5)
            
            if self.connected:
                logger.info("Telegram bot başlatıldı")
                return True
            else:
                logger.error("Telegram bot başlatılamadı (zaman aşımı)")
                return False
            
        except Exception as e:
            logger.error(f"Telegram bot başlatma hatası: {e}", exc_info=True)
            return False
    
    def stop(self) -> bool:
        """
        Telegram botunu durdur
        
        Returns:
            bool: Durdurma başarılıysa True, aksi halde False
        """
        try:
            # Bot çalışıyor mu kontrol et
            if not self.running or not self.application:
                logger.info("Telegram bot zaten durmuş")
                return True
            
            # Botu durdur
            async def stop_bot():
                await self.application.stop()
                await self.application.shutdown()
            
            # Async fonksiyonu çalıştır
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(stop_bot())
            loop.close()
            
            # Thread'i durdur
            self.running = False
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5.0)
            
            self.connected = False
            logger.info("Telegram bot durduruldu")
            return True
            
        except Exception as e:
            logger.error(f"Telegram bot durdurma hatası: {e}", exc_info=True)
            return False
    
    def _run_bot(self):
        """
        Telegram bot'u thread içinde çalıştır
        """
        try:
            # Event loop oluştur
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Bot'u oluştur ve başlat
            self._start_bot(loop)
        except Exception as e:
            logger.error(f"Telegram bot çalıştırma hatası: {e}", exc_info=True)
            self.running = False
            self.connected = False
    
    def _start_bot(self, loop):
        """
        Telegram bot'u başlat
        
        Args:
            loop: Asyncio event loop
        """
        try:
            # Bot token'ını al
            bot_token = self.settings.get_api_key("telegram.bot_token")
            
            if not bot_token:
                logger.error("Telegram bot token'ı ayarlanmamış")
                return
            
            # ApplicationBuilder ve bot oluştur
            application_builder = ApplicationBuilder().token(bot_token)
            self.application = application_builder.build()
            
            # Bot örneğini al
            self.bot = self.application.bot
            
            # Komut işleyicileri ekle
            for command, handler in self.commands.items():
                self.application.add_handler(CommandHandler(command, handler))
            
            # İki özel komut için özel işleyiciler
            self.application.add_handler(CommandHandler("onay", self._cmd_confirm))
            self.application.add_handler(CommandHandler("red", self._cmd_reject))
            
            # Callback işleyicisi ekle
            self.application.add_handler(CallbackQueryHandler(self._handle_callback))
            
            # Mesaj işleyicisi ekle (tüm mesajlar)
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            
            # Bot'u başlat
            self.running = True
            self.connected = True
            
            # Bot bilgilerini al
            async def get_bot_info():
                bot_info = await self.bot.get_me()
                self.bot_username = bot_info.username
                logger.info(f"Telegram bot başlatıldı: @{self.bot_username}")
            
            # Bot bilgilerini al
            loop.run_until_complete(get_bot_info())
            
            # Bot'u çalıştır
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Telegram bot başlatma hatası: {e}", exc_info=True)
            self.running = False
            self.connected = False
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /start komutu için işleyici
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Chat ID'yi kontrol et
            chat_id = update.effective_chat.id
            
            # Doğru chat ID mi?
            expected_chat_id = self.settings.get_api_key("telegram.chat_id")
            if expected_chat_id and str(chat_id) != str(expected_chat_id):
                await update.message.reply_text(
                    "Üzgünüm, bu botu kullanma yetkiniz yok. "
                    "Lütfen bot ayarlarında doğru Chat ID'yi yapılandırın."
                )
                return
            
            # Hoş geldin mesajı
            welcome_message = (
                f"🤖 *Forex Trading Bot*\n\n"
                f"Forex Trading Bot'a hoş geldiniz! Bu bot size otomatik alım-satım sinyalleri "
                f"gönderir ve işlemleri onaylamanızı veya reddetmenizi sağlar.\n\n"
                f"Kullanılabilir komutlar:\n"
                f"/durum - Hesap durumunu göster\n"
                f"/pozisyonlar - Açık pozisyonları listele\n"
                f"/sinyaller - Son sinyalleri göster\n"
                f"/ayarlar - Bot ayarlarını göster\n"
                f"/onay\\_XXXX - İşlemi onayla (XXXX: İşlem ID'si)\n"
                f"/red\\_XXXX - İşlemi reddet (XXXX: İşlem ID'si)\n"
                f"/help - Bu yardım mesajını göster"
            )
            
            await update.message.reply_text(welcome_message, parse_mode="Markdown")
            
            # Chat ID'yi kaydet
            if not expected_chat_id:
                self.settings.set_api_key("telegram.chat_id", str(chat_id))
                await update.message.reply_text(
                    f"Chat ID kaydedildi: {chat_id}\n"
                    f"Artık bu chat üzerinden bot ile etkileşime geçebilirsiniz."
                )
        except Exception as e:
            logger.error(f"Start komutu hatası: {e}", exc_info=True)
            await update.message.reply_text("Bir hata oluştu. Lütfen daha sonra tekrar deneyin.")
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /help komutu için işleyici
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Komut listesi
            help_message = (
                f"🤖 *Forex Trading Bot Komutları*\n\n"
                f"/durum - Hesap durumunu göster\n"
                f"/pozisyonlar - Açık pozisyonları listele\n"
                f"/sinyaller - Son sinyalleri göster\n"
                f"/ayarlar - Bot ayarlarını göster\n"
                f"/onay\\_XXXX - İşlemi onayla (XXXX: İşlem ID'si)\n"
                f"/red\\_XXXX - İşlemi reddet (XXXX: İşlem ID'si)\n"
                f"/help - Bu yardım mesajını göster"
            )
            
            await update.message.reply_text(help_message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Help komutu hatası: {e}", exc_info=True)
            await update.message.reply_text("Bir hata oluştu. Lütfen daha sonra tekrar deneyin.")
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /durum komutu için işleyici
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Chat ID'yi kontrol et
            if not self._check_chat_id(update.effective_chat.id):
                await update.message.reply_text("Bu komutu kullanma yetkiniz yok.")
                return
            
            # Hesap bilgilerini al
            account_info = self.broker.get_account_info()
            
            if not account_info:
                await update.message.reply_text("Hesap bilgileri alınamıyor. MT5 bağlantısını kontrol edin.")
                return
            
            # Risk özeti
            risk_summary = self.risk_manager.get_risk_summary()
            
            # Durum mesajı
            status_message = (
                f"📊 *Hesap Durumu*\n\n"
                f"*Bakiye:* {account_info.get('balance', 0):.2f} {account_info.get('currency', 'USD')}\n"
                f"*Varlık:* {account_info.get('equity', 0):.2f} {account_info.get('currency', 'USD')}\n"
                f"*Kar/Zarar:* {account_info.get('profit', 0):.2f} {account_info.get('currency', 'USD')}\n"
                f"*Serbest Marjin:* {account_info.get('free_margin', 0):.2f} {account_info.get('currency', 'USD')}\n"
                f"*Marjin Seviyesi:* {account_info.get('margin_level', 0):.2f}%\n\n"
                f"*Risk Durumu:*\n"
                f"Günlük Risk: {risk_summary.get('daily_risk', 0):.2f}% / {risk_summary.get('max_daily_risk', 5.0):.2f}%\n"
                f"Haftalık Risk: {risk_summary.get('weekly_risk', 0):.2f}% / {risk_summary.get('max_weekly_risk', 10.0):.2f}%\n"
                f"Bugünkü İşlemler: {risk_summary.get('total_trades_today', 0)}"
            )
            
            await update.message.reply_text(status_message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Durum komutu hatası: {e}", exc_info=True)
            await update.message.reply_text("Hesap durumu alınırken bir hata oluştu.")
    
    async def _cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /pozisyonlar komutu için işleyici
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Chat ID'yi kontrol et
            if not self._check_chat_id(update.effective_chat.id):
                await update.message.reply_text("Bu komutu kullanma yetkiniz yok.")
                return
            
            # Açık pozisyonları al
            positions_df = self.broker.get_positions()
            
            if positions_df.empty:
                await update.message.reply_text("Şu anda açık pozisyon yok.")
                return
            
            # Pozisyon mesajı
            positions_message = f"📈 *Açık Pozisyonlar ({len(positions_df)})*\n\n"
            
            for idx, position in positions_df.iterrows():
                symbol = position.get("symbol", "")
                direction = position.get("direction", "")
                volume = position.get("volume", 0)
                open_price = position.get("price_open", 0)
                current_price = position.get("price_current", 0)
                profit = position.get("profit", 0)
                ticket = position.get("ticket", 0)
                
                # Pozisyon detayı
                positions_message += (
                    f"🔸 *{symbol}* - {direction}\n"
                    f"   Lot: {volume:.2f}\n"
                    f"   Açılış: {open_price:.5f}\n"
                    f"   Mevcut: {current_price:.5f}\n"
                    f"   Kar/Zarar: {profit:.2f}\n"
                    f"   Ticket: {ticket}\n\n"
                )
            
            # Kapatma butonları
            keyboard = []
            
            for idx, position in positions_df.iterrows():
                ticket = position.get("ticket", 0)
                symbol = position.get("symbol", "")
                
                # Her pozisyon için kapatma butonu
                keyboard.append([
                    InlineKeyboardButton(
                        f"Kapat: {symbol} (#{ticket})", 
                        callback_data=f"close_{ticket}"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                positions_message, 
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Pozisyonlar komutu hatası: {e}", exc_info=True)
            await update.message.reply_text("Açık pozisyonlar alınırken bir hata oluştu.")
    
    async def _cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /ayarlar komutu için işleyici
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Chat ID'yi kontrol et
            if not self._check_chat_id(update.effective_chat.id):
                await update.message.reply_text("Bu komutu kullanma yetkiniz yok.")
                return
            
            # Ayarları al
            auto_trade_enabled = self.settings.get("auto_trade_enabled", False)
            auto_trade_threshold = self.settings.get("auto_trade_threshold", 70)
            
            # Risk ayarları
            risk_settings = self.settings.get("risk_management", {})
            max_risk_percent = risk_settings.get("max_risk_percent", 2.0)
            max_daily_risk_percent = risk_settings.get("max_daily_risk_percent", 5.0)
            max_open_positions = risk_settings.get("max_open_positions", 5)
            
            # Ayarlar mesajı
            settings_message = (
                f"⚙️ *Bot Ayarları*\n\n"
                f"*Otomatik İşlem:* {'Açık ✅' if auto_trade_enabled else 'Kapalı ❌'}\n"
                f"*İşlem Eşiği:* {auto_trade_threshold}% başarı olasılığı\n\n"
                f"*Risk Ayarları:*\n"
                f"İşlem Başına Risk: {max_risk_percent:.2f}%\n"
                f"Günlük Maks. Risk: {max_daily_risk_percent:.2f}%\n"
                f"Maks. Açık Pozisyon: {max_open_positions}\n\n"
            )
            
            # Ayar değiştirme butonları
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"Otomatik İşlem: {'Kapat' if auto_trade_enabled else 'Aç'}", 
                        callback_data=f"toggle_auto_trade"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Eşik: 60%", 
                        callback_data="set_threshold_60"
                    ),
                    InlineKeyboardButton(
                        "Eşik: 70%", 
                        callback_data="set_threshold_70"
                    ),
                    InlineKeyboardButton(
                        "Eşik: 80%", 
                        callback_data="set_threshold_80"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                settings_message, 
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ayarlar komutu hatası: {e}", exc_info=True)
            await update.message.reply_text("Ayarlar alınırken bir hata oluştu.")
    
    async def _cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /sinyaller komutu için işleyici
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Chat ID'yi kontrol et
            if not self._check_chat_id(update.effective_chat.id):
                await update.message.reply_text("Bu komutu kullanma yetkiniz yok.")
                return
            
            # Son sinyalleri al
            signals = self.signal_generator.get_signal_history(10)
            
            if not signals:
                await update.message.reply_text("Henüz sinyal yok.")
                return
            
            # Sinyaller mesajı
            signals_message = f"🚨 *Son Sinyaller ({len(signals)})*\n\n"
            
            for signal in signals:
                symbol = signal.get("symbol", "")
                direction = signal.get("signal", "neutral").upper()
                entry_price = signal.get("entry_price", 0)
                probability = signal.get("success_probability", 0)
                timestamp = signal.get("timestamp", datetime.now())
                status = signal.get("status", "pending")
                signal_id = signal.get("id", "")
                
                # Direction emojisi
                direction_emoji = "🟢" if direction == "BUY" else "🔴" if direction == "SELL" else "⚪️"
                
                # Sinyal detayı
                signals_message += (
                    f"{direction_emoji} *{symbol}* - {direction}\n"
                    f"   Giriş: {entry_price:.5f}\n"
                    f"   Olasılık: {probability:.1f}%\n"
                    f"   Zaman: {timestamp.strftime('%d.%m.%Y %H:%M')}\n"
                    f"   Durum: {status.capitalize()}\n\n"
                )
                
                # Bekleyen sinyal ise ID'sini ekle
                if status == "pending":
                    signals_message += f"   ID: `{signal_id}`\n\n"
            
            # Onay butonları
            keyboard = []
            
            # Bekleyen sinyaller için onay/red butonları
            pending_signals = [s for s in signals if s.get("status") == "pending"]
            
            for signal in pending_signals:
                signal_id = signal.get("id", "")
                symbol = signal.get("symbol", "")
                direction = signal.get("signal", "neutral").upper()
                
                if signal_id:
                    # Her sinyal için onay/red butonları
                    keyboard.append([
                        InlineKeyboardButton(
                            f"Onayla: {symbol} {direction}", 
                            callback_data=f"confirm_{signal_id}"
                        ),
                        InlineKeyboardButton(
                            f"Reddet", 
                            callback_data=f"reject_{signal_id}"
                        )
                    ])
            
            # Butonları ekle
            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    signals_message, 
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(signals_message, parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Sinyaller komutu hatası: {e}", exc_info=True)
            await update.message.reply_text("Sinyaller alınırken bir hata oluştu.")
    
    async def _cmd_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /onay komutu için işleyici
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Chat ID'yi kontrol et
            if not self._check_chat_id(update.effective_chat.id):
                await update.message.reply_text("Bu komutu kullanma yetkiniz yok.")
                return
            
            # Komut parametrelerini al
            message_text = update.message.text
            
            # Signal ID'yi çıkar
            match = re.search(r'/onay_([a-zA-Z0-9-]+)', message_text)
            
            if not match:
                await update.message.reply_text(
                    "Geçersiz komut formatı. Doğru format: /onay_ID\n"
                    "Örnek: /onay_1234567890"
                )
                return
            
            signal_id = match.group(1)
            
            # Sinyali onayla
            await self._confirm_signal(update, signal_id)
                
        except Exception as e:
            logger.error(f"Onay komutu hatası: {e}", exc_info=True)
            await update.message.reply_text("İşlem onaylanırken bir hata oluştu.")
    
    async def _cmd_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /red komutu için işleyici
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Chat ID'yi kontrol et
            if not self._check_chat_id(update.effective_chat.id):
                await update.message.reply_text("Bu komutu kullanma yetkiniz yok.")
                return
            
            # Komut parametrelerini al
            message_text = update.message.text
            
            # Signal ID'yi çıkar
            match = re.search(r'/red_([a-zA-Z0-9-]+)', message_text)
            
            if not match:
                await update.message.reply_text(
                    "Geçersiz komut formatı. Doğru format: /red_ID\n"
                    "Örnek: /red_1234567890"
                )
                return
            
            signal_id = match.group(1)
            
            # Sinyali reddet
            await self._reject_signal(update, signal_id)
                
        except Exception as e:
            logger.error(f"Red komutu hatası: {e}", exc_info=True)
            await update.message.reply_text("İşlem reddedilirken bir hata oluştu.")
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Buton callback işleyicisi
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Chat ID'yi kontrol et
            if not self._check_chat_id(update.callback_query.message.chat.id):
                await update.callback_query.answer("Bu işlemi yapma yetkiniz yok.")
                return
            
            # Callback verilerini al
            query = update.callback_query
            callback_data = query.data
            
            # İşlem tipini belirle
            if callback_data.startswith("confirm_"):
                # Sinyal onaylama
                signal_id = callback_data[8:]
                await self._confirm_signal(update, signal_id, is_callback=True)
                
            elif callback_data.startswith("reject_"):
                # Sinyal reddetme
                signal_id = callback_data[7:]
                await self._reject_signal(update, signal_id, is_callback=True)
                
            elif callback_data.startswith("close_"):
                # Pozisyon kapatma
                ticket = int(callback_data[6:])
                await self._close_position(update, ticket)
                
            elif callback_data == "toggle_auto_trade":
                # Otomatik işlem durumunu değiştir
                current_state = self.settings.get("auto_trade_enabled", False)
                new_state = not current_state
                
                self.settings.set_setting("auto_trade_enabled", new_state)
                
                state_text = "açıldı ✅" if new_state else "kapatıldı ❌"
                await query.answer(f"Otomatik işlem modu {state_text}")
                
                # Mesajı güncelle
                await self._update_settings_message(query.message)
                
            elif callback_data.startswith("set_threshold_"):
                # Eşik değerini değiştir
                threshold = int(callback_data[14:])
                
                self.settings.set_setting("auto_trade_threshold", threshold)
                
                await query.answer(f"İşlem eşiği {threshold}% olarak ayarlandı")
                
                # Mesajı güncelle
                await self._update_settings_message(query.message)
                
            else:
                await query.answer("Bilinmeyen işlem.")
                
        except Exception as e:
            logger.error(f"Callback işleme hatası: {e}", exc_info=True)
            await update.callback_query.answer("İşlem sırasında bir hata oluştu.")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Mesaj işleyicisi
        
        Args:
            update: Telegram güncellemesi
            context: Callback context
        """
        try:
            # Chat ID'yi kontrol et
            if not self._check_chat_id(update.effective_chat.id):
                return
            
            # Mesaj metnini al
            message_text = update.message.text.lower()
            
            # Basit cevaplar
            if any(keyword in message_text for keyword in ["merhaba", "selam", "hello", "hi"]):
                await update.message.reply_text(
                    f"Merhaba! Size nasıl yardımcı olabilirim?\n\n"
                    f"Komutları görmek için /help yazabilirsiniz."
                )
            
            elif any(keyword in message_text for keyword in ["durum", "hesap", "bakiye"]):
                # Durum komutunu çalıştır
                await self._cmd_status(update, context)
            
            elif any(keyword in message_text for keyword in ["pozisyon", "işlem", "trade"]):
                # Pozisyonlar komutunu çalıştır
                await self._cmd_positions(update, context)
            
            elif any(keyword in message_text for keyword in ["sinyal", "signal"]):
                # Sinyaller komutunu çalıştır
                await self._cmd_signals(update, context)
                
        except Exception as e:
            logger.error(f"Mesaj işleme hatası: {e}", exc_info=True)
    
    async def _confirm_signal(self, update, signal_id, is_callback=False):
        """
        Sinyali onayla ve işlemi gerçekleştir
        
        Args:
            update: Telegram güncellemesi
            signal_id: Sinyal kimliği
            is_callback: Callback'ten mi geldi
        """
        try:
            # Sinyali al
            signal = self.signal_generator.get_signal_by_id(signal_id)
            
            if not signal:
                message = f"ID: {signal_id} ile sinyal bulunamadı."
                
                if is_callback:
                    await update.callback_query.answer(message)
                    await update.callback_query.edit_message_text(
                        f"{update.callback_query.message.text}\n\n❌ {message}"
                    )
                else:
                    await update.message.reply_text(message)
                    
                return
            
            # Sinyal durumunu kontrol et
            if signal.get("status") != "pending":
                message = f"Bu sinyal zaten '{signal.get('status')}' durumunda."
                
                if is_callback:
                    await update.callback_query.answer(message)
                else:
                    await update.message.reply_text(message)
                    
                return
            
            # Pozisyon açılabilir mi kontrol et
            can_open, reason = self.risk_manager.can_open_position(signal)
            
            if not can_open:
                message = f"İşlem açılamıyor: {reason}"
                
                if is_callback:
                    await update.callback_query.answer(message)
                    await update.callback_query.edit_message_text(
                        f"{update.callback_query.message.text}\n\n❌ {message}"
                    )
                else:
                    await update.message.reply_text(message)
                    
                return
            
            # Risk parametrelerini hesapla
            risk_params = self.risk_manager.calculate_risk_params(signal)
            
            # İşlemi aç
            result = self.broker.open_position(
                symbol=signal.get("symbol"),
                order_type=signal.get("signal"),
                volume=risk_params.get("lot_size", 0.01),
                stop_loss=signal.get("stop_loss"),
                take_profit=signal.get("take_profit"),
                comment="Telegram onaylı sinyal"
            )
            
            if "error" in result:
                message = f"İşlem açılamadı: {result['error']}"
                
                if is_callback:
                    await update.callback_query.answer(message)
                    await update.callback_query.edit_message_text(
                        f"{update.callback_query.message.text}\n\n❌ {message}"
                    )
                else:
                    await update.message.reply_text(message)
                    
                return
            
            # Başarılı işlem
            # Sinyali güncelle
            self.signal_generator.update_signal_status(
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
            self.risk_manager.update_risk_history(trade_data)
            
            # Başarı mesajı
            symbol = signal.get("symbol")
            direction = signal.get("signal").upper()
            entry_price = result.get("price", signal.get("entry_price"))
            ticket = result.get("ticket", "N/A")
            lot = risk_params.get("lot_size", 0.01)
            
            success_message = (
                f"✅ *İşlem Başarıyla Açıldı*\n\n"
                f"*{symbol}* - {direction}\n"
                f"Giriş: {entry_price:.5f}\n"
                f"Stop Loss: {signal.get('stop_loss', 0):.5f}\n"
                f"Take Profit: {signal.get('take_profit', 0):.5f}\n"
                f"Lot: {lot:.2f}\n"
                f"Ticket: {ticket}"
            )
            
            if is_callback:
                await update.callback_query.answer("İşlem başarıyla açıldı!")
                await update.callback_query.edit_message_text(
                    success_message,
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(success_message, parse_mode="Markdown")
            
            # Bekleyen sinyallerden kaldır
            if signal_id in self.pending_signals:
                del self.pending_signals[signal_id]
                
        except Exception as e:
            logger.error(f"Sinyal onaylama hatası: {e}", exc_info=True)
            
            message = "İşlem onaylanırken bir hata oluştu."
            
            if is_callback:
                await update.callback_query.answer(message)
            else:
                await update.message.reply_text(message)
    
    async def _reject_signal(self, update, signal_id, is_callback=False):
        """
        Sinyali reddet
        
        Args:
            update: Telegram güncellemesi
            signal_id: Sinyal kimliği
            is_callback: Callback'ten mi geldi
        """
        try:
            # Sinyali al
            signal = self.signal_generator.get_signal_by_id(signal_id)
            
            if not signal:
                message = f"ID: {signal_id} ile sinyal bulunamadı."
                
                if is_callback:
                    await update.callback_query.answer(message)
                    await update.callback_query.edit_message_text(
                        f"{update.callback_query.message.text}\n\n❌ {message}"
                    )
                else:
                    await update.message.reply_text(message)
                    
                return
            
            # Sinyal durumunu kontrol et
            if signal.get("status") != "pending":
                message = f"Bu sinyal zaten '{signal.get('status')}' durumunda."
                
                if is_callback:
                    await update.callback_query.answer(message)
                else:
                    await update.message.reply_text(message)
                    
                return
            
            # Sinyali güncelle
            self.signal_generator.update_signal_status(signal.get("id"), "rejected")
            
            # Başarı mesajı
            symbol = signal.get("symbol")
            direction = signal.get("signal").upper()
            
            reject_message = (
                f"❌ *İşlem Reddedildi*\n\n"
                f"*{symbol}* - {direction}\n"
                f"Sinyal ID: {signal_id}"
            )
            
            if is_callback:
                await update.callback_query.answer("İşlem reddedildi!")
                await update.callback_query.edit_message_text(
                    reject_message,
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(reject_message, parse_mode="Markdown")
            
            # Bekleyen sinyallerden kaldır
            if signal_id in self.pending_signals:
                del self.pending_signals[signal_id]
                
        except Exception as e:
            logger.error(f"Sinyal reddetme hatası: {e}", exc_info=True)
            
            message = "İşlem reddedilirken bir hata oluştu."
            
            if is_callback:
                await update.callback_query.answer(message)
            else:
                await update.message.reply_text(message)
    
    async def _close_position(self, update, ticket):
        """
        Pozisyonu kapat
        
        Args:
            update: Telegram güncellemesi
            ticket: Pozisyon bileti
        """
        try:
            # Pozisyonu kapat
            result = self.broker.close_position(ticket)
            
            if "error" in result:
                await update.callback_query.answer(f"Pozisyon kapatılamadı: {result['error']}")
                return
            
            # Başarı mesajı
            symbol = result.get("symbol", "")
            profit = result.get("profit", 0)
            
            success_message = (
                f"✅ *Pozisyon Başarıyla Kapatıldı*\n\n"
                f"*{symbol}* - Ticket: {ticket}\n"
                f"Kar/Zarar: {profit:.2f}"
            )
            
            await update.callback_query.answer("Pozisyon başarıyla kapatıldı!")
            await update.callback_query.edit_message_text(
                success_message,
                parse_mode="Markdown"
            )
                
        except Exception as e:
            logger.error(f"Pozisyon kapatma hatası: {e}", exc_info=True)
            await update.callback_query.answer("Pozisyon kapatılırken bir hata oluştu.")
    
    async def _update_settings_message(self, message):
        """
        Ayarlar mesajını güncelle
        
        Args:
            message: Güncellenecek mesaj
        """
        try:
            # Ayarları al
            auto_trade_enabled = self.settings.get("auto_trade_enabled", False)
            auto_trade_threshold = self.settings.get("auto_trade_threshold", 70)
            
            # Risk ayarları
            risk_settings = self.settings.get("risk_management", {})
            max_risk_percent = risk_settings.get("max_risk_percent", 2.0)
            max_daily_risk_percent = risk_settings.get("max_daily_risk_percent", 5.0)
            max_open_positions = risk_settings.get("max_open_positions", 5)
            
            # Ayarlar mesajı
            settings_message = (
                f"⚙️ *Bot Ayarları*\n\n"
                f"*Otomatik İşlem:* {'Açık ✅' if auto_trade_enabled else 'Kapalı ❌'}\n"
                f"*İşlem Eşiği:* {auto_trade_threshold}% başarı olasılığı\n\n"
                f"*Risk Ayarları:*\n"
                f"İşlem Başına Risk: {max_risk_percent:.2f}%\n"
                f"Günlük Maks. Risk: {max_daily_risk_percent:.2f}%\n"
                f"Maks. Açık Pozisyon: {max_open_positions}\n\n"
            )
            
            # Butonları güncelle
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"Otomatik İşlem: {'Kapat' if auto_trade_enabled else 'Aç'}", 
                        callback_data=f"toggle_auto_trade"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Eşik: 60%", 
                        callback_data="set_threshold_60"
                    ),
                    InlineKeyboardButton(
                        "Eşik: 70%", 
                        callback_data="set_threshold_70"
                    ),
                    InlineKeyboardButton(
                        "Eşik: 80%", 
                        callback_data="set_threshold_80"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Mesajı güncelle
            await message.edit_text(
                settings_message, 
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
                
        except Exception as e:
            logger.error(f"Ayarlar mesajı güncelleme hatası: {e}", exc_info=True)
    
    def _check_chat_id(self, chat_id) -> bool:
        """
        Chat ID'yi doğrula
        
        Args:
            chat_id: Kontrol edilecek chat ID
            
        Returns:
            bool: Doğruysa True, aksi halde False
        """
        expected_chat_id = self.settings.get_api_key("telegram.chat_id")
        
        if not expected_chat_id:
            # Chat ID yapılandırılmamış, ilk etkileşime izin ver
            return True
            
        return str(chat_id) == str(expected_chat_id)
    
    def send_message(self, message: str, parse_mode: str = None, 
                   reply_markup: Any = None) -> bool:
        """
        Telegram üzerinden mesaj gönder
        
        Args:
            message: Mesaj metni
            parse_mode: Metin biçimlendirme modu
            reply_markup: Cevap düğmeleri
            
        Returns:
            bool: Gönderim başarılıysa True, aksi halde False
        """
        try:
            # Bot bağlı mı kontrol et
            if not self.connected or not self.bot:
                logger.error("Telegram bot bağlı değil, mesaj gönderilemiyor")
                return False
            
            # Chat ID kontrolü
            chat_id = self.settings.get_api_key("telegram.chat_id")
            
            if not chat_id:
                logger.error("Telegram chat ID ayarlanmamış, mesaj gönderilemiyor")
                return False
            
            # Asenkron fonksiyonu çalıştır
            async def send():
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
            
            # Event loop oluştur
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Asenkron fonksiyonu çalıştır
            loop.run_until_complete(send())
            loop.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Telegram mesajı gönderme hatası: {e}", exc_info=True)
            return False
    
    def send_signal_confirmation(self, signal: Dict, risk_params: Dict) -> bool:
        """
        İşlem sinyali onayı gönder
        
        Args:
            signal: İşlem sinyali
            risk_params: Risk parametreleri
            
        Returns:
            bool: Gönderim başarılıysa True, aksi halde False
        """
        try:
            # Bot bağlı mı kontrol et
            if not self.connected or not self.bot:
                logger.error("Telegram bot bağlı değil, sinyal onayı gönderilemiyor")
                return False
            
            # Signal ID
            signal_id = signal.get("id", "")
            
            if not signal_id:
                logger.error("Geçersiz sinyal ID, onay gönderilemiyor")
                return False
                
            # Signal detayları
            symbol = signal.get("symbol", "")
            direction = signal.get("signal", "").upper()
            entry_price = signal.get("entry_price", 0)
            stop_loss = signal.get("stop_loss", 0)
            take_profit = signal.get("take_profit", 0)
            probability = signal.get("success_probability", 0)
            risk_reward = signal.get("risk_reward", 0)
            
            # Risk parametreleri
            lot_size = risk_params.get("lot_size", 0.01)
            risk_amount = risk_params.get("risk_amount", 0)
            risk_percent = risk_params.get("risk_percent", 0)
            
            # Yön emojisi
            direction_emoji = "🟢" if direction == "BUY" else "🔴" if direction == "SELL" else "⚪️"
            
            # Onay mesajı
            confirmation_message = (
                f"🚨 *YENİ İŞLEM SİNYALİ* 🚨\n\n"
                f"{direction_emoji} *{symbol}* - {direction}\n\n"
                f"*Giriş Fiyatı:* {entry_price:.5f}\n"
                f"*Stop Loss:* {stop_loss:.5f}\n"
                f"*Take Profit:* {take_profit:.5f}\n"
                f"*Başarı Olasılığı:* {probability:.1f}%\n"
                f"*Risk/Ödül:* {risk_reward:.2f}\n"
                f"*Lot:* {lot_size:.2f}\n"
                f"*Risk:* {risk_amount:.2f} ({risk_percent:.2f}%)\n\n"
                f"*Onay için:* /onay_{signal_id}\n"
                f"*Reddetmek için:* /red_{signal_id}\n\n"
                f"⏰ *{self.settings.get('confirmation_timeout', 300) // 60} dakika içinde yanıt vermelisiniz* ⏰"
            )
            
            # Onay butonları
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"✅ ONAYLA: {symbol} {direction}", 
                        callback_data=f"confirm_{signal_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ REDDET", 
                        callback_data=f"reject_{signal_id}"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Mesajı gönder
            success = self.send_message(
                confirmation_message, 
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
            if success:
                # Bekleyen sinyallere ekle
                self.pending_signals[signal_id] = {
                    "signal": signal,
                    "risk_params": risk_params,
                    "timestamp": datetime.now()
                }
                
                # Onay zaman aşımı için thread başlat
                timeout_thread = threading.Thread(
                    target=self._handle_confirmation_timeout,
                    args=(signal_id,)
                )
                timeout_thread.daemon = True
                timeout_thread.start()
            
            return success
            
        except Exception as e:
            logger.error(f"Sinyal onayı gönderme hatası: {e}", exc_info=True)
            return False
    
    def send_signal_info(self, signal: Dict, risk_params: Dict) -> bool:
        """
        İşlem sinyali bilgisi gönder (onay gerektirmeyen)
        
        Args:
            signal: İşlem sinyali
            risk_params: Risk parametreleri
            
        Returns:
            bool: Gönderim başarılıysa True, aksi halde False
        """
        try:
            # Bot bağlı mı kontrol et
            if not self.connected or not self.bot:
                logger.error("Telegram bot bağlı değil, sinyal bilgisi gönderilemiyor")
                return False
                
            # Signal detayları
            symbol = signal.get("symbol", "")
            direction = signal.get("signal", "").upper()
            entry_price = signal.get("entry_price", 0)
            stop_loss = signal.get("stop_loss", 0)
            take_profit = signal.get("take_profit", 0)
            probability = signal.get("success_probability", 0)
            risk_reward = signal.get("risk_reward", 0)
            
            # Yön emojisi
            direction_emoji = "🟢" if direction == "BUY" else "🔴" if direction == "SELL" else "⚪️"
            
            # Bilgi mesajı
            info_message = (
                f"ℹ️ *YENİ İŞLEM SİNYALİ* ℹ️\n\n"
                f"{direction_emoji} *{symbol}* - {direction}\n\n"
                f"*Giriş Fiyatı:* {entry_price:.5f}\n"
                f"*Stop Loss:* {stop_loss:.5f}\n"
                f"*Take Profit:* {take_profit:.5f}\n"
                f"*Başarı Olasılığı:* {probability:.1f}%\n"
                f"*Risk/Ödül:* {risk_reward:.2f}\n\n"
                f"⚠️ *Not:* Bu sinyal bilgi amaçlıdır. Otomatik işlem için Başarı Olasılığı "
                f"eşik değerinin ({self.settings.get('auto_trade_threshold', 70)}%) "
                f"üzerinde olmalıdır."
            )
            
            # Mesajı gönder
            return self.send_message(info_message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Sinyal bilgisi gönderme hatası: {e}", exc_info=True)
            return False
    
    def send_trade_notification(self, trade: Dict) -> bool:
        """
        İşlem bildirimi gönder
        
        Args:
            trade: İşlem bilgileri
            
        Returns:
            bool: Gönderim başarılıysa True, aksi halde False
        """
        try:
            # Bot bağlı mı kontrol et
            if not self.connected or not self.bot:
                logger.error("Telegram bot bağlı değil, işlem bildirimi gönderilemiyor")
                return False
                
            # İşlem detayları
            symbol = trade.get("symbol", "")
            direction = trade.get("direction", "").upper()
            price = trade.get("price", 0)
            stop_loss = trade.get("stop_loss", 0)
            take_profit = trade.get("take_profit", 0)
            volume = trade.get("volume", 0)
            ticket = trade.get("ticket", "")
            
            # Yön emojisi
            direction_emoji = "🟢" if direction == "BUY" else "🔴" if direction == "SELL" else "⚪️"
            
            # Bildirim mesajı
            notification_message = (
                f"✅ *YENİ İŞLEM AÇILDI* ✅\n\n"
                f"{direction_emoji} *{symbol}* - {direction}\n\n"
                f"*Giriş Fiyatı:* {price:.5f}\n"
                f"*Stop Loss:* {stop_loss:.5f}\n"
                f"*Take Profit:* {take_profit:.5f}\n"
                f"*Lot:* {volume:.2f}\n"
                f"*Ticket:* {ticket}\n\n"
                f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            
            # Mesajı gönder
            return self.send_message(notification_message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"İşlem bildirimi gönderme hatası: {e}", exc_info=True)
            return False
    
    def _handle_confirmation_timeout(self, signal_id: str):
        """
        Sinyal onayı zaman aşımını işle
        
        Args:
            signal_id: Sinyal kimliği
        """
        try:
            # Bekleyen sinyal var mı kontrol et
            if signal_id not in self.pending_signals:
                return
                
            # Zaman aşımı süresini al
            timeout_seconds = self.settings.get("confirmation_timeout", 300)
            pending_signal = self.pending_signals[signal_id]
            
            # Zaman aşımı bekleme
            signal_time = pending_signal["timestamp"]
            while (datetime.now() - signal_time).total_seconds() < timeout_seconds:
                # Sinyal hâlâ bekliyor mu kontrol et
                if signal_id not in self.pending_signals:
                    return
                    
                time.sleep(5)
            
            # Zaman aşımı oldu, hâlâ bekliyor mu kontrol et
            if signal_id not in self.pending_signals:
                return
                
            # Sinyali al ve güncellenmiş durumu kontrol et
            signal = self.signal_generator.get_signal_by_id(signal_id)
            
            if signal and signal.get("status") == "pending":
                # Sinyali güncelle
                self.signal_generator.update_signal_status(signal_id, "expired")
                
                # Zaman aşımı mesajı
                symbol = signal.get("symbol", "")
                direction = signal.get("signal", "").upper()
                
                timeout_message = (
                    f"⏰ *ZAMAN AŞIMI* ⏰\n\n"
                    f"*{symbol}* - {direction} sinyal için onay zaman aşımına uğradı.\n"
                    f"Sinyal ID: {signal_id}"
                )
                
                # Mesajı gönder
                self.send_message(timeout_message, parse_mode="Markdown")
                
                # Bekleyen sinyallerden kaldır
                del self.pending_signals[signal_id]
                
        except Exception as e:
            logger.error(f"Onay zaman aşımı işleme hatası: {e}", exc_info=True)