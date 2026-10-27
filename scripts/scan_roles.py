#!/usr/bin/env python3
"""Fresh role scan for the Role pipeline (Channel B).

Pulls postings straight from public remote job feeds and from the hiring systems
companies actually use (Lever, Greenhouse, Ashby, Recruitee, Workable). Every record
carries the system's own posting date, and a role that has been closed disappears from
its feed, so a posting that appears here is both dated and open. Nothing here is a search
engine guess.

Northern Europe mode (added 26 Oct 2026): also keeps roles located in Sweden, Norway, Denmark, Finland, Iceland,
Estonia, Latvia, Lithuania, Ireland and the UK in any work mode, and prints them in their own section.

Usage: python3 scripts/scan_roles.py [--days 21] [--out scan_output.json]
Prints a shortlist with red flags (commission only, language, US only, years asked,
hybrid, relocation) so each candidate can be judged. Run from the repo root.
"""
import urllib.request, urllib.parse, json, re, sys, html, argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

ap = argparse.ArgumentParser(); ap.add_argument('--days', type=int, default=21); ap.add_argument('--out', default='scan/latest.json')
args = ap.parse_args()
H = {'User-Agent': 'Mozilla/5.0 (role-scan)'}
NOW = datetime.now(timezone.utc)

def get(u, t=25, raw=False):
    try:
        b = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=t).read()
        return b if raw else json.loads(b)
    except Exception:
        return None

def must(x, what):
    if x is None: raise RuntimeError(f'{what} unreachable from this machine')
    return x

def dt(x):
    if x in (None, ''): return None
    if isinstance(x, (int, float)): return datetime.fromtimestamp(x / 1000 if x > 1e11 else x, timezone.utc)
    x = str(x)
    try:
        if re.match(r'\d{4}-', x): return datetime.fromisoformat(x.replace('Z', '+00:00')).astimezone(timezone.utc)
        return parsedate_to_datetime(x).astimezone(timezone.utc)
    except Exception:
        return None

def strip(h): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h or '')))

recs = []; status = {}
def add(src, title, company, date, loc, url, sal='', desc=''):
    if isinstance(loc, list):
        # A long country list means a whole region (for example EMEA), not a located role.
        if len(loc) > 12: loc = 'Remote, Europe/EMEA (many countries)' if any(c in loc for c in ('Croatia', 'Germany', 'France', 'Sweden', 'Italy')) else 'Remote, restricted country list'
        else: loc = ', '.join(map(str, loc))
    recs.append(dict(src=src, title=title or '', company=company or '', date=dt(date), loc=str(loc or ''), url=str(url or ''), sal=str(sal or ''), desc=strip(desc)))

def feed(name, fn):
    before = len(recs)
    try: fn()
    except Exception as e: status[name] = 'FAILED ' + str(e)[:60]; return
    status[name] = f'ok {len(recs) - before} postings'

def remotive():
    for j in must(get('https://remotive.com/api/remote-jobs?limit=500'),'remotive')['jobs']:
        add('remotive', j['title'], j['company_name'], j['publication_date'], j.get('candidate_required_location'), j['url'], j.get('salary'), j.get('description'))
def remoteok():
    for j in must(get('https://remoteok.com/api'),'remoteok')[1:]:
        add('remoteok', j.get('position'), j.get('company'), j.get('date'), j.get('location') or 'Worldwide', j.get('url'), f"{j.get('salary_min','')}-{j.get('salary_max','')}", j.get('description'))
def arbeitnow():
    for p in range(1, 6):
        for j in must(get(f'https://www.arbeitnow.com/api/job-board-api?page={p}'),'arbeitnow')['data']:
            add('arbeitnow', j['title'], j['company_name'], j['created_at'], ('Remote, ' if j.get('remote') else '') + j.get('location', ''), j['url'], '', j.get('description'))
def himalayas():
    for off in range(0, 400, 20):
        d = get(f'https://himalayas.app/jobs/api?limit=20&offset={off}')
        if not d or not d.get('jobs'): break
        for j in d['jobs']:
            add('himalayas', j.get('title'), j.get('companyName'), j.get('pubDate'), j.get('locationRestrictions') or 'Worldwide', j.get('applicationLink') or j.get('guid'), f"{j.get('minSalary','')}-{j.get('maxSalary','')} {j.get('currency','')}", j.get('description'))
