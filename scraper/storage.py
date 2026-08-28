from __future__ import annotations
import json, hashlib, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
from scraper.common import now_iso, clean

def load_json(path, default):
    p=Path(path)
    if not p.exists(): return default
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return default

def save_json(path,obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")

def key(item):
    return f'{item.get("source","")}::{item.get("source_listing_id","")}'

def canonical_dealer(name):
    low=clean(name).lower().replace("ё","е")
    if "восток" in low: return "vostok"
    if "базис" in low: return "basis"
    if "форвард" in low: return "forward"
    if "альянс" in low: return "alliance"
    return low

def vehicle_fingerprint(x):
    vin=re.sub(r"[^A-Z0-9*]","",(x.get("vin_masked") or "").upper())
    if len(vin)>=10 and vin.count("*") < len(vin)-5:
        return "vin:"+vin
    dealer=canonical_dealer(x.get("dealer_name",""))
    parts=[
      dealer, str(x.get("model","")).lower(), str(x.get("year") or ""),
      str(x.get("trim","")).lower(), str(x.get("color","")).lower(),
      str(x.get("drive","")).lower(), str(x.get("power_hp") or "")
    ]
    # source listing is added only when signature is too sparse to avoid false merging.
    signal=sum(bool(p) for p in parts[1:])
    if signal<3: parts.append(key(x))
    return "sig:"+hashlib.sha1("|".join(parts).encode()).hexdigest()[:20]

def merge_vehicles(listings):
    groups=defaultdict(list)
    for x in listings:
        if x.get("model"):
            groups[vehicle_fingerprint(x)].append(x)
    vehicles=[]
    for i,(fp,grp) in enumerate(groups.items(),1):
        price_items=[x for x in grp if x.get("promo_price") or x.get("regular_price")]
        best=min(price_items,key=lambda x:x.get("promo_price") or x.get("regular_price")) if price_items else grp[0]
        sources=sorted(set(x.get("source","") for x in grp))
        image=next((u for x in grp for u in x.get("images",[]) if u), "")
        vehicles.append({
          "vehicle_id":f"veh_{i:06d}","fingerprint":fp,
          "brand":"TENET","model":best.get("model"),"year":best.get("year"),"trim":best.get("trim"),
          "engine_l":best.get("engine_l"),"power_hp":best.get("power_hp"),"fuel":best.get("fuel"),
          "gearbox":best.get("gearbox"),"drive":best.get("drive"),"color":best.get("color"),
          "dealer_name":best.get("dealer_name"),"dealer_address":best.get("dealer_address"),
          "best_price":best.get("promo_price") or best.get("regular_price"),
          "regular_price":best.get("regular_price"),"monthly_payment":best.get("monthly_payment"),
          "image":image,"sources":sources,"source_count":len(sources),
          "credit_terms":best.get("credit_terms",[])[:8],
          "tradein_terms":best.get("tradein_terms",[])[:8],
          "gifts":best.get("gifts",[])[:8],
          "listings":grp
        })
    vehicles.sort(key=lambda v:(v.get("best_price") or 10**12,v.get("model") or ""))
    return vehicles

def update_history(history, listings):
    history=history if isinstance(history,dict) else {}
    now=now_iso()
    for x in listings:
        k=key(x)
        price=x.get("promo_price") or x.get("regular_price")
        if not price: continue
        arr=history.setdefault(k,[])
        if not arr or arr[-1].get("price")!=price:
            arr.append({"at":now,"price":price,"regular_price":x.get("regular_price")})
        # cap at 200 changes per listing
        if len(arr)>200: history[k]=arr[-200:]
    return history


TRANSIENT_KEYS={"generated_at","last_seen_at","last_list_scan_at","last_detail_at","last_checked","scraped_at"}

def stable_market_view(obj):
    if isinstance(obj,dict):
        return {k:stable_market_view(v) for k,v in sorted(obj.items()) if k not in TRANSIENT_KEYS}
    if isinstance(obj,list):
        return [stable_market_view(v) for v in obj]
    return obj

def market_hash(output):
    payload=json.dumps(stable_market_view(output),ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
