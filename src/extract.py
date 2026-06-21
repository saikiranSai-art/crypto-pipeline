import json
import logging
import time
from datetime import datetime
import requests
from src import config

logger = logging.getLogger("crypto_bi_pipeline.extract")

def extract_market_data():
    """
    Fetches the top 100 cryptocurrencies by market cap from CoinGecko API.
    Saves the response as a timestamped JSON file in data/raw/.
    Returns the path to the saved raw file.
    """
    logger.info("Starting data extraction from CoinGecko API...")
    
    endpoint = f"{config.COINGECKO_BASE_URL}/coins/markets"
    
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h"
    }
    
    headers = {
        "accept": "application/json"
    }
    
    # Handle API credentials if provided
    if config.COINGECKO_API_KEY:
        # Check if we should use Pro endpoint or Demo endpoint
        # Pro keys use pro-api.coingecko.com, Demo/free keys use api.coingecko.com
        if "pro-api" in config.COINGECKO_BASE_URL:
            headers["x-cg-pro-api-key"] = config.COINGECKO_API_KEY
            logger.info("Using CoinGecko Pro API key headers.")
        else:
            headers["x-cg-demo-api-key"] = config.COINGECKO_API_KEY
            logger.info("Using CoinGecko Demo/Free API key headers.")
            
    # Retry mechanism for API robustness (e.g., rate limits, network blips)
    max_retries = 3
    retry_delay = 10  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Sending GET request to {endpoint} (Attempt {attempt}/{max_retries})...")
            response = requests.get(endpoint, params=params, headers=headers, timeout=15)
            
            if response.status_code == 429:
                logger.warning(f"Rate limited (HTTP 429). Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            if not data:
                raise ValueError("Received empty response from CoinGecko API.")
                
            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"markets_snapshot_{timestamp}.json"
            file_path = config.RAW_DATA_DIR / filename
            latest_path = config.RAW_DATA_DIR / "latest.json"
            
            # Save timestamped JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                
            # Save a copy as latest.json for convenience
            with open(latest_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                
            logger.info(f"Successfully extracted {len(data)} records. Saved raw data to {file_path}")
            return str(file_path)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error on attempt {attempt}: {e}")
            if attempt == max_retries:
                raise
            time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Unexpected error during extraction on attempt {attempt}: {e}")
            if attempt == max_retries:
                raise
            time.sleep(retry_delay)
            
    raise RuntimeError("Failed to extract data after maximum retries.")

if __name__ == "__main__":
    # Ensure config logging output shows
    logger.info("Running extract.py standalone...")
    try:
        saved_file = extract_market_data()
        print(f"Extraction successful. Output file: {saved_file}")
    except Exception as ex:
        print(f"Extraction failed: {ex}")
