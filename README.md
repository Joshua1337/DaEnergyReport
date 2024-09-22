# Energy Drink Offers Bot

A Python script that fetches energy drink offers from major German cities, filters them by popular supermarkets, and sends a neatly formatted overview to a Telegram chat. The script includes blacklist filtering, random energy drink facts, and automatic message pinning in Telegram groups.

## Features

- **City-based filtering**: Fetch offers from major German cities like Berlin, Hamburg, Munich, and more.
- **Blacklist support**: Exclude unwanted products such as batteries or specific brands.
- **Random energy drink facts**: Display a fun fact with each message.
- **HTML-formatted messages**: Clean, readable messages with bold, italics, and emojis.
- **Automatic message pinning**: Pins the last sent message in Telegram groups.
- **Long message handling**: Automatically splits long messages into chunks to meet Telegram's 4096-character limit.

## How It Works

1. **City-based Offer Fetching**: The script pulls energy drink offers from various cities across Germany, filtering out irrelevant products and organizing them by city.
2. **Blacklist**: Products containing blacklisted terms (stored in `blacklist.json`) are filtered out of the final results.
3. **Random Energy Drink Facts**: At the end of the message, the bot sends a random energy drink fact (stored in `facts.json`).
4. **Automatic Message Pinning**: After sending the message to the Telegram chat, the bot automatically pins the last message in the chat.

## Installation and Setup

### Prerequisites

- **Python 3.x**: Make sure you have Python installed. You can download it [here](https://www.python.org/downloads/).
- **Pip**: Python’s package installer (usually comes pre-installed with Python).
- **Telegram Bot**: You need a Telegram bot token, which you can obtain from [BotFather](https://t.me/BotFather).

### Steps

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/energy-drink-offers-bot.git
   cd energy-drink-offers-bot
   ```

2. **Install the required dependencies**:

   Create a virtual environment (optional but recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

   Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your `config.ini`**:

   Copy the provided `config.ini` template:

   ```bash
   cp config.ini.example config.ini
   ```

   Open `config.ini` and add your Telegram bot token and chat ID:
   (You can leave api shit empty, the script gets that data itself after first run)

   ```ini
   [Telegram]
   bot_token = your_telegram_bot_token
   chat_id = your_chat_id

   [API]
   x_apikey = 
   x_clientkey = 
   ```

4. **Blacklist setup**:

   Create a `blacklist.json` file to exclude certain products:

   ```json
   {
     "blacklisted_terms": ["batterie", "akku", "l'oréal", "hydra"]
   }
   ```

5. **Facts setup**:

   Add some energy drink facts to `facts.json`:

   ```json
   {
     "facts": [
       "Red Bull was the first energy drink to become globally known.",
       "Energy drinks can improve focus and reaction times."
     ]
   }
   ```

6. **Run the script**:

   To run the bot, use the following command:

   ```bash
   python energy_drink_offers.py
   ```

## Setting Up a Cron Job

To automate the running of the script at specific intervals (e.g., weekly), you can set up a cron job. Follow these steps:

1. **Open your crontab**:

   ```bash
   crontab -e
   ```

2. **Add the cron job**:

   Here’s an example to run the script every Monday at 4:20 AM:

   ```bash
   20 4 * * 1 /path/to/your/venv/bin/python /path/to/your/repo/energy_drink_offers.py >> /path/to/your/repo/logs/output.log 2>&1
   ```

   - Replace `/path/to/your/venv/bin/python` with the path to your virtual environment's Python binary.
   - Replace `/path/to/your/repo` with the path to where the script is stored.
   - The output will be logged in `logs/output.log`.

3. **Save and exit**.

## Contribution

Feel free to fork this repository, open issues, or submit pull requests for any feature enhancements or bug fixes.

---

## License

This project is licensed under the MIT License.
