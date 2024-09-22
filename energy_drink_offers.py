"""
Energy Drink Offers Bot
This script fetches energy drink offers and sends them to a Telegram bot.
"""

import os
import re
import datetime
import json
import random
import html
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# File paths for config and facts
CONFIG_FILE_PATH = 'config.ini'
FACTS_FILE_PATH = 'facts.json'

# Toggle supermarket filter (True to filter by popular supermarkets, False to include all)
USE_SUPERMARKET_FILTER = True

# List of big cities in Germany with their zip codes
BIG_CITIES = {
    'Berlin': '10115',
    'Hamburg': '20095',
    'Munich': '80331',
    'Cologne': '50667',
    'Frankfurt': '60311',
    'Stuttgart': '70173',
    'Düsseldorf': '40213',
    'Dortmund': '44135',
    'Essen': '45127',
    'Leipzig': '04109',
}

# Read configuration from config.ini
config = configparser.ConfigParser()


def update_api_keys(x_apikey, x_clientkey):
    """Updates the API keys in the config.ini file."""
    print("Updating API keys in config.ini...")

    # Ensure the API section exists
    if not config.has_section('API'):
        config.add_section('API')

    # Set the new keys
    config.set('API', 'x_apikey', x_apikey)
    config.set('API', 'x_clientkey', x_clientkey)

    # Write to the config file
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as config_file:
            config.write(config_file)
        print("API keys successfully written to config.ini.")
    except Exception as error:
        print(f"Error writing to config.ini: {error}")


def retrieve_api_keys():
    """Retrieves API keys from the Marktguru website."""
    print("Retrieving API keys from Marktguru...")

    response = requests.get("https://www.marktguru.de/")
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Search for API keys in the HTML or scripts using regular expressions
        scripts = soup.find_all('script')
        x_apikey = None
        x_clientkey = None

        for script in scripts:
            script_content = script.string
            if script_content:
                apikey_match = re.search(r'"x_apikey":"(.*?)"', script_content)
                clientkey_match = re.search(r'"x_clientkey":"(.*?)"', script_content)

                if apikey_match:
                    x_apikey = apikey_match.group(1)
                if clientkey_match:
                    x_clientkey = clientkey_match.group(1)

                if x_apikey and x_clientkey:
                    break

        if x_apikey and x_clientkey:
            print(f"Retrieved x_apikey: {x_apikey}, x_clientkey: {x_clientkey}")
            update_api_keys(x_apikey, x_clientkey)
        else:
            print("Failed to find API keys in the response.")
    else:
        print(f"Failed to retrieve API keys. Status code: {response.status_code}")


if os.path.exists(CONFIG_FILE_PATH):
    print("Loading config.ini...")
    config.read(CONFIG_FILE_PATH)
else:
    print("Creating new config.ini...")
    config['Telegram'] = {'bot_token': '', 'chat_id': ''}
    config['API'] = {'x_apikey': '', 'x_clientkey': ''}
    with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as config_file:
        config.write(config_file)

if not config.get('API', 'x_apikey') or not config.get('API', 'x_clientkey'):
    retrieve_api_keys()

TELEGRAM_BOT_TOKEN = config.get('Telegram', 'bot_token')
CHAT_ID = config.get('Telegram', 'chat_id')

# List of most popular supermarkets in Germany
MOST_POPULAR_SUPERMARKETS = [
    'EDEKA', 'REWE', 'Lidl', 'ALDI NORD', 'PENNY', 'Kaufland',
    'Netto Marken-Discount', 'Rossmann', 'dm', 'Real', 'ALDI SÜD', 'tegut'
]


def load_energy_drink_facts():
    """Loads random energy drink facts from facts.json."""
    if os.path.exists(FACTS_FILE_PATH):
        try:
            with open(FACTS_FILE_PATH, 'r', encoding='utf-8') as file:
                data = file.read().strip()
                if not data:
                    return []
                facts = json.loads(data).get('facts', [])
                return [fact for fact in facts if fact.strip()]
        except json.JSONDecodeError:
            print(f"Error decoding '{FACTS_FILE_PATH}'. Please check the JSON format.")
            return []
    return []


def fetch_offers(zip_code):
    """Fetches energy drink offers for a given city."""
    api_url = "https://api.marktguru.de/api/v1/offers/search"
    params = {
        'as': 'web',
        'limit': '100',
        'offset': '0',
        'q': 'energy',
        'zipCode': zip_code
    }
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'x-apikey': config.get('API', 'x_apikey'),
        'x-clientkey': config.get('API', 'x_clientkey'),
        'Content-Type': 'application/json',
    }

    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code == 200:
        offers = response.json().get('results', [])
        if USE_SUPERMARKET_FILTER:
            return [offer for offer in offers if offer.get('advertisers', [{}])[0].get('name', '') in MOST_POPULAR_SUPERMARKETS]
        return offers
    print(f"Error {response.status_code}: {response.text}")
    return []


