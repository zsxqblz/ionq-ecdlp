"""Deterministic verification; new circuits are never replaced by dummy functions.

Known Qarton exact arithmetic primitives retain the baseline's fast simulator
in large tests. Small exact tests additionally use fully decomposed circuits.
All state checks include amplitudes/phases and Qarton's workspace assertions.
"""
import argparse,json,random,time,math,pathlib
from qarton.binary_operations import AndGate
AndGate.replace_by_ccx=True
from qarton.circuit import UInt,QartonBool,QuantumSimulator,Decompose
from qarton.modular_arithmetic import ModInt
from qarton.elliptic_curve import EC,AffPointType
from .primitives import IntegerSquare,SignedAdder
from .squaring import P,ModularSquareSubtract
from .modular import SignedModularAdder
from .gcd import OddIPModMul,record_model,replay_model
from .point_add import IonQPointAdd

def check_state(q,args,want):
    state=q.simulate_state(args)
    assert set(state)=={want},('value',state,want)
    assert abs(state[want]-1)<1e-8,('phase',state,want)

def coherent(q,pairs):
    inp={a:1/math.sqrt(len(pairs)) for a,_ in pairs}
    expected={b:1/math.sqrt(len(pairs)) for _,b in pairs}
    assert len(inp)==len(pairs) and len(expected)==len(pairs)
    state=QuantumSimulator(q).simulate_state(inp)
    assert set(state)==set(expected),('coherent support',state,expected)
    assert all(abs(state[k]-v)<1e-8 for k,v in expected.items()),('coherent phase',state,expected)

