import requests

# Render canlı webhook adresin
url = "https://whatsapp-sheets-bot-dvhc.onrender.com/webhook"

# Green-API'den gelen örnek bir WhatsApp mesajı verisi
mock_payload = {
    "typeWebhook": "incomingMessageReceived",
    "instanceData": {
        "idInstance": 12345,
        "wid": "12345@c.us",
        "typeInstance": "whatsapp"
    },
    "timestamp": 1578047700,
    "idMessage": "F16361B1686324F08000",
    "senderData": {
        "chatId": "905551112233@c.us",
        "sender": "905551112233@c.us",
        "senderName": "Test Kullanici"
    },
    "messageData": {
        "typeMessage": "extendedTextMessage",
        "textMessageData": {
            "textMessage": "Bugün marketten 200 TL'ye kahve ve çikolata aldım"
        }
    }
}

response = requests.post(url, json=mock_payload)
print("Render Yanıtı Status Code:", response.status_code)
print("Render Yanıtı Body:", response.text)