def load_blacklist(blacklist_file='blacklist.json'):
    """Loads blacklisted terms from blacklist.json."""
    try:
        with open(blacklist_file, 'r', encoding='utf-8') as file:
            data = file.read().strip()
            if not data:
                return []
            return json.loads(data).get('blacklisted_terms', [])
    except FileNotFoundError:
        print(f"Blacklist file '{blacklist_file}' not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding '{blacklist_file}'. Please check the JSON format.")
        return []


def split_message(message, max_length=4000):
    """Splits long messages into chunks."""
    if len(message) > max_length:
        parts = []
        current_part = ""
        for line in message.split("\n"):
            if len(current_part) + len(line) + 1 > max_length:
                parts.append(current_part)
                current_part = line + "\n"
            else:
                current_part += line + "\n"
        if current_part:
            parts.append(current_part)
        return parts
    return [message]


def format_offers_for_all_cities(all_offers):
    """Formats the offers and generates the final message."""
    today = datetime.today()
    week_number = today.isocalendar()[1]
    message = f"<b>🥤 Wöchentliche Energy Drink Angebote 🥤</b>\n\n"
    message += f"<i>Woche {week_number} ({today.strftime('%d.%m.%Y')})</i>\n\n"

    blacklist = load_blacklist()

    unique_offers = {}
    tracked_offers = set()

    for city, offers in all_offers.items():
        for offer in offers:
            store = html.escape(offer.get('advertisers', [{}])[0].get('name', 'Unbekannter Laden'))
            price = offer.get('price')
            product_name = html.escape(offer.get('product', {}).get('name', 'Kein Titel').strip().lower())
            brand_name = html.escape(offer.get('brand', {}).get('name', 'Unbekannte Marke'))

            if any(blacklisted_term in product_name for blacklisted_term in blacklist):
                continue

            unique_identifier = (product_name, brand_name, price, store)

            if unique_identifier in tracked_offers:
                continue

            tracked_offers.add(unique_identifier)

            if store not in unique_offers:
                unique_offers[store] = []

            description = html.escape(offer.get('description', ''))
            validity = ''
            if 'validityDates' in offer and offer['validityDates']:
                valid_from = datetime.strptime(offer['validityDates'][0].get('from', '')[:10], '%Y-%m-%d').strftime('%d.%m.%Y')
                valid_to = datetime.strptime(offer['validityDates'][0].get('to', '')[:10], '%Y-%m-%d').strftime('%d.%m.%Y')
                validity = f"{valid_from} bis {valid_to}"
            else:
                validity = "Gültigkeitsdatum nicht verfügbar"

            offer_text = (
                f"• <b>{brand_name.title()} {product_name.title()}</b>\n"
                f"  💰 <u><b>Preis:</b> €{price:.2f}</u>\n"
                f"  📄 <i>{description}</i>\n"
                f"  📅 <b>Gültig:</b> {validity}\n\n"
            )

            unique_offers[store].append(offer_text)

    for store, offers in unique_offers.items():
        if offers:
            message += f"<b>Angebote bei {store}:</b>\n"
            message += ''.join(offers)
            message += '\n'

    energy_drink_facts = load_energy_drink_facts()

    if energy_drink_facts:
        fact = random.choice(energy_drink_facts) if energy_drink_facts else None
        if fact:
            message += "<b>🔍 Energy Drink Fakt 🔍</b>\n\n"
            message += f"{html.escape(fact)}\n"
    else:
        message += "Keine Energy Drink Fakten verfügbar."

    return split_message(message)


def send_telegram_message(message_parts):
    """Sends multiple messages if needed and pins the last one."""
    if config.has_option('Telegram', 'chat_id'):
        chat_ids = config.get('Telegram', 'chat_id').split(',')
    else:
        print("No 'chat_id' found in config.ini. Please add chat IDs.")
        return

    for chat_id in chat_ids:
        chat_id = chat_id.strip()
        message_id_to_pin = None

        for part in message_parts:
            telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': part,
                'parse_mode': 'HTML'
            }

            response = requests.post(telegram_url, data=payload)

            if response.status_code == 200:
                print(f"Message part sent successfully to chat ID {chat_id}!")
                message_id_to_pin = response.json().get('result', {}).get('message_id')
            else:
                print(f"Failed to send message to chat ID {chat_id}. Error {response.status_code}: {response.text}")
                return

        if message_id_to_pin:
            pin_message_in_chat(chat_id, message_id_to_pin)


def pin_message_in_chat(chat_id, message_id):
    """Pins a message in a Telegram chat."""
    pin_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/pinChatMessage"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id
    }

    response = requests.post(pin_url, data=payload)

    if response.status_code == 200:
        print(f"Message pinned successfully in chat ID {chat_id}!")
    else:
        print(f"Failed to pin message in chat ID {chat_id}. Error {response.status_code}: {response.text}")


def main():
    """Main function to fetch offers and send them to Telegram."""
    all_offers = {}
    for city, zip_code in BIG_CITIES.items():
        offers = fetch_offers(zip_code)
        all_offers[city] = offers

    message_parts = format_offers_for_all_cities(all_offers)
    send_telegram_message(message_parts)


if __name__ == '__main__':
    main()
