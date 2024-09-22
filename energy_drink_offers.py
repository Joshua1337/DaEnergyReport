import os
import configparser
import requests
from bs4 import BeautifulSoup
import re
import datetime
import random
import json
from datetime import datetime
import html

# File paths for config and facts
config_file_path = 'config.ini'
facts_file_path = 'facts.json'

# Toggle supermarket filter (True to filter by popular supermarkets, False to include all)
use_supermarket_filter = True

# List of big cities in Germany with their zip codes
big_cities = {
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

# Function to update API keys in config.ini
def update_api_keys(x_apikey, x_clientkey):
    print("Updating API keys in config.ini...")

    # Ensure the API section exists
    if not config.has_section('API'):
        config.add_section('API')

    # Set the new keys
    config.set('API', 'x_apikey', x_apikey)
    config.set('API', 'x_clientkey', x_clientkey)

    # Write to the config file
    try:
        with open(config_file_path, 'w') as configfile:
            config.write(configfile)
        print("API keys successfully written to config.ini.")
    except Exception as e:
        print(f"Error writing to config.ini: {e}")

# Function to retrieve API keys from Marktguru
def retrieve_api_keys():
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

# Load or create config.ini
if os.path.exists(config_file_path):
    print("Loading config.ini...")
    config.read(config_file_path)
else:
    print("Creating new config.ini...")
    config['Telegram'] = {'bot_token': '', 'chat_id': ''}
    config['API'] = {'x_apikey': '', 'x_clientkey': ''}
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)

# Fetch API keys if not already set or empty
if not config.get('API', 'x_apikey') or not config.get('API', 'x_clientkey'):
    retrieve_api_keys()

# Telegram bot information
TELEGRAM_BOT_TOKEN = config.get('Telegram', 'bot_token')
CHAT_ID = config.get('Telegram', 'chat_id')

# List of most popular supermarkets in Germany
most_popular_supermarkets = [
    'EDEKA', 'REWE', 'Lidl', 'ALDI NORD', 'PENNY', 'Kaufland',
    'Netto Marken-Discount', 'Rossmann', 'dm', 'Real', 'ALDI SÜD', 'tegut' 
]

# Load random energy drink facts from facts.json
def load_energy_drink_facts():
    if os.path.exists(facts_file_path):
        try:
            with open(facts_file_path, 'r') as file:
                data = file.read().strip()  # Read and strip whitespace
                if not data:
                    return []  # Handle empty file
                facts = json.loads(data).get('facts', [])  # Extract the 'facts' list
                # Filter out any empty strings from the facts list
                return [fact for fact in facts if fact.strip()]
        except json.JSONDecodeError:
            print(f"Error decoding '{facts_file_path}'. Please check the JSON format.")
            return []
    else:
        return []

# Function to fetch offers for a given city
def fetch_offers(zip_code):
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
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.marktguru.de/',
        'x-apikey': config.get('API', 'x_apikey'),
        'x-clientkey': config.get('API', 'x_clientkey'),
        'Content-Type': 'application/json',
        'Origin': 'https://www.marktguru.de',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'TE': 'trailers'
    }

    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code == 200:
        offers = response.json().get('results', [])
        if use_supermarket_filter:
            filtered_offers = [
                offer for offer in offers
                if offer.get('advertisers', [{}])[0].get('name', '') in most_popular_supermarkets
            ]
            return filtered_offers
        return offers
    else:
        print(f"Error {response.status_code}: {response.text}")
        return []

# Load blacklist from JSON file
def load_blacklist(blacklist_file='blacklist.json'):
    try:
        with open(blacklist_file, 'r') as file:
            data = file.read().strip()  # Read and strip whitespace
            if not data:
                return []  # Handle empty file
            return json.loads(data).get('blacklisted_terms', [])
    except FileNotFoundError:
        print(f"Blacklist file '{blacklist_file}' not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding '{blacklist_file}'. Please check the JSON format.")
        return []

# Refined function to split messages into chunks if too long (max 4096 characters for Telegram)
def split_message(message, max_length=4000):
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
    else:
        return [message]

def format_offers_for_all_cities(all_offers):
    today = datetime.today()
    week_number = today.isocalendar()[1]
    message = f"<b>🥤 Wöchentliche Energy Drink Angebote 🥤</b>\n\n"
    message += f"<i>Woche {week_number} ({today.strftime('%d.%m.%Y')})</i>\n\n"

    # Load the blacklist
    blacklist = load_blacklist()

    unique_offers = {}  # To store unique offers by store
    tracked_offers = set()  # To track unique identifiers to avoid duplicates

    for city, offers in all_offers.items():
        for offer in offers:
            store = html.escape(offer.get('advertisers', [{}])[0].get('name', 'Unbekannter Laden'))
            price = offer.get('price')
            product_name = html.escape(offer.get('product', {}).get('name', 'Kein Titel').strip().lower())
            brand_name = html.escape(offer.get('brand', {}).get('name', 'Unbekannte Marke'))

            if any(blacklisted_term in product_name for blacklisted_term in blacklist):
                continue  # Skip this offer if a blacklisted term is found

            unique_identifier = (product_name, brand_name, price, store)

            if unique_identifier in tracked_offers:
                continue

            tracked_offers.add(unique_identifier)

            if store not in unique_offers:
                unique_offers[store] = []

            description = html.escape(offer.get('description', ''))  # Escape any special characters
            validity = ''
            if 'validityDates' in offer and offer['validityDates']:
                valid_from = datetime.strptime(offer['validityDates'][0].get('from', '')[:10], '%Y-%m-%d').strftime('%d.%m.%Y')
                valid_to = datetime.strptime(offer['validityDates'][0].get('to', '')[:10], '%Y-%m-%d').strftime('%d.%m.%Y')
                validity = f"{valid_from} bis {valid_to}"
            else:
                validity = "Gültigkeitsdatum nicht verfügbar"

            offer_text = (
                f"• <b>{brand_name.title()} {product_name.title()}</b>\n"
                f"  💶 <u><b>Preis:</b> €{price:.2f}</u>\n"
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

# Function to send multiple messages if needed and pin the last one
def send_telegram_message(message_parts):
    if config.has_option('Telegram', 'chat_id'):
        chat_ids = config.get('Telegram', 'chat_id').split(',')
    else:
        print("No 'chat_id' found in config.ini. Please add chat IDs.")
        return

    for chat_id in chat_ids:
        chat_id = chat_id.strip()  # Remove any extra spaces
        message_id_to_pin = None  # Track message ID to pin the last message

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

# Function to pin a message in Telegram chat for each chat ID
def pin_message_in_chat(chat_id, message_id):
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

# Main function
def main():
    all_offers = {}
    for city, zip_code in big_cities.items():
        offers = fetch_offers(zip_code)
        all_offers[city] = offers

    message_parts = format_offers_for_all_cities(all_offers)
    send_telegram_message(message_parts)

if __name__ == '__main__':
    main()
