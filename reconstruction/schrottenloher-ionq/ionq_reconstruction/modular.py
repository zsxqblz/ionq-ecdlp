"""Approximate signed modular addition, with explicit zero-representation repair.

The report uses a shifted replay representation. Our inverse-GCD replay instead
keeps canonical residues: it needs a post 0<->p swap as well as the pre-swap.
This small, explicitly charged deviation avoids assuming the unpublished layout.
"""
from qarton.arithmetic import GidneyAdder,ControlledGidneyConstantAdder
from qarton.binary_operations import EfficientMCX
from qarton.circuit import Circuit,InPlaceCircuit,BoolType,UIntType,UInt,memoize,qc_reg_cast,qc_reg_from_bits,qc_bool_reg,CZ_GATE,Z_GATE
from .squaring import PhaseLT,uint,P
from .primitives import FixedAdder

@memoize
class ZeroPSwap(InPlaceCircuit):
    """Controlled approximate transposition 0 <-> p (other matched pairs also flip)."""
    def __init__(self,p=P,bits=32):
        super().__init__();n=p.bit_length();assert p&1
        b=self.add_input_output(BoolType());v=self.add_input_output(UIntType(n))
        for i in range(1,n):
            if (p>>i)&1:self.cx(v[0],v[i])
        ctrl=v[n-bits:]
        for t in ctrl:self.x(t)
        self.append(EfficientMCX(bits+1),qc_reg_from_bits(b,ctrl),qc_bool_reg(v[0]))
        for t in ctrl:self.x(t)
        for i in range(1,n):
            if (p>>i)&1:self.cx(v[0],v[i])

@memoize
class SignedModularAdder(InPlaceCircuit):
    def __init__(self,p=P,kappa=65,delta=32,zero_bits=32,repair_zero_target=False,handle_zero=True):
        super().__init__();self.params=(p,kappa,delta,zero_bits);self.handle_zero=handle_zero;self.repair_zero_target=repair_zero_target;n=p.bit_length();c=(1<<n)-p
        b=self.add_input_output(BoolType());u=self.add_input_output(UIntType(n));v=self.add_input_output(UIntType(n))
        if repair_zero_target:zflag=self.add_input_output(BoolType())
        def swap_zero():
            self.x(b[0]);self.append(ZeroPSwap(p,zero_bits),b,v);self.x(b[0])
        if handle_zero:swap_zero()
        for t in v:self.cx(b[0],t)
        pad=self.add_anc(1);h=self.add_anc(1)
        self.append(GidneyAdder(n+1),uint(u+pad),uint(v+h))
        self.append(FixedAdder(kappa,c,True),h,uint(v[:kappa]))
        m=self.get_classical(1);self.h(h[0]);self.msr(h[0],m[0])
        one=self.add_anc(1);self.x(one[0])
        if repair_zero_target:
            # Legacy comparison retained for explicit tests of the old promise repair.
            self.append_controlled(PhaseLT(delta+1),uint(qc_reg_from_bits(b,v[n-delta:])),uint(qc_reg_from_bits(one,u[n-delta:])),controls=[m[0]])
            self.append_basic_gate_controlled(CZ_GATE,b[0],zflag[0],controls=[m[0]])
        else:
            # Choose carry=1 on equal top windows, in both sign branches.
            # (-1)^[v_top <= u_top] = -(-1)^[u_top < v_top].
            # This handles the noncanonical complement of a zero subtraction target
            # without retaining a history of zero-target promises.
            self.append_basic_gate_controlled(Z_GATE,one[0],controls=[m[0]])
            self.append_controlled(PhaseLT(delta),uint(u[n-delta:]),uint(v[n-delta:]),controls=[m[0]])
        self.x(one[0]);self.assert_anc(one,pad,h);self.release_classical(m)
        for t in v:self.cx(b[0],t)
        if handle_zero:swap_zero()
    def define_inverse(self):
        if self.repair_zero_target:
            raise NotImplementedError("Use the explicitly constructed OddReplay division; its zero promises change under inversion.")
        return SignedModularAdderInverse(*self.params,handle_zero=self.handle_zero)
    def dummy_classical_function(self,args):
        b,u,v=args[:3];p=self.params[0];return (b,u,UInt((int(v)+(1-2*int(b))*int(u))%p))+tuple(args[3:])

@memoize
class SignedModularAdderInverse(InPlaceCircuit):
    def __init__(self,p=P,kappa=65,delta=32,zero_bits=32,handle_zero=True):
        super().__init__();self.params=(p,kappa,delta,zero_bits);self.handle_zero=handle_zero;n=p.bit_length()
        b=self.add_input_output(BoolType());u=self.add_input_output(UIntType(n));v=self.add_input_output(UIntType(n))
        self.x(b[0]);self.append(SignedModularAdder(*self.params,handle_zero=self.handle_zero),b,u,v);self.x(b[0])
    def define_inverse(self):return SignedModularAdder(*self.params,handle_zero=self.handle_zero)

@memoize
class ModularNegation(InPlaceCircuit):
    def __init__(self,p=P,kappa=65,zero_bits=32):
        super().__init__();n=p.bit_length();c=(1<<n)-p
        v=self.add_input_output(UIntType(n))
        for t in v:self.x(t)
        self.append(FixedAdder(kappa,c-1).inverse(),uint(v[:kappa]))
        one=self.add_anc(1);self.x(one[0]);self.append(ZeroPSwap(p,zero_bits),one,v);self.x(one[0]);self.assert_anc(one)
    def define_inverse(self):return self
