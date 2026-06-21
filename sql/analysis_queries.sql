-- Analytical SQL Queries for Crypto BI Pipeline

-- Query 1: Top 10 Gainers in the last 24h
SELECT 
    d.name, 
    d.symbol, 
    f.current_price_usd, 
    f.price_change_percentage_24h
FROM fact_market_snapshot f
JOIN dim_coin d ON f.coin_id = d.coin_id
WHERE f.extracted_at = (SELECT MAX(extracted_at) FROM fact_market_snapshot)
ORDER BY f.price_change_percentage_24h DESC
LIMIT 10;

-- Query 2: Top 10 Losers in the last 24h
SELECT 
    d.name, 
    d.symbol, 
    f.current_price_usd, 
    f.price_change_percentage_24h
FROM fact_market_snapshot f
JOIN dim_coin d ON f.coin_id = d.coin_id
WHERE f.extracted_at = (SELECT MAX(extracted_at) FROM fact_market_snapshot)
ORDER BY f.price_change_percentage_24h ASC
LIMIT 10;

-- Query 3: Top 10 coins by market capitalization
SELECT 
    d.market_cap_rank, 
    d.name, 
    d.symbol, 
    f.market_cap_usd
FROM fact_market_snapshot f
JOIN dim_coin d ON f.coin_id = d.coin_id
WHERE f.extracted_at = (SELECT MAX(extracted_at) FROM fact_market_snapshot)
ORDER BY f.market_cap_usd DESC
LIMIT 10;

-- Query 4: Most volatile coins in the last 24h
SELECT 
    d.name, 
    d.symbol, 
    f.high_24h_usd, 
    f.low_24h_usd, 
    f.volatility_24h
FROM fact_market_snapshot f
JOIN dim_coin d ON f.coin_id = d.coin_id
WHERE f.extracted_at = (SELECT MAX(extracted_at) FROM fact_market_snapshot)
ORDER BY f.volatility_24h DESC
LIMIT 10;

-- Query 5: Highest volume-to-market-cap ratio (Liquidity)
SELECT 
    d.name, 
    d.symbol, 
    f.total_volume_usd, 
    f.market_cap_usd, 
    f.volume_to_market_cap_ratio
FROM fact_market_snapshot f
JOIN dim_coin d ON f.coin_id = d.coin_id
WHERE f.extracted_at = (SELECT MAX(extracted_at) FROM fact_market_snapshot)
ORDER BY f.volume_to_market_cap_ratio DESC
LIMIT 10;

-- Query 6: Average 24h price change by market cap category
SELECT 
    f.market_cap_category, 
    COUNT(*) AS num_coins,
    AVG(f.price_change_percentage_24h) AS avg_price_change_pct
FROM fact_market_snapshot f
WHERE f.extracted_at = (SELECT MAX(extracted_at) FROM fact_market_snapshot)
GROUP BY f.market_cap_category
ORDER BY avg_price_change_pct DESC;

-- Query 7: Count of coins moving Up, Down, and Neutral
SELECT 
    f.price_direction, 
    COUNT(*) AS coin_count
FROM fact_market_snapshot f
WHERE f.extracted_at = (SELECT MAX(extracted_at) FROM fact_market_snapshot)
GROUP BY f.price_direction
ORDER BY coin_count DESC;
