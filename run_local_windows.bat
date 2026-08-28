@echo off
chcp 65001 >nul
set DETAIL_BUDGET=20
python scraper\run.py
python -m http.server 8000
