import os
import json
import logging
import glob
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from src import config

logger = logging.getLogger("crypto_bi_pipeline.transform")

def find_latest_raw_file():
    """
    Finds the most recently created raw JSON file in data/raw/.
    """
    search_path = str(config.RAW_DATA_DIR / "markets_snapshot_*.json")
    files = glob.glob(search_path)
    if not files:
        latest_fallback = config.RAW_DATA_DIR / "latest.json"
        if latest_fallback.exists():
            return str(latest_fallback)
        raise FileNotFoundError("No raw JSON data files found to transform.")
    # Sort by creation/modification time
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

def transform_raw_data(raw_file_path=None):
    """
    Cleans raw JSON data, converts types, calculates derived metrics,
    and writes to CSV in data/processed/.
    """
    if raw_file_path is None:
        raw_file_path = find_latest_raw_file()
        
    logger.info(f"Starting transformation of raw file: {raw_file_path}")
    
    with open(raw_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if not data:
        raise ValueError("Raw JSON file is empty.")
        
    df = pd.DataFrame(data)
    
    # 1. Clean and Map Columns
    # List of columns to keep and their target names
    column_mapping = {
        "id": "coin_id",
        "symbol": "symbol",
        "name": "name",
        "market_cap_rank": "market_cap_rank",
        "current_price": "current_price_usd",
        "market_cap": "market_cap_usd",
        "total_volume": "total_volume_usd",
        "high_24h": "high_24h_usd",
        "low_24h": "low_24h_usd",
        "price_change_24h": "price_change_24h",
        "price_change_percentage_24h": "price_change_percentage_24h",
        "market_cap_change_percentage_24h": "market_cap_change_percentage_24h"
    }
    
    # Ensure all mapping columns exist in the DataFrame (fill with NaN if missing)
    for col in column_mapping.keys():
        if col not in df.columns:
            df[col] = np.nan
            
    df = df[list(column_mapping.keys())].rename(columns=column_mapping)
    
    # 2. Handle missing or inconsistent data
    # Drop rows where critical identifiers are missing
    df = df.dropna(subset=["coin_id", "symbol", "name"])
    
    # Remove duplicates
    df = df.drop_duplicates(subset=["coin_id"])
    
    # Coerce numeric fields to float/int
    numeric_cols = [
        "market_cap_rank", "current_price_usd", "market_cap_usd", 
        "total_volume_usd", "high_24h_usd", "low_24h_usd", 
        "price_change_24h", "price_change_percentage_24h", 
        "market_cap_change_percentage_24h"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        # Fill missing values with default 0 or 0.0
        if col == "market_cap_rank":
            df[col] = df[col].fillna(999999).astype(int) # Assign a high rank if missing
        else:
            df[col] = df[col].fillna(0.0)
            
    # Clean symbol and name strings
    df["symbol"] = df["symbol"].str.upper().str.strip()
    df["name"] = df["name"].str.strip()
    
    # 3. Add calculated columns
    
    # Volatility 24h = ((high_24h - low_24h) / current_price) * 100
    df["volatility_24h"] = np.where(
        df["current_price_usd"] > 0,
        ((df["high_24h_usd"] - df["low_24h_usd"]) / df["current_price_usd"]) * 100,
        0.0
    )
    
    # Volume-to-market-cap ratio = total_volume / market_cap
    df["volume_to_market_cap_ratio"] = np.where(
        df["market_cap_usd"] > 0,
        df["total_volume_usd"] / df["market_cap_usd"],
        0.0
    )
    
    # Price Direction: Up, Down, Neutral
    df["price_direction"] = np.select(
        [
            df["price_change_percentage_24h"] > 0.05, # > +0.05%
            df["price_change_percentage_24h"] < -0.05  # < -0.05%
        ],
        ["Up", "Down"],
        default="Neutral"
    )
    
    # Market Cap Category: Large Cap (> 10B), Mid Cap (1B - 10B), Small Cap (< 1B)
    df["market_cap_category"] = np.select(
        [
            df["market_cap_usd"] >= 1e10, # 10 Billion USD
            (df["market_cap_usd"] >= 1e9) & (df["market_cap_usd"] < 1e10) # 1 Billion to 10 Billion USD
        ],
        ["Large Cap", "Mid Cap"],
        default="Small Cap"
    )
    
    # Add snapshot date and extraction timestamp
    # Parse timestamp from filename if possible, otherwise use current time
    try:
        filename = os.path.basename(raw_file_path)
        time_str = filename.replace("markets_snapshot_", "").replace(".json", "")
        extracted_dt = datetime.strptime(time_str, "%Y%m%d_%H%M%S")
    except Exception:
        extracted_dt = datetime.now()
        
    df["snapshot_date"] = extracted_dt.date()
    df["extracted_at"] = extracted_dt
    
    # 4. Save processed data to CSV
    timestamp_str = extracted_dt.strftime("%Y%m%d_%H%M%S")
    processed_filename = f"markets_processed_{timestamp_str}.csv"
    processed_file_path = config.PROCESSED_DATA_DIR / processed_filename
    latest_processed_path = config.PROCESSED_DATA_DIR / "latest.csv"
    
    # Save CSV files
    df.to_csv(processed_file_path, index=False, encoding="utf-8")
    df.to_csv(latest_processed_path, index=False, encoding="utf-8")
    
    logger.info(f"Successfully transformed data. Saved processed data to {processed_file_path}")
    return str(processed_file_path)

if __name__ == "__main__":
    logger.info("Running transform.py standalone...")
    try:
        processed_file = transform_raw_data()
        print(f"Transformation successful. Output file: {processed_file}")
    except Exception as ex:
        print(f"Transformation failed: {ex}")
