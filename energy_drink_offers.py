""""
Energy Drink Offers Bot
This script fetches energy drink offers and sends them to a Telegram bot.
"""

import os
import re
import json
import random
import html
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import configparser
import logging

# ================================
# Configuration and Logging Setup
# ================================

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

# List of most popular supermarkets in Germany
MOST_POPULAR_SUPERMARKETS = [
    'EDEKA', 'REWE', 'Lidl', 'ALDI NORD', 'PENNY', 'Kaufland',
    'Netto Marken-Discount', 'Rossmann', 'dm', 'Real', 'ALDI SÜD', 'tegut'
]

# Manual reference prices based on product name and size patterns
MANUAL_REFERENCE_PRICES = [
    {
        'product_name': 'red bull energy drink',
        'size_patterns': [r'0[.,]25\s*l', r'025\s*l'],
        'reference_price': 1.39
    },
    {
        'product_name': 'effect energy drink',
        'size_patterns': [r'1[-\s]?l[-\s]?fl', r'1\s*l\s*fl'],
        'reference_price': 2.49
    },
    {
        'product_name': 'effect energy drink',
        'size_patterns': [r'0[.,]33\s*liter', r'0.33\s*liter'],
        'reference_price': 1.09
    }
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("energy_drink_bot.log"),
        logging.StreamHandler()
    ]
)

# =============================
# Configuration File Handling
# =============================

# Read configuration from config.ini
config = configparser.ConfigParser()

def update_api_keys(x_apikey, x_clientkey):
    """Updates the API keys in the config.ini file."""
    logging.info("Updating API keys in config.ini...")

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
        logging.info("API keys successfully written to config.ini.")
    except Exception as error:
        logging.error(f"Error writing to config.ini: {error}")

def retrieve_api_keys():
    """Retrieves API keys from the Marktguru website."""
    logging.info("Retrieving API keys from Marktguru...")

    try:
        response = requests.get("https://www.marktguru.de/", timeout=10)
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
                logging.info(f"Retrieved x_apikey: {x_apikey}, x_clientkey: {x_clientkey}")
                update_api_keys(x_apikey, x_clientkey)
            else:
                logging.error("Failed to find API keys in the response.")
        else:
            logging.error(f"Failed to retrieve API keys. Status code: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Exception occurred while retrieving API keys: {e}")

# Initialize config
if os.path.exists(CONFIG_FILE_PATH):
    logging.info("Loading config.ini...")
    config.read(CONFIG_FILE_PATH)
else:
    logging.info("Creating new config.ini...")
    config['Telegram'] = {'bot_token': '', 'chat_id': ''}
    config['API'] = {'x_apikey': '', 'x_clientkey': ''}
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as config_file:
            config.write(config_file)
        logging.info("config.ini created successfully.")
    except Exception as error:
        logging.error(f"Error creating config.ini: {error}")

# Retrieve API keys if not present
if not config.get('API', 'x_apikey') or not config.get('API', 'x_clientkey'):
    retrieve_api_keys()

# Telegram credentials
TELEGRAM_BOT_TOKEN = config.get('Telegram', 'bot_token')
CHAT_ID = config.get('Telegram', 'chat_id')

# ==============================
# Utility Functions
# ==============================

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
            logging.error(f"Error decoding '{FACTS_FILE_PATH}'. Please check the JSON format.")
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

    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            offers = response.json().get('results', [])
            if USE_SUPERMARKET_FILTER:
                return [
                    offer for offer in offers
                    if offer.get('advertisers', [{}])[0].get('name', '') in MOST_POPULAR_SUPERMARKETS
                ]
            return offers
        logging.error(f"Error {response.status_code}: {response.text}")
    except requests.RequestException as e:
        logging.error(f"Exception occurred while fetching offers: {e}")
    return []

def load_blacklist(blacklist_file='blacklist.json'):
    """Loads blacklisted terms from blacklist.json."""
    try:
        with open(blacklist_file, 'r', encoding='utf-8') as file:
            data = file.read().strip()
            if not data:
                return []
            # Convert all blacklisted terms to lowercase for case-insensitive matching
            return [term.lower() for term in json.loads(data).get('blacklisted_terms', [])]
    except FileNotFoundError:
        logging.error(f"Blacklist file '{blacklist_file}' not found.")
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding '{blacklist_file}'. Please check the JSON format.")
        return []

def get_manual_reference_price(product_name, description):
    """
    Returns the manual reference price for a given product based on its name and description.
    If no manual reference price is found, returns None.
    """
    for entry in MANUAL_REFERENCE_PRICES:
        if entry['product_name'] in product_name:
            for pattern in entry['size_patterns']:
                if re.search(pattern, description, re.IGNORECASE):
                    return entry['reference_price']
    return None

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

# ======================================
# Offer Formatting and Message Generation
# ======================================

