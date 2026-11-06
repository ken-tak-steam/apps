"""Generate a static catalog from public GitHub repositories (standard library only)."""
import json, os, re, urllib.request, urllib.error
from urllib.parse import quote
from pathlib import Path
from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
OWNER = 'ken-tak-steam'
ROOT = Path(__file__).resolve().parents[1]
def get(path):
    headers = {'Accept':'application/vnd.github+json','User-Agent':'apps-catalog'}
    if os.environ.get('GITHUB_TOKEN'): headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urllib.request.urlopen(urllib.request.Request('https://api.github.com'+path, headers=headers), timeout=30) as response:
        return json.load(response)
def discover():
    repos=[]
    page=1
    while True:
        batch=get(f'/users/{OWNER}/repos?per_page=100&page={page}')
        repos.extend(batch)
        if len(batch)<100: break
        page+=1
    apps=[]
    for repo in repos:
        if repo['name']=='apps' or repo['fork'] or repo['archived']: continue
        try:
            files=get(f"/repos/{OWNER}/{repo['name']}/contents/")
        except urllib.error.HTTPError as error:
            if error.code == 404: continue  # Empty repositories have no contents.
            raise
        names={f['name'] for f in files}
        if 'index.html' not in names: continue
        raw_url=f"https://raw.githubusercontent.com/{OWNER}/{repo['name']}/{quote(repo['default_branch'],safe='')}/index.html"
        with urllib.request.urlopen(raw_url,timeout=30) as response:
            html=response.read(65536).decode('utf-8',errors='replace')
        title=re.search(r'<title[^>]*>(.*?)</title>', html, re.I|re.S)
        from html import unescape
        label=unescape(title.group(1)).split('｜')[0].split(' - ')[0].strip() if title else repo['name']
        base=f"https://{OWNER}.github.io/{repo['name']}/"
        apps.append({'repo':repo['name'],'name':label,'description':repo.get('description') or '', 'url':base if repo['has_pages'] else None,'download':base+'download.html' if repo['has_pages'] and 'download.html' in names else None})
    return sorted(apps,key=lambda a:a['repo'])
def render(apps):
    cards=[]
    for a in apps:
        name=escape(a['name']); base=f"https://github.com/{OWNER}/{a['repo']}"
        links=[]
        if a['url']: links.append(f'<a class="primary" href="{escape(a["url"],quote=True)}">{name}アプリを今すぐ使う <span aria-hidden="true">↗</span></a>')
        else: links.append('<span class="pending">Web版は未公開です</span>')
        if a['download']: links.append(f'<a href="{escape(a["download"],quote=True)}">{name}をダウンロード</a>')
        else: links.append(f'<a href="{base}/blob/HEAD/index.html">{name}のHTMLを取得（GitHub）</a>')
        links.append(f'<a class="source" href="{base}">GitHubリンク ↗</a>')
        cards.append(f'<article><h2>{name}</h2><p>{escape(a["description"])}</p><div class="links">'+''.join(links)+'</div></article>')
    template=(ROOT/'template.html').read_text()
    stamp=datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y年%m月%d日')
    (ROOT/'index.html').write_text(template.replace('{{CARDS}}','\n'.join(cards)).replace('{{COUNT}}',str(len(apps))).replace('{{DATE}}',stamp))
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args()
    if args.offline: apps=json.loads((ROOT/'apps.json').read_text())
    else:
        apps=discover()
        if not apps: raise RuntimeError('No applications found; keep existing catalog')
        (ROOT/'apps.json').write_text(json.dumps(apps,ensure_ascii=False,indent=2)+'\n')
    render(apps)
