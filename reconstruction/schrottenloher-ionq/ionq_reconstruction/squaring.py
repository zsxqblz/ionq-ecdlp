"""Report Algorithms 7--11, specialized to the actual uncontrolled square-subtract.

Low carry kappa=65, local padding rho=32, measured phase comparison delta=32.
A phase comparator uses an X-eigenstate target, an exact equivalent of compute /
phase / uncompute. It is an explicit circuit, not a zero-cost classical test.
"""
from qarton.arithmetic import GidneyAdder, GidneyComparator, GidneyConstantAdder, ControlledGidneyConstantAdder
from qarton.circuit import Circuit,InPlaceCircuit,UIntType,UInt,memoize,qc_reg_cast
from .primitives import IntegerSquare,FixedAdder
P=(1<<256)-(1<<32)-977
TERMS=((32,1),(10,1),(6,-1),(4,1),(0,1))
def uint(reg):return qc_reg_cast(reg,UIntType(len(reg)))

@memoize
class PhaseLT(InPlaceCircuit):
    def __init__(self,n):
        super().__init__();self.n=n
        x=self.add_input_output(UIntType(n));y=self.add_input_output(UIntType(n))
        a=self.add_anc(1)
        self.x(a[0]);self.h(a[0])
        self.append(GidneyComparator(n),x,y,a)
        self.h(a[0]);self.x(a[0]);self.assert_anc(a)

@memoize
class AddSlice(InPlaceCircuit):
    def __init__(self,ns,o,w,t,sign=1,kappa=65,rho=32,delta=32):
        super().__init__();n=256;c=(1<<32)+977
        assert t+w==n or t+w+rho<n
        assert sign in (-1,1)
        s=self.add_input_output(UIntType(ns));v=self.add_input_output(UIntType(n))
        a=s[o:o+w]
        def complement_orientation():
            self.append(FixedAdder(kappa,c),uint(v[:kappa]))
            for bit in v:self.x(bit)
        if sign<0:complement_orientation()
        if t+w+rho<n:
            z=self.add_anc(rho)
            self.append(GidneyAdder(w+rho),uint(a+z),uint(v[t:t+w+rho]))
            self.assert_anc(z)
        else:
            pad=self.add_anc(1);h=self.add_anc(1)
            self.append(GidneyAdder(w+1),uint(a+pad),uint(v[t:]+h))
            self.append(FixedAdder(kappa,c,True),h,uint(v[:kappa]))
            m=self.get_classical(1);self.h(h[0]);self.msr(h[0],m[0])
            # Report (-1)^m * PhaseGE = PhaseLT; these include the same global sign.
            self.append_controlled(PhaseLT(delta),uint(v[n-delta:]),uint(a[w-delta:]),controls=[m[0]])
            self.release_classical(m);self.assert_anc(pad,h)
        if sign<0:complement_orientation()

@memoize
class AddBMultiple(InPlaceCircuit):
    def __init__(self,ns,sign=1,kappa=65,rho=32,delta=32):
        super().__init__();s=self.add_input_output(UIntType(ns));v=self.add_input_output(UIntType(256))
        self.append(AddSlice(ns,0,128,128,sign,kappa,rho,delta),s,v)
        for d,e in TERMS:self.append(AddSlice(ns,128,ns-128,d,sign*e,kappa,rho,delta),s,v)

@memoize
class HighCorrection(Circuit):
    """Exact |s>|0> -> |s>|c*sum epsilon*s[n-d:n]> in 65 scratch bits."""
    def __init__(self):
        super().__init__();s=self.add_input_output(UIntType(256))
        h=self.add_anc(33);g=self.get_anc(UIntType(65));self.add_output(g)
        def accumulate_h(reverse=False):
            seq=list(TERMS[:-1]);seq=seq[::-1] if reverse else seq
            for d,e in seq:
                pad=self.add_anc(33-d)
                q=GidneyAdder(33)
                if (e<0)^reverse:q=q.inverse()
                self.append(q,uint(s[256-d:]+pad),uint(h));self.assert_anc(pad)
        accumulate_h()
        for d,e in TERMS:
            width=65-d;pad=self.add_anc(width-33)
            q=GidneyAdder(width)
            if e<0:q=q.inverse()
            self.append(q,uint(h+pad),uint(g[d:]));self.assert_anc(pad)
        accumulate_h(True);self.assert_anc(h)

@memoize
class AddCMultiple(InPlaceCircuit):
    def __init__(self,sign=-1,kappa=65,rho=32,delta=32):
        super().__init__();s=self.add_input_output(UIntType(256));v=self.add_input_output(UIntType(256))
        for d,e in TERMS:self.append(AddSlice(256,0,256-d,d,sign*e,kappa,rho,delta),s,v)
        _,g=self.append(HighCorrection(),s)
        self.append(AddSlice(65,0,65,0,sign,kappa,rho,delta),g,v)
        self.append(HighCorrection().inverse(),s,g)

@memoize
class ModularSquareSubtract(InPlaceCircuit):
    def __init__(self,kappa=65,rho=32,delta=32):
        super().__init__();x=self.add_input_output(UIntType(256));y=self.add_input_output(UIntType(256))
        lo=uint(x[:128]);hi=uint(x[128:])
        _,v=self.append(IntegerSquare(128),lo)
        self.append(AddBMultiple(256,1,kappa,rho,delta),v,y)
        self.append(AddSlice(256,0,256,0,-1,kappa,rho,delta),v,y)
        self.append(IntegerSquare(128).inverse(),lo,v)
        _,v=self.append(IntegerSquare(128),hi)
        self.append(AddBMultiple(256,1,kappa,rho,delta),v,y)
        self.append(AddCMultiple(-1,kappa,rho,delta),v,y)
        self.append(IntegerSquare(128).inverse(),hi,v)
        pad=self.add_anc(1);zero=self.add_anc(1)
        hi2=uint(hi+pad);lo2=uint(lo+zero)
        self.append(GidneyAdder(129),lo2,hi2)
        _,v=self.append(IntegerSquare(129),hi2)
        self.append(AddBMultiple(258,-1,kappa,rho,delta),v,y)
        self.append(IntegerSquare(129).inverse(),hi2,v)
        self.append(GidneyAdder(129).inverse(),lo2,hi2)
        self.assert_anc(pad,zero)
    def dummy_classical_function(self,args):
        x,y=args;return x,UInt((int(y)-int(x)**2)%P)
