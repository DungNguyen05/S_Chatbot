import requests
import os
from datetime import datetime
from database import connect_db
from config import API_KEY_COINMARKETCAP

API_KEY = os.getenv("COINMARKETCAPAPI_KEY", API_KEY_COINMARKETCAP)

BASE_URL_COINS = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
BASE_URL_FG = "https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest"

def fetch_coin_data(limit=100, convert="USD"):
    """Fetch top `limit` coins data from the CoinMarketCap API."""
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": API_KEY,
    }
    
    params = {
        "start": 1, 
        "limit": limit,  
        "convert": convert
    }
    
    try:
        # Fetch coin data
        response = requests.get(BASE_URL_COINS, headers=headers, params=params)
        data = response.json()

        if "data" not in data:
            print("❌ Error: No valid data received from the API.")
            return []
        
        coins = []
        for coin_data in data["data"]:
            quote = coin_data["quote"][convert]

            coins.append({
                "name": coin_data["name"],
                "symbol": coin_data["symbol"],
                "price": quote["price"],
                "market_cap": quote["market_cap"],
                "volume_24h": quote["volume_24h"]
            })
        
        print(f"✅ Successfully fetched data for {len(coins)} coins!")
        return coins

    except Exception as e:
        print(f"❌ Error when calling CoinMarketCap API: {e}")
        return []

def fetch_fear_and_greed():
    """Fetch the Fear and Greed index data from CoinMarketCap API."""
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": API_KEY,
    }
    
    try:
        response = requests.get(BASE_URL_FG, headers=headers)
        data = response.json()

        if "data" not in data:
            print("❌ Error: No valid data received from the API.")
            return None
        
        fear_and_greed_data = data["data"]

        # Get the update time and convert it to the correct format
        update_time = fear_and_greed_data.get("update_time", None)
        if update_time:
            update_time = update_time.replace('T', ' ').replace('Z', '') 
            update_time = datetime.strptime(update_time, '%Y-%m-%d %H:%M:%S.%f')

        result = {
            "value": fear_and_greed_data["value"],
            "value_classification": fear_and_greed_data["value_classification"],
            "update_time": update_time
        }
        
        print(f"✅ Successfully fetched Fear and Greed data!")
        return result

    except Exception as e:
        print(f"❌ Error when calling Fear and Greed API: {e}")
        return None

def save_coin_data(coins):
    if not coins:
        print("❌ No coin data to save!")
        return
    
    conn = connect_db()
    cursor = conn.cursor()

    try:
        for coin in coins:
            cursor.execute(
                "INSERT INTO coin_data (name, symbol, price, market_cap, volume_24h) VALUES (%s, %s, %s, %s, %s)",
                (coin["name"], coin["symbol"], coin["price"], coin["market_cap"], coin["volume_24h"])
            )

        conn.commit()
        print(f"✅ Saved {len(coins)} coins to database")

    except Exception as e:
        print(f"⚠️ Error when saving coin data into DB: {e}")

    finally:
        cursor.close()
        conn.close()

def save_fear_and_greed(data):
    if not data:
        print("❌ No Fear and Greed data to save!")
        return
    
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO fear_and_greed (value, value_classification, update_time) VALUES (%s, %s, %s)",
            (data["value"], data["value_classification"], data["update_time"])
        )

        conn.commit()
        print("✅ Fear and Greed data successfully saved into database!")

    except Exception as e:
        print(f"⚠️ Error when saving Fear and Greed data into DB: {e}")

    finally:
        cursor.close()
        conn.close()