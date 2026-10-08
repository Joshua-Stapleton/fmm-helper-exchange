#!/usr/bin/env python3
"""Check the selected public tree and nested archives, without printing contents."""
from pathlib import Path
import ast,io,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','__pycache__','.venv','results','build','replay','lower_replay'}
PRIVATE=re.compile(rb'/(?:Users|home)/[^/\s]+/|/(?:private)/tmp/|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}')
issues=[];counts={'files':0,'python_sources':0,'archives':0,'markdown_links':0}
def check(name,data,depth=0):
    counts['files']+=1
    if PRIVATE.search(data):issues.append({'file':name,'issue':'private path or credential pattern'})
    if data[:4]in [b'\x7fELF',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe']:issues.append({'file':name,'issue':'compiled binary'})
    if name.endswith(('.pyc','.pyo'))or '/__pycache__/'in name:issues.append({'file':name,'issue':'Python cache'})
    if name.endswith('.py'):
        try:ast.parse(data.decode(),filename=name);counts['python_sources']+=1
        except (UnicodeDecodeError,SyntaxError)as e:issues.append({'file':name,'issue':str(e)})
    if name.endswith('.zip'):
        counts['archives']+=1
        if depth>=6:raise ValueError('archive recursion limit')
        with zipfile.ZipFile(io.BytesIO(data))as z:
            for n in z.namelist():
                if n.startswith('/')or '..'in Path(n).parts:issues.append({'file':name+'!'+n,'issue':'unsafe archive member'})
                if not n.endswith('/'):check(name+'!'+n,z.read(n),depth+1)
for p in sorted(ROOT.rglob('*')):
    if not p.is_file()or any(s in SKIP for s in p.relative_to(ROOT).parts):continue
    check(str(p.relative_to(ROOT)),p.read_bytes())
    if p.suffix=='.md':
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            target=target.split('#')[0].split(' "')[0].strip('<>')
            if not target or '://'in target or target.startswith('mailto:'):continue
            counts['markdown_links']+=1
            if not(p.parent/target).exists():issues.append({'file':str(p.relative_to(ROOT)),'issue':'missing link '+target})
print(json.dumps({'status':'PASS'if not issues else 'FAIL','counts':counts,'issues':issues},indent=2))
raise SystemExit(bool(issues))
