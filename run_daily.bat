@echo off
cd /d "%~dp0"
python run_pipeline.py >> run_daily_output.log 2>&1