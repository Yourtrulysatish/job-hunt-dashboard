#!/usr/bin/env python3
"""Build the files the dashboard reads.
Inputs: scan_raw/latest.json (feeds and company boards), scan_raw/boards.json (national boards), data/jobs.json (roles read by hand),
        data/rejected.json, data/seen.json, config/profile.json.
Outputs: data/auto.json (best matches), data/scan.json (the rest), data/seen.json, and the ratings inside data/jobs.json.
Every posting gets a fit rating out of 10 from scripts/evaluate.py."""
import json, re, hashlib
from datetime import datetime, timezone
from evaluate import evaluate, posting_check
NOW = datetime.now(timezone.utc); TODAY = NOW.strftime('%Y-%m-%d')
doc = json.load(open('data/jobs.json')); cur = doc['jobs']
raw = json.load(open('scan_raw/latest.json'))
jd_by_url = {r['url']: r.get('desc', '') for r in raw}
try: rejected = [x.lower() for x in json.load(open('data/rejected.json'))['companies']]
except Exception: rejected = []
try: seen = json.load(open('data/seen.json'))
except Exception: seen = {}
KEY = re.compile(r'partner|affiliate|business development|bizdev|\bbd\b|alliance|ecosystem|channel|growth (?:marketing )?(?:manager|lead|specialist|associate)|performance marketing|sponsorship|acquisition manager|marketing manager|seo (?:manager|lead|specialist)|paid (?:media|social|search) (?:manager|specialist)|community manager|content marketing (?:manager|lead)|social media manager|email marketing manager|crm manager|lifecycle', re.I)
BAD = re.compile(r'director|\bvp\b|vice president|chief|principal|intern\b|internship|student|head of|developer|engineer|designer|recruit|hr business|people partner|business partner|talent|compensation|\bdei\b|legal|counsel|assistant|representative|\bsdr\b|\bbdr\b|account executive|merchandis|sustainability|finance|accountant|architect|nurse|driver', re.I)
POS = re.compile(r'affiliate|partnerships?\b.*(?:manager|specialist|lead|associate|executive|development)|partner (?:manager|development|success)|alliances? (?:partner )?manager|business development (?:manager|specialist|executive|associate)|channel (?:manager|partner)|ecosystem (?:manager|lead)|growth (?:marketing )?(?:manager|lead)|sponsorship manager|(?:performance |growth |content |email )marketing manager|seo (?:manager|lead)|community manager', re.I)
EXCL = re.compile(r'volunteer|unpaid|trainee|apprentice|intern\b|coordinator|supervisor|\bhse\b|drilling|engineer|operations|analyst|m&a|application:|influencer|youtube|tiktok|media buyer|programmatic|delivery partner|interim|frivillig|søger|medarbeider|forretningsutvikler|co-founder|founder|\bog\b|\btil\b|[æøåäöüé]', re.I)
PLACES = [('Sweden', r'sweden|stockholm|gothenburg|göteborg|malmö|malmo|uppsala'), ('Norway', r'norway|oslo|bergen|trondheim|stavanger'), ('Denmark', r'denmark|copenhagen|københavn|aarhus|odense|aalborg'),
          ('Finland', r'finland|helsinki|espoo|tampere|oulu'), ('Iceland', r'iceland|reykjavik'), ('Estonia', r'estonia|tallinn|tartu'), ('Latvia', r'latvia|riga'), ('Lithuania', r'lithuania|vilnius|kaunas'),
          ('Ireland', r'ireland|dublin|cork|galway|limerick'), ('United Kingdom', r'united kingdom|\buk\b|london|manchester|edinburgh|england|scotland|wales|belfast|bristol|birmingham|leeds|glasgow|cambridge|oxford|brighton'),
          ('Germany', r'germany|berlin|munich|münchen|hamburg|frankfurt|cologne|köln|stuttgart|düsseldorf|leipzig'), ('France', r'france|paris|lyon|marseille|toulouse|nice'),
          ('Netherlands', r'netherlands|amsterdam|rotterdam|the hague|utrecht|eindhoven'), ('Belgium', r'belgium|brussels|antwerp'), ('Luxembourg', r'luxembourg'), ('Austria', r'austria|vienna|wien|graz'),
          ('Switzerland', r'switzerland|zurich|zürich|geneva|basel|zug'), ('Spain', r'spain|madrid|barcelona|valencia|seville|malaga'), ('Portugal', r'portugal|lisbon|porto'),
          ('Italy', r'italy|milan|milano|rome|roma|turin|bologna'), ('Malta', r'malta|valletta'), ('Cyprus', r'cyprus|nicosia|limassol'), ('Greece', r'greece|athens|thessaloniki'),
          ('Poland', r'poland|warsaw|krakow|kraków|wroclaw'), ('Czechia', r'czechia|czech republic|prague|brno'), ('Slovakia', r'slovakia|bratislava'), ('Hungary', r'hungary|budapest'),
          ('Romania', r'romania|bucharest|cluj'), ('Bulgaria', r'bulgaria|sofia'), ('Croatia', r'croatia|zagreb|split'), ('Slovenia', r'slovenia|ljubljana'), ('Serbia', r'serbia|belgrade')]
