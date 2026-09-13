"""Exact module-level SVG circuit diagrams for the reconstruction report."""
from pathlib import Path
from html import escape

def canvas(title,h=350):
 return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{h}" viewBox="0 0 1000 {h}"><rect width="100%" height="100%" fill="#fff"/><style>text{{font:16px sans-serif;fill:#172a43}}.title{{font-size:22px;font-weight:bold}}.small{{font-size:14px}}line,path{{stroke:#334f70;stroke-width:2;fill:none}}rect.box{{fill:#eaf1fa;stroke:#456b9a;stroke-width:1.5}}</style>',f'<text x="24" y="32" class="title">{escape(title)}</text>']
def text(s,x,y,t,cls=''):s.append(f'<text x="{x}" y="{y}" class="{cls}">{escape(t)}</text>')
def line(s,x,y,X,Y,dash=False):s.append(f'<line x1="{x}" y1="{y}" x2="{X}" y2="{Y}"'+(' stroke-dasharray="5 4"' if dash else '')+'/>')
def box(s,x,y,w,h,t):s.append(f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/>');text(s,x+8,y+h/2+6,t)
def save(s,name):Path('figures',name).write_text(''.join(s)+'</svg>')
def run():
 Path('figures').mkdir(exist_ok=True)
 s=canvas('Carry cleanup with an inclusive truncated comparison',360)
 for y,label in [(90,'u'),(160,'v'),(230,'h = 0')]:text(s,24,y+5,label);line(s,95,y,470 if y==230 else 955,y)
 box(s,125,65,130,190,'Add u into v,h')
 box(s,300,137,130,46,'If h: add c');line(s,365,185,365,230)
 box(s,460,208,94,44,'X measure');line(s,554,230,655,230,True);line(s,655,230,655,193,True)
 box(s,605,62,310,130,'Phase: −(−1)^[u_hi < v_hi]')
 text(s,568,252,'classical outcome m','small');text(s,615,84,'Execute only when m = 1','small')
 text(s,26,292,'Measurement gives (−1)^(m h). Correction uses ĥ = [v_hi ≤ u_hi].')
 text(s,26,321,'Their product is +1 when ĥ = h; tied high windows choose carry = 1.','small')
 save(s,'carry-cleanup.svg')
 s=canvas('Delayed lookup cleanup: measure three times, correct once',420)
 text(s,24,81,'address j');line(s,112,76,970,76)
 for x,y,name in [(150,155,'(x₂, y₂)'),(380,220,'3x₂ + R'),(610,285,'(x₂, y₂)')]:
  line(s,x+45,76,x+45,y);box(s,x,y-22,95,44,'Lookup');text(s,x-72,y+5,'|0⟩');line(s,x-32,y,x,y)
  line(s,x+95,y,x+112,y);box(s,x+112,y-22,106,44,'Use; X-clear');text(s,x+30,y+44,name,'small')
  line(s,x+218,y,888,y,True)
 box(s,830,51,135,50,'Phase (−1)^f(j)');line(s,888,101,888,285,True)
 text(s,25,353,'f(j) = (m₁ ⊕ m₃) · (x₂(j), y₂(j)) ⊕ m₂ · (3x₂(j) + R)','small')
 text(s,25,385,'Rows show successive workspace lifetimes. Dashed lines carry classical measurement masks.','small')
 save(s,'merged-lookup.svg')
if __name__=='__main__':run()
