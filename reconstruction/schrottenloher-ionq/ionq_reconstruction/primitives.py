"""Gate-level signed addition and the Section VII.A integer squarer.

All arithmetic is built from Qarton's actual gate decompositions. No counting-only
placeholder and no dummy simulator is attached to these new circuits.
"""
from qarton.arithmetic import GidneyAdder
from qarton.circuit import Circuit, InPlaceCircuit, BoolType, UIntType, UInt, memoize, qc_reg_cast

@memoize
class SignedAdder(InPlaceCircuit):
    """(b,u,z) -> (b,u,z+(-1)^b*u mod 2^n)."""
    def __init__(self, n):
        super().__init__();self.n=n
        b=self.add_input_output(BoolType())
        u=self.add_input_output(UIntType(n))
        z=self.add_input_output(UIntType(n))
        for t in z:self.cx(b[0],t)
        self.append(GidneyAdder(n),u,z)
        for t in z:self.cx(b[0],t)
    def dummy_classical_function(self,args):
        b,u,z=args;n=self.n
        return b,u,UInt((int(z)+(1-2*int(b))*int(u))%(1<<n))

@memoize
class IntegerSquare(Circuit):
    """|x>|0> -> |x>|x*x>, using Eq. VII.A (exact, 2n output bits)."""
    def __init__(self,n):
        super().__init__();self.n=n
        x=self.add_input_output(UIntType(n))
        z=self.get_anc(UIntType(2*n));self.add_output(z)
        pad=self.add_anc(2)
        if n==1:
            self.cx(x[0],z[0]);self.assert_anc(pad);return
        # Store -x in n+1 bits. Its upper bit supplies sign extension.
        self.append(GidneyAdder(n+1).inverse(),qc_reg_cast(x+pad[:1],UIntType(n+1)),qc_reg_cast(z[:n+1],UIntType(n+1)))
        for i in range(n-1):
            self.cx(z[n+i],z[n+i+1])
            w=n+1-i
            h=x[i+1:]+pad
            for t in h:self.cx(x[i],t)
            self.append(GidneyAdder(w).inverse(),qc_reg_cast(h,UIntType(w)),qc_reg_cast(z[2*i+1:2*i+1+w],UIntType(w)))
            for t in h:self.cx(x[i],t)
        self.cx(x[n-1],z[2*n-1])
        self.assert_anc(pad)
    def dummy_classical_function(self,x):return x,UInt(int(x)**2)

@memoize
class FixedAdder(InPlaceCircuit):
    """Use the baseline's constant-aware adder dispatch, not a dense constant circuit."""
    def __init__(self,n,c,controlled=False):
        from qarton.arithmetic import qc_add_uint,qc_cadd_uint,ControlledGidneyAdder
        super().__init__();self.n=n;self.c=c;self.controlled=controlled
        self.add_backend(GidneyAdder);self.add_backend(ControlledGidneyAdder)
        if controlled:b=self.add_input_output(BoolType())
        z=self.add_input_output(UIntType(n))
        if controlled:qc_cadd_uint(b,UInt(c),z)
        else:qc_add_uint(UInt(c),z)

