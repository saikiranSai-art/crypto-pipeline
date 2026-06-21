import os
import logging
import pandas as pd
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Double, Date, DateTime, Text, ForeignKey, text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from src import config

logger = logging.getLogger("crypto_bi_pipeline.load")

Base = declarative_base()

class DimCoin(Base):
    __tablename__ = 'dim_coin'
    
    coin_id = Column(String(100), primary_key=True)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    market_cap_rank = Column(Integer, nullable=True)

class FactMarketSnapshot(Base):
    __tablename__ = 'fact_market_snapshot'
    
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    coin_id = Column(String(100), ForeignKey('dim_coin.coin_id'), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    current_price_usd = Column(Double, nullable=False)
    market_cap_usd = Column(Double, nullable=False)
    total_volume_usd = Column(Double, nullable=False)
    high_24h_usd = Column(Double, nullable=False)
    low_24h_usd = Column(Double, nullable=False)
    price_change_24h = Column(Double, nullable=False)
    price_change_percentage_24h = Column(Double, nullable=False)
    market_cap_change_percentage_24h = Column(Double, nullable=False)
    volatility_24h = Column(Double, nullable=False)
    volume_to_market_cap_ratio = Column(Double, nullable=False)
    price_direction = Column(String(20), nullable=False)
    market_cap_category = Column(String(20), nullable=False)
    extracted_at = Column(DateTime, nullable=False)

class EtlRunLog(Base):
    __tablename__ = 'etl_run_log'
    
    run_id = Column(Integer, primary_key=True, autoincrement=True)
    run_timestamp = Column(DateTime, default=datetime.now)
    status = Column(String(20), nullable=False)
    rows_extracted = Column(Integer, nullable=False)
    rows_loaded = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=True)

def create_database_if_not_exists():
    """
    Connects to the database server using server-level credentials (without database name)
    and ensures the database exists before proceeding with table definitions.
    """
    db_type = config.DB_TYPE
    host = config.DB_HOST
    port = config.DB_PORT
    user = config.DB_USER
    password = config.DB_PASSWORD
    db_name = config.DB_NAME
    
    if db_type == "mysql":
        # Connect to MySQL server without specifying database
        server_uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/"
        engine = create_engine(server_uri)
        try:
            with engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
                logger.info(f"Database '{db_name}' verified or created in MySQL.")
        except Exception as e:
            logger.error(f"Error checking/creating MySQL database: {e}")
            raise
    else:
        # Connect to default postgres DB
        server_uri = f"postgresql://{user}:{password}@{host}:{port}/postgres"
        engine = create_engine(server_uri)
        try:
            # PostgreSQL doesn't support CREATE DATABASE IF NOT EXISTS natively in a single statement
            # We check if it exists in pg_database first
            with engine.connect() as conn:
                # Set execution options to autocommit because database creation cannot run inside transaction block
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"))
                if not result.fetchone():
                    conn.execute(text(f"CREATE DATABASE {db_name}"))
                    logger.info(f"Database '{db_name}' created in PostgreSQL.")
                else:
                    logger.info(f"Database '{db_name}' already exists in PostgreSQL.")
        except Exception as e:
            logger.error(f"Error checking/creating PostgreSQL database: {e}")
            # We don't raise here, as the DB might be pre-created or connection might be direct
            pass

