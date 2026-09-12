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
This module defines optimized modular arithmetic circuits used in this package.

The circuits are optimized for primes of the form: 2^u - f where f  is small, i.e.,
pseudo-Mersenne primes.

"""

from __future__ import annotations

from qarton.arithmetic import (
    ControlledGidneyAdder,
    ControlledGidneyComparator,
    GidneyAdder,
    GidneyComparator,
    qc_cadd_uint,
    qc_clt_uint,
)
from qarton.binary_operations import qc_cxor, qc_mcx, qc_shift_right
from qarton.circuit import (
    BoolType,
    Circuit,
    InPlaceCircuit,
    QartonBool,
    UInt,
    UIntType,
    memoize,
    qc_reg_cast,
)
from qarton.modular_arithmetic import ModInt, ModIntType


# Do not dummify sinve the circuit is approximate
@memoize
class SpecialPrimeModularDouble(InPlaceCircuit[ModInt]):
    """
    In-place modular double for a pseudo-Mersenne prime.
    """

    def __init__(
        self,
        p: int,
        padding: int = 30,
        backends: frozenset[type[Circuit]] = frozenset(),
    ) -> None:
        """
        :param p: Modulus
        :type p: int
        :param padding: Amount of padding used when adding f, defaults to 30. When adding
             f, we suppose that the carry does not propagate more than 'padding' positions;
             the probability that this is correct is roughly 2^{-padding}.
        :type padding: int, optional
        """
        super().__init__()
        p_bit_length = p.bit_length()
        f = (1 << p_bit_length) - p  # is positive
        assert f > 0
        f_bit_length = f.bit_length()

        self.p = UInt(p)

        x_reg = self.add_input_output(ModIntType(p))
        anc1 = self.add_anc(1)

        # shift
        qc_shift_right(x_reg + anc1, 1)

        lsbs = padding + f_bit_length

        qc_cadd_uint(anc1, UInt(f), qc_reg_cast(x_reg[:lsbs], datatype=UIntType(lsbs)))

        self.cx(x_reg[0], anc1[0])
        self.assert_anc(anc1)

    def dummy_classical_function(self, args: ModInt) -> ModInt:
        return ModInt((2 * args.v) % self.p, self.p)

    def dummy_classical_function_inverse(self, args: ModInt) -> ModInt:
        return ModInt((pow(2, -1, self.p) * args.v) % self.p, self.p)


# Do not dummify since the circuit is approximate
@memoize
class SpecialPrimeHandlePControlledModularAdder(
    InPlaceCircuit[tuple[QartonBool, ModInt, ModInt]]
):
    """
    In-place modular addition for a pseudo-Mersenne prime, handling the case where
    x + y = p.
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
        p_bit_length = p.bit_length()
        f = (1 << p_bit_length) - p  # is positive
        assert f > 0
        f_bit_length = f.bit_length()

        bit_size = p.bit_length()

        self.p = UInt(p)
        # p_high_bits = UInt(p >> (bit_size - msbs))
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
        self.release_anc(anc_x)

        anc = self.get_anc(BoolType())

        # --- all of this handles the case y == p
        # approximate that y >= p iff anc_y = 1 OR msbs of y are 1
        # (this hanles the case of the prime)
        y_is_p = self.get_anc(BoolType())

        qc_mcx(y_reg[-padding:], y_is_p, negate=False)  # all must be 1

        # if y == p then the reduction simply consists in writing p in the number
        # we can erase later by checking if all high bits are 0
        qc_cxor(y_is_p, UInt(p), qc_reg_cast(y_reg, datatype=UIntType(bit_size)))

        # This handles the case y != p and y > p, in which case anc_y is 1
        self.cx(anc_y[0], anc[0])
        # in this case we have the standard method
        lsbs = padding + f_bit_length
        # approximate, approximate!
        qc_cadd_uint(anc, UInt(f), qc_reg_cast(y_reg[:lsbs], datatype=UIntType(lsbs)))
        self.cx(anc[0], anc_y[0])

        self.test_anc(anc_y, msg="anc_y not released")
        self.release_anc(anc_y)

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

        # correct the case of y == p (in which we also XOR 1 to anc above)
        # then anc is
        self.cx(y_is_p[0], anc[0])
        qc_mcx(y_reg[-padding:], y_is_p, negate=True)  # all must be 0 for this case
        self.test_anc(y_is_p, msg="y_is_p not released")
        self.release_anc(y_is_p)

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


# Do not dummify since the circuit is approximate
@memoize
class SpecialPrimeControlledModularAdder(
    InPlaceCircuit[tuple[QartonBool, ModInt, ModInt]]
):
    """
    In-place controlled modular addition for a pseudo-Mersenne prime, not handling the case where
    x + y = p.
    """

    def __init__(
        self,
        p: int,
        padding: int = 30,
        backends: frozenset[type[Circuit]] = frozenset(),
    ) -> None:
        """
        :param p: Modulus.
        """
        super().__init__()
        p_bit_length = p.bit_length()
        f = (1 << p_bit_length) - p  # is positive
        assert f > 0
        f_bit_length = f.bit_length()

        bit_size = p.bit_length()

        self.p = UInt(p)
        control = self.add_input_output(BoolType())

        x_reg = self.add_input_output(ModIntType(p))
        y_reg = self.add_input_output(ModIntType(p))

        anc_x = self.add_anc(1)
        anc_y = self.add_anc(1)

        # self.print(x_reg, y_reg)

        # add
        qc_cadd_uint(
            control,
            qc_reg_cast(x_reg + anc_x, datatype=UIntType(bit_size + 1)),
            qc_reg_cast(y_reg + anc_y, datatype=UIntType(bit_size + 1)),
        )
        self.assert_anc(anc_x)
        self.release_anc(anc_x)

        lsbs = f_bit_length + padding
        qc_cadd_uint(anc_y, UInt(f), qc_reg_cast(y_reg[:lsbs], datatype=UIntType(lsbs)))

        qc_clt_uint(
            control,
            qc_reg_cast(y_reg[-padding:], datatype=UIntType(padding)),
            qc_reg_cast(x_reg[-padding:], datatype=UIntType(padding)),
            anc_y,
        )
        self.test_anc(anc_y)

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


# Do not dummify since the circuit is approximate
@memoize
class ControlledSpecialPrimeModularSquareAdd(
    InPlaceCircuit[tuple[QartonBool, ModInt, ModInt]]
):
    """
    Circuit that squares a number and adds it to another, modulo p, for a pseudo-Mersenne
    prime. Controlled.
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

        dbl = SpecialPrimeModularDouble(p, padding, backends=self.backends)
        cadd = SpecialPrimeControlledModularAdder(p, padding, backends=self.backends)

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
