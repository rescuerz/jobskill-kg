"""Run after the user publishes: verify anonymous GitHub access and file hashes."""
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'JobSkill-KG-publication-check'})
    with urllib.request.urlopen(req,timeout=60) as response:return response.read()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default='rescuerz/JobSkill-KG');args=ap.parse_args()
    local=Path(__file__).resolve().parents[1]
    repo=json.loads(get('https://api.github.com/repos/'+args.repo))
    if repo['private']:raise SystemExit('Repository is not public')
    branch=repo['default_branch'];base=f'https://raw.githubusercontent.com/{args.repo}/{branch}/'
    manifest=json.loads(get(base+'SHA256SUMS.json'))
    expected=json.loads((local/'SHA256SUMS.json').read_text())
    if manifest!=expected:raise SystemExit('Remote manifest differs from this release')
    for name in ('README.md','JobSkill-KG-data.zip','eval/holdout_v1/ai_report.json','src/app/serve_api.py'):
        digest=hashlib.sha256(get(base+name)).hexdigest()
        if digest!=expected[name]:raise SystemExit('Hash mismatch: '+name)
        print('Verified:',name)
    print('Public repository and core downloads verified:',repo['html_url'])
if __name__=='__main__':main()
