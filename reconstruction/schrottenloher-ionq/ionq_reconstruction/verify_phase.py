"""Fully decomposed, coherent tests of the phase and zero-representation primitives."""
from qarton.binary_operations import AndGate
AndGate.replace_by_ccx=True
from qarton.circuit import Decompose,QuantumSimulator,UInt,QartonBool
from .squaring import PhaseLT
from .modular import ZeroPSwap
from .verify import check_state,coherent
import json,pathlib,math

def run():
    count=0
    for n in range(1,5):
        q=Decompose(PhaseLT(n))
        for x in range(1<<n):
            for y in range(1<<n):
                a=UInt(x),UInt(y);s=q.simulate_state(a)
                assert set(s)=={a} and abs(s[a]-(-1 if x<y else 1))<1e-8
                count+=1
        inputs=[(UInt(x),UInt(y)) for x,y in [(0,0),(0,1),(1,0),(1,1)]]
        state=QuantumSimulator(q).simulate_state({a:.5 for a in inputs})
        assert all(abs(state[a]-(-.5 if int(a[0])<int(a[1]) else .5))<1e-8 for a in inputs)
        count+=1
    q=Decompose(ZeroPSwap(13,3));pairs=[]
    for b in range(2):
        for v in range(16):
            a=QartonBool(b),UInt(v);w=13-v if b and v in (0,13) else v
            want=QartonBool(b),UInt(w);check_state(q,a,want);count+=1
            if v in (0,13):pairs.append((a,want))
    coherent(q,pairs);count+=1
    pathlib.Path('results/phase-verification.json').write_text(json.dumps({'success':True,'fully_decomposed_cases':count},indent=2)+'\n')
    print('PASS',count,flush=True)
if __name__=='__main__':run()
