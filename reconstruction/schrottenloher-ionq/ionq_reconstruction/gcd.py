"""Section VI odd-remainder GCD, using the repository's compressed ternary record.

Explicit reconstruction choices: one extra value bit, one initial parity bit,
and an initial orientation swap. These are charged, not assumed free. Record
pairs remain (a,m) with m implying a, so the original 3-pairs/5-bits compressor
applies unchanged. The value-width schedule is the baseline schedule plus one bit.
"""
from math import ceil,sqrt
from qarton.arithmetic import ControlledGidneyAdder,ControlledGidneyConstantAdder,ControlledGidneyComparator,qc_load_uint
from qarton.binary_operations import qc_cswap,qc_cxor,qc_shift_right,qc_xor
from qarton.circuit import Circuit,UIntType,UInt,BoolType,BitVector,BitVectorType,memoize,qc_reg_cast,qc_reg_from_bits,qc_bool_reg
from point_add.compressor import Absorber,Swapper,compress,uncompress
from .primitives import SignedAdder

@memoize
class OddRecord(Circuit):
    def __init__(self,p,cmp_bits=77):
        super().__init__();self.p=p;self.n=n=p.bit_length();N=n+1
        L=ceil((1.413*n+2.4*sqrt(n))/3)*3;self.nsteps=L
        upad=ceil(2.3*sqrt(n));ng=5*(L//3)
        x=self.add_input(UIntType(n));vx=self.add_anc(1)
        uu=qc_load_uint(UInt(p),self);uz=self.add_anc(1)
        trueu=uu+uz;truev=x+vx
        extra=max(0,ceil(ng/2-N+upad+2))
        ufull=trueu+self.add_anc(extra);vfull=truev+self.add_anc(extra)
        garb=qc_reg_from_bits(list(reversed([b for pair in zip(ufull,vfull) for b in pair])))
        a0=self.add_anc(1);self.cx(x[0],a0[0])
        self.add_output(qc_reg_cast(qc_reg_from_bits(a0,garb[:ng]),BitVectorType(ng+1)))
        self.x(a0[0]);self.append(ControlledGidneyAdder(N),a0,qc_reg_cast(trueu,UIntType(N)),qc_reg_cast(truev,UIntType(N)));self.x(a0[0])
        qc_cswap(qc_bool_reg(a0[0]),trueu,truev)
        for i in range(L):
            w=min(ceil(min(max(ceil(n-i*.5*1.415+upad),0),n)/2)*2,n)+1
            u=trueu[:w];v=truev[:w]
            a=self.get_anc(BoolType());m=self.get_anc(BoolType())
            self.cx(u[1],a[0]);self.cx(v[1],a[0])
            pad=self.get_anc(1);carry=self.get_anc(1)
            self.append(SignedAdder(w+1),a,qc_reg_cast(u+pad,UIntType(w+1)),qc_reg_cast(v+carry,UIntType(w+1)))
            qc_shift_right(v+carry,offset=-1)
            self.assert_anc(pad,carry);self.release_anc(pad);self.release_anc(carry)
            cw=min(cmp_bits,w)
            self.append(ControlledGidneyComparator(cw),a,qc_reg_cast(v[-cw:],UIntType(cw)),qc_reg_cast(u[-cw:],UIntType(cw)),m)
            qc_cswap(m,u,v)
            small=garb[5*(i//3):5*(i//3+1)]
            if i%3==0:qc_xor(compress(BitVector(0,0,0,0,0,0)),small)
            self.append(Absorber(i%3),qc_reg_from_bits(a,m),small)
        self.x(trueu[0]);self.x(truev[0]);self.test_anc(garb[ng:],msg='odd GCD remainder/width failure')
    def validate_input(self,x):return 0<int(x)<self.p

def record_model(x,p):
    n=p.bit_length();L=ceil((1.413*n+2.4*sqrt(n))/3)*3
    a0=x&1;u=p;v=x+(1-a0)*p
    if a0:u,v=v,u
    out=[]
    for i in range(L):
        a=((u>>1)^(v>>1))&1
        v=(v+(1-2*a)*u)//2
        m=int(a and u>v)
        if m:u,v=v,u
        out.append((a,m))
    assert (u,v)==(1,1),(u,v)
    return a0,out

def unpack_record(bv):
    a0=int(bv[0]);pairs=[]
    for i in range((len(bv)-1)//5):
        b=uncompress(bv[1+5*i:1+5*(i+1)])
        pairs.extend((int(b[j]),int(b[j+1])) for j in (0,2,4))
    return a0,pairs

def replay_model(y,p,record):
    a0,pairs=record;r=s=y
    for a,m in reversed(pairs):
        if m:r,s=s,r
        s=(2*s-(1-2*a)*r)%p
    if a0:r,s=s,r
    assert r==0
    return s

from qarton.circuit import InPlaceCircuit
from qarton.binary_operations import qc_swap,AndGate,AndGateUncompute
from qarton.arithmetic import ControlledGidneyAdder,GidneyAdder
from qarton.modular_arithmetic import ModIntType,ModInt
from point_add.special_mod_arithmetic import SpecialPrimeModularDouble
from .modular import SignedModularAdder
from .squaring import uint

@memoize
class OddReplay(InPlaceCircuit):
    """(record,y) -> (record,xy) by replaying inverse integer GCD maps over F_p.

Initial (y,y) becomes (0,xy). Duplicate values are coherent CNOT copies.
The inverse runs the algebraic forward maps and clears the duplicate by CNOT.
"""
    def __init__(self,p,inverse=False):
        super().__init__();self.p=p;self.reverse=inverse;n=p.bit_length()
        L=ceil((1.413*n+2.4*sqrt(n))/3)*3;ng=5*(L//3)
        d=self.add_input_output(BitVectorType(ng+1));y=self.add_input_output(UIntType(n));s=self.get_anc(UIntType(n))
        dbl=SpecialPrimeModularDouble(p,padding=32,backends=frozenset([GidneyAdder,ControlledGidneyAdder]))
        signed=SignedModularAdder(p,handle_zero=False)
        signed_special=SignedModularAdder(p)
        r=y;a=self.add_anc(1);m=self.add_anc(1);pair=qc_reg_from_bits(a,m)
        zero_targets=[];prefixes=[];special_rounds=min(37,L)
        if inverse:
            first=self.add_anc(1);self.x(first[0]);self.cx(d[0],first[0]);prefixes.append(first)
            zero_targets.append(qc_reg_from_bits(d[0]))
            for k in range(special_rounds-1):
                small=d[1+5*(k//3):1+5*(k//3+1)]
                self.append(Swapper(k%3),pair,small)
                nz=self.add_anc(1);np=self.add_anc(1)
                self.append(AndGate(),qc_reg_from_bits(prefixes[-1],m,nz))
                self.x(m[0]);self.append(AndGate(),qc_reg_from_bits(prefixes[-1],m,np));self.x(m[0])
                zero_targets.append(nz);prefixes.append(np)
                self.append(Swapper(k%3),pair,small)
        def dupe():
            for i in range(n):self.cx(r[i],s[i])
        def apply_step(i,reverse):
            small=d[1+5*(i//3):1+5*(i//3+1)]
            self.append(Swapper(i%3),pair,small)
            if not reverse:
                qc_cswap(qc_bool_reg(m[0]),r,s)
                self.append(dbl,qc_reg_cast(s,ModIntType(p)))
                self.x(a[0]);self.append(signed_special if i<special_rounds else signed,a,r,s);self.x(a[0])
            else:
                if i<special_rounds:
                    self.append(SignedModularAdder(p,repair_zero_target=True),a,r,s,zero_targets[i])
                else:self.append(signed,a,r,s)
                self.append(dbl.inverse(),qc_reg_cast(s,ModIntType(p)))
                qc_cswap(qc_bool_reg(m[0]),r,s)
            self.append(Swapper(i%3),pair,small)
        if not inverse:
            dupe()
            for i in reversed(range(L)):apply_step(i,False)
            qc_cswap(qc_bool_reg(d[0]),r,s)
            qc_swap(r,s)
        else:
            qc_swap(r,s)
            qc_cswap(qc_bool_reg(d[0]),r,s)
            for i in range(L):apply_step(i,True)
            dupe()
        if inverse:
            for k in reversed(range(special_rounds-1)):
                small=d[1+5*(k//3):1+5*(k//3+1)]
                self.append(Swapper(k%3),pair,small)
                self.x(m[0]);self.append(AndGateUncompute(),qc_reg_from_bits(prefixes[k],m,prefixes[k+1]));self.x(m[0])
                self.append(AndGateUncompute(),qc_reg_from_bits(prefixes[k],m,zero_targets[k+1]))
                self.append(Swapper(k%3),pair,small)
            self.cx(d[0],prefixes[0][0]);self.x(prefixes[0][0])
            self.assert_anc(*prefixes,*zero_targets[1:])
        self.test_anc(s,a,m,msg='replay zero-register failure')
    def define_inverse(self):return OddReplay(self.p,not self.reverse)

@memoize
class OddIPModMul(InPlaceCircuit):
    def __init__(self,p,inverse=False):
        super().__init__();self.p=p;self.reverse=inverse;n=p.bit_length()
        x=self.add_input_output(ModIntType(p));y=self.add_input_output(ModIntType(p))
        rec=OddRecord(p)
        (d,)=self.append(rec,uint(x))
        self.append(OddReplay(p,inverse),d,uint(y))
        (xx,)=self.append(rec.inverse(),d)
        self.remap(qc_reg_cast(xx,ModIntType(p)),y)
    def define_inverse(self):return OddIPModMul(self.p,not self.reverse)
    def validate_input(self,args):return 0<int(args[0])<self.p
    def dummy_classical_function(self,args):
        x,y=args;return x,y*(x**(-1) if self.reverse else x)
