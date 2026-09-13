# --------------------------------------------------------------------------
#
# Copyright (C) 2026
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------

"""
Optimized quantum circuits for GCD and in-place modular multiplication.

The two main ingredients of these circuits come from [KSGZ+25], which applied the
"dialog representation" idea to polynomials.

* Instead of performing an extended Euclidean algorithm (where we need to store both the
  input pair of integers (u,v) and the constructed integers (r,s)), we *first* operate
  on (u,v), and store a log of all the GCD steps which were performed. This is known
  in [KSGZ+25] as a "dialog" representation. In our circuits we use a custom implementation
  that aims at minimizing both space and gate count, and we simply call it a BitVector.
  Then, only in a second step, we can use the BitVector to construct (r,s) by operating
  exactly as if we had computed the EGCD. At this point, we have freed the space occupied
  by (u,v), leading to an overall decreased space.

* Instead of starting from (0,1) like we would do in the EGCD, we can start from (0,y)
  for any y. By linearity, this will directly construct the *product* of the modular
  inverse and y, modulo q (if we perform all computations modulo q). This is exactly
  what we need for the point addition circuit.

The circuits defined in this file make errors. Errors come from:

* Errors in the GCD computation (not the right number of iterations, not the right
  amount of padding)

* Arithmetic errors in the modular arithmetic circuits

The latter are controlled by a few constants:

- TRUNCATE: Amount of truncation used when computing some comparisons
- ITER_CAN_BE_Q: Amount of iterations in which we use the modular addition circuit that
  handles the "x+y = q" case
- PADDING: Amount of padding that we use when performing optimized modular arithmetic

Other constants hard-coded in this module can make the CCX count vary.


References
----------

.. [KSGZ+25] Khattar, T., Shutty, N., Gidney, C., Zalcman, A., Yosri, N., Maslov, D., ... & Jordan, S. P. (2025).
   *Verifiable quantum advantage via optimized DQI circuits*. arXiv preprint arXiv:2510.10967.

"""

from __future__ import annotations

from math import ceil, sqrt
from typing import cast

from qarton.arithmetic import (
    CDKMAdder,
    ControlledCDKMAdder,
    ControlledCDKMComparator,
    ControlledGidneyAdder,
    ControlledGidneyComparator,
    ControlledGidneyConstantAdder,
    ControlledGidneyConstantComparator,
    ControlledHybridAdder,
    GidneyConstantAdder,
    GidneyConstantComparator,
    qc_clt_uint,
    qc_load_uint,
)
from qarton.binary_operations import (
    MCXWithBorrowedBits,
    qc_cswap,
    qc_shift_right,
    qc_swap,
    qc_xor,
)
from qarton.circuit import (
    Bit,
    BitVector,
    BitVectorType,
    BoolType,
    Circuit,
    CircuitParameterInvalid,
    InPlaceCircuit,
    UInt,
    UIntType,
    memoize,
    qc_reg_cast,
    qc_reg_from_bits,
)
from qarton.modular_arithmetic import (
    ModInt,
    ModIntType,
)
from sympy import isprime  # type: ignore

from .compressor import Absorber, Swapper, compress, validate_uncompress
from .efficient_mod_arithmetic import (
    EfficientControlledModularAdder,
    EfficientModularDouble,
)
from .gcd_functions import (
    ITERATIONS_VAR,
    U_PAD_VAR,
    apply_bitvector,
    apply_bitvector_reverse,
    from_bitvector,
    to_bitvector,
)
from .special_mod_arithmetic import (
    SpecialPrimeControlledModularAdder,
    SpecialPrimeHandlePControlledModularAdder,
    SpecialPrimeModularDouble,
)

# --------------------------------------
# Parameters
# --------------------------------------
TRUNCATE = 40
ITER_CAN_BE_Q = 50
# A parameter for the Bézout reconstruction circuit

PADDING = 40

STEP = 2
# A parameter for the ToBitVector circuit. Choosing a larger STEP value makes the
# circuit construction faster, but increases the CCX count a bit, and might increase
# the qubit count a bit. The difference for small values is minor.


# --------------------------------------


