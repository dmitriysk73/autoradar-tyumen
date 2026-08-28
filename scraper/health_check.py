from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "data/current.json").read_text(encoding="utf-8"))

coverage = data.get("coverage", [])
attempted = [x for x in coverage if x.get("status") in ("ok", "error")]
productive = [x for x in attempted if x.get("status") == "ok" and int(x.get("count") or 0) > 0]

print("AUTORADAR health:")
for x in attempted:
    print(f'  {x.get("label")} | {x.get("dealer","")} | {x.get("status")} | count={x.get("count",0)} | {x.get("note","")}')

if attempted and not productive:
    print("ERROR: collector completed, but no attempted source returned any listings/offers.")
    sys.exit(2)

print(f"Health OK: {len(productive)} productive source(s).")
