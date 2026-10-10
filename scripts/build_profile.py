"""Generate repository-hosted profile art and public GitHub widgets (stdlib only)."""
import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER = 'aathish-m'

def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'aathish-profile'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urlopen(Request('https://api.github.com/' + path, headers=headers), timeout=30) as response:
        return json.load(response)

user = api(f'users/{USER}')
repos = []
page = 1
while True:
    batch = api(f'users/{USER}/repos?per_page=100&page={page}&type=owner')
    repos.extend(batch)
    if len(batch) < 100:
        break
    page += 1
originals = [r for r in repos if not r['fork']]
langs = Counter(r['language'] for r in originals if r['language'])
updated = datetime.now(timezone.utc).strftime('%d %b %Y')

def svg(body, height, title):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>{body}</svg>'''

def text(x, y, value, size=16, color=None, weight=400, extra=''):
    return f'<text x="{x}" y="{y}" fill="{color or fg}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{weight}" {extra}>{escape(str(value))}</text>'

for theme in ('dark', 'light'):
    bg, panel, fg, muted, line, mint = ('#0D1117','#151D27','#F0F6FC','#9BAEC2','#263442','#79F2C0') if theme == 'dark' else ('#F6F8FA','#FFFFFF','#172B3A','#526579','#D8E2EA','#087F62')
    header = f'''<defs><pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{line}" stroke-width="0.6"/></pattern><linearGradient id="accent"><stop stop-color="{mint}"/><stop offset="1" stop-color="#739CFF"/></linearGradient></defs>
<style>@keyframes drift{{to{{stroke-dashoffset:-160}}}}@keyframes pulse{{50%{{opacity:.25}}}}.orbit{{animation:drift 16s linear infinite}}.pulse{{animation:pulse 3s ease-in-out infinite}}@media(prefers-reduced-motion:reduce){{.orbit,.pulse{{animation:none}}}}</style>
<rect width="960" height="360" rx="24" fill="{bg}"/><rect width="960" height="360" rx="24" fill="url(#grid)" opacity=".5"/>
<rect x="1" y="1" width="958" height="358" rx="23" fill="none" stroke="{line}"/>
<rect x="40" y="42" width="4" height="18" rx="2" fill="{mint}"/>
{ text(56,56,'AATHISH M  /  SOFTWARE ENGINEER',13,muted,700, 'letter-spacing="2"') }
{ text(40,134,'Curiosity into code.',52,fg,700) }
{ text(40,192,'Ideas into interfaces.',46,mint,700) }
{ text(42,236,'React · TypeScript · Thoughtful user experiences',18,muted) }
<path d="M42 274H588" stroke="{line}"/>
{ text(42,310,'PALANI, INDIA',12,muted,700,'letter-spacing="2"') }
{ text(300,310,'EXPLORE. BUILD. KEEP LEARNING.',12,muted,700,'letter-spacing="1.5"') }
<circle cx="793" cy="172" r="111" fill="{panel}" stroke="{line}"/>
<circle class="orbit" cx="793" cy="172" r="111" fill="none" stroke="url(#accent)" stroke-width="2" stroke-dasharray="24 16"/>
<circle cx="793" cy="172" r="84" fill="none" stroke="{line}"/>
<path d="M763 149l-25 23 25 23m59-46 25 23-25 23m-20-63-20 79" fill="none" stroke="url(#accent)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
<circle class="pulse" cx="793" cy="61" r="6" fill="{mint}"/>
{ text(793,322,'ALWAYS A WORK IN PROGRESS',10,muted,700,'text-anchor="middle" letter-spacing="1"') }'''
    stats = f'<rect x="1" y="1" width="958" height="228" rx="20" fill="{bg}" stroke="{line}"/>'
    stats += text(32,36,'THE PUBLIC WORKBENCH',12,mint,700,'letter-spacing="2"')
    for i,(label,value) in enumerate([('PUBLIC REPOSITORIES',user['public_repos']),('ORIGINAL REPOSITORIES',len(originals)),('STARS ON ORIGINALS',sum(r['stargazers_count'] for r in originals)),('FOLLOWERS',user['followers'])]):
        x=32+i*232
        stats += text(x,92,value,38,fg,700)+text(x,118,label,10,muted,700,'letter-spacing="1"')
    stats += f'<path d="M32 140H928" stroke="{line}"/>'
    stats += text(32,166,'PRIMARY LANGUAGES · ORIGINAL REPOSITORIES',10,muted,700,'letter-spacing="1"')
    x=32
    for language,count in langs.most_common(5):
        stats += f'<circle cx="{x+4}" cy="191" r="4" fill="{mint}"/>' + text(x+16,196,f'{language}  {count}',13,fg)
        x += 170
    stats += text(928,36,f'UPDATED {updated.upper()} · UTC',10,muted,400,'text-anchor="end"')
    (ROOT / f'assets/stats-{theme}.svg').write_text(svg(stats,230,'Public GitHub statistics. Language counts represent primary languages of original public repositories.'))
    stack = f'<rect x="1" y="1" width="958" height="148" rx="20" fill="{bg}" stroke="{line}"/>'
    for row, items in enumerate([['React','TypeScript','JavaScript','Next.js','Tailwind CSS'],['HTML & CSS','C++','Git','Figma','Firebase']]):
        for col,item in enumerate(items):
            x,y=20+col*186,20+row*64
            stack += f'<rect x="{x}" y="{y}" width="176" height="48" rx="10" fill="{panel}" stroke="{line}"/>'
            stack += text(x+88,y+30,item,16,mint if row==0 else fg,600,'text-anchor="middle"')
print(f'Refreshed two statistics SVG assets from {len(repos)} public repositories.')
