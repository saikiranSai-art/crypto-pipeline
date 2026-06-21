@echo off
title Crypto BI ETL Pipeline Runner
echo ==================================================
echo Starting Crypto BI ETL Pipeline Orchestrator...
echo ==================================================
cd /d "C:\Users\saiki\OneDrive\Documents\BI-Project\crypto-bi-etl-project\"
call .venv\Scripts\activate
python src/main.py
echo ==================================================
echo Pipeline execution finished.
echo ==================================================
pause