def format_offers_for_all_cities(all_offers):
    """Formats the offers and generates the final message."""
    today = datetime.today()
    week_number = today.isocalendar()[1]
    message = f"<b>🥤 Weekly Energy Drink Offers 🥤</b>\n\n"
    message += f"<i>Week {week_number} ({today.strftime('%d.%m.%Y')})</i>\n\n"

    blacklist = load_blacklist()

    unique_offers = {}
    tracked_offers = set()

    for city, offers in all_offers.items():
        for offer in offers:
            store = html.escape(offer.get('advertisers', [{}])[0].get('name', 'Unknown Store'))
            price = offer.get('price')
            if price is not None:
                try:
                    price = float(price)
                except ValueError:
                    price = 0.0
            else:
                price = 0.0  # Fallback if price is not available

            product_name = html.escape(offer.get('product', {}).get('name', 'No Title').strip().lower())
            brand_name = html.escape(offer.get('brand', {}).get('name', 'Unknown Brand'))

            # Case-insensitive blacklist filtering
            if any(blacklisted_term in product_name for blacklisted_term in blacklist):
                logging.info(f"Excluded offer '{product_name}' due to blacklist.")
                continue

            unique_identifier = (product_name, brand_name, price, store)

            if unique_identifier in tracked_offers:
                continue

            tracked_offers.add(unique_identifier)

            if store not in unique_offers:
                unique_offers[store] = []

            description = html.escape(offer.get('description', '').lower())  # Convert description to lowercase for matching
            validity = ''
            if 'validityDates' in offer and offer['validityDates']:
                try:
                    valid_from = datetime.strptime(offer['validityDates'][0].get('from', '')[:10], '%Y-%m-%d').strftime('%d.%m.%Y')
                    valid_to = datetime.strptime(offer['validityDates'][0].get('to', '')[:10], '%Y-%m-%d').strftime('%d.%m.%Y')
                    validity = f"{valid_from} to {valid_to}"
                except (ValueError, TypeError):
                    validity = "Validity date not available"
            else:
                validity = "Validity date not available"

            # Retrieve manual reference price if applicable
            manual_reference_price = get_manual_reference_price(product_name, description)
            if manual_reference_price is not None:
                reference_price = manual_reference_price
                reference_source = "manual"  # Flag to indicate manual reference price
                logging.info(f"Using manual reference price for '{product_name}': €{reference_price:.2f}")
            else:
                # Extract referencePrice as UVP, if available
                reference_price = offer.get('referencePrice')
                if reference_price:
                    try:
                        reference_price = float(reference_price)
                        reference_source = "api"  # Flag to indicate API-provided reference price
                        logging.info(f"Using API reference price for '{product_name}': €{reference_price:.2f}")
                    except ValueError:
                        reference_price = None
                        reference_source = "none"
                        logging.warning(f"Invalid referencePrice format for '{product_name}'.")
                else:
                    reference_price = None
                    reference_source = "none"

            # Calculate savings if reference_price is available
            if reference_price is not None:
                try:
                    savings = reference_price - price
                except TypeError:
                    savings = 0.0
            else:
                savings = 0.0

            # Updated Price Formatting with Manual Reference Price Indicator
            if reference_price and savings > 0:
                # Determine the indicator based on the reference source
                if reference_source == "manual":
                    manual_indicator = " 🛠️"  # You can choose any suitable emoji or text
                else:
                    manual_indicator = ""
                offer_text = (
                    f"• <b>{brand_name.title()} {product_name.title()}</b>\n"
                    f"  💶<b>Price:</b><s>€{reference_price:.2f}</s> €{price:.2f} (You save €{savings:.2f}!){manual_indicator}\n"
                    f"  📄 <i>{description}</i>\n"
                    f"  📅 <b>Valid:</b> {validity}\n\n"
                )
            else:
                # Fallback if referencePrice is not available or no savings
                offer_text = (
                    f"• <b>{brand_name.title()} {product_name.title()}</b>\n"
                    f"  💶<b>Price:</b> €{price:.2f}\n"
                    f"  📄 <i>{description}</i>\n"
                    f"  📅 <b>Valid:</b> {validity}\n\n"
                )

            unique_offers[store].append(offer_text)

    for store, offers in unique_offers.items():
        if offers:
            message += f"<b>Offers at {store}:</b>\n"
            message += ''.join(offers)
            message += '\n'

    energy_drink_facts = load_energy_drink_facts()

    if energy_drink_facts:
        fact = random.choice(energy_drink_facts) if energy_drink_facts else None
        if fact:
            message += "<b>🔍 Energy Drink Fact 🔍</b>\n\n"
            message += f"{html.escape(fact)}\n"
    else:
        message += "No Energy Drink facts available."

    return split_message(message)

# ======================================
# Telegram Messaging Functions
# ======================================

def send_telegram_message(message_parts):
    """Sends multiple messages if needed and pins the last one."""
    if config.has_option('Telegram', 'chat_id'):
        chat_ids = config.get('Telegram', 'chat_id').split(',')
    else:
        logging.error("No 'chat_id' found in config.ini. Please add chat IDs.")
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

            try:
                response = requests.post(telegram_url, data=payload, timeout=10)
                if response.status_code == 200:
                    logging.info(f"Message part sent successfully to chat ID {chat_id}!")
                    message_id_to_pin = response.json().get('result', {}).get('message_id')
                else:
                    logging.error(f"Failed to send message to chat ID {chat_id}. Error {response.status_code}: {response.text}")
                    return
            except requests.RequestException as e:
                logging.error(f"Exception occurred while sending message to chat ID {chat_id}: {e}")
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

    try:
        response = requests.post(pin_url, data=payload, timeout=10)
        if response.status_code == 200:
            logging.info(f"Message pinned successfully in chat ID {chat_id}!")
        else:
            logging.error(f"Failed to pin message in chat ID {chat_id}. Error {response.status_code}: {response.text}")
    except requests.RequestException as e:
        logging.error(f"Exception occurred while pinning message in chat ID {chat_id}: {e}")

# ============================
# Main Execution Function
# ============================

def main():
    """Main function to fetch offers and send them to Telegram."""
    all_offers = {}
    for city, zip_code in BIG_CITIES.items():
        logging.info(f"Fetching offers for {city} (ZIP: {zip_code})...")
        offers = fetch_offers(zip_code)
        all_offers[city] = offers

    message_parts = format_offers_for_all_cities(all_offers)
    send_telegram_message(message_parts)

# ======================
# Script Entry Point
# ======================

if __name__ == '__main__':
    main()
