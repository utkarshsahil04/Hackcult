"""Standalone structural check for seed_data/. NOT your pipeline's validator:
it re-implements the README rules so a reviewer can run them anywhere.
Usage: python tools/validate_seed.py [seed_data_dir] [--baseline OLD_DIR]
"""

import collections
import json
import sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith("--")]
base = None
if "--baseline" in sys.argv:
    idx = sys.argv.index("--baseline")
    base_val = sys.argv[idx + 1]
    base = Path(base_val)
    args = [a for a in args if a != base_val]
d = (
    Path(args[0])
    if args
    else Path(__file__).resolve().parents[1] / "app" / "db" / "seed_data"
)


def load(name):
    return json.loads((d / f"{name}.json").read_text(encoding="utf-8"))


mon, src, clm, rel = (
    load("monuments"),
    load("sources"),
    load("claims"),
    load("relationships"),
)
errs, warns = [], []
BANNED = ("wikipedia", "wikiwand", "newworldencyclopedia", "wikimedia", "indiatv")


def dup(items, k, what):
    c = collections.Counter(i[k] for i in items)
    for v, n in c.items():
        if n > 1:
            errs.append(f"duplicate {what} {v!r}")


dup(mon, "slug", "monument slug")
dup(src, "key", "source key")
mslugs = {m["slug"] for m in mon}
skeys = {s["key"]: s for s in src}
for s in src:
    if any(b in s["url"].lower() or b in s["publisher"].lower() for b in BANNED):
        errs.append(f"banned/derivative source {s['key']}")
for m in mon:
    if m["coordinates_source"] not in skeys:
        errs.append(f"{m['slug']}: coordinates_source unresolved")
ck = set()
per_m = collections.defaultdict(list)
for c in clm:
    k = (c["monument"], c["key"])
    if k in ck:
        errs.append(f"duplicate claim {k}")
    ck.add(k)
    per_m[c["monument"]].append(c["position"])
    if c["monument"] not in mslugs:
        errs.append(f"claim {k}: monument unresolved")
    if not isinstance(c.get("is_legend"), bool):
        errs.append(f"claim {k}: is_legend not bool")
    pubs = set()
    for s in c["sources"]:
        if s["source"] not in skeys:
            errs.append(f"claim {k}: source {s['source']} unresolved")
        else:
            pubs.add(skeys[s["source"]]["publisher"])
    if not c["is_legend"] and len(pubs) < 2:
        errs.append(f"claim {k}: <2 distinct publishers {pubs}")
    if c["is_legend"] and (c["type"] != "tradition" or not c["sources"]):
        errs.append(f"claim {k}: bad legend")
for m, ps in per_m.items():
    if len(ps) != len(set(ps)):
        errs.append(f"{m}: duplicate claim positions {ps}")
for m in mslugs - set(per_m):
    warns.append(f"{m}: no claims (empty description)")
claims = {f"{c['monument']}/{c['key']}": c for c in clm}
edges = set()
for r in rel:
    e = (r["from"], r["to"], r["type"])
    if e in edges:
        errs.append(f"duplicate edge {e}")
    edges.add(e)
    if r["from"] not in mslugs or r["to"] not in mslugs:
        errs.append(f"edge {e}: endpoint unresolved")
    c = claims.get(r["claim"])
    if not c:
        errs.append(f"edge {e}: claim {r['claim']} unresolved")
        continue
    if c["is_legend"]:
        errs.append(f"edge {e}: backed by legend")
    if c["monument"] not in (r["from"], r["to"]):
        errs.append(f"edge {e}: claim not about an endpoint")
if base:
    for n in ("monuments", "sources", "claims", "relationships"):
        old = json.loads((base / f"{n}.json").read_text(encoding="utf-8"))
        new = load(n)
        idf = {
            "monuments": lambda x: x["slug"],
            "sources": lambda x: x["key"],
            "claims": lambda x: (x["monument"], x["key"]),
            "relationships": lambda x: (x["from"], x["to"], x["type"]),
        }[n]
        nm = {idf(x): x for x in new}
        for o in old:
            if idf(o) not in nm:
                errs.append(f"[baseline] {n}: removed {idf(o)}")
            elif nm[idf(o)] != o:
                errs.append(f"[baseline] {n}: modified {idf(o)}")
print(f"monuments={len(mon)} sources={len(src)} claims={len(clm)} edges={len(rel)}")
print(
    f"targets: monuments 15 -> {'MET' if len(mon)==15 else 'NOT MET'}; edges 30 -> {'MET' if len(rel)>=30 else 'NOT MET'}"
)
for w in warns:
    print("WARN", w)
for e in errs:
    print("ERROR", e)
sys.exit(1 if errs else 0)
