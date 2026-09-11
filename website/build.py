from pathlib import Path
import json,re,html,shutil,subprocess
from html.parser import HTMLParser
from visuals import fourier_visual

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'dist'
SOURCE='https://cdn.prod.website-files.com/68836d4838193cb461ebc7d2/6a9f3d3ada3cb06dec2ac20e_IonQ%20Fully%20Compiled%20End-to-End%20Resource%20Estimate%20for%20Breaking%20256-Bit%20Elliptic-Curve%20Signatures.pdf'
TITLE='Breaking 256-bit elliptic-curve signatures: a circuit-to-hardware study'
pages=[]
for p in sorted((ROOT/'content').glob('*.json')):
 data=json.loads(p.read_text());pages.extend(data if isinstance(data,list) else data['pages'])
assert len({p['slug'] for p in pages})==len(pages),'duplicate page slug'
def part(p):
 if p['group']=='references':return 'References'
 if p['group']=='appendix':return 'VII · Appendices'
 if p['group']=='guide':return 'Reading guide'
 n=float(p.get('order',0))
 if n<3:return 'I · Overview'
 if n<5:return 'II · ECDLP'
 if n<8:return 'III · Arithmetic'
 if n<12:return 'IV · Compiler'
 if n<13:return 'V · Architecture'
 return 'VI · Conclusion'
GROUPS=['I · Overview','II · ECDLP','III · Arithmetic','IV · Compiler','V · Architecture','VI · Conclusion','VII · Appendices','References','Reading guide']
def pkey(p):return (GROUPS.index(part(p)),float(p.get('order',100)),p['title'])
pages.sort(key=pkey)
byid={p['slug']:p for p in pages}
def url(p):return '/' if p['slug']=='index' else '/lesson/'+p['slug']+'/'
def e(x):return html.escape(str(x),quote=True)
figs=json.loads((ROOT/'assets/figures.json').read_text())
figrefs={}
class ProseCounter(HTMLParser):
 def __init__(self,include_details=False):
  super().__init__();self.skip=0;self.parts=[];self.ignored={'svg','script','style'} | (set() if include_details else {'details'})
 def handle_starttag(self,tag,attrs):
  if tag in self.ignored:self.skip+=1
 def handle_endtag(self,tag):
  if tag in self.ignored:self.skip-=1
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
def prose_words(body,include_details=False):
 body=re.sub(r'\\\(.*?\\\)|\\\[.*?\\\]',' ',body,flags=re.S)
 counter=ProseCounter(include_details);counter.feed(body)
 return len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b",' '.join(counter.parts)))
def figure(match):
 n=match.group(1);f=figs.get(n)
 if not f:
  source_page=26 if n=='7' else 64 if n=='22' else 1
  return f'<p class="evidence"><a href="{SOURCE}#page={source_page}" target="_blank" rel="noopener">Inspect source Figure {e(n)} and its simulation curves (p. {source_page}).</a> The disclosed rates and experimental settings are explained here. The underlying point-by-point simulation samples are not supplied with the PDF; these notes do not reconstruct unreported samples.</p>'
 figrefs[n]=figrefs.get(n,0)+1
 cap=f['caption'];cap=re.sub(r'^FIG\. \d+:\s*','',cap)
 alt=cap[:240] or 'Original circuit or architecture drawing from the source paper'
 hint=f.get('hint',cap)
 caption_details=f'<details class="caption-details"><summary>Original caption</summary><p>{e(cap)}</p></details>' if hint!=cap else ''
 out=f'<figure class="source-figure" id="source-figure-{e(n)}"><a class="figurelink" href="{e(f["file"])}" target="_blank" rel="noopener"><img src="{e(f["file"])}" alt="{e(alt)}" loading="lazy"></a><figcaption><strong>Source Figure {e(n)}.</strong> {e(hint)} <a href="{SOURCE}#page={f["page"]}" target="_blank" rel="noopener">Paper, p. {f["page"]}</a><a class="fig-open" href="{e(f["file"])}" target="_blank" rel="noopener">Open full-size drawing ↗</a>{caption_details}</figcaption></figure>'
 if f.get('fold'):
  out=f'<details class="source-panel"><summary>Source Figure {e(n)} · {e(f["label"])}</summary>{out}</details>'
 if n=='21':out+=figure(type('M',(),{'group':lambda self,i:'21b'})())
 return out
glossary=json.loads((ROOT/'data/notation.json').read_text())
def definitions(prefix=''):
 return '<dl>'+''.join(f'<dt id="{prefix}def-{e(d["id"])}">{d["symbol"]} — {e(d["name"])}</dt><dd>{d["definition"]} <a href="{e(d["url"])}">Use in the construction</a></dd>' for d in glossary)+'</dl>'
