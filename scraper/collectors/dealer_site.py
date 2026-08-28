from __future__ import annotations
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from scraper.common import *

def parse_page(html,url,cfg):
    soup=BeautifulSoup(html,"lxml")
    text=soup.get_text("\n",strip=True); flat=clean(text)
    results=[]
    # model-specific anchors/cards
    seen=set()
    for a in soup.find_all("a",href=True):
        node=card_ancestor(a)
        txt=clean(node.get_text(" ",strip=True))
        model=model_from(txt)
        if not model or "TENET" not in txt.upper(): continue
        prices=price_candidates(txt)
        if not prices: continue
        href=urljoin(url,a["href"])
        key=(model,href,tuple(prices[:3]))
        if key in seen: continue
        seen.add(key)
        engine,power,fuel,gearbox,drive,color=vehicle_specs(txt)
        results.append({
          "source":"Сайт дилера","source_id":cfg["id"],
          "source_listing_id":compact_id("|".join(map(str,key))),
          "source_url":href,"dealer_name":cfg.get("dealer",""),"dealer_address":cfg.get("address",""),
          "title":clean(a.get_text(" ",strip=True)) or f"TENET {model}",
          "model":model,"year":extract_year(txt),"trim":trim_from(txt),
          "engine_l":engine,"power_hp":power,"fuel":fuel,"gearbox":gearbox,"drive":drive,"color":color,
          "regular_price":max(prices[:3]),"promo_price":min(prices[:3]),
          "monthly_payment":None,"vin_masked":"","images":images_from(node)[:10],
          "description":txt[:6000],**classify_terms(txt),
          "card_text":txt[:5000]
        })
    # Page-level promo fallback
    if not results:
        prices=price_candidates(flat)
        results.append({
          "source":"Сайт дилера","source_id":cfg["id"],"source_listing_id":compact_id(url),
          "source_url":url,"dealer_name":cfg.get("dealer",""),"dealer_address":cfg.get("address",""),
          "title":clean(soup.title.get_text(" ",strip=True) if soup.title else url),
          "model":model_from(flat),"year":None,"trim":"",
          "engine_l":None,"power_hp":None,"fuel":"","gearbox":"","drive":"","color":"",
          "regular_price":max(prices[:5]) if prices else None,"promo_price":min(prices[:5]) if prices else None,
          "monthly_payment":None,"vin_masked":"","images":images_from(soup)[:10],
          "description":flat[:10000],**classify_terms(text),
          "card_text":flat[:5000]
        })
    return results
