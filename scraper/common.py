from __future__ import annotations
import hashlib, json, re, time
from datetime import datetime, timezone
from urllib.parse import urljoin
from bs4 import BeautifulSoup

PRICE_RE = re.compile(r"(\d[\d\s\xa0]{3,})\s*₽")
YEAR_RE = re.compile(r"\b(20\d{2})\b")
POWER_RE = re.compile(r"(\d{2,4})\s*л\.?\s*с\.?", re.I)
ENGINE_RE = re.compile(r"(\d(?:[.,]\d)?)\s*л\b", re.I)
VIN_RE = re.compile(r"\b([A-HJ-NPR-Z0-9*]{10,17})\b", re.I)
MONTHLY_RE = re.compile(r"(?:от\s*)?([\d\s\xa0]+)\s*₽\s*/?\s*мес", re.I)

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()

def digits(s):
    d = re.sub(r"\D", "", str(s or ""))
    return int(d) if d else None

def price_candidates(text):
    out=[]
    for m in PRICE_RE.finditer(text or ""):
        p=digits(m.group(1))
        if p and 500_000 <= p <= 20_000_000 and p not in out:
            out.append(p)
    return out

def model_from(text):
    m=re.search(r"\b(T4L|T4|T7|T8|T9|A8)\b", (text or "").upper())
    return m.group(1) if m else ""

def trim_from(text):
    low=(text or "").lower()
    for canonical, variants in [
        ("Ultra", ("ultra","ультра")),
        ("Prime", ("prime","прайм")),
        ("Active", ("active","актив")),
        ("Line", ("line","лайн")),
    ]:
        if any(v in low for v in variants): return canonical
    return ""

def vehicle_specs(text):
    flat=clean(text)
    low=flat.lower()
    ep=ENGINE_RE.search(flat)
    pp=POWER_RE.search(flat)
    engine=None
    if ep:
        try: engine=float(ep.group(1).replace(",","."))
        except: pass
    power=int(pp.group(1)) if pp else None
    fuel=next((x for x in ("бензин","дизель","электро","гибрид") if x in low),"")
    gearbox=next((x for x in ("робот","вариатор","автомат","механика") if x in low),"")
    drive=""
    if "4wd" in low or "полный привод" in low or "полный" in low: drive="Полный"
    elif "передний" in low: drive="Передний"
    elif "задний" in low: drive="Задний"
    color=""
    colors=("белый","чёрный","черный","серый","серебристый","красный","синий","зелёный","зеленый","бежевый","коричневый")
    for c in colors:
        if re.search(rf"\b{re.escape(c)}\b",low):
            color=c.capitalize()
            break
    return engine,power,fuel,gearbox,drive,color

def images_from(soup):
    urls=[]
    def add(u):
        if isinstance(u,str) and u.startswith("http") and u not in urls:
            urls.append(u)
    for m in soup.select('meta[property="og:image"],meta[name="twitter:image"]'):
        add(m.get("content"))
    for img in soup.find_all("img"):
        for attr in ("src","data-src","data-original","data-lazy-src"):
            add(img.get(attr))
        ss=img.get("srcset") or img.get("data-srcset")
        if ss:
            for part in ss.split(","):
                add(part.strip().split(" ")[0])
    return urls[:40]

def pick_lines(text, keys, limit=20):
    out=[]
    for ln in [clean(x) for x in (text or "").splitlines() if clean(x)]:
        low=ln.lower()
        if any(k in low for k in keys) and ln not in out:
            out.append(ln)
        if len(out)>=limit: break
    return out

def card_ancestor(anchor):
    node=anchor
    best=anchor
    for _ in range(7):
        node=node.parent
        if not node: break
        txt=clean(node.get_text(" ",strip=True))
        if len(txt)>len(clean(best.get_text(" ",strip=True))) and len(txt)<5000:
            best=node
        if "₽" in txt and ("TENET" in txt.upper() or "Tenet" in txt):
            return node
    return best

def fp(text):
    return hashlib.sha1(clean(text).encode("utf-8")).hexdigest()

def compact_id(text):
    return hashlib.sha1(str(text).encode("utf-8")).hexdigest()[:18]

def list_fingerprint(item):
    important = "|".join(str(item.get(k,"")) for k in [
        "source","source_listing_id","title","regular_price","promo_price","model","year","dealer_name"
    ])
    return fp(important)

def extract_vin(text):
    candidates=[v for v in VIN_RE.findall(clean(text)) if "*" in v or len(v)>=15]
    return candidates[0] if candidates else ""

def extract_year(text):
    m=YEAR_RE.search(text or "")
    return int(m.group(1)) if m else None

def classify_terms(text):
    return {
      "credit_terms": pick_lines(text,("кредит","ставк","первоначальн","рассроч","банк"),30),
      "tradein_terms": pick_lines(text,("trade-in","трейд","обмен","ваш автомобиль"),20),
      "gifts": pick_lines(text,("подар","путёв","путев","обслуживан","то в подарок"),20),
    }