def nav(current):
 top='';side=''
 for g in GROUPS:
  pp=[p for p in pages if part(p)==g and p['slug']!='index']
  if not pp:continue
  lis=''.join(f'<a href="{url(p)}">{e(p.get("navTitle",p["title"]))}</a>' for p in pp)
  if g!='Reading guide':top+=f'<div class="topitem {"active" if part(current)==g else ""}"><a href="{url(pp[0])}">{e(g)}</a><div class="topdrop">{lis}</div></div>'
  side+=f'<section class="navgroup"><h2>{e(g)}</h2>'+''.join(f'<a href="{url(p)}" class="{"current" if current["slug"]==p["slug"] else ""} {"sub" if p.get("order",0)%1 else ""}" {"aria-current=page" if current["slug"]==p["slug"] else ""}>{e(p.get("navTitle",p["title"]))}</a>' for p in pp)+'</section>'
 return top,side
def template(p):
 body=p['body'].replace('[[notation]]',definitions('page-'))
 body=body.replace('<div data-fourier-visual></div>',fourier_visual())
 body=re.sub(r'<div\s+data-paper-figure=[\"\']([^\"\']+)[\"\']\s*></div>',figure,body)
 for symbol,slug in [('p','p'),('r','r'),('d','d'),('p_f','pf'),('P_0','p0'),('w','w'),('\\kappa','kappa')]:
  if p.get('notationContext')=='probability':
   if symbol=='p':slug='p-prob'
   elif symbol in {'r','d','w','\\kappa'}:continue
  literal='\\('+symbol+'\\)'
  body=body.replace(literal,f'<span class="symbol" data-symbol="{slug}" aria-describedby="def-{slug}">{literal}</span>')
 body=re.sub(r'href="(/lesson/[^"#]+?)(#[^"]*)?"',lambda m:'href="'+m[1].rstrip('/')+'/'+(m[2] or '')+'"',body)
 # Shared circuit styling and scroll wrappers preserve original gate geometry.
 body=re.sub(r'(<table\b[^>]*>.*?</table>)',r'<div class="table-scroll">\1</div>',body,flags=re.S)
 circuit_index=0
 def circuit_scroll(m):
  nonlocal circuit_index
  circuit_index+=1
  svg=m[0];view=re.search(r'viewBox=[\"\']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)',svg)
  scope=f'{p["slug"]}-{circuit_index}'
  svg=svg.replace('<svg',f'<svg data-diagram="{e(scope)}"',1)
  def scoped_style(style):
   css=re.sub(r'([^{}]+)\{([^{}]*)\}',lambda rule:','.join(f'[data-diagram="{scope}"] '+s.strip() for s in rule[1].split(','))+'{'+rule[2]+'}',style[1])
   return '<style>'+css+'</style>'
  svg=re.sub(r'<style>(.*?)</style>',scoped_style,svg,flags=re.S)
  if '<title' not in svg:
   label=re.search(r'aria-label=[\"\']([^\"\']+)[\"\']',svg)
   svg=svg.replace('>','><title>'+e(html.unescape(label[1]) if label else 'Explanatory quantum circuit')+'</title>',1)
  width=0 if 'data-fit="true"' in svg else (max(420,min(1100,float(view[1]))) if view else 650)
  return f'<div class="diagram-scroll" style="--circuit-width:{width:g}px">{svg}</div>'
 body=re.sub(r'<svg\b.*?</svg>',circuit_scroll,body,flags=re.S)
 headers=[];used=set()
 def heading(m):
  attrs,text=m.group(1),m.group(2);idm=re.search(r'\bid=[\"\']([^\"\']+)[\"\']',attrs)
  slug=idm[1] if idm else re.sub('[^a-z0-9]+','-',re.sub('<[^>]+>','',text).lower()).strip('-')
  if not slug:slug='section'
  base=slug;idx=2
  while slug in used:slug=f'{base}-{idx}';idx+=1
  used.add(slug)
  if idm:attrs=attrs[:idm.start()]+f'id="{slug}"'+attrs[idm.end():]
  else:attrs+=f' id="{slug}"'
  headers.append((slug,re.sub('<[^>]+>','',text)))
  return f'<h2{attrs}>{text}</h2>'
 body=re.sub(r'<h2([^>]*)>(.*?)</h2>',heading,body,flags=re.S)
 top,side=nav(p);sources=''
 refs=p.get('refs',[])
 if refs:
  sources='<section class="sources" id="sources"><h2>Sources and dependencies</h2><ol>'+''.join(f'<li><a href="{e(r["url"])}" target="_blank" rel="noopener">{e(r["title"])}</a><div class="role">{e(r.get("role",""))}</div></li>' for r in refs)+'</ol></section>'
 prevnext=''
 if p['slug']!='index':
  i=pages.index(p);prev=pages[i-1] if i>0 else byid['index'];nxt=pages[i+1] if i+1<len(pages) else byid['index']
  prevnext=f'<nav class="pagenav" aria-label="Lesson sequence"><a href="{url(prev)}"><small>Previous lesson</small>{e(prev["title"])}</a><a href="{url(nxt)}"><small>Next lesson</small>{e(nxt["title"])}</a></nav>'
 src=p.get('sourcePages',[])
 srcstr=' · '.join(f'<a href="{SOURCE}#page={n}" target="_blank" rel="noopener">p. {n}</a>' for n in src)
 if len(src)>7:srcstr=f'<a href="{SOURCE}#page={src[0]}" target="_blank" rel="noopener">pp. {src[0]}–{src[-1]}</a>'
 words=prose_words(body)
 reading_tools='<div class="reading-tools"><button id="expand-derivations">Open all details</button><button id="collapse-derivations">Close all details</button></div>' if '<details' in body else ''
 title=p['title']
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><meta name="description" content="{e(p['summary'])}"><meta name="theme-color" content="#101f32"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/vendor/katex/katex.min.css"><link rel="stylesheet" href="/styles.css"><script src="/site.js" defer></script></head><body>
<a class="skip" href="#main">Skip to lesson</a><header class="topbar"><div class="brandline"><a class="brand" href="/">ECDLP · Teaching notes</a><span class="edition">IonQ paper · 3 September 2026</span><button class="utility mobile-button" id="menu-toggle" aria-expanded="false" aria-controls="top-navigation">Parts</button><button class="utility mobile-button" id="chapters-toggle" aria-expanded="false" aria-controls="sidebar">Lessons</button><button class="utility" data-open-notation>Notation</button></div><nav class="topnav" id="top-navigation" aria-label="Paper parts">{top}</nav></header>
<div class="sitegrid"><aside class="sidebar" id="sidebar" aria-label="All lessons"><div class="searchwrap"><label for="lesson-search">Find a lesson</label><input id="lesson-search" type="search" placeholder="Section or technique" autocomplete="off"></div><nav class="lessonsnav"><section class="navgroup"><a href="/" class="{'current' if p['slug']=='index' else ''}">Start here · Result and reading path</a></section>{side}<p id="no-results" class="no-results" hidden>No matching lessons.</p></nav></aside>
<main class="main" id="main"><div class="eyebrow">{e(part(p))}</div><h1>{e(title)}</h1><p class="deck">{e(p['summary'])}</p><div class="sourceline"><span>{max(1,round(words/210))} min core reading</span><span>{srcstr or 'Companion lesson · primary sources below'}</span><a href="/lesson/audit/">Coverage &amp; audit</a></div>{reading_tools}<article class="lesson">{body}{sources}</article>{prevnext}<footer class="footer">Independent teaching notes · <a href="{SOURCE}" target="_blank" rel="noopener">Häner et al., source paper</a> · <a href="/lesson/conclusion/#limitations">Limitations</a> · <a href="/lesson/notation/">Notation</a> · <a href="/lesson/audit/">Source coverage</a></footer></main>
<aside class="toc" aria-label="On this page"><span>On this page</span><nav>{''.join(f'<a href="#{e(s)}">{e(t)}</a>' for s,t in headers)}<a href="#sources">Sources</a></nav></aside></div>
<dialog class="dialog" id="notation-dialog" aria-labelledby="notation-title"><div class="dialoghead"><h2 id="notation-title">Notation and physical meaning</h2><button id="close-notation" aria-label="Close notation">Close</button></div><div class="dialogbody"><p>Definitions are also given where they are used. <a href="/lesson/notation/">Open the full notation page</a>.</p>{definitions()}</div></dialog></body></html>'''

if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
for folder in ['assets','data','vendor']:
 if (ROOT/folder).exists():shutil.copytree(ROOT/folder,OUT/folder)
for file in ['styles.css','site.js','favicon.svg']:shutil.copy2(ROOT/file,OUT/file)
for p in pages:
 dest=OUT/'index.html' if p['slug']=='index' else OUT/'lesson'/p['slug']/'index.html'
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(template(p))
(OUT/'sitemap.json').write_text(json.dumps([{'title':p['title'],'url':url(p),'group':part(p),'sourcePages':p.get('sourcePages',[])} for p in pages],indent=2))
(ROOT/'data/coverage-generated.json').write_text(json.dumps({'pages':len(pages),'figures':figrefs,'sections':[{'slug':p['slug'],'title':p['title'],'sourcePages':p.get('sourcePages',[])} for p in pages]},indent=2))
print(f'Generated {len(pages)} pages, {len(figrefs)} distinct source figure panels.')
subprocess.run(['node',str(ROOT/'render-math.cjs'),str(OUT)],check=True)