def jobicy():
    for j in must(get('https://jobicy.com/api/v2/remote-jobs?count=100&geo=europe'),'jobicy')['jobs']:
        add('jobicy', j.get('jobTitle'), j.get('companyName'), j.get('pubDate'), j.get('jobGeo'), j.get('url'), f"{j.get('salaryMin','')}-{j.get('salaryMax','')}", j.get('jobDescription'))
def wwr():
    for cat in ('remote-sales-and-marketing-jobs', 'remote-business-and-management-jobs', 'all-other-remote-jobs'):
        b = get(f'https://weworkremotely.com/categories/{cat}.rss', raw=True)
        if not b: continue
        for it in ET.fromstring(b).iter('item'):
            t = it.findtext('title') or ''; c, _, r = t.partition(': ')
            add('wwr', r or t, c, it.findtext('pubDate'), it.findtext('region') or 'Remote', it.findtext('link'), '', it.findtext('description'))

for n, f in (('remotive', remotive), ('remoteok', remoteok), ('arbeitnow', arbeitnow), ('himalayas', himalayas), ('jobicy', jobicy), ('wwr', wwr)): feed(n, f)

def remotive_search():
    for q in ('partnership', 'partner manager', 'affiliate', 'business development', 'growth manager', 'alliances'):
        d = get('https://remotive.com/api/remote-jobs?limit=100&search=' + urllib.parse.quote(q))
        for j in (d or {}).get('jobs', []):
            add('remotive', j['title'], j['company_name'], j['publication_date'], j.get('candidate_required_location'), j['url'], j.get('salary'), j.get('description'))
def jobicy_geo():
    for g in ('sweden', 'denmark', 'norway', 'finland', 'ireland', 'uk', 'estonia', 'latvia', 'lithuania', 'iceland'):
        d = get(f'https://jobicy.com/api/v2/remote-jobs?count=50&geo={g}')
        for j in (d or {}).get('jobs', []):
            add('jobicy', j.get('jobTitle'), j.get('companyName'), j.get('pubDate'), j.get('jobGeo'), j.get('url'), f"{j.get('salaryMin','')}-{j.get('salaryMax','')}", j.get('jobDescription'))
def jobtech():
    # Swedish public employment service, open API, no key.
    for q in ('partnership', 'partner manager', 'affiliate', 'business development', 'growth manager', 'alliance', 'channel manager', 'sponsorship'):
        d = get('https://jobsearch.api.jobtechdev.se/search?limit=100&q=' + urllib.parse.quote(q))
        for j in (d or {}).get('hits', []):
            a = j.get('workplace_address') or {}
            add('jobtech', j.get('headline'), (j.get('employer') or {}).get('name'), j.get('publication_date'), f"{a.get('municipality') or a.get('region') or ''}, Sweden", j.get('webpage_url'), '', (j.get('description') or {}).get('text'))
def himalayas_search():
    for c in ('SE', 'NO', 'DK', 'FI', 'IS', 'EE', 'LV', 'LT', 'IE', 'GB'):
        for q in ('partnerships', 'affiliate', 'business development', 'growth', 'partner manager'):
            d = get(f'https://himalayas.app/jobs/api/search?sort=recent&country={c}&q=' + urllib.parse.quote(q))
            for j in (d or {}).get('jobs', []):
                add('himalayas', j.get('title'), j.get('companyName'), j.get('pubDate'), j.get('locationRestrictions') or 'Worldwide', j.get('applicationLink') or j.get('guid'), f"{j.get('minSalary','')}-{j.get('maxSalary','')} {j.get('currency','')}", j.get('description') or j.get('excerpt'))
for n, f in (('remotive search', remotive_search), ('jobicy by country', jobicy_geo), ('jobtech sweden', jobtech), ('himalayas by country', himalayas_search)): feed(n, f)