# Do not dummify since the circuit is approximate
@memoize
class ToBitVector(Circuit[UInt, BitVector]):
    """
    Convert an integer to a BitVector representation, containing the steps of GCD.

    Sources of errors in this algorithm:

    - the dialog algorithm itself
    - the truncation when comparing integers (depends on the parameter TRUNCATE)
    """

    def __init__(self, p: int, gate_efficient: bool = False) -> None:
        """
        :param p: Input prime
        :type p: int
        """
        super().__init__()
        if not isprime(p):
            raise CircuitParameterInvalid(self, p, "Should be prime")

        # When doing this circuit we have to store at most one additional integer.
        # This means that we have actually more ancillas during thie circuit than during
        # other operations.
        # i.e., we can use aggressive optimizations
        self.add_backend(ControlledGidneyComparator)

        n = p.bit_length()
        self.p = p

        # input registers
        true_v_reg = self.add_input(UIntType(n))
        true_u_reg = qc_load_uint(UInt(p), self)

        # parameters
        expected_iterations = ceil((1.413 * n + ITERATIONS_VAR * sqrt(n)) / 3) * 3
        # nbr of iterations is multiple of 3
        self.nsteps = expected_iterations
        u_padding = ceil(U_PAD_VAR * sqrt(n))

        expected_garbage = ceil(expected_iterations / 3) * 5

        # additional bits for u: expected_garbage//2 - n + u_padding
        #  why +5? because of the rounding later
        u_add = self.add_anc(ceil(expected_garbage / 2 - n + u_padding + STEP))
        v_add = self.add_anc(ceil(expected_garbage / 2 - n + u_padding + STEP))

        u_full = true_u_reg + u_add
        v_full = true_v_reg + v_add
        # enough space for u, v and garbage
        assert len(u_full) + len(v_full) >= expected_garbage + 2 * u_padding

        # all bits we can use as garbage
        garbage_full = qc_reg_from_bits(
            list(
                reversed(
                    sum(
                        [[u_full[i], v_full[i]] for i in range(len(u_full))],
                        cast(list[Bit], []),
                    )
                )
            )
        )

        self.add_output(garbage_full[:expected_garbage])
        other_padding = garbage_full[expected_garbage:]
        assert len(other_padding) >= 2 * u_padding
        # other_padding contains at least the padding of u and v
        u_reg = true_u_reg
        v_reg = true_v_reg

        assert n - expected_iterations * 0.5 * 1.415 + u_padding >= 0

        # This is the amount of ancillas that we can use
        ancilla_budget = n + 5 - len(other_padding)

        for i in range(expected_iterations):
            b0, b0andb1 = self.get_anc(BoolType()), self.get_anc(BoolType())

            current_n = min(max(ceil(n - i * 0.5 * 1.415 + u_padding), 0), n)
            # use a step for current_n to have less circuits to construct
            current_n = min(ceil(current_n / STEP) * STEP, n)

            v_reg = qc_reg_cast(true_v_reg[:current_n], UIntType(current_n))
            u_reg = qc_reg_cast(true_u_reg[:current_n], UIntType(current_n))

            small_garbage_reg = garbage_full[5 * (i // 3) : (5 * (i // 3 + 1))]
            assert not v_reg.positions.to_set().intersects(
                small_garbage_reg.positions.to_set()
            )

            # ----------------------------------
            # compute b0, b1
            self.cx(v_reg[0], b0[0])

            # we approximate the comparator by truncation to the MSBs of u and v
            v_reg_truncated = v_reg[-(TRUNCATE + u_padding) :]
            v_reg_truncated = qc_reg_cast(
                v_reg_truncated, UIntType(len(v_reg_truncated))
            )
            u_reg_truncated = u_reg[-(TRUNCATE + u_padding) :]
            u_reg_truncated = qc_reg_cast(
                u_reg_truncated, UIntType(len(u_reg_truncated))
            )
            qc_clt_uint(b0, v_reg_truncated, u_reg_truncated, b0andb1)
            # ----

            # now use b0 and (b0&b1) to control the operations
            qc_cswap(b0andb1, u_reg, v_reg)

            # Because of the relative sizes
            # of everything when n = 256, using the gidney adder for too large registers
            # will overfill our ancilla budget, and will start to dominate. So we
            # use a hybrid adder which uses all available ancillas.
            if gate_efficient:
                qc: Circuit = ControlledGidneyAdder(current_n)
            else:
                qc = ControlledHybridAdder(current_n, anc=ancilla_budget)

            self.append(qc.inverse(), b0, u_reg, v_reg)

            qc_shift_right(v_reg, offset=-1)

            # consume the garbage
            bb = qc_reg_from_bits(b0, b0andb1)
            if i % 3 == 0:
                # initialize register (which is now 0)
                bv = compress(BitVector(0, 0, 0, 0, 0, 0))
                qc_xor(bv, small_garbage_reg)
            self.append(Absorber(i % 3), bb, small_garbage_reg)

        # now u_reg should be 1 and v_reg should be 0
        self.test_anc(v_reg, msg="v_reg not 0")
        self.x(u_reg[0])
        self.test_anc(u_reg, msg="u_reg not 0")
        self.test_anc(other_padding, msg="other padding not 0")

    def validate_input(self, args: UInt) -> bool:
        v = args
        return v != 0 and v < self.p

    def dummy_classical_function(self, args: UInt) -> BitVector:
        v = args
        return to_bitvector(self.p, v)

    def dummy_classical_function_inverse(self, args: BitVector) -> UInt:
        _, v = from_bitvector(args, self.nsteps)
        return UInt(v)


# Do not dummify since the circuit is approximate
@memoize
class ApplyBitVector(InPlaceCircuit[tuple[BitVector, ModInt, ModInt]]):
    """
    Apply the bitvector representation to a pair of integers, reconstructing the Bézout
    coefficients.

    Source of errors in this algorithm:

    - the non-exact modular arithmetic circuits
    - the parameter ITER_CAN_BE_Q deciding for how many iterations we use the
      special modular adder which handles the case where x+y = q (overflow); otherwise
      we don't use it.

    This circuit dominates the space complexity, so we use space-efficient arithmetic
    circuits. Alternatively, the space complexity will increase by n (size of q) bits.
    """

    def __init__(
        self, p: int, gate_efficient: bool = False, special_prime: bool = True
    ) -> None:
        """
        :param p: Prime number.
        :type p: int
        :param gate_efficient: True if we use the gate-efficient circuit with more space, defaults to False
        :type gate_efficient: bool, optional
        """
        super().__init__()
        n = p.bit_length()

        # Here we need space-efficient backends
        if not gate_efficient:
            self.add_backend(ControlledCDKMAdder)
            self.add_backend(GidneyConstantAdder)
            self.add_backend(ControlledGidneyConstantAdder)
            self.add_backend(GidneyConstantComparator)
            self.add_backend(ControlledGidneyConstantComparator)
            self.add_backend(ControlledCDKMComparator)
            self.add_backend(MCXWithBorrowedBits)
            # space-efficient MCX gate used in the SpecialPrimeHandlePControlledModularAdder
            # circuit (the case when x + y equals p is tested with a small MCX gate)
        else:
            # aggressive backends: will cost +n qubits of space
            self.add_backend(ControlledGidneyComparator)
            self.add_backend(ControlledGidneyAdder)

        expected_iterations = ceil((1.413 * n + ITERATIONS_VAR * sqrt(n)) / 3) * 3
        self.nsteps = expected_iterations
        expected_garbage = ceil(expected_iterations / 3) * 5

        self.p = p  # type: ignore
        self.n = n

        d_reg = self.add_input_output(BitVectorType(expected_garbage))

        x_reg_mod = self.add_input_output(ModIntType(p))
        y_reg_mod = self.add_input_output(ModIntType(p))

        # with padding = 40 we shouldn't see any errors here
        if not special_prime:
            # case of a generic prime. In the gate_efficient case, there is a tiny
            # backend issue where the controlled addition by a constant must
            # be performed using a CDKM adder (space-efficient), otherwise we overflow
            # our ancilla budget. This is the only place where the CDKM adder will
            # be used.
            _backends = frozenset(set(self.backends) | {CDKMAdder})
            cadd: Circuit = EfficientControlledModularAdder(
                self.p,
                padding=PADDING,
                backends=_backends,
            )
            cadd2: Circuit = cadd
            dbl: Circuit = EfficientModularDouble(
                self.p,
                padding=PADDING,
                backends=_backends,
            )

        else:
            dbl = SpecialPrimeModularDouble(
                self.p, padding=PADDING, backends=self.backends
            )
            cadd = SpecialPrimeHandlePControlledModularAdder(
                self.p, padding=PADDING, backends=self.backends
            )
            cadd2 = SpecialPrimeControlledModularAdder(
                self.p, padding=PADDING, backends=self.backends
            )

        b0, b0andb1 = self.add_anc(BoolType()), self.add_anc(BoolType())

        # we need to read the garbage bits backwards
        for i in reversed(range(expected_iterations)):
            # Swapper
            small_garbage_reg = d_reg[5 * (i // 3) : (5 * (i // 3 + 1))]
            bb = qc_reg_from_bits(b0, b0andb1)

            # load in bb
            self.append(Swapper(i % 3), bb, small_garbage_reg)

            # operate controlled on b0 and b0andb1
            self.append(dbl, y_reg_mod)

            if i < ITER_CAN_BE_Q:
                # the initial numbers may remain in the problematic case for a while.
                self.append(cadd, b0, x_reg_mod, y_reg_mod)
            else:
                # very optimized version (but not for the last steps,
                # where we may be close to the prime)
                self.append(cadd2, b0, x_reg_mod, y_reg_mod)
            qc_cswap(b0andb1, x_reg_mod, y_reg_mod)

            # unload
            self.append(Swapper(i % 3), bb, small_garbage_reg)
            self.test_anc(b0, b0andb1, msg="b0 / b0andb1 not 0")

    def validate_input(self, args: tuple[BitVector, ModInt, ModInt]) -> bool:
        bv, _, _ = args
        for i in range(self.nsteps // 3):
            small = bv[5 * i : (5 * (i + 1))]
            if not validate_uncompress(small):
                return False
        return True

    def dummy_classical_function(
        self, args: tuple[BitVector, ModInt, ModInt]
    ) -> tuple[BitVector, ModInt, ModInt]:
        d, x, y = args
        xx, yy = apply_bitvector(int(x), int(y), d, self.p, nsteps=self.nsteps)
        return d, ModInt(xx, self.p), ModInt(yy, self.p)

    def dummy_classical_function_inverse(
        self, args: tuple[BitVector, ModInt, ModInt]
    ) -> tuple[BitVector, ModInt, ModInt]:
        d, x, y = args
        xx, yy = apply_bitvector_reverse(int(x), int(y), d, self.p, nsteps=self.nsteps)
        return d, ModInt(xx, self.p), ModInt(yy, self.p)


@memoize
class IPModMul(InPlaceCircuit[tuple[ModInt, ModInt]]):
    """
    Performs in-place modular multiplication using the "dialog" strategy: computation
    of the GCD, then reconstruction, then erasure of the BitVector representation.

    """

    def __init__(
        self, p: int, gate_efficient: bool = False, special_prime: bool = True
    ) -> None:
        """
        :param p: Prime number.
        :type p: int
        :param gate_efficient: True if we use the gate-efficient circuit with more space, defaults to False
        :type gate_efficient: bool, optional
        """
        if not isprime(p):
            raise CircuitParameterInvalid(self, p, "Should be prime")
        super().__init__()

        self.p = p
        x_reg = self.add_input_output(ModIntType(p))
        y_reg = self.add_input_output(ModIntType(p))

        # first step: convert x_reg to dialog
        x_reg_uint = qc_reg_cast(x_reg, UIntType(p.bit_length()))
        (d_reg,) = self.append(
            ToBitVector(p, gate_efficient=gate_efficient), x_reg_uint
        )

        # then apply_dialog on (y,0) and obtain xx, yy where xx = 0 and yy = x*y mod p
        tmp_reg = self.get_anc(ModIntType(p))
        self.append(
            ApplyBitVector(
                p, gate_efficient=gate_efficient, special_prime=special_prime
            ),
            d_reg,
            y_reg,
            tmp_reg,
        )

        # now y_reg, tmp_reg contains 0, x*y mod p
        qc_swap(tmp_reg, y_reg)
        self.test_anc(tmp_reg, msg="tmp_reg not 0!")
        self.release_anc(tmp_reg)

        # finally uncompute the dialog
        (x_reg_uint,) = self.append(
            ToBitVector(p, gate_efficient=gate_efficient).inverse(), d_reg
        )
        # x_reg also restored
        x_reg = qc_reg_cast(x_reg_uint, ModIntType(p))
        self.remap(x_reg, y_reg)

    def dummy_classical_function(
        self, args: tuple[ModInt, ModInt]
    ) -> tuple[ModInt, ModInt]:
        x, y = args
        return x, y * x

    def dummy_classical_function_inverse(
        self, args: tuple[ModInt, ModInt]
    ) -> tuple[ModInt, ModInt]:
        x, y = args
        return x, y * (x ** (-1))
