import os
import sys
import time
import logging
import traceback
from datetime import datetime

# Setup path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import config
from src.extract import extract_market_data
from src.transform import transform_raw_data
from src.load import load_processed_data, log_etl_run

logger = logging.getLogger("crypto_bi_pipeline.main")

def send_failure_notification(stage, error_msg):
    """
    Simulates a pipeline failure notification system (e.g., SMTP or Slack Webhook).
    Logs the alert details and writes to data/alerts.log.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alert_text = (
        f"\n=========================================\n"
        f"🚨 PIPELINE FAILURE ALERT [MADSC301 BI]\n"
        f"Timestamp: {timestamp}\n"
        f"Stage: {stage}\n"
        f"Error Details: {error_msg}\n"
        f"=========================================\n"
    )
    logger.error(alert_text)
    
    # Save the alert to a persistent alerts file
    alert_file = config.DATA_DIR / "alerts.log"
    try:
        with open(alert_file, "a", encoding="utf-8") as f:
            f.write(alert_text)
    except Exception as e:
        logger.error(f"Failed to write alert to file: {e}")

def run_pipeline():
    """
    Executes the end-to-end ETL workflow:
    1. Extract (src/extract.py)
    2. Transform (src/transform.py)
    3. Load (src/load.py)
    4. Log run status in etl_run_log
    """
    start_time = time.time()
    logger.info("=========================================")
    logger.info("🚀 STARTING CRYPTO BI ETL PIPELINE RUN 🚀")
    logger.info("=========================================")
    
    rows_extracted = 0
    rows_loaded = 0
    stage = "INITIALIZATION"
    
    try:
        # 1. Extraction Phase
        stage = "EXTRACTION"
        logger.info("--- Stage 1/3: Extracting raw market data ---")
        raw_file_path = extract_market_data()
        
        # Determine number of rows extracted (usually 100 from API)
        import json
        with open(raw_file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            rows_extracted = len(raw_data)
        
        # 2. Transformation Phase
        stage = "TRANSFORMATION"
        logger.info("--- Stage 2/3: Transforming raw data ---")
        processed_file_path = transform_raw_data(raw_file_path)
        
        # 3. Loading Phase
        stage = "LOADING"
        logger.info("--- Stage 3/3: Loading data to database ---")
        rows_loaded = load_processed_data(processed_file_path)
        
        # Log Success in DB
        log_etl_run(
            status="SUCCESS",
            rows_extracted=rows_extracted,
            rows_loaded=rows_loaded
        )
        
        duration = time.time() - start_time
        logger.info("=========================================")
        logger.info(f"🎉 ETL PIPELINE COMPLETE (SUCCESS) 🎉")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Rows Extracted: {rows_extracted} | Rows Loaded: {rows_loaded}")
        logger.info("=========================================")
        
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Exception in {stage} stage: {str(e)}\n{traceback.format_exc()}"
        
        logger.error("=========================================")
        logger.error(f"❌ ETL PIPELINE FAILED (STAGE: {stage}) ❌")
        logger.error(f"Duration: {duration:.2f} seconds")
        logger.error("=========================================")
        
        # Log Failure in DB
        log_etl_run(
            status="FAILED",
            rows_extracted=rows_extracted,
            rows_loaded=0,
            error_message=str(e)
        )
        
        # Trigger Notification
        send_failure_notification(stage, str(e))
        
        # Raise to indicate failure to caller/task schedulers
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()