# Company hiring systems: slugs come from every company in tracker.md plus a target list.
EXTRA = """coinbase kraken bitpanda nansen ledger consensys ripple circle okx bybit gemini bitstamp moonpay ramp transak alchemy polygon aave uniswap 1inch lido safe etherscan dune phantom trezor bitfinex bitget kucoin mexc wintermute anchorage fireblocks copper bitgo paxos figment blockdaemon messari kaiko tenderly sumsub veriff plaid wise revolut n26 klarna adyen checkout stripe mollie paysera hostinger nordsecurity surfshark deel remote multiplier oysterhr rippling papaya-global velocity-global getyourguide tiqets omio trainline holidu hostaway guesty lodgify zalando vinted vestiaire-collective depop farfetch asos lyst reflaunt aboutyou mytheresa websummit slush informa elastic canonical bitwarden gitlab automattic zapier doist buffer toggl hotjar semrush similarweb coingecko coinmarketcap chainalysis elliptic trmlabs blockchain bitso zerohash deribit sorare immutable animoca nexo bitvavo swissborg ankr infura quicknode chainlink near solana optimism arbitrum offchainlabs eigenlayer layerzero wormhole axelar celestia awin impact partnerstack appsflyer adjust singular kochava nordvpn expressvpn proton namecheap godaddy kinsta wpengine cloudways ionos wix squarespace shopify bigcommerce ahrefs kajabi teachable thinkific systeme getresponse mailerlite brevo activecampaign klaviyo omnisend etoro trading212 freetrade xtb saxo exness pepperstone mistral cohere huggingface perplexity elevenlabs synthesia runwayml jasper writer glean lovable replit vercel supabase notion linear figma airtable intercom hubspot pipedrive typeform miro canva grammarly deepl personio celonis contentful storyblok sanity algolia mirakl openai anthropic coinlist gateio htx bitmart bingx whitebit paybis banxa changelly coinpayments nowpayments bitpay coingate sygnum seba taurus metaco hextrust tangany bunq monzo starling tide payoneer paysafe worldline nexi satispay sumup lightspeed square toast""".split()
NORTH_SLUGS = """spotify klarna king truecaller tink trustly epidemicsound voi einride kry livi mentimeter sanalabs lovable hemnet tradera storytel sinch pagero soundtrap tibber vipps schibsted finn adevinta cognite kahoot oura wolt supercell rovio smartly supermetrics nordsecurity nordvpn surfshark vinted eneba oxylabs castai paysera transfergo bolt veriff pipedrive wise glia skeleton mintos printful sonarworks giraffe360 pleo lunar trustpilot zendesk vivino unity tradeshift podimo airtame templafy firi anyfin zimpler safello coinify bitvavo forefront wayflyer flipdish tines workhuman fenergo intercom hubspot stripe revolut gocardless checkout paddle snyk deliveroo octopusenergy cleo zego thoughtmachine elliptic luno blockchaincom paxful bitpanda coinhouse booking adyen mollie messagebird bitfury ultimate nordea danskebank saxo vestas maersk ikea hm spotifyab northvolt voiceflow qlik kambi evolution betsson unibet mr green storyblok elevenlabs lokalise bolt-eu playtech nortal skeleton-technologies pipedrive-oy dixa onfido monese yoyo tradeledger kevin-pay paysera-lt vinted-lt tesonet surfshark-lt cyberghost""".split()
EXTRA = EXTRA + NORTH_SLUGS
names = []
try:
    t = open('tracker.md').read()
    sec = t[t.index('## Drafted so far'):t.index('## Ready to send manually')]
    names = [l[4:].strip() for l in sec.split('\n') if l.startswith('### ')]
except Exception: pass
slugs = []
for n in names + EXTRA:
    n = re.sub(r'\(.*?\)', '', n).strip().lower()
    for v in (re.sub(r'[^a-z0-9]', '', n), re.sub(r'[^a-z0-9]+', '-', n).strip('-'), re.sub(r'[^a-z0-9]', '', n.split()[0]) if n.split() else ''):
        if v and len(v) > 2: slugs.append(v)
slugs = list(dict.fromkeys(slugs))

