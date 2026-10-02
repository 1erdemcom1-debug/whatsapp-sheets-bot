import os
import json
import requests
from datetime import datetime
from fastapi import FastAPI, Request, BackgroundTasks
from dotenv import load_dotenv
import openai
import gspread

# 1. Çevre Değişkenlerini Yükle (.env)
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GREEN_API_INSTANCE_ID = os.getenv("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
# Eğer customers.json'da yoksa kullanılacak varsayılan Google Sheets ID'si
DEFAULT_SPREADSHEET_ID = os.getenv("DEFAULT_SPREADSHEET_ID", "https://docs.google.com/spreadsheets/d/1dZtjQ6XcwRk7CTHBfGAIgD2fs6KRIu_xTXFpLjlJF3U/edit?pli=1&gid=0#gid=0")

# OpenAI ve Google Sheets İstemcileri
openai.api_key = OPENAI_API_KEY
gc = gspread.service_account(filename=GOOGLE_SERVICE_ACCOUNT_FILE)

app = FastAPI(title="WhatsApp Google Sheets Bot")


def load_customers():
    """Müşteri veritabanını (customers.json) okur."""
    if os.path.exists("customers.json"):
        try:
            with open("customers.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"customers.json okuma hatası: {e}")
    return {}


def send_whatsapp_message(chat_id: str, text: str):
    """WhatsApp'tan kullanıcıya yanıt mesajı gönderir."""
    url = f"https://api.greenapi.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {"chatId": chat_id, "message": text}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"WhatsApp yanıtı gönderildi ({chat_id}): {res.status_code}")
    except Exception as e:
        print(f"WhatsApp mesaj hatası: {e}")


def process_voice_or_text(data: dict):
    """Arka planda çalışacak ses/metin işleme mantığı."""
    try:
        sender_data = data.get("senderData", {})
        chat_id = sender_data.get("chatId")
        print(f"--- İŞLEM BAŞLADI | Chat ID: {chat_id} ---")

        customers = load_customers()
        target_spreadsheet_id = None

        # A) Müşteri ve Abonelik Kontrolü
        if chat_id in customers:
            customer = customers[chat_id]
            if customer.get("status") != "ACTIVE":
                send_whatsapp_message(chat_id, "❌ Aboneliğiniz pasif durumdadır. Yenilemek için iletişime geçin.")
                print(f"Pasif müşteri: {chat_id}")
                return
            target_spreadsheet_id = customer.get("spreadsheet_id")
        else:
            # Kayıtlı değilse varsayılan spreadsheet_id veya fallback
            print(f"Kayıtsız numara tespit edildi: {chat_id}")
            target_spreadsheet_id = DEFAULT_SPREADSHEET_ID

        if not target_spreadsheet_id or target_spreadsheet_id == "BURAYA_GOOGLE_SHEET_ID_YAZABILIRSIN":
            print("HATA: Hedef Google Sheets ID bulunamadı!")
            send_whatsapp_message(chat_id, "⚠️ Sistemde tanımlı bir Google Sheets tablosu bulunamadı.")
            return

        # B) Mesaj Verisini Al (Ses veya Metin)
        message_data = data.get("messageData", {})
        message_type = message_data.get("typeMessage")
        raw_text = ""

        # Ses Mesajı Geldi İse:
        if message_type in ["audioMessage", "voiceMessage"]:
            file_data = message_data.get("fileMessageData", {})
            download_url = file_data.get("downloadUrl")

            if download_url:
                print("Ses dosyası indiriliyor...")
                audio_bytes = requests.get(download_url).content
                temp_filename = f"temp_{data.get('idMessage', 'voice')}.ogg"

                with open(temp_filename, "wb") as f:
                    f.write(audio_bytes)

                print("Whisper STT çalıştırılıyor...")
                with open(temp_filename, "rb") as audio_file:
                    transcript = openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="tr"
                    )
                    raw_text = transcript.text
                print(f"Transkripsiyon: {raw_text}")

                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

        # Yazılı Metin Geldi İse:
        elif message_type in ["textMessage", "extendedTextMessage"]:
            raw_text = message_data.get("textMessageData", {}).get("textMessage", "")
            print(f"Gelen Metin: {raw_text}")

        if not raw_text:
            print("İşlenecek metin bulunamadı.")
            return

        # C) GPT-4o-mini ile Veriyi Yapılandır
        print("GPT-4o-mini analizi yapılıyor...")
        system_prompt = """
        Gelen Türkçe metni analiz et ve SADECE şu JSON formatında çıktı ver:
        {
          "musteri": "Müşteri/Şirket adı (Yoksa 'Belirtilmedi')",
          "islem": "Yapılan işlem veya ürün açıklaması",
          "miktar": "Miktar (Yoksa null)",
          "tutar": "Sayısal tutar (TL cinsinden rakam, yoksa null)",
          "tip": "Gelir" veya "Gider" veya "Sipariş" veya "Not"
        }
        """

        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.1
        )

        parsed_json = json.loads(completion.choices[0].message.content)
        print(f"GPT Çıktısı: {parsed_json}")

        # D) Müşterinin Google Sheet Tablosuna Yaz
        print(f"Google Sheets'e yazılıyor (Sheet ID: {target_spreadsheet_id})...")
        sheet = gc.open_by_key(target_spreadsheet_id).sheet1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        row = [
            now_str,
            parsed_json.get("musteri", "Belirtilmedi"),
            parsed_json.get("islem", "-"),
            parsed_json.get("miktar", ""),
            parsed_json.get("tutar", ""),
            parsed_json.get("tip", "Not")
        ]
        sheet.append_row(row)
        print("Google Sheets'e başarıyla eklendi! ✅")

        # E) WhatsApp Teyit Mesajı
        musteri_adi = parsed_json.get("musteri", "Belirtilmedi")
        tutar_val = parsed_json.get("tutar")
        tutar_str = f"{tutar_val} TL" if tutar_val else "Tutar Belirtilmedi"
        islem_tipi = parsed_json.get("tip", "İşlem")

        reply_text = f"✅ \"{musteri_adi} - {tutar_str} ({islem_tipi})\" Google Tablonuza eklendi!"
        send_whatsapp_message(chat_id, reply_text)

    except Exception as e:
        print(f"İşlem hatası: {e}")


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    print("--- GELEN WEBHOOK PAYLOAD ---")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if data.get("typeWebhook") == "incomingMessageReceived":
        background_tasks.add_task(process_voice_or_text, data)
    return {"status": "ok"}