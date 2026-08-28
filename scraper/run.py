from __future__ import annotations
import asyncio, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from scraper.browser import Browser
from scraper.common import now_iso, list_fingerprint
from scraper.storage import load_json, save_json, merge_vehicles, update_history, key, market_hash
from scraper.collectors import drom, autoru, dealer_site

DATA=ROOT/"data"
CONFIG=ROOT/"config.json"

def minutes_since(iso):
    if not iso: return 10**9
    try:
        dt=datetime.fromisoformat(iso.replace("Z","+00:00"))
        return (datetime.now(timezone.utc)-dt).total_seconds()/60
    except: return 10**9

def should_run(interval_minutes):
    # Manual/local run can explicitly force every enabled source.
    if os.environ.get("FORCE_ALL", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    # Workflow starts at :03/:18/:33/:48. This bucket rule remains robust to modest delays.
    now=datetime.now(timezone.utc)
    quarter=(now.minute//15)
    if interval_minutes<=15: return True
    if interval_minutes<=30: return quarter in (0,2)
    if interval_minutes<=60: return quarter==0
    if interval_minutes<=180: return quarter==0 and now.hour%3==0
    return True

def canonical_coverage_previous(prev):
    return {x.get("id"):x for x in prev.get("coverage",[]) if x.get("id")}

async def main():
    cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
    prev=load_json(DATA/"current.json",{"listings":[],"coverage":[]})
    prev_map={key(x):x for x in prev.get("listings",[])}
    current_map=dict(prev_map)
    prev_cov=canonical_coverage_previous(prev)
    coverage=[]
    detail_candidates=[]
    scanned_source_ids=set()

    async with Browser(headless=True) as br:
        for src in cfg["sources"]:
            sid=src["id"]
            if not src.get("enabled"):
                coverage.append({"id":sid,"label":src.get("label"),"dealer":src.get("dealer",""),
                                 "status":"not_configured","count":0,"last_checked":None,"note":src.get("note","")})
                continue

            if not should_run(src.get("interval_minutes",15)):
                old=prev_cov.get(sid,{})
                coverage.append({"id":sid,"label":src.get("label"),"dealer":src.get("dealer",""),
                                 "status":"skipped","count":old.get("count",0),
                                 "last_checked":old.get("last_checked"),"note":"Источник проверяется по своему интервалу"})
                continue

            scanned_source_ids.add(sid)
            try:
                summaries=[]
                if src["type"]=="drom":
                    for page_no in range(1,src.get("pages",4)+1):
                        url=src["url"] if page_no==1 else f'{src["url"]}?page={page_no}'
                        html,_=await br.html(url)
                        rows=drom.parse_listing_page(html,src)
                        before=len({x["source_listing_id"] for x in summaries})
                        existing={x["source_listing_id"]:x for x in summaries}
                        for r in rows: existing[r["source_listing_id"]]=r
                        summaries=list(existing.values())
                        if page_no>1 and len(summaries)==before: break
                elif src["type"]=="autoru":
                    html,_=await br.html(src["url"],scrolls=src.get("scrolls",8))
                    summaries=autoru.parse_listing_page(html,src)
                elif src["type"]=="dealer_site":
                    for url in src.get("urls",[]):
                        try:
                            html,final=await br.html(url)
                            summaries.extend(dealer_site.parse_page(html,final,src))
                        except Exception as e:
                            print("[SITE URL ERROR]",url,e)

                now=now_iso()
                coverage.append({"id":sid,"label":src.get("label"),"dealer":src.get("dealer",""),
                                 "status":"ok","count":len(summaries),"last_checked":now,"note":""})

                for summary in summaries:
                    k=key(summary)
                    prev_item=prev_map.get(k)
                    fingerprint=list_fingerprint(summary)
                    old_fp=list_fingerprint(prev_item) if prev_item else None
                    changed=(fingerprint!=old_fp)

                    merged=dict(prev_item or {})
                    merged.update({kk:vv for kk,vv in summary.items() if vv not in (None,"",[])})
                    merged["last_seen_at"]=now
                    merged["last_list_scan_at"]=now
                    current_map[k]=merged

                    # New/changed ads get detail priority. Old ads get a daily detail refresh
                    # only during one UTC window, preventing hundreds of repeated requests.
                    daily_window=(datetime.now(timezone.utc).hour==2 and datetime.now(timezone.utc).minute<20)
                    stale_detail=minutes_since((prev_item or {}).get("last_detail_at"))>=cfg.get("detail_refresh_hours",24)*60
                    if src["type"] in ("drom","autoru") and (changed or not prev_item or (daily_window and stale_detail)):
                        detail_candidates.append((0 if changed or not prev_item else 1,src,summary))

            except Exception as e:
                now=now_iso()
                coverage.append({"id":sid,"label":src.get("label"),"dealer":src.get("dealer",""),
                                 "status":"error","count":0,"last_checked":now,"note":str(e)[:180]})
                print("[SOURCE ERROR]",sid,type(e).__name__,e)

        detail_candidates.sort(key=lambda x:x[0])
        budget=int(os.environ.get("DETAIL_BUDGET",cfg.get("detail_budget_per_run",35)))
        for idx,(priority,src,summary) in enumerate(detail_candidates[:budget],1):
            k=key(summary)
            try:
                print(f"[DETAIL {idx}/{min(len(detail_candidates),budget)}]",summary["source_url"])
                html,_=await br.html(summary["source_url"])
                item=drom.parse_detail(html,summary) if src["type"]=="drom" else autoru.parse_detail(html,summary)
                now=now_iso()
                item["last_seen_at"]=now
                item["last_detail_at"]=now
                current_map[k]=item
            except Exception as e:
                print("[DETAIL ERROR]",summary["source_url"],type(e).__name__,e)

    # Ads are retired only after not being seen for 48h. Skipped sources do not falsely remove cars.
    now=datetime.now(timezone.utc)
    listings=[]
    for k,x in current_map.items():
        seen=x.get("last_seen_at")
        active=True
        if seen:
            try:
                age=(now-datetime.fromisoformat(seen.replace("Z","+00:00"))).total_seconds()/3600
                active=age<48
            except: pass
        x["active"]=active
        listings.append(x)

    history=update_history(load_json(DATA/"history.json",{}),listings)
    active=[x for x in listings if x.get("active",True)]
    vehicles=merge_vehicles(active)
    output={
      "meta":{
        "city":cfg.get("city"),"brand":cfg.get("brand"),"generated_at":now_iso(),
        "listings_total":len(listings),"listings_active":len(active),
        "vehicles_active":len(vehicles),"detail_queue_remaining":max(0,len(detail_candidates)-budget)
      },
      "coverage":coverage,
      "vehicles":vehicles,
      "listings":listings
    }
    save_json(DATA/"current.json",output)
    save_json(DATA/"history.json",history)
    (DATA/"market_hash.txt").write_text(market_hash(output)+"\n",encoding="utf-8")
    print(json.dumps(output["meta"],ensure_ascii=False))

if __name__=="__main__":
    asyncio.run(main())
