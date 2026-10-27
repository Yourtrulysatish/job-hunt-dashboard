#!/usr/bin/env python3
"""Check whether each listed posting is still open and write data/live.json.
Greenhouse, Ashby and Lever postings are checked against the company's own public job API. Anything else is fetched and read for a 404 or a closed-posting message.
This follows the liveness gate idea in career-ops: a dead link should never look like an open role. A check that cannot tell says 'unknown', never 'closed'."""
import json, re, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/124 Safari/537.36'}
CLOSED = re.compile(r'no longer (?:available|accepting|open)|position (?:has been|is) (?:filled|closed)|job (?:has expired|is closed|is no longer)|this (?:job|posting|position) (?:has )?(?:expired|been removed|is no longer)|page not found|diese stelle ist nicht mehr|stillingen er utløpt', re.I)
def fetch(u, t=20, limit=400000):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t)
        return r.status, r.read(limit).decode('utf-8', 'ignore')
    except urllib.error.HTTPError as e: return e.code, ''
    except Exception: return None, ''
def check(url):
    m = re.search(r'greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m:
        s, _ = fetch(f'https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}')
        return 'closed' if s == 404 else ('open' if s == 200 else 'unknown')
    m = re.search(r'ashbyhq\.com/([^/]+)/([0-9a-f-]{36})', url)
    if m:
        s, body = fetch(f'https://api.ashbyhq.com/posting-api/job-board/{m.group(1)}', 30, 20000000)
        if s != 200: return 'unknown'
        return 'open' if m.group(2) in body else 'closed'
    m = re.search(r'jobs\.lever\.co/([^/]+)/([0-9a-f-]{36})', url)
    if m:
        s, _ = fetch(f'https://api.lever.co/v0/postings/{m.group(1)}/{m.group(2)}')
        return 'closed' if s == 404 else ('open' if s == 200 else 'unknown')
    s, body = fetch(url)
    if s in (404, 410): return 'closed'
    if s == 200: return 'closed' if CLOSED.search(re.sub(r'<script.*?</script>', ' ', body, flags=re.S)[:60000]) else 'open'
    return 'unknown'
urls = set()
for f, key in (('data/jobs.json', 'jobs'), ('data/auto.json', 'items')):
    try: urls |= {j['url'] for j in json.load(open(f))[key] if j.get('url')}
    except Exception: pass
try: old = json.load(open('data/live.json'))
except Exception: old = {}
with ThreadPoolExecutor(12) as ex: res = dict(zip(urls, ex.map(check, urls)))
out = {}
for u, st in res.items():
    prev = old.get(u, {}).get('state')
    out[u] = {'state': (prev if (st == 'unknown' and prev == 'closed') else st), 'checked': TODAY}
json.dump(out, open('data/live.json', 'w'), indent=0)
import collections; print(collections.Counter(v['state'] for v in out.values()))
