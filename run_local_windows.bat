@echo off
chcp 65001 >nul
set DETAIL_BUDGET=20
set FORCE_ALL=1
python scraper\run.py
python -m http.server 8000
