Whatsappa ses atılıyor whatsapptaki botumuz o sesi metne çevirip ai agent'a gönderip o agentta onu google sheets'e ekliyor.

open ai whisper
green api

kullanıldı


# 🎙️ WhatsApp Voice Note to Google Sheets Bot

OpenAI Whisper, GPT-4o-mini, Green-API ve Google Sheets API kullanarak WhatsApp üzerinden gönderilen sesli mesajları otomatik olarak metne dönüştüren, analiz eden ve Google Sheets tablosuna işleyen 7/24 otomasyon sistemi.

## 🚀 Mimari ve Teknoloji Yığını

- **Backend:** FastAPI & Python 3.10+
- **WhatsApp Gateway:** Green-API (REST API)
- **STT (Speech-to-Text):** OpenAI Whisper
- **LLM / Parser:** OpenAI GPT-4o-mini
- **Database / Output:** Google Sheets API (gspread)
- **Cloud Deployment:** Render.com (Web Service)

---

## 🛠️ Kurulum & Yerel Çalıştırma

1. **Repoyu klonlayın:**
   ```bash
   git clone [https://github.com/1erdemcom1-debug/whatsapp-sheets-bot.git](https://github.com/1erdemcom1-debug/whatsapp-sheets-bot.git)
   cd whatsapp-sheets-bot