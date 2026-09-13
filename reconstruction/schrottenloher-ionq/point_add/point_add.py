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
(Windowed) elliptic curve point addition circuit.

The circuit follows exactly the three-lookup architecture of [GRLGS23]. It uses
a few modular arithmetic operations, two in-place modular multiplications, and
a modular squaring. The modular squaring is also optimized for primes of the form
2^u - f.

References
----------

.. [GRLGS23] Gouzien, É., Ruiz, D., Le Régent, F. M., Guillaud, J., & Sangouard, N. (2023). Performance
   analysis of a repetition cat code architecture: Computing 256-bit elliptic curve logarithm
   in 9 hours with 126 133 cat qubits. Physical review letters, 131(4), 040602.

"""

from math import ceil, log2

from qarton.arithmetic import (
    CDKMAdder,
    CDKMComparator,
    ControlledCDKMAdder,
    ControlledCDKMComparator,
    ControlledGidneyConstantAdder,
    ControlledGidneyConstantComparator,
    GidneyConstantAdder,
    GidneyConstantComparator,
)
from qarton.binary_operations import MCXWithBorrowedBits, qc_cxor, qc_mcx
from qarton.circuit import (
    BoolType,
    Circuit,
    CircuitParameterInvalid,
    InPlaceCircuit,
    Register,
    UInt,
    UIntType,
    memoize,
    qc_bool_reg,
)
from qarton.data_structures import OOPTableLookup, OOPTableLookupInverse
from qarton.elliptic_curve import EC, AffPoint, AffPointType
from qarton.modular_arithmetic import (
    ModInt,
    ModIntType,
    qc_add_modint,
    qc_cneg_modint,
    qc_sub_modint,
)

from .efficient_mod_arithmetic import ControlledEfficientModularSquareAdd
from .gcd import IPModMul
from .special_mod_arithmetic import ControlledSpecialPrimeModularSquareAdd

# -------------------------------
# Parameters
# -------------------------------

PADDING2 = 50


# do not dummify since we want to run the actual sub-circuits
@memoize
class WindowAffAddSpaceOpt(InPlaceCircuit[tuple[UInt, AffPoint]]):
    """
    (Windowed) elliptic curve point addition, in affine coordinates.

    The window is a parameter of the circuit. The circuit is then an in-place
    addition by a constant, selected in the window depending on a control register.

    If there are 2 points in the window, there is a simple control. If there are
    more, we use a lookup table circuit, whose uncomputation uses conditional operations,
    so it's a little more complicated.
    """

    def pt_lookup_fwd(self, creg: Register) -> Register:
        if len(self.window) == 2:
            p_reg = self.get_anc(AffPointType(self.ec))
            # 0 is the point at infinity
            qc_cxor(qc_bool_reg(creg[0]), self.window[1], p_reg)
        else:
            _, p_reg = self.append(
                OOPTableLookup(self.window, datatype=AffPointType(self.ec)), creg
            )
        return p_reg

    def pt_lookup_bwd(self, creg: Register, p_reg: Register) -> None:
        if len(self.window) == 2:
            qc_cxor(qc_bool_reg(creg[0]), self.window[1], p_reg)
            self.assert_anc(p_reg)
            self.release_anc(p_reg)
        else:
            self.append(
                OOPTableLookupInverse(
                    self.window, datatype=AffPointType(self.ec), l=None
                ),
                creg,
                p_reg,
            )

    def x31_lookup_fwd(self, creg: Register) -> Register:
        if len(self.window) == 2:
            x31 = self.get_anc(ModIntType(self.ec.q))
            qc_cxor(qc_bool_reg(creg[0]), self.x3window[1], x31)
        else:
            _, x31 = self.append(
                OOPTableLookup(self.x3window, datatype=ModIntType(self.ec.q)), creg
            )
        return x31

    def x31_lookup_bwd(self, creg: Register, x31: Register) -> None:
        if len(self.window) == 2:
            qc_cxor(qc_bool_reg(creg[0]), self.x3window[1], x31)
            self.assert_anc(x31)
            self.release_anc(x31)
        else:
            self.append(
                OOPTableLookupInverse(
                    self.x3window, datatype=ModIntType(self.ec.q), l=None
                ),
                creg,
                x31,
            )

    def __init__(
        self,
        window: tuple[AffPoint, ...],
        ec: EC,
        gate_efficient: bool = False,
        special_prime: bool = True,
        backends: frozenset[type[Circuit]] = frozenset(),
    ) -> None:
        """
        :param window: Window of points.
        :type window: tuple[AffPoint, ...]
        :param ec: Elliptic curve.
        :type ec: EC
        :param gate_efficient: If True, does a time-space trade-off using a little
                 more space, and a little less gates, defaults to False
        :type gate_efficient: bool, optional
        """
        super().__init__()

        self.window = window
        # point 0 in the window needs to be 0
        assert not window[0].not_infty
        for pp in window[1:]:
            if not pp.not_infty:
                raise CircuitParameterInvalid(
                    self, pp, "First point in the window must be the point at infinity"
                )

        self.x3window = tuple(ModInt((3 * pp.x) % ec.q, ec.q) for pp in window)

        self.xwindow = tuple(ModInt(pp.x, ec.q) for pp in window)
        self.ywindow = tuple(ModInt(pp.y, ec.q) for pp in window)

        nb_controls = ceil(log2(len(window)))
        creg = self.add_input_output(UIntType(nb_controls))

        # Default set of backends to use for modular arithmetic operations
        good_backends: frozenset[type[Circuit]] = frozenset(
            {
                GidneyConstantAdder,
                ControlledGidneyConstantAdder,
                GidneyConstantComparator,
                ControlledGidneyConstantComparator,
                CDKMComparator,
                ControlledCDKMComparator,
                ControlledCDKMAdder,
                CDKMAdder,
                MCXWithBorrowedBits,
            }
        )
        for _b in good_backends:
            self.add_backend(_b)

        self.ec = ec
        qq = self.add_input_output(AffPointType(ec))
        x2, y2 = qq.a["x"], qq.a["y"]

        # Formulas to follow:
        # lambda = (y1-y2) / (x1 - x2) = (y1 + y3)/(x1-x3)
        # x3 = lambda^2 - x1 - x2
        # y3 = lambda(x1-x3) - y1

        # --- first lookup: the full point
        p_reg = self.pt_lookup_fwd(creg)
        x1, y1 = p_reg.a["x"], p_reg.a["y"]

        # -x2, -y2
        # when infty, this does nothing
        qc_sub_modint(x1, x2)
        qc_sub_modint(y1, y2)

        # Unlookup the full point
        self.pt_lookup_bwd(creg, p_reg)
        # this also destroys x1,y1

        # x2-x1, y2-y1

        # in-place modular division: do y2 * x2^(-1)
        self.append(
            IPModMul(
                ec.q, gate_efficient=gate_efficient, special_prime=special_prime
            ).inverse(),
            x2,
            y2,
        )

        # --- second lookup: only 3*x1

        x31 = self.x31_lookup_fwd(creg)
        # x2-x1, lambda
        # when infty, this does nothing
        qc_add_modint(x31, x2)
        # x2 + 2x1, lambda
        self.x31_lookup_bwd(creg, x31)

        # --- end of second lookup

        # x2 + 2x1, lambda
        # we can be extremely aggressive in the backends of this function.
        if not special_prime:
            _qc: Circuit = ControlledEfficientModularSquareAdd(
                ec.q, padding=PADDING2
            ).inverse()
        else:
            _qc = ControlledSpecialPrimeModularSquareAdd(
                ec.q, padding=PADDING2
            ).inverse()

        # ---- first operation controlled on creg != 0
        creg_is_not_0 = self.get_anc(BoolType())
        qc_mcx(creg, creg_is_not_0, negate=True)
        self.x(creg_is_not_0[0])

        self.append(_qc, creg_is_not_0, y2, x2)
        # qc_sqrsub_modint(y2, x2)  # multiplication
        # x2 + 2x1 - lambda^2, lambda = -x3 + x1, lambda

        qc_mcx(creg, creg_is_not_0, negate=True)
        self.x(creg_is_not_0[0])
        self.release_anc(creg_is_not_0)  # release anc: we gain 1 qubit

        self.append(
            IPModMul(ec.q, gate_efficient=gate_efficient, special_prime=special_prime),
            x2,
            y2,
        )

        # --- second operation controlled on creg != 0
        creg_is_not_0 = self.get_anc(BoolType())
        qc_mcx(creg, creg_is_not_0, negate=True)
        self.x(creg_is_not_0[0])

        # x3 - x1, -lambda(x1-x3)
        qc_cneg_modint(creg_is_not_0, x2)
        # x3-x1, lambda(x1-x3)

        qc_mcx(creg, creg_is_not_0, negate=True)
        self.x(creg_is_not_0[0])
        self.assert_anc(creg_is_not_0)

        # --- third lookup: the full point
        p_reg = self.pt_lookup_fwd(creg)
        x1, y1 = p_reg.a["x"], p_reg.a["y"]

        # -----
        # x3-x1, lambda(x1-x3)
        # when infty, this does nothing
        qc_sub_modint(y1, y2)
        qc_add_modint(x1, x2)
        # x3, y3

        # Unlookup the full point
        self.pt_lookup_bwd(creg, p_reg)

    def validate_input(self, args: tuple[UInt, AffPoint]) -> bool:
        """
        Input invalid in the following cases:

        * the infinity point
        * the point P itself
        * the negation of P
        """
        i, qq = args
        pp = self.window[i]
        return bool(qq.not_infty) and qq != -pp and qq != pp

    def dummy_classical_function(
        self, args: tuple[UInt, AffPoint]
    ) -> tuple[UInt, AffPoint]:
        i, qq = args
        return i, qq + self.window[i]
