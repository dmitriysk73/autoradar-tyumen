from __future__ import annotations
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from scraper.common import *

AD_RE=re.compile(r"https?://[^/]*drom\.ru/[^?#]+/(\d+)\.html(?:[?#].*)?$",re.I)

def parse_listing_page(html, cfg):
    soup=BeautifulSoup(html,"lxml")
    found={}
    for a in soup.find_all("a",href=True):
        href=urljoin(cfg["url"],a["href"]).split("?")[0].split("#")[0]
        m=AD_RE.match(href)
        if not m: continue
        ad_id=m.group(1)
        card=card_ancestor(a)
        txt=clean(card.get_text(" ",strip=True))
        if "TENET" not in txt.upper(): continue
        prices=price_candidates(txt)
        year=extract_year(txt)
        model=model_from(txt)
        engine,power,fuel,gearbox,drive,color=vehicle_specs(txt)
        imgs=images_from(card)
        item={
          "source":"Дром","source_id":cfg["id"],"source_listing_id":ad_id,"source_url":href,
          "dealer_name":cfg.get("dealer",""),"dealer_address":cfg.get("address",""),
          "title":clean(a.get_text(" ",strip=True)) or f"TENET {model}",
          "model":model,"year":year,"trim":trim_from(txt),
          "engine_l":engine,"power_hp":power,"fuel":fuel,"gearbox":gearbox,"drive":drive,"color":color,
          "regular_price":prices[0] if prices else None,
          "promo_price":prices[1] if len(prices)>1 and prices[1]<=prices[0] else (prices[0] if prices else None),
          "monthly_payment":None,"vin_masked":"",
          "images":imgs[:10],"description":"","credit_terms":[],"tradein_terms":[],"gifts":[],
          "card_text":txt[:5000]
        }
        # keep richer duplicate
        if ad_id not in found or len(txt)>len(found[ad_id].get("card_text","")):
            found[ad_id]=item
    return list(found.values())

def parse_detail(html, summary):
    soup=BeautifulSoup(html,"lxml")
    text=soup.get_text("\n",strip=True)
    flat=clean(text)
    h1=soup.find("h1")
    title=clean(h1.get_text(" ",strip=True) if h1 else summary.get("title",""))
    prices=price_candidates(flat)
    engine,power,fuel,gearbox,drive,color=vehicle_specs(flat)
    out=dict(summary)
    out.update({
      "title":title or out.get("title",""),
      "model":model_from(title+" "+flat[:1200]) or out.get("model",""),
      "year":extract_year(title) or out.get("year"),
      "trim":trim_from(flat) or out.get("trim",""),
      "engine_l":engine or out.get("engine_l"),
      "power_hp":power or out.get("power_hp"),
      "fuel":fuel or out.get("fuel",""),
      "gearbox":gearbox or out.get("gearbox",""),
      "drive":drive or out.get("drive",""),
      "color":color or out.get("color",""),
      "vin_masked":extract_vin(flat),
      "regular_price":prices[0] if prices else out.get("regular_price"),
      "promo_price":prices[1] if len(prices)>1 and prices[1]<=prices[0] else (out.get("promo_price") or (prices[0] if prices else None)),
      "images":images_from(soup) or out.get("images",[]),
      "description":flat[:12000],
    })
    mm=MONTHLY_RE.search(flat)
    out["monthly_payment"]=digits(mm.group(1)) if mm else out.get("monthly_payment")
    out.update(classify_terms(text))
    return out
