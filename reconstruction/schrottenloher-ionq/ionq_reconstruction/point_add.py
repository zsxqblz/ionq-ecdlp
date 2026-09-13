"""The report's affine schedule, built on the original repository and Qarton LUTs.

Three table loads; baseline's measurement-based unlookups; shifted tables exclude
infinity. The middle table incorporates a fresh classical mask R. This is the
logical arithmetic circuit, not IonQ's trapped-ion routing or Clifford-frame ISA.
"""
from qarton.circuit import InPlaceCircuit,UIntType,UInt,memoize,qc_reg_cast,qc_hadamard_measure
from qarton.arithmetic import qc_load_uint
from qarton.binary_operations import qc_xor
from qarton.data_structures import OOPTableLookup,OOPTableLookupInverse
from qarton.elliptic_curve import AffPointType
from qarton.modular_arithmetic import ModIntType,ModInt
from .lookup import MergedLookupPhaseFix
from .gcd import OddIPModMul
from .squaring import ModularSquareSubtract,AddSlice,uint,P
from .modular import ModularNegation
from math import ceil,log2

@memoize
class IonQPointAdd(InPlaceCircuit):
    def __init__(self,window,ec,mask=0,merged_lookup=False):
        super().__init__();assert ec.q==P;assert all(p.not_infty for p in window)
        self.window=window;self.ec=ec;self.mask=mask
        j=self.add_input_output(UIntType(ceil(log2(len(window)))))
        A=self.add_input_output(AffPointType(ec));x=A.a['x'];y=A.a['y']
        def load(table,typ):
            _,reg=self.append(OOPTableLookup(table,datatype=typ),j)
            return reg
        def unload(table,typ,reg):
            self.append(OOPTableLookupInverse(table,datatype=typ,l=None),j,reg)
        def add(src,dst,sign):self.append(AddSlice(256,0,256,0,sign),uint(src),uint(dst))
        if merged_lookup:
            xy=tuple(UInt(p.x+(p.y<<256)) for p in window)
            middle=tuple(UInt((3*p.x+mask)%P) for p in window)
            T=load(xy,UIntType(512));add(uint(T[:256]),x,-1);add(uint(T[256:]),y,-1)
            m1=qc_hadamard_measure(T)
            self.append(OddIPModMul(P,True),x,y)
            M=load(middle,UIntType(256));add(M,x,1);m2=qc_hadamard_measure(M)
            self.append(ModularSquareSubtract(),uint(y),uint(x))
            if mask:
                R=self.get_anc(UIntType(256));qc_xor(UInt(mask),R);add(R,x,-1)
                qc_xor(UInt(mask),R);self.assert_anc(R);self.release_anc(R)
            self.append(OddIPModMul(P),x,y)
            T=load(xy,UIntType(512));add(uint(T[256:]),y,-1);add(uint(T[:256]),x,-1)
            self.append(ModularNegation(),uint(x));m3=qc_hadamard_measure(T)
            self.append(MergedLookupPhaseFix(xy,middle),j,m1,m2,m3)
            for m in [m1,m2,m3]:self.release_classical(m)
            return
        typ=AffPointType(ec)
        T=load(window,typ);add(T.a['x'],x,-1);add(T.a['y'],y,-1);unload(window,typ,T)
        self.append(OddIPModMul(P,True),x,y)
        middle=tuple(ModInt((3*p.x+mask)%P,P) for p in window)
        M=load(middle,ModIntType(P));add(M,x,1);unload(middle,ModIntType(P),M)
        self.append(ModularSquareSubtract(),uint(y),uint(x))
        if mask:
            R=self.get_anc(UIntType(256));qc_xor(UInt(mask),R)
            add(R,x,-1)
            qc_xor(UInt(mask),R);self.assert_anc(R);self.release_anc(R)
        self.append(OddIPModMul(P),x,y)
        T=load(window,typ);add(T.a['y'],y,-1);add(T.a['x'],x,-1);unload(window,typ,T)
        self.append(ModularNegation(),uint(x))
    def validate_input(self,args):
        j,A=args;T=self.window[int(j)]
        return A.not_infty and A!=T and A!=-T and A!=-(T*2)
    def dummy_classical_function(self,args):
        j,A=args;return j,A+self.window[int(j)]
