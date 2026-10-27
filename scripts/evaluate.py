#!/usr/bin/env python3
"""Fit rating out of 10 for one posting, measured against config/profile.json.

The rubric borrows two ideas from the open source career-ops project (github.com/career-ops-hq/career-ops):
scoring several named dimensions instead of one gut number, and saying how much evidence backs the score.
Dimensions: role match (3.5), seniority fit (2), work model and place (2), pay (1), sector (1.5). Red flags subtract.
Confidence is High when the posting text was read and years and pay are known, Medium when the text was read but something is missing,
Low when only the title was available. A posting check (freshness, how specific the text is) is kept apart from the score, like career-ops' legitimacy block."""
import json, re
P = json.load(open('config/profile.json'))
MY_SKILLS = P['skills']
VOCAB = ['affiliate', 'partnership', 'partner onboarding', 'partner management', 'business development', 'account management', 'negotiat', 'crm', 'hubspot', 'salesforce',
         'seo', 'paid media', 'google ads', 'meta ads', 'analytics', 'reporting', 'excel', 'sql', 'b2b', 'saas', 'fintech', 'payments', 'crypto', 'web3', 'blockchain', 'content',
         'social media', 'community', 'influencer', 'kpi', 'revenue share', 'commission', 'tracking', 'attribution', 'impact', 'awin', 'partnerstack', 'looker', 'api', 'integration',
         'go-to-market', 'gtm', 'lead generation', 'email marketing', 'lifecycle', 'retention', 'cac', 'ltv', 'a/b test', 'stakeholder', 'enterprise', 'product partnerships']
def rhalf(x): return round(x * 2) / 2
def years(job, jd):
    ys = [int(m.group(1)) for f in job.get('flags', []) for m in [re.search(r'up to (\d+)', f)] if m]
    ys += [int(m.group(1)) for m in re.finditer(r'(\d{1,2})\s*\+?\s*(?:years|yrs)', (job.get('exp') or '') + ' ' + (jd or '')) if int(m.group(1)) <= 15]
    return max(ys) if ys else None
def role_points(job, jd):
    t = job['title'].lower(); txt = (t + ' ' + (jd or '')[:2500]).lower()
    if 'affiliate' in t and re.search(r'partner|manager|lead', t): p = 3.5
    elif 'affiliate' in t: p = 3.2
    elif re.search(r'partnerships?\b|partner (?:manager|development)|alliances?', t): p = 3.0
    elif re.search(r'business development|\bbd\b', t): p = 2.5
    elif re.search(r'channel|ecosystem|sponsorship', t): p = 2.3
    elif re.search(r'growth|performance marketing|acquisition|lifecycle', t): p = 2.0
    elif re.search(r'product marketing|events? marketing|experiential|brand|vibe', t): p = 0.8
    elif re.search(r'growth|seo |paid (?:media|social|search)|community manager|content marketing|social media manager|email marketing|crm manager|lifecycle', t): p = 1.8
    elif 'marketing manager' in t: p = 1.5
    else: p = 1.0
    if jd and re.search(r'affiliate|partner onboarding|revenue share|referral', txt) and p < 3.5: p += 0.5
    return min(3.5, p)
