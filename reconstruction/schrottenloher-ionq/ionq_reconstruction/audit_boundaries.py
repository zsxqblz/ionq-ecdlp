"""Deterministic value/phase diagnosis of deliberately adversarial signed adds."""
import json,random,pathlib
from .squaring import P
from .modular import SignedModularAdder
from .verify import QartonBool,UInt

def model(b,u,v,bits=32,kappa=65,delta=32):
    n=256;N=1<<n;c=N-P;events=[]
    def zs(v,site):
        folded=v^((P^1) if v&1 else 0)
        hit=(folded>>(n-bits))==0
        if hit and v not in (0,P):events.append(site+': false-positive zero/p swap')
        return v^P if hit else v
    if not b:v=zs(v,'pre')
    if b:v=N-1-v
    h,z=divmod(v+u,N);lo=(z&((1<<kappa)-1))+h*c
    if lo>>kappa:events.append('constant-correction carry escaped truncated window')
    z=(z>>kappa<<kappa)|(lo&((1<<kappa)-1))
    pred=int((z>>(n-delta))<=(u>>(n-delta)))
    if h!=pred:events.append('carry phase predicate disagrees')
    if z>=P:events.append('noncanonical reduced intermediate')
    if b:z=N-1-z
    if not b:z=zs(z,'post')
    return z,h^pred,events

def run():
    random.seed(733129);q=SignedModularAdder();rows=[]
    for u,v in [(0,0),(1,0),(0,1),(1,1),(P-1,1),(1,P-1),(P-1,P-1)]:
        for b in (0,1):
            value,phase_bad,events=model(b,u,v);signs=set()
            for _ in range(64):
                state=q.simulate_state((QartonBool(b),UInt(u),UInt(v)))
                assert len(state)==1
                (got,amp),=state.items();assert int(got[2])==value
                assert abs(abs(amp)-1)<1e-8
                signs.add(1 if amp.real>0 else -1)
            assert signs==({-1,1} if phase_bad else {1})
            rows.append({'b':b,'u':hex(u),'v':hex(v),'output':hex(value),'wanted':hex((v+(1-2*b)*u)%P),'wrong_value':value!=(v+(1-2*b)*u)%P,'phase_error_if_measurement_one':bool(phase_bad),'events':events,'observed_signs':sorted(signs)})
    out={'success':True,'basis_trajectories':14*64,'cases':rows,'meaning':'Success means the independent diagnosis matches the circuit; it does not mean these adversarial arithmetic inputs are all correct.'}
    pathlib.Path('results/boundary-audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print('PASS boundary model agrees with 896 circuit trajectories; value failures',sum(r['wrong_value'] for r in rows),'phase-sensitive cases',sum(r['phase_error_if_measurement_one'] for r in rows))
if __name__=='__main__':run()
