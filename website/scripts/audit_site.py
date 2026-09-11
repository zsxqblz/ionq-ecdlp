from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,re,sys,collections,os
base=os.environ.get("SITE_BASE_PATH", "").rstrip("/")
root=Path(sys.argv[1]).resolve();errors=[];warnings=[];documents={};counts=collections.Counter()
class Doc(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.ids=[];self.refs=[];self.svg=0;self.math=0;self.text=[];self.ignored=0;self.svg_depth=0;self.svg_title=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id'in a:self.ids.append(a['id'])
  for k in ['href','src']:
   if a.get(k):self.refs.append((tag,k,a[k]))
  if tag=='img' and not a.get('alt'):errors.append((self.file,'image missing alt',a.get('src')))
  if tag=='math':self.math+=1
  if tag=='svg':self.svg+=int(a.get('role')=='img');self.svg_depth+=1;self.svg_title=a.get('role')!='img'
  if self.svg_depth and tag=='title':self.svg_title=True
  if tag in ['script','style','annotation']:self.ignored+=1
 def handle_endtag(self,tag):
  if tag=='svg':
   if not self.svg_title:warnings.append((self.file,'SVG lacks title'))
   self.svg_depth-=1
  if tag in ['script','style','annotation']:self.ignored-=1
 def handle_data(self,data):
  if not self.ignored:self.text.append(data)
for file in root.rglob('*.html'):
 d=Doc();d.file=str(file.relative_to(root));d.feed(file.read_text());documents[file]=d
 duplicates=[k for k,n in collections.Counter(d.ids).items() if n>1]
 for k in duplicates:errors.append((d.file,'duplicate id',k))
 for fragment in [r'\(',r'\)',r'\[',r'\]',r'\left',r'\right']:
  if fragment in ''.join(d.text):errors.append((d.file,'unrendered math fragment',fragment))
 counts.update({'pages':1,'svg':d.svg,'math':d.math,'words':len(re.findall(r'\b\w+\b',' '.join(d.text)))})
for file,d in documents.items():
 for tag,key,ref in d.refs:
  u=urlsplit(ref)
  if u.scheme or u.netloc or ref.startswith('data:'):continue
  path=unquote(u.path)
  if base and (path==base or path.startswith(base+'/')):path=path[len(base):] or '/'
  dest=root/path.lstrip('/') if path.startswith('/') else file.parent/path
  if not u.path:dest=file
  if dest.is_dir():dest=dest/'index.html'
  if not dest.exists():errors.append((d.file,'missing internal target',ref));continue
  if u.fragment and dest.suffix=='.html':
   other=documents.get(dest)
   if other and unquote(u.fragment) not in other.ids:errors.append((d.file,'missing anchor',ref))
audit={'counts':dict(counts),'errors':errors,'warnings':warnings}
(root/'format-audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps({'counts':dict(counts),'errors':len(errors),'warnings':len(warnings)},indent=2))
for x in list(dict.fromkeys(tuple(x)for x in errors))[:100]:print(x)
if errors:sys.exit(1)