def evaluate(job, jd=''):
    jd = jd or ''
    flags = job.get('flags', []) or []
    yrs = years(job, jd); t = job['title'].lower()
    role = role_points(job, jd)
    # seniority: he has about 4 years
    if yrs is None: sen = 1.0
    elif yrs <= 3: sen = 2.0
    elif yrs == 4: sen = 2.0
    elif yrs == 5: sen = 1.0
    else: sen = 0.0
    if re.search(r'senior|lead|principal', t): sen = max(0.0, sen - 0.5)
    if re.search(r'junior|associate|entry', t): sen = min(sen, 1.0)
    # work model and place
    region = job.get('region'); where = ((job.get('country') or '') + ' ' + (job.get('city') or '')).lower(); mode = (job.get('mode') or '').lower()
    needs_rtw = any('right to work' in f for f in flags) or 'right to work' in (job.get('visa') or '').lower()
    reloc = any('relocation' in f for f in flags) or bool(re.search(r'relocation (?:and visa )?(?:support|assistance) (?:is )?(?:available|offered|provided)|visa sponsorship', jd, re.I))
    if region == 'r':
        c = job.get('country') or 'Remote'
        place = 2.0 if c in ('Remote', 'Croatia') else 1.0
        if needs_rtw: place = min(place, 1.0)
    else:
        if 'croatia' in where or 'zagreb' in where: place = 2.0
        else:
            place = 0.8
            if 'hybrid' in mode: place += 0.1
            if reloc: place += 0.5
            if job.get('visaState') == 'none': place = 0.2
    # pay
    pay_txt = (job.get('pay') or '') + ' ' + ' '.join(re.findall(r'[€$£]\s?[\d,\.]+', jd[:3000]))
    nums = [int(n.replace(',', '')) for n in re.findall(r'(\d{1,3}(?:,\d{3})+|\d{4,6})', pay_txt)]
    if not nums: pay = 0.5
    else:
        top = max(nums); monthly = top / 12 if top > 20000 else top
        pay = 1.0 if monthly >= 2500 else (0.6 if monthly >= 1000 else 0.2)
    # sector
    blob = (job.get('company', '') + ' ' + t + ' ' + jd[:1500]).lower()
    sector = 1.5 if any(s in blob for s in P['strong_sectors']) else 0.7
    # red flags
    pen = 0.0; notes = []
    if any(f.startswith('LANGUAGE') for f in flags): pen += 1.5; notes.append('local language asked')
    if any(f.startswith('COMMISSION') for f in flags): pen += 3.0; notes.append('commission only')
    if needs_rtw: pen += 0.5; notes.append('needs existing right to work')
    if re.search(r'contractor|service contract|freelance|maternity cover|fixed term|fixed-term|temporary', (job.get('mode') or '') + ' ' + jd[:1500] + ' ' + (job.get('why') or ''), re.I): pen += 1.0; notes.append('contract rather than employee')
    total = role + sen + place + pay + sector - pen
    fit = max(1.0, min(10.0, rhalf(total)))
    # confidence: how much of the rating rests on text that was actually read
    read = bool(job.get('read')) or (bool(jd) and len(jd) > 600)
    if read and yrs is not None and nums: conf = 'High'
    elif read: conf = 'Medium'
    else: conf = 'Low'
    if conf == 'Low': fit = min(fit, 7.0)
    elif conf == 'Medium': fit = min(fit, 8.5)
    low = jd.lower()
    have = sorted({k for k, syn in MY_SKILLS.items() if any(s in low for s in syn)}) if jd else []
    want = sorted({v for v in VOCAB if v in low}) if jd else []
    mine_words = {s for syn in MY_SKILLS.values() for s in syn}
    missing = sorted({v for v in want if not any(v in s or s in v for s in mine_words)})[:8]
    return dict(fit=fit, conf=conf, parts=dict(role=round(role, 1), level=round(sen, 1), place=round(place, 1), pay=round(pay, 1), sector=round(sector, 1), flags=round(-pen, 1)),
                notes=notes, have=have, missing=missing)
def posting_check(job, jd, age):
    """Looks live, or check first. Not part of the score."""
    sig = []
    if age is not None and age <= 14: sig.append('posted in the last two weeks')
    if jd and len(jd) > 1500: sig.append('detailed description')
    if job.get('closes'): sig.append('has a closing date')
    bad = []
    if age is None: bad.append('no posting date')
    elif age > 21: bad.append('older than three weeks')
    if not jd: bad.append('text not read')
    tier = 'Looks live' if len(sig) >= 2 and not bad else ('Check first' if bad else 'Looks live')
    return dict(tier=tier, good=sig, check=bad)
