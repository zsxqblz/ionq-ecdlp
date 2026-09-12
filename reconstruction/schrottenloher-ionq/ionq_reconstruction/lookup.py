"""Delayed X-clear with one merged lookup-phase correction (report Algorithm 6).

The masks are classical measurement results. The address and data remain quantum.
No new circuit in this file has a dummy simulation implementation.
"""
from math import ceil,log2,sqrt
from qarton.circuit import Circuit,InPlaceCircuit,UIntType,UInt,BitVectorType,BoolType,TupleType,QartonBool,memoize,qc_hadamard_measure,Decompose
from qarton.data_structures import OOPTableLookup
from qarton.data_structures.select_swap_table_lookup import SelectSwapFwd

@memoize
class MergedLookupPhaseFix(Circuit):
    def __init__(self,xy,middle,n=256,lam=None,decomposed=False):
        super().__init__();assert len(xy)==len(middle)
        lam=max(2,1 << round(log2(sqrt(len(xy)/2)))) if lam is None else lam
        j=self.add_input_output(UIntType(ceil(log2(len(xy)))))
        masks=[self.add_input_output(BitVectorType(w),classical=True) for w in (2*n,n,2*n)]
        def phase_table(m1,m2,m3):
            def integer(b):return sum(int(t)<<i for i,t in enumerate(b))
            a=integer(m1)^integer(m3);b=integer(m2)
            return tuple(QartonBool(((a&int(t)).bit_count()+(b&int(s)).bit_count())%2) for t,s in zip(xy,middle))
        def f(*m):
            q=SelectSwapFwd(phase_table(*m),BoolType(),l=lam)
            return Decompose(q) if decomposed else q
        def inv(*m):
            q=SelectSwapFwd(phase_table(*m),BoolType(),l=lam).inverse()
            return Decompose(q) if decomposed else q
        tmp=self.get_anc(BoolType());anc=self.get_anc(TupleType(lam,BoolType()))
        self.append_conditioned(f,j,tmp,anc,controls=masks)
        self.z(tmp[0])
        self.append_conditioned(inv,j,tmp,anc,controls=masks)
        self.assert_anc(tmp,anc)

@memoize
class DelayedLookupIdentity(InPlaceCircuit):
    """Load and X-clear three times, then correct once; identity on all addresses."""
    def __init__(self,xy,middle,n,decomposed=False):
        super().__init__();j=self.add_input_output(UIntType(ceil(log2(len(xy)))));m=[]
        for t,w in [(xy,2*n),(middle,n),(xy,2*n)]:
            load=OOPTableLookup(t,UIntType(w))
            _,v=self.append(Decompose(load) if decomposed else load,j)
            m.append(qc_hadamard_measure(v))
        self.append(MergedLookupPhaseFix(xy,middle,n,decomposed=decomposed),j,*m)
        for b in m:self.release_classical(b)
