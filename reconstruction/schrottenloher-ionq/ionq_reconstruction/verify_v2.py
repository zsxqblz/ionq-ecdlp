"""Targeted verification of changed replay and actual delayed lookup measurements."""
import json,random,pathlib,time
from .verify import check_state,coherent
from .gcd import OddIPModMul
from .point_add import IonQPointAdd
from .lookup import DelayedLookupIdentity
from .modular import SignedModularAdder
from .squaring import P
from qarton.circuit import UInt,QartonBool
from qarton.modular_arithmetic import ModInt
from qarton.elliptic_curve import EC,AffPointType

def run():
    random.seed(923591);rng=random.Random(2609122);out={'seed':2609122,'measurement_seed':923591,'groups':{}}
    def group(name,fn):
        t=time.time();n=fn();out['groups'][name]={'passed':n,'seconds':round(time.time()-t,3)}
        pathlib.Path('results/v2-verification.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS',name,n,flush=True)
    def lookup():
        k=0
        for trial in range(20):
            xy=tuple(UInt(rng.randrange(256)) for _ in range(8));mid=tuple(UInt(rng.randrange(16)) for _ in range(8))
            q=DelayedLookupIdentity(xy,mid,4,decomposed=True)
            for j in range(8):check_state(q,UInt(j),UInt(j));k+=1
            for _ in range(4):coherent(q,[(UInt(j),UInt(j)) for j in range(8)]);k+=1
        return k
    group('fully_decomposed_delayed_lookup_measurements',lookup)
    def signed():
        q=SignedModularAdder();k=0
        for _ in range(2000):
            b=rng.randrange(2);u=rng.randrange(1,P);v=rng.randrange(1,P)
            a=QartonBool(b),UInt(u),UInt(v);check_state(q,a,(a[0],a[1],UInt((v+(1-2*b)*u)%P)));k+=1
        for _ in range(100):
            u=rng.randrange(1,P)
            for b in (0,1):
                a=QartonBool(b),UInt(u),UInt(0);check_state(q,a,(a[0],a[1],UInt(((1-2*b)*u)%P)));k+=1
        return k
    group('signed_addition_and_unflagged_zero_targets',signed)
    for inv in (False,True):
        def product(inv=inv):
            q=OddIPModMul(P,inv);pairs=[]
            for _ in range(24):
                x=rng.randrange(1,P);y=rng.randrange(1,P);a=ModInt(x,P),ModInt(y,P)
                w=a[0],ModInt(y*(pow(x,-1,P) if inv else x)%P,P)
                check_state(q,a,w)
                if len(pairs)<4:pairs.append((a,w))
            coherent(q,pairs);return 25
        group('division_without_promise_flags' if inv else 'multiplication_inclusive_carry',product)
    def point():
        ec=EC(P,0,7);G=AffPointType(ec).random_value();tab=tuple(G*i for i in range(7,15));pairs=[]
        q=IonQPointAdd(tab,ec,rng.randrange(1<<255,P),merged_lookup=True)
        for j in range(8):
            a=UInt(j),G*rng.randrange(20,1<<250);w=a[0],a[1]+tab[j]
            assert q.validate_input(a);check_state(q,a,w)
            if len(pairs)<4:pairs.append((a,w))
        coherent(q,pairs);return 9
    group('complete_point_with_delayed_lookup',point)
    out['success']=True;pathlib.Path('results/v2-verification.json').write_text(json.dumps(out,indent=2)+'\n');print('DONE',flush=True)
if __name__=='__main__':run()