def run(quick=False):
    rng=random.Random(20260912);random.seed(923578)
    result={'seed_inputs':20260912,'seed_measurements':923578,'groups':{},'failures':[],'limitations':[
      'Large tests expand every new algorithm module but use the existing exact-arithmetic dummy implementations.',
      'Small tests separately decompose exact primitives into gates.',
      'Random tests do not reproduce IonQ million-sample confidence bound or hardware compilation.',
      'Zero/small-residue adversarial cases can fail in truncated arithmetic and are recorded separately.'
    ]}
    def group(name,func):
        start=time.time()
        try:n=func();result['groups'][name]={'passed':n,'seconds':round(time.time()-start,3)};print('PASS',name,n,flush=True)
        except Exception as e:
            result['failures'].append({'group':name,'error':repr(e)});print('FAIL',name,repr(e),flush=True)
        pathlib.Path('results/verification.json').write_text(json.dumps(result,indent=2)+'\n')
    def small_squares():
        count=0
        for n in range(1,9):
            q=IntegerSquare(n)
            for x in range(1<<n):check_state(q,UInt(x),(UInt(x),UInt(x*x)));count+=1
        return count
    group('exhaustive_integer_squares_1_to_8_bits',small_squares)
    def decomposed():
        count=0
        for n in range(2,5):
            q=Decompose(IntegerSquare(n))
            for x in range(1<<n):check_state(q,UInt(x),(UInt(x),UInt(x*x)));count+=1
        for n in range(1,5):
            q=Decompose(SignedAdder(n))
            for b in [0,1]:
                for u in range(1<<n):
                    for v in range(1<<n):
                        a=QartonBool(b),UInt(u),UInt(v);w=(v+(1-2*b)*u)%(1<<n)
                        check_state(q,a,(a[0],a[1],UInt(w)));count+=1
        coherent(Decompose(IntegerSquare(4)),[(UInt(x),(UInt(x),UInt(x*x))) for x in [0,3,9,15]])
        return count+1
    group('fully_decomposed_exact_primitives',decomposed)
    def model():
        count=0
        for i in range(1000 if quick else 10000):
            x=rng.randrange(1,P);y=rng.randrange(1,P)
            try:r=record_model(x,P)
            except AssertionError:
                result.setdefault('statistical_iteration_failures',[]).append(hex(x));continue
            assert replay_model(y,P,r)==x*y%P;count+=1
        return count
    group('independent_modular_product_reference',model)
    def signed():
        q=SignedModularAdder();count=0;pairs=[]
        for i in range(100 if quick else 1000):
            b=rng.randrange(2);u=rng.randrange(1,P);v=rng.randrange(1,P)
            args=QartonBool(b),UInt(u),UInt(v);want=args[0],args[1],UInt((v+(1-2*b)*u)%P)
            check_state(q,args,want);count+=1
            if len(pairs)<4:pairs.append((args,want))
        coherent(q,pairs);count+=1
        # Promised zero-target flag used in the first 37 division steps.
        q=SignedModularAdder(repair_zero_target=True)
        for i in range(20):
            u=rng.randrange(1,P)
            for b in [0,1]:
                args=QartonBool(b),UInt(u),UInt(0),QartonBool(1)
                want=args[0],args[1],UInt(((1-2*b)*u)%P),args[3]
                check_state(q,args,want);count+=1
        return count
    group('signed_modular_addition_256_bits',signed)
    def squares():
        q=ModularSquareSubtract();pairs=[];count=0
        for i in range(10 if quick else 200):
            x=rng.randrange(P);y=rng.randrange(P);a=UInt(x),UInt(y);b=UInt(x),UInt((y-x*x)%P)
            check_state(q,a,b);count+=1
            if len(pairs)<4:pairs.append((a,b))
        coherent(q,pairs);return count+1
    group('modular_square_256_bits',squares)
    for inverse in [False,True]:
        def products(inverse=inverse):
            q=OddIPModMul(P,inverse);pairs=[];count=0
            for i in range(5 if quick else 100):
                x=rng.randrange(1,P);y=rng.randrange(1,P);a=ModInt(x,P),ModInt(y,P)
                want=a[0],ModInt(y*(pow(x,-1,P) if inverse else x)%P,P)
                check_state(q,a,want);count+=1
                if len(pairs)<2:pairs.append((a,want))
            coherent(q,pairs);return count+1
        group('division_256_bits' if inverse else 'multiplication_256_bits',products)
    def points():
        ec=EC(P,0,7);G=AffPointType(ec).random_value();table=tuple(G*k for k in range(7,15));mask=rng.randrange(1<<255,P)
        q=IonQPointAdd(table,ec,mask);count=0;pairs=[]
        for i in range(4 if quick else 32):
            j=UInt(i%8);A=G*rng.randrange(20,1<<255);a=j,A;b=j,A+table[int(j)]
            assert q.validate_input(a)
            check_state(q,a,b);count+=1
            if len(pairs)<2:pairs.append((a,b))
        coherent(q,pairs);return count+1
    group('point_addition_with_coherent_lookup',points)
    def baseline():
        from build_circuit import construct_circuit
        q=construct_circuit(0,gate_efficient=True);ec=q.ec
        for i in range(2 if quick else 10):
            A=AffPointType(ec).random_value();a=UInt(1),A
            assert q.validate_input(a);check_state(q,a,q.dummy_classical_function(a))
        return 2 if quick else 10
    group('original_repository_point_addition_control',baseline)
    q=SignedModularAdder();adversarial=[]
    for u,v in [(0,0),(1,0),(0,1),(1,1),(P-1,1),(1,P-1),(P-1,P-1)]:
        for b in [0,1]:
            a=QartonBool(b),UInt(u),UInt(v);want=a[0],a[1],UInt((v+(1-2*b)*u)%P)
            try:check_state(q,a,want)
            except Exception as e:adversarial.append({'b':b,'u':hex(u),'v':hex(v),'error':repr(e)})
    result['adversarial_truncation_failures']=adversarial
    result['success']=not result['failures']
    pathlib.Path('results/verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print('DONE',result['success'],'adversarial failures',len(adversarial),flush=True)
    if result['failures']:raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--quick',action='store_true');run(p.parse_args().quick)
