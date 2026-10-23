"""Package the same static release for GitHub's project-subpath hosting."""
import hashlib,json,pathlib,re,shutil,zipfile
from urllib.parse import urlparse
R=pathlib.Path(__file__).resolve().parents[1]; C=json.loads((R/'config.json').read_text(encoding='utf-8'))
source=R/'dist'; target=R/'outputs/pages'; prefix=urlparse(C['origin']).path.rstrip('/')
target.mkdir(parents=True,exist_ok=True)
for p in source.rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(source); dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix=='.html':
        s=p.read_text(encoding='utf-8')
        s=re.sub(r'(href|src)="/(?!/)',lambda m:m[1]+'="'+prefix+'/',s)
        dest.write_text(s,encoding='utf-8',newline='\n')
    else:shutil.copyfile(p,dest)
(target/'.nojekyll').write_text('',encoding='utf-8')
assert (target/'index.html').exists()
for p in target.rglob('*.html'):
    s=p.read_text(encoding='utf-8')
    assert not re.search(r'(?:href|src)="/(?!'+re.escape(prefix.lstrip('/'))+r'/)',s)
print(json.dumps({'mirror':str(target),'canonical_origin':C['origin'],'prefix':prefix}))
