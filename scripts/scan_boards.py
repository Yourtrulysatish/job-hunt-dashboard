#!/usr/bin/env python3
"""Read national job boards that have no API: CVbankas (Lithuania), CV Keskus (Estonia), FINN (Norway), Jobindex (Denmark).
Writes a list of postings (title, company, country, posted date when the board shows one, url) to the file given as the first argument.
Dates are only filled when the board states one. Boards change their pages now and then, so a board that returns nothing is reported, not fatal.
Usage: python3 scripts/scan_boards.py scan_raw/boards.json"""
import urllib.request, urllib.parse, re, json, sys, html
from datetime import datetime, timezone, timedelta
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/124 Safari/537.36', 'Accept-Language': 'en'}
NOW = datetime.now(timezone.utc)
QUERIES = ['partnership', 'partner manager', 'affiliate', 'business development', 'growth manager', 'channel manager', 'alliances']
def get(u):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read().decode('utf-8', 'ignore')
    except Exception: return ''
def clean(t): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t))).strip()
recs, status = [], {}
def add(src, title, company, country, url, date=None):
    if title and url: recs.append(dict(src=src, title=title, company=company, country=country, url=url, date=date.isoformat() if date else None))

def cvbankas():
    for q in QUERIES:
        s = get('https://www.cvbankas.lt/?keyw=' + urllib.parse.quote(q))
        for m in re.finditer(r'<a class="list_a[^"]*" href="(https://www\.cvbankas\.lt/[^"]+/1-\d+)">(.*?)</a>', s, re.S):
            b = m.group(2)
            t = re.search(r'<h3 class="list_h3"[^>]*lang="en"[^>]*>(.*?)</h3>', b, re.S)
            if not t: continue                      # title not in English: skip
            c = re.search(r'<span class="dib mt5 mr5">(.*?)</span>', b, re.S)
            d = re.search(r'prieš\s+(\d+)\s*d\.', b)
            add('cvbankas', clean(t.group(1)), clean(c.group(1)) if c else '', 'Lithuania', m.group(1), NOW - timedelta(days=int(d.group(1))) if d else None)

def cvkeskus():
    for q in QUERIES:
        s = get('https://www.cvkeskus.ee/toopakkumised?keyword=' + urllib.parse.quote(q))
        seen = set()
        for m in re.finditer(r'<a[^>]+href="(/[^"]+-\d{6,7})"[^>]*>(.*?)</a>', s, re.S):
            if m.group(1) in seen: continue
            seen.add(m.group(1))
            tok = [x.strip() for x in re.sub(r'<[^>]+>', '|', m.group(2)).split('|') if x.strip()]
            tok = [html.unescape(x) for x in tok]
            if len(tok) < 3: continue
            when, title, company = tok[0], tok[1], tok[2]
            date = None
            if 'tagasi' in when:
                n = re.search(r'(\d+)', when); n = int(n.group(1)) if n else 1
                days = n * 7 if ('näd' in when or 'nädal' in when) else (0 if 'tund' in when else n)
                date = NOW - timedelta(days=days)
            add('cvkeskus', title, company, 'Estonia', 'https://www.cvkeskus.ee' + m.group(1), date)

NORW = re.compile(r'\b(utvikler|leder|sjef|rådgiver|konsulent|ansvarlig|medarbeider|rekrutterer|selger|kunde|prosjekt)\b', re.I)
def finn():
    for q in QUERIES:
        s = get('https://www.finn.no/job/fulltime/search.html?q=' + urllib.parse.quote(q))
        for m in re.finditer(r'<a class="job-card-link[^"]*" href="(https://www\.finn\.no/job/ad/\d+)"[^>]*>(.*?)</a>(?:<div[^>]*><strong>(.*?)</strong>)?', s, re.S):
            title = clean(m.group(2))
            if NORW.search(title): continue
            add('finn', title, clean(m.group(3) or ''), 'Norway', m.group(1))

def jobindex():
    for q in QUERIES:
        s = get('https://www.jobindex.dk/jobsoegning?lang=en&q=' + urllib.parse.quote(q)).replace('\\/', '/').replace('\\n', '\n').replace('\\"', '"')
        for b in re.split(r'data-jobad-tid="', s)[1:]:
            t = re.search(r'<h4[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
            if not t: continue
            c = re.search(r'jix-toolbar-top__company">\s*(?:<a[^>]*>)?\s*([^<\n]+)', b)
            d = re.search(r'\b(\d\d)-(\d\d)-(20\d\d)\b', b)
            date = datetime(int(d.group(3)), int(d.group(2)), int(d.group(1)), tzinfo=timezone.utc) if d else None
            href = html.unescape(t.group(1)); href = href if href.startswith('http') else 'https://www.jobindex.dk' + href
            add('jobindex', clean(t.group(2)), clean(c.group(1)) if c else '', 'Denmark', href, date)

for name, fn in (('cvbankas', cvbankas), ('cvkeskus', cvkeskus), ('finn', finn), ('jobindex', jobindex)):
    before = len(recs)
    try: fn()
    except Exception as e: status[name] = 'FAILED ' + str(e)[:50]; continue
    status[name] = f'{len(recs) - before} rows'
uniq = {}
for r in recs: uniq.setdefault(r['url'], r)
json.dump({'status': status, 'rows': list(uniq.values())}, open(sys.argv[1], 'w'), indent=1, ensure_ascii=False)
print(status, len(uniq), 'unique')