def probe(s):
    out = []
    j = get(f'https://api.lever.co/v0/postings/{s}?mode=json', 12) or get(f'https://api.eu.lever.co/v0/postings/{s}?mode=json', 12)
    if isinstance(j, list):
        for p in j:
            c = p.get('categories') or {}
            lst = ' '.join((l.get('text', '') + ' ' + strip(l.get('content', ''))) for l in (p.get('lists') or []))
            out.append(('lever', s, p.get('text'), p.get('createdAt'), (c.get('location') or '') + ' | ' + (p.get('workplaceType') or ''), p.get('hostedUrl'), p.get('salaryRange'), (p.get('descriptionPlain') or '') + ' ' + lst))
    j = get(f'https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true', 15)
    if isinstance(j, dict) and j.get('jobs'):
        for p in j['jobs']:
            out.append(('greenhouse', s, p.get('title'), p.get('first_published') or p.get('updated_at'), (p.get('location') or {}).get('name', ''), p.get('absolute_url'), '', html.unescape(p.get('content', ''))))
    j = get(f'https://api.ashbyhq.com/posting-api/job-board/{s}?includeCompensation=true', 15)
    if isinstance(j, dict) and j.get('jobs'):
        for p in j['jobs']:
            comp = (p.get('compensation') or {}).get('compensationTierSummary', '') if isinstance(p.get('compensation'), dict) else ''
            out.append(('ashby', s, p.get('title'), p.get('publishedAt'), (p.get('location') or '') + ' | ' + (p.get('workplaceType') or '') + (' | remote' if p.get('isRemote') else ''), p.get('jobUrl'), comp, p.get('descriptionPlain') or ''))
    j = get(f'https://{s}.recruitee.com/api/offers/', 12)
    if isinstance(j, dict) and j.get('offers'):
        for p in j['offers']:
            out.append(('recruitee', s, p.get('title'), p.get('published_at') or p.get('created_at'), (p.get('location') or '') + (' | remote' if p.get('remote') else ''), p.get('careers_url'), '', (p.get('description') or '') + ' ' + (p.get('requirements') or '')))
    j = get(f'https://apply.workable.com/api/v1/widget/accounts/{s}?details=true', 12)
    if isinstance(j, dict) and j.get('jobs'):
        for p in j['jobs']:
            out.append(('workable', s, p.get('title'), p.get('published_on') or p.get('created_at'), f"{p.get('city','')}, {p.get('country','')}" + (' | remote' if p.get('telecommuting') else ''), p.get('url'), '', p.get('description') or ''))
    j = get(f'https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=100', 12)
    if isinstance(j, dict) and j.get('content'):
        for p in j['content']:
            loc = p.get('location') or {}
            desc = ''
            if re.search(r'partner|affiliate|business development|alliance|growth|channel', p.get('name', ''), re.I):
                dd = get(f"https://api.smartrecruiters.com/v1/companies/{s}/postings/{p.get('id')}", 12) or {}
                desc = ' '.join(strip((v or {}).get('text', '')) for v in ((dd.get('jobAd') or {}).get('sections') or {}).values())
            out.append(('smartrecruiters', s, p.get('name'), p.get('releasedDate'), f"{loc.get('city','')}, {loc.get('country','').upper()}" + (' | remote' if loc.get('remote') else ''), f"https://jobs.smartrecruiters.com/{s}/{p.get('id')}", '', desc))
    b = get(f'https://{s}.teamtailor.com/jobs.rss', 12, raw=True)
    if b:
        try:
            for it in ET.fromstring(b).iter('item'):
                locs = ' '.join((e.text or '') for e in it.iter() if e.tag.endswith('city') or e.tag.endswith('country') or e.tag.endswith('name'))
                out.append(('teamtailor', s, it.findtext('title'), it.findtext('pubDate'), locs, it.findtext('link'), '', it.findtext('description') or ''))
        except Exception: pass
    return out
with ThreadPoolExecutor(24) as ex: res = list(ex.map(probe, slugs))
live = set()
for r in res:
    for (ats, s, title, date, loc, url, sal, desc) in r:
        live.add(s); add(ats, title, s, date, loc, url, sal, desc)
status['company boards'] = f'{len(live)} of {len(slugs)} guessed slugs have a live board'

KEY = re.compile(r'partner|affiliate|business development|bizdev|\bbd\b|alliance|ecosystem|channel|growth manager|sponsorship', re.I)
BAD = re.compile(r'director|\bvp\b|vice president|chief|principal|intern\b|internship|student|head of|developer|engineer|designer|recruit|hr business|people partner|business partner|legal|counsel|assistant|representative|\bsdr\b|\bbdr\b', re.I)
LOCOK = re.compile(r'remote|europe|emea|worldwide|anywhere|global|croatia|zagreb|\beu\b', re.I)
LOCBAD = re.compile(r'\b(us only|usa|united states|north america|americas|canada|latam|latin america|apac|asia|india|australia|singapore|brazil|mexico|new york|nyc|san francisco|austin|boston|seattle|chicago|toronto)\b', re.I)
def flags(r):
    t = r['desc']; f = []
    m = [int(x) for x in re.findall(r'(\d{1,2})\s*\+?\s*(?:years|yrs)', t)]
    if m: f.append(f'asks up to {max(m)}+ years')
    if re.search(r'no base salary|commission[- ]only|100% commission|(?:role|position|compensation|pay) (?:is|will be) (?:entirely |fully )?commission', t, re.I): f.append('COMMISSION ONLY')
    LANGS = r'german|french|spanish|dutch|italian|portuguese|polish|czech|slovak|japanese|korean|arabic|chinese|mandarin|cantonese|vietnamese|thai|indonesian|turkish|russian|ukrainian|hebrew|swedish|norwegian|danish|finnish|greek|romanian|hungarian|bulgarian'
    if re.search(r'\b(' + LANGS + r')\b[^.]{0,40}(speak|fluen|native|required|mandatory|must)|(fluen|native|proficien|impeccable)[^.]{0,40}\b(' + LANGS + r'|local language)\b|local language|must\b[^.]{0,20}(?:' + LANGS + r')', t, re.I): f.append('LANGUAGE required')
    if re.search(r'located in the u\.?s|must (?:be|reside).{0,25}(?:u\.?s|united states|nyc|new york)|nyc[- ]based', t, re.I): f.append('US based only')
    if re.search(r'hybrid|in[- ]office|days? (?:a|per) week in', t, re.I): f.append('hybrid/office days')
    if re.search(r'relocat|visa sponsor', t, re.I): f.append('relocation/visa mentioned')
    if re.search(r'right to work', t, re.I): f.append('needs right to work')
    return f
