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
Non-exact modular arithmetic circuits which work for a generic prime.
"""

from __future__ import annotations

from qarton.arithmetic import (
    ControlledGidneyAdder,
    ControlledGidneyComparator,
    GidneyAdder,
    GidneyComparator,
    qc_cadd_uint,
    qc_clt_uint,
    qc_csub_uint,
    qc_lt_uint,
)
from qarton.binary_operations import qc_shift_right
from qarton.circuit import (
    BoolType,
    Circuit,
    CircuitParameterInvalid,
    InPlaceCircuit,
    QartonBool,
    UInt,
    UIntType,
    memoize,
    qc_reg_cast,
)
from qarton.modular_arithmetic import ModInt, ModIntType

__all__ = [
    "EfficientControlledModularAdder",
    "EfficientModularDouble",
    "ControlledEfficientModularSquareAdd",
]


@memoize
class EfficientControlledModularAdder(
    InPlaceCircuit[tuple[QartonBool, ModInt, ModInt]]
):
    """
    Non-exact controlled modular adder.
    """

    def __init__(
        self,
        p: int,
        padding: int = 50,
        backends: frozenset[type[Circuit]] = frozenset(),
    ) -> None:
        """
        :param p: Modulus.
        """
        super().__init__()
        bit_size = p.bit_length()
        if p.bit_count() == 1:
            raise CircuitParameterInvalid(self, p, "Should not be a power of 2")

        self.p = UInt(p)
        p_high_bits = UInt(p >> (bit_size - padding))
        control = self.add_input_output(BoolType())

        x_reg = self.add_input_output(ModIntType(p))
        y_reg = self.add_input_output(ModIntType(p))

        anc_x = self.add_anc(1)
        anc_y = self.add_anc(1)

        qc_cadd_uint(
            control,
            qc_reg_cast(x_reg + anc_x, datatype=UIntType(bit_size + 1)),
            qc_reg_cast(y_reg + anc_y, datatype=UIntType(bit_size + 1)),
        )

        self.assert_anc(anc_x)
        self.release_anc(anc_x)

        anc = self.get_anc(1)

        # we're checking if y_reg >= p
        qc_lt_uint(
            qc_reg_cast(y_reg[-padding:] + anc_y, datatype=UIntType(padding + 1)),
            p_high_bits,
            anc,
        )
        self.x(anc[0])

        qc_csub_uint(
            anc, self.p, qc_reg_cast(y_reg + anc_y, datatype=UIntType(bit_size + 1))
        )
        # y is not bigger than p, and anc_y is 0
        self.test_anc(anc_y)
        self.assert_anc(anc_y)
        self.release_anc(anc_y)
        # self.print(y_reg)

        # self.print(x_reg, msg="yo")

        # self.print(x_reg, y_reg, msg="test")
        # anc <=> there is a subtraction of p
        # there was a subtraction of p iff y < x in the result
        # qc_clt_uint(control, y_reg, x_reg, anc)
        qc_clt_uint(
            control,
            qc_reg_cast(y_reg[-padding:], datatype=UIntType(padding)),
            qc_reg_cast(x_reg[-padding:], datatype=UIntType(padding)),
            anc,
        )

        # self.print(anc_y, anc)
        self.assert_anc(anc)

    def dummy_classical_function(
        self, args: tuple[QartonBool, ModInt, ModInt]
    ) -> tuple[QartonBool, ModInt, ModInt]:
        c, x, y = args
        return (c, x, x + y if c else y)

    def dummy_classical_function_inverse(
        self, args: tuple[QartonBool, ModInt, ModInt]
    ) -> tuple[QartonBool, ModInt, ModInt]:
        c, x, y = args
        return (c, x, y - x if c else y)


@memoize
class EfficientModularDouble(InPlaceCircuit[ModInt]):
    def __init__(
        self,
        p: int,
        padding: int = 50,
        backends: frozenset[type[Circuit]] = frozenset(),
    ) -> None:
        """
        :param p: Modulus.
        """
        super().__init__()
        if p % 2 == 0:
            raise CircuitParameterInvalid(self, p, "must be odd")
        bit_size = p.bit_length()
        self.p = UInt(p)
        p_high_bits = UInt(p >> (bit_size - padding))

        x_reg = self.add_input_output(ModIntType(p))
        anc1 = self.add_anc(1)
        anc2 = self.add_anc(1)

        # shift
        qc_shift_right(x_reg + anc1, 1)

        qc_lt_uint(
            qc_reg_cast(x_reg[-padding:] + anc1, datatype=UIntType(padding + 1)),
            p_high_bits,
            anc2,
        )
        self.x(anc2[0])

        qc_csub_uint(
            anc2, self.p, qc_reg_cast(x_reg + anc1, datatype=UIntType(bit_size + 1))
        )

        # erase anc2 with first bit of x_reg (it's 1 iff there was a reduction)
        self.cx(x_reg[0], anc2[0])
        self.assert_anc(anc1, anc2)

    def dummy_classical_function(self, args: ModInt) -> ModInt:
        return ModInt((2 * args.v) % self.p, self.p)

    def dummy_classical_function_inverse(self, args: ModInt) -> ModInt:
        return ModInt((pow(2, -1, self.p) * args.v) % self.p, self.p)


# Do not dummify since the circuit is approximate
@memoize
class ControlledEfficientModularSquareAdd(
    InPlaceCircuit[tuple[QartonBool, ModInt, ModInt]]
):
    """
    Circuit that squares a number and adds it to another, modulo p, controlled.
    """

    def __init__(
        self,
        p: int,
        padding: int = 30,
        backends: frozenset[type[Circuit]] = frozenset(),
    ) -> None:
        super().__init__()

        # we reset the backends. At the time of calling, we have a lots of ancilla
        # qubits available, so we can be very aggressive in terms of backends
        self._backends = frozenset(
            {
                GidneyComparator,
                ControlledGidneyComparator,
                ControlledGidneyAdder,
                GidneyAdder,
            }
        )

        creg = self.add_input_output(BoolType())

        bit_size = p.bit_length()
        self.p = p
        y_reg = self.add_input_output(ModIntType(p))
        output_reg = self.add_input_output(ModIntType(p))
        c = self.get_anc(BoolType())

        dbl = EfficientModularDouble(p, padding, backends=self.backends)
        cadd = EfficientControlledModularAdder(p, padding, backends=self.backends)

        for _ in range(bit_size - 1):
            self.append(dbl.inverse(), output_reg)

        for i in range(bit_size):
            # add y in output, controlled by its own bit number n-i
            self.ccx(creg[0], y_reg[bit_size - 1 - i], c[0])
            self.append(cadd, c, y_reg, output_reg)
            self.ccx(creg[0], y_reg[bit_size - 1 - i], c[0])

            # double output_reg
            if i < bit_size - 1:
                self.append(dbl, output_reg)
        self.assert_anc(c)

    def dummy_classical_function(
        self, args: tuple[QartonBool, ModInt, ModInt]
    ) -> tuple[QartonBool, ModInt, ModInt]:
        c, y, z = args
        return (c, y, z + y * y if c else z)

    def dummy_classical_function_inverse(
        self, args: tuple[QartonBool, ModInt, ModInt]
    ) -> tuple[QartonBool, ModInt, ModInt]:
        c, y, z = args
        return (c, y, z - y * y if c else z)