def init_db(engine):
    """
    Initializes database tables.
    """
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully (if they didn't exist).")

def load_processed_data(processed_file_path):
    """
    Connects to the database, upserts dim_coin, inserts fact_market_snapshot,
    and returns the count of loaded rows.
    """
    if not os.path.exists(processed_file_path):
        raise FileNotFoundError(f"Processed file not found: {processed_file_path}")
        
    logger.info(f"Loading data from processed file: {processed_file_path}")
    df = pd.read_csv(processed_file_path)
    
    # Pre-create database if not exists
    create_database_if_not_exists()
    
    # Connect to the specific database
    db_uri = config.get_db_uri()
    engine = create_engine(db_uri)
    init_db(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    rows_loaded = 0
    try:
        # 1. Upsert dim_coin entries
        # Since it's only 100 entries, a simple check-and-insert/update is fast and database agnostic
        coin_ids = df['coin_id'].tolist()
        existing_coins = {c.coin_id: c for c in session.query(DimCoin).filter(DimCoin.coin_id.in_(coin_ids)).all()}
        
        for _, row in df.iterrows():
            coin_id = row['coin_id']
            symbol = row['symbol']
            name = row['name']
            market_cap_rank = int(row['market_cap_rank']) if pd.notna(row['market_cap_rank']) else None
            
            if coin_id in existing_coins:
                # Update existing coin dimension
                coin = existing_coins[coin_id]
                coin.symbol = symbol
                coin.name = name
                coin.market_cap_rank = market_cap_rank
            else:
                # Add new coin dimension
                new_coin = DimCoin(
                    coin_id=coin_id,
                    symbol=symbol,
                    name=name,
                    market_cap_rank=market_cap_rank
                )
                session.add(new_coin)
                
        # Flush to make sure dims are available for foreign key constraints
        session.flush()
        
        # 2. Insert fact_market_snapshot entries
        for _, row in df.iterrows():
            # Robust parsing for extracted_at
            extracted_at_str = row['extracted_at']
            try:
                extracted_at_dt = datetime.strptime(extracted_at_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                try:
                    extracted_at_dt = datetime.strptime(extracted_at_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    extracted_at_dt = datetime.now()

            fact = FactMarketSnapshot(
                coin_id=row['coin_id'],
                snapshot_date=datetime.strptime(row['snapshot_date'], "%Y-%m-%d").date(),
                current_price_usd=float(row['current_price_usd']),
                market_cap_usd=float(row['market_cap_usd']),
                total_volume_usd=float(row['total_volume_usd']),
                high_24h_usd=float(row['high_24h_usd']),
                low_24h_usd=float(row['low_24h_usd']),
                price_change_24h=float(row['price_change_24h']),
                price_change_percentage_24h=float(row['price_change_percentage_24h']),
                market_cap_change_percentage_24h=float(row['market_cap_change_percentage_24h']),
                volatility_24h=float(row['volatility_24h']),
                volume_to_market_cap_ratio=float(row['volume_to_market_cap_ratio']),
                price_direction=row['price_direction'],
                market_cap_category=row['market_cap_category'],
                extracted_at=extracted_at_dt
            )
            session.add(fact)
            rows_loaded += 1
            
        session.commit()
        logger.info(f"Successfully loaded {rows_loaded} rows into database.")
        return rows_loaded
    except Exception as e:
        session.rollback()
        logger.error(f"Error during loading data to DB: {e}")
        raise
    finally:
        session.close()

def log_etl_run(status, rows_extracted, rows_loaded, error_message=None):
    """
    Records an entry in the etl_run_log table.
    """
    try:
        # Create database and connection if logging directly
        db_uri = config.get_db_uri()
        engine = create_engine(db_uri)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        run_log = EtlRunLog(
            run_timestamp=datetime.now(),
            status=status,
            rows_extracted=rows_extracted,
            rows_loaded=rows_loaded,
            error_message=error_message
        )
        session.add(run_log)
        session.commit()
        session.close()
        logger.info(f"ETL run log saved. Status={status}, Loaded={rows_loaded}")
    except Exception as e:
        logger.error(f"Failed to write to etl_run_log table: {e}")

if __name__ == "__main__":
    # Test DB load logic
    # Set up basic logging output for debug
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing load.py module...")
    
    # Try finding latest processed CSV file to load
    import glob
    search_path = str(config.PROCESSED_DATA_DIR / "markets_processed_*.csv")
    files = glob.glob(search_path)
    if files:
        latest_file = max(files, key=os.path.getmtime)
        try:
            loaded_count = load_processed_data(latest_file)
            print(f"Test loading successful. Loaded {loaded_count} rows.")
        except Exception as ex:
            print(f"Test loading failed: {ex}")
    else:
        print("No processed CSV files found to test loading.")