NORTH = re.compile(r'\b(sweden|stockholm|gothenburg|goteborg|g\u00f6teborg|malm\u00f6|malmo|uppsala|link\u00f6ping|norway|oslo|bergen|trondheim|stavanger|denmark|copenhagen|k\u00f8benhavn|aarhus|odense|aalborg|finland|helsinki|espoo|tampere|oulu|iceland|reykjavik|estonia|tallinn|tartu|latvia|riga|lithuania|vilnius|kaunas|ireland|dublin|cork|galway|limerick|united kingdom|uk|london|manchester|edinburgh|england|scotland|wales|belfast|bristol|birmingham|leeds|glasgow|cambridge|oxford)\b', re.I)
KEY2 = re.compile(r'growth (?:marketing )?(?:manager|lead|specialist|associate)|performance marketing|partner success|acquisition manager|marketing partnerships|community partnerships', re.I)
def nonenglish(t):
    w = re.findall(r"[a-z\u00e5\u00e4\u00f6\u00e6\u00f8]+", t.lower()[:3000])
    en = sum(1 for x in w if x in ('the', 'and', 'to', 'of', 'you', 'we', 'with', 'for', 'our', 'will'))
    other = sum(1 for x in w if x in ('och', 'att', 'som', 'vi', 'f\u00f6r', 'med', 'du', 'ett', 'till', '\u00e4r', 'og', 'er', 'det', 'der', 'ja', 'ja', 'ett', 'kun', 'tai', 'ovat', 'meid\u00e4n', 'jotta'))
    return other >= 8 and other > en
out = []
for r in recs:
    if not r['date'] or (NOW - r['date']).days > args.days: continue
    if not (KEY.search(r['title']) or KEY2.search(r['title'])) or BAD.search(r['title']): continue
    loc = r['loc'] or 'Remote'
    north = bool(NORTH.search(loc))
    if not north:
        if not LOCOK.search(loc): continue
        if LOCBAD.search(loc) and not re.search(r'europe|emea|worldwide|anywhere|croatia|\beu\b', loc, re.I): continue
    r['flags'] = flags(r)
    if nonenglish(r['desc']) and 'LANGUAGE required' not in r['flags']: r['flags'].append('LANGUAGE required (ad not in English)')
    r['north'] = north; r['age_days'] = (NOW - r['date']).days; out.append(r)
out.sort(key=lambda r: r['date'], reverse=True)
import os, io, contextlib
os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
json.dump([dict(r, date=r['date'].isoformat()) for r in out], open(args.out, 'w'), indent=1)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    print(f"Generated: {NOW.strftime('%Y-%m-%d %H:%M UTC')}")
    print('SOURCES'); [print(f'  {k}: {v}') for k, v in status.items()]
    print(f"\n{len(out)} dated, open postings within {args.days} days matching the title filter (full text in {args.out})\n")
    for label, pick in (('NORTHERN EUROPE (located in the ten countries, any work mode)', True), ('REMOTE OR EUROPE WIDE (not located in the ten countries)', False)):
        print(f"== {label}")
        for r in (x for x in out if x['north'] == pick):
            print(f"{r['date'].date()} ({r['age_days']}d) | {r['company'][:22]:22} | {r['title'][:58]:58} | {r['loc'][:34]:34} | {r['sal'][:22]:22} | {', '.join(r['flags']) or '-'}\n    {r['url']}")
        print()
txt = buf.getvalue()
open(os.path.splitext(args.out)[0] + '.txt', 'w').write(txt)
print(txt)
