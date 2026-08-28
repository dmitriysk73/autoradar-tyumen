@echo off
chcp 65001 >nul
set FORCE_ALL=1
set DETAIL_BUDGET=30
python scraper\run.py
python scraper\health_check.py
python -m http.server 8000
