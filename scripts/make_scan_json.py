#!/usr/bin/env python3
"""Turn the raw role scan into a slim public file for the dashboard (no job descriptions).
Usage: python3 scripts/make_scan_json.py scan_raw/latest.json data/scan.json"""
import json, re, sys
from datetime import datetime, timezone
raw = json.load(open(sys.argv[1]))
jobs = json.load(open('data/jobs.json'))['jobs']
known = {j['url'] for j in jobs if j.get('url')} | {(j['company'].lower(), j['title'].lower()) for j in jobs}
seen, items = set(), []
for r in raw:
    f = r.get('flags', [])
    if any(x.startswith('LANGUAGE') or x.startswith('COMMISSION') or x.startswith('US based') for x in f): continue
    yrs = [int(m.group(1)) for x in f for m in [re.search(r'up to (\d+)', x)] if m]
    if yrs and max(yrs) >= 7: continue
    if re.search(r'talent|people|compensation|dei |recruit|hr |sustainability|merchandis|account executive|sales rep|\bsdr\b', r['title'], re.I): continue
    k = (r['company'].lower().strip(), r['title'].lower().strip())
    if k in seen or k in known or r['url'] in known: continue
    seen.add(k)
    items.append({k2: r[k2] for k2 in ('title', 'company', 'loc', 'date', 'url', 'north', 'age_days', 'src')} | {'flags': f})
items.sort(key=lambda x: x['date'], reverse=True)
json.dump({'generated': datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC'), 'count': len(items), 'items': items[:150]}, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
print(len(items), 'items written')
