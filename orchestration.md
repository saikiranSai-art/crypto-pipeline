# Workflow Orchestration Guide

This document describes how to schedule and automate the execution of the Crypto Market Intelligence ETL Pipeline.

## Windows Automation (Task Scheduler)

Since the target environment is Windows, you can automate execution using Windows Task Scheduler.

### Step 1: Create a Batch Wrapper Script
To run the Python script reliably, create a file named `run_pipeline.bat` in the root of the project:

```batch
@echo off
cd /d "C:\Users\saiki\OneDrive\Documents\BI-Project\crypto-bi-etl-project"
call .venv\Scripts\activate
python src/main.py
pause
```

### Step 2: Register the Task
1. Open **Task Scheduler** in Windows.
2. Click **Create Basic Task** in the Actions pane on the right.
3. **Name**: `Crypto_BI_ETL_Pipeline`
4. **Trigger**: Select **Daily** or **Hourly** depending on preference.
5. **Start Time**: Set the desired execution time.
6. **Action**: Choose **Start a program**.
7. **Program/script**: Browse and select the `run_pipeline.bat` script.
8. **Start in (optional)**: Enter `C:\Users\saiki\OneDrive\Documents\BI-Project\crypto-bi-etl-project`
9. Click **Finish**.

---

## Linux / macOS Automation (cron)

For POSIX-compliant environments, use `cron`.

### Step 1: Create a Shell Wrapper Script
Create a file named `run_pipeline.sh` in the root of the project:

```bash
#!/bin/bash
cd /Users/username/crypto-bi-etl-project
source .venv/bin/activate
python src/main.py
```
Make it executable:
```bash
chmod +x run_pipeline.sh
```

### Step 2: Configure the Crontab
Open the cron scheduler editor:
```bash
crontab -e
```
Add a line to run the pipeline every hour:
```cron
0 * * * * /Users/username/crypto-bi-etl-project/run_pipeline.sh >> /Users/username/crypto-bi-etl-project/data/cron_logs.log 2>&1
```