def place(loc):
    for c, p in PLACES:
        if re.search(r'\b(' + p + r')\b', loc or '', re.I): return c
    return None
def age_of(iso):
    try: return (NOW - datetime.fromisoformat(iso.replace('Z', '+00:00'))).days
    except Exception: return None
def pack(r): return {k: r[k] for k in ('fit', 'conf', 'parts', 'notes', 'have', 'missing') if k in r}
rows = [dict(src=r['src'], title=r['title'], company=r['company'], loc=r.get('loc', ''), date=r['date'], url=r['url'], flags=r.get('flags', []), jd=r.get('desc', ''), desc=True) for r in raw]
try:
    for r in json.load(open('scan_raw/boards.json'))['rows']:
        rows.append(dict(src=r['src'], title=r['title'], company=r['company'], loc=r['country'], date=r['date'], url=r['url'], flags=[], jd='', desc=False))
except Exception: pass
known_url = {j.get('url') for j in cur}; known_key = {(j['company'].lower().strip(), j['title'].lower().strip()) for j in cur}
auto, rest, keys = [], [], set()
for r in rows:
    f = r['flags']
    if not (KEY.search(r['title']) and not BAD.search(r['title'])) or EXCL.search(r['title']): continue
    if any(x.startswith(('COMMISSION', 'US based')) for x in f): continue
    if any(x in r['company'].lower() for x in rejected): continue
    k = (r['company'].lower().strip(), r['title'].lower().strip())
    if r['url'] in known_url or k in known_key or k in keys: continue
    keys.add(k)
    country = place(r['loc']); is_remote = bool(re.search(r'remote|anywhere|worldwide|global|emea|europe|\beu\b', r['loc'], re.I)) or not country
    if not country and not is_remote: continue
    d = r['date']; age = age_of(d) if d else None
    if age is not None and age > 21: continue
    first = seen.get(r['url'], {}).get('first') or TODAY
    seen[r['url']] = {'first': first, 'last': TODAY}
    region = 'r' if (is_remote and (re.search(r'remote|anywhere|worldwide', r['loc'], re.I) or not country)) else 'e'
    job = dict(title=r['title'], company=r['company'], country=country or 'Remote', region=region, flags=f, loc=r['loc'], url=r['url'])
    if re.search(r'hybrid|office', ' '.join(f) + ' ' + r['loc'], re.I): job['mode'] = 'Hybrid or office'
    if region == 'r': job['mode'] = 'Remote'
    ev = evaluate(job, r['jd'])
    yrs = [int(m.group(1)) for x in f for m in [re.search(r'up to (\d+)', x)] if m]
    if yrs and max(yrs) >= 7: continue
    pc = posting_check(job, r['jd'], age)
    item = dict(id='a' + hashlib.sha1(r['url'].encode()).hexdigest()[:10], title=r['title'], company=r['company'], country=job['country'], region=region, tier='auto', fit=ev['fit'], rating=pack(ev),
                posted=d[:10] if d else None, firstSeen=first, url=r['url'], source=r['src'], flags=[x for x in f if not x.startswith('hybrid')], check=pc,
                new=(first == TODAY) or (age is not None and age <= 1), why='Found by the daily scan' + ('' if r['desc'] else ' from a national job board') + '. Open the posting and read it before applying.')
    if 'mode' in job: item['mode'] = job['mode']
    if ev['fit'] >= 7 and r['desc'] and POS.search(r['title']) and not any(x.startswith('LANGUAGE') for x in f): auto.append(item)
    elif ev['fit'] > 6 and not any(x.startswith('LANGUAGE') for x in f): rest.append(item)
def key(x): return (-x['fit'], -int((x['posted'] or x['firstSeen']).replace('-', '')))
auto.sort(key=key); rest.sort(key=key)
cut = NOW.timestamp() - 30 * 86400
seen = {u: v for u, v in seen.items() if datetime.strptime(v['last'], '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() >= cut}
# ratings for the roles read by hand
for j in cur:
    jd = jd_by_url.get(j.get('url'), '')
    j['read'] = True
    ev = evaluate(j, jd)
    j['rating'] = pack(ev)
    j['fit'] = max(1.0, min(10.0, ev['fit'] + j.get('fitAdjust', 0)))
    j['below'] = j['fit'] <= 6
    j['check'] = posting_check(j, jd, age_of(j['posted'] + 'T00:00:00+00:00') if j.get('posted') else None)
stamp = NOW.strftime('%d %b %Y %H:%M UTC')
doc['rated'] = stamp
json.dump(doc, open('data/jobs.json', 'w'), indent=1, ensure_ascii=False)
json.dump({'generated': stamp, 'count': len(auto), 'items': auto[:60]}, open('data/auto.json', 'w'), indent=1, ensure_ascii=False)
json.dump({'generated': stamp, 'count': len(rest), 'items': rest[:100]}, open('data/scan.json', 'w'), indent=1, ensure_ascii=False)
json.dump(seen, open('data/seen.json', 'w'), indent=0)
print(len(auto), 'auto,', len(rest), 'rest,', len(cur), 'rated by hand')
