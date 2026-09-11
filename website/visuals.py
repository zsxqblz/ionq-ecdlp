"""Exact, deterministic teaching diagrams. No experimental samples are inferred."""
import html

def fourier_grid(kind,d=3,c=2):
    horizontal,vertical=('k','l') if kind=='input' else ('u','v')
    points=[(x,y) for y in range(7) for x in range(7)
            if ((x+d*y-c)%7==0 if kind=='input' else (y-d*x)%7==0)]
    desc='Highlighted pairs: '+', '.join(f'({x},{y})' for x,y in points)+'. Each has probability 1/7.'
    svg=f'<svg data-fourier-grid="{kind}" data-fit="true" viewBox="0 0 300 295" role="img" aria-label="{horizontal},{vertical} grid modulo seven"><title>{horizontal},{vertical} grid modulo seven</title><desc>{desc}</desc>'
    svg+='<g stroke="#dfe7f0" stroke-width="1">'
    for i in range(7):
        a=44+33*i
        svg+=f'<path d="M44 {a}H242 M{a} 44V242"/>'
    svg+='</g><g fill="#64788e" font-size="12" text-anchor="middle">'
    for i in range(7):
        svg+=f'<text x="{44+33*i}" y="263">{i}</text><text x="25" y="{246-33*i}">{i}</text>'
    svg+=f'<text x="143" y="286">{horizontal}</text><text x="14" y="145">{vertical}</text></g><g>'
    for y in range(7):
        for x in range(7):
            active=(x,y) in points
            svg+=f'<circle data-x="{x}" data-y="{y}" cx="{44+33*x}" cy="{242-33*y}" r="{7 if active else 3}" class="{"fourier-hit" if active else "fourier-empty"}"/>'
    return svg+'</g></svg>'

def fourier_visual():
    return r'''<section class="fourier-visual" aria-labelledby="fourier-visual-title">
<h3 id="fourier-visual-title">Move the coset; the Fourier line stays put</h3>
<p class="section-purpose"><strong>Purpose.</strong> Show that the measured output point changes the input line, but not the Fourier probabilities used to recover the key.</p>
<p>This exact-order toy model uses \(r=7\), with seven states per register. Solid circles mark outcomes of probability \(1/7\); small dots have probability zero. It illustrates the group identity, before binary-register broadening.</p>
<p>Condition on the target containing the point \([c]P\): its compatible inputs obey \(k+dl=c\pmod7\). The target stores point coordinates, not the scalar c. This is a way to analyze the state, not required postselection: any target outcome works, and leaving it unmeasured gives the same Fourier probabilities.</p>
<div class="visual-controls">
<label for="fourier-d">Secret scalar \(d\): <output id="fourier-d-value" for="fourier-d">3</output><input type="range" id="fourier-d" min="0" max="6" step="1" value="3"></label>
<label for="fourier-c">Output point \([c]P\): <output id="fourier-c-value" for="fourier-c">2</output><input type="range" id="fourier-c" min="0" max="6" step="1" value="2"></label>
</div><div class="mechanism-grid">
<div class="visual-step"><strong>Input labels with one point output</strong>\[k+dl=c\pmod7\]'''+fourier_grid('input')+r'''</div>
<div class="visual-step"><strong>Frequencies that survive interference</strong>\[v=du\pmod7\]'''+fourier_grid('frequency')+r'''</div></div>
<p class="visual-feedback" aria-live="polite" id="fourier-feedback">For d = 3, changing c moves the input coset but leaves the Fourier probabilities unchanged.</p>
<div class="equation-note">\[\frac1{\sqrt7}\sum_l|c-dl,l\rangle\xrightarrow{F_7^\dagger\otimes F_7^\dagger}\frac1{\sqrt7}\sum_u e^{-2\pi iuc/7}|u,du\rangle.\]</div>
<p>The point label appears only in phase. The secret determines the surviving line: any measured \(u\ne0\) gives \(d=vu^{-1}\pmod7\).</p>
</section>'''
