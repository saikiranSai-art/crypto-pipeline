-- SQL Database Schema Setup - Crypto BI Pipeline

-- 1. dim_coin Table
CREATE TABLE IF NOT EXISTS dim_coin (
    coin_id VARCHAR(100) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    market_cap_rank INT
);

-- 2. fact_market_snapshot Table
CREATE TABLE IF NOT EXISTS fact_market_snapshot (
    snapshot_id INT AUTO_INCREMENT PRIMARY KEY,
    coin_id VARCHAR(100) NOT NULL,
    snapshot_date DATE NOT NULL,
    current_price_usd DOUBLE PRECISION NOT NULL,
    market_cap_usd DOUBLE PRECISION NOT NULL,
    total_volume_usd DOUBLE PRECISION NOT NULL,
    high_24h_usd DOUBLE PRECISION NOT NULL,
    low_24h_usd DOUBLE PRECISION NOT NULL,
    price_change_24h DOUBLE PRECISION NOT NULL,
    price_change_percentage_24h DOUBLE PRECISION NOT NULL,
    market_cap_change_percentage_24h DOUBLE PRECISION NOT NULL,
    volatility_24h DOUBLE PRECISION NOT NULL,
    volume_to_market_cap_ratio DOUBLE PRECISION NOT NULL,
    price_direction VARCHAR(20) NOT NULL,
    market_cap_category VARCHAR(20) NOT NULL,
    extracted_at TIMESTAMP NOT NULL,
    FOREIGN KEY (coin_id) REFERENCES dim_coin(coin_id)
);

-- 3. etl_run_log Table
CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id INT AUTO_INCREMENT PRIMARY KEY,
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    rows_extracted INT NOT NULL,
    rows_loaded INT NOT NULL,
    error_message TEXT
);
