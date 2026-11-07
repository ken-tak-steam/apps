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
NOTE_DATA = {
    'file_asshukun': {
        'image': 'https://assets.st-note.com/production/uploads/images/326813055/rectangle_large_type_2_50021050485a1eb1f2bb2f94ed88e95f.png?dpr=2&frame=1&width=297',
        'note': 'https://note.com/kentak2020',
    },
    'trimming-kun': {
        'image': 'https://assets.st-note.com/production/uploads/images/326785150/rectangle_large_type_2_30bf994ea27cec5c756ace3d3b1595da.png?dpr=2&frame=1&width=297',
        'note': 'https://note.com/kentak2020',
    },
    'koukaishashin_shiagerukun': {
        'image': 'https://assets.st-note.com/production/uploads/images/328367837/rectangle_large_type_2_36bf32f61b5de3be47ca11d4185b9091.png?dpr=2&frame=1&width=297',
        'note': 'https://note.com/kentak2020/n/nefb63a7a25f4',
    },
    'pdf_kakikomikun': {
        'image': 'https://assets.st-note.com/production/uploads/images/327597417/rectangle_large_type_2_5ab9770306014a7b28c32151bb2de78f.png?dpr=2&frame=1&width=297',
        'note': 'https://note.com/kentak2020/n/n64befef18889',
    },
    'pdf_matomerukun': {
        'image': 'https://assets.st-note.com/production/uploads/images/326551708/rectangle_large_type_2_db2731787615481ef0c46921811b3041.png?dpr=2&frame=1&width=297',
        'note': 'https://note.com/kentak2020/n/n853f091cb1bf',
    },
}

def render(apps):
    cards = []
    for a in apps:
        name = escape(a['name'])
        data = NOTE_DATA.get(a['repo'], {})
        image = data.get('image')
        note = data.get('note')
        visual = (f'<img src="{escape(image, quote=True)}" alt="{name}のnote見出し画像" loading="lazy">' if image
                  else f'<div class="placeholder"><span>{name}</span><small>noteサムネイル準備中</small></div>')
        if a['download']:
            download = f'<a class="primary" href="{escape(a["download"],quote=True)}" target="_blank" rel="noopener noreferrer">ダウンロード ↗</a>'
        else:
            download = '<span class="pending">ダウンロードページ準備中</span>'
        note_link = (f'<a href="{escape(note,quote=True)}" target="_blank" rel="noopener noreferrer">note記事を見る ↗</a>'
                     if note and '/n/' in note else
                     f'<a href="{escape(note,quote=True)}" target="_blank" rel="noopener noreferrer">noteの記事一覧を見る ↗</a>'
                     if note else '<span class="pending">note記事準備中</span>')
        cards.append(f'<article><div class="thumb">{visual}</div><div class="card-body"><h2>{name}</h2><div class="links">{download}{note_link}</div></div></article>')
    template = (ROOT/'template.html').read_text()
    stamp = datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y年%m月%d日')
    (ROOT/'index.html').write_text(template.replace('{{CARDS}}','\n'.join(cards)).replace('{{COUNT}}',str(len(apps))).replace('{{DATE}}',stamp))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    if args.offline:
        apps = json.loads((ROOT/'apps.json').read_text())
    else:
        apps = discover()
        if not apps:
            raise RuntimeError('No applications found; keep existing catalog')
        (ROOT/'apps.json').write_text(json.dumps(apps, ensure_ascii=False, indent=2)+'\n')
    render(apps)
