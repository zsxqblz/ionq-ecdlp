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
This module defines a compression / decompression circuit.

The compression maps 3 pairs of bits (b0, b0&b1) obtained during the GCD algorithm to
5 bits. The decompression is simply the reverse circuit.

In practice we can use the circuit ``Swapper`` which takes as input 2 bits (b0, b0&b1)
and a compressed bitvector, and swaps these two bits with a given position in the
compressed bitvector (so it uses a compression-decompression).

"""

from frozendict import frozendict
from qarton.circuit import (
    BitVector,
    Circuit,
    CircuitParameterInvalid,
    InvolutoryCircuit,
    dummify,
    memoize,
)

_LIST = [BitVector(1, 0), BitVector(1, 1), BitVector(0, 0)]

_FUNCTION: frozendict[BitVector, BitVector] = frozendict(
    {
        BitVector(0, 0, 0, 0, 0, 0): BitVector(0, 0, 1, 0, 1),
        BitVector(0, 0, 0, 0, 1, 0): BitVector(0, 0, 1, 0, 0),
        BitVector(0, 0, 0, 0, 1, 1): BitVector(0, 0, 1, 1, 1),
        BitVector(0, 0, 1, 0, 0, 0): BitVector(0, 0, 0, 0, 1),
        BitVector(0, 0, 1, 0, 1, 0): BitVector(0, 0, 0, 0, 0),
        BitVector(0, 0, 1, 0, 1, 1): BitVector(0, 0, 0, 1, 1),
        BitVector(0, 0, 1, 1, 0, 0): BitVector(1, 1, 1, 1, 1),
        BitVector(0, 0, 1, 1, 1, 0): BitVector(0, 0, 1, 1, 0),
        BitVector(0, 0, 1, 1, 1, 1): BitVector(1, 1, 1, 0, 1),
        BitVector(1, 0, 0, 0, 0, 0): BitVector(1, 0, 0, 0, 1),
        BitVector(1, 0, 0, 0, 1, 0): BitVector(1, 0, 0, 0, 0),
        BitVector(1, 0, 0, 0, 1, 1): BitVector(1, 0, 0, 1, 1),
        BitVector(1, 0, 1, 0, 0, 0): BitVector(1, 0, 1, 0, 1),
        BitVector(1, 0, 1, 0, 1, 0): BitVector(1, 0, 1, 0, 0),
        BitVector(1, 0, 1, 0, 1, 1): BitVector(1, 0, 1, 1, 1),
        BitVector(1, 0, 1, 1, 0, 0): BitVector(1, 1, 0, 1, 1),
        BitVector(1, 0, 1, 1, 1, 0): BitVector(1, 0, 0, 1, 0),
        BitVector(1, 0, 1, 1, 1, 1): BitVector(1, 1, 0, 0, 1),
        BitVector(1, 1, 0, 0, 0, 0): BitVector(0, 1, 1, 0, 0),
        BitVector(1, 1, 0, 0, 1, 0): BitVector(0, 1, 1, 0, 1),
        BitVector(1, 1, 0, 0, 1, 1): BitVector(0, 1, 1, 1, 0),
        BitVector(1, 1, 1, 0, 0, 0): BitVector(0, 1, 0, 0, 0),
        BitVector(1, 1, 1, 0, 1, 0): BitVector(0, 1, 0, 0, 1),
        BitVector(1, 1, 1, 0, 1, 1): BitVector(0, 1, 0, 1, 0),
        BitVector(1, 1, 1, 1, 0, 0): BitVector(1, 1, 1, 1, 0),
        BitVector(1, 1, 1, 1, 1, 0): BitVector(0, 1, 1, 1, 1),
        BitVector(1, 1, 1, 1, 1, 1): BitVector(1, 1, 1, 0, 0),
    }
)

_FUNCTION_REV: frozendict[BitVector, BitVector] = frozendict(
    {
        BitVector(0, 0, 1, 0, 1): BitVector(0, 0, 0, 0, 0, 0),
        BitVector(0, 0, 1, 0, 0): BitVector(0, 0, 0, 0, 1, 0),
        BitVector(0, 0, 1, 1, 1): BitVector(0, 0, 0, 0, 1, 1),
        BitVector(0, 0, 0, 0, 1): BitVector(0, 0, 1, 0, 0, 0),
        BitVector(0, 0, 0, 0, 0): BitVector(0, 0, 1, 0, 1, 0),
        BitVector(0, 0, 0, 1, 1): BitVector(0, 0, 1, 0, 1, 1),
        BitVector(1, 1, 1, 1, 1): BitVector(0, 0, 1, 1, 0, 0),
        BitVector(0, 0, 1, 1, 0): BitVector(0, 0, 1, 1, 1, 0),
        BitVector(1, 1, 1, 0, 1): BitVector(0, 0, 1, 1, 1, 1),
        BitVector(1, 0, 0, 0, 1): BitVector(1, 0, 0, 0, 0, 0),
        BitVector(1, 0, 0, 0, 0): BitVector(1, 0, 0, 0, 1, 0),
        BitVector(1, 0, 0, 1, 1): BitVector(1, 0, 0, 0, 1, 1),
        BitVector(1, 0, 1, 0, 1): BitVector(1, 0, 1, 0, 0, 0),
        BitVector(1, 0, 1, 0, 0): BitVector(1, 0, 1, 0, 1, 0),
        BitVector(1, 0, 1, 1, 1): BitVector(1, 0, 1, 0, 1, 1),
        BitVector(1, 1, 0, 1, 1): BitVector(1, 0, 1, 1, 0, 0),
        BitVector(1, 0, 0, 1, 0): BitVector(1, 0, 1, 1, 1, 0),
        BitVector(1, 1, 0, 0, 1): BitVector(1, 0, 1, 1, 1, 1),
        BitVector(0, 1, 1, 0, 0): BitVector(1, 1, 0, 0, 0, 0),
        BitVector(0, 1, 1, 0, 1): BitVector(1, 1, 0, 0, 1, 0),
        BitVector(0, 1, 1, 1, 0): BitVector(1, 1, 0, 0, 1, 1),
        BitVector(0, 1, 0, 0, 0): BitVector(1, 1, 1, 0, 0, 0),
        BitVector(0, 1, 0, 0, 1): BitVector(1, 1, 1, 0, 1, 0),
        BitVector(0, 1, 0, 1, 0): BitVector(1, 1, 1, 0, 1, 1),
        BitVector(1, 1, 1, 1, 0): BitVector(1, 1, 1, 1, 0, 0),
        BitVector(0, 1, 1, 1, 1): BitVector(1, 1, 1, 1, 1, 0),
        BitVector(1, 1, 1, 0, 0): BitVector(1, 1, 1, 1, 1, 1),
    }
)


def validate_uncompress(bv: BitVector) -> bool:
    return bv in _FUNCTION_REV


def compress(bv: BitVector) -> BitVector:
    """Compress a 6-bit string of the form (00|10|11)^3 into 5 bits.

    :param bv: Input bit-string (5 bits)
    :type bv: BitVector
    :return: Output bit-string (6 bits)
    :rtype: BitVector
    """
    return _FUNCTION[bv].copy()


def uncompress(bv: BitVector) -> BitVector:
    """Reverse of ``compress``. Map a 5-bit string into a 6-bit string of the form
    (00|10|11)^3.

    :param bv: Input bit-string (5 bits)
    :type bv: BitVector
    :return: Output bit-string (6 bits)
    :rtype: BitVector
    """
    return _FUNCTION_REV[bv].copy()


@dummify
@memoize
class Compressor(Circuit[BitVector, BitVector]):
    """
    This compressor circuit maps a 6-bit string of the form (00|10|11)^3 into 5 bits.
    it is equivalent to the function ``compress``.

    The circuit itself is ad hoc, and was obtained using a SAT-based synthesis method.
    """

    def __init__(self) -> None:
        super().__init__()
        xreg = self.add_input(6)  # BitVector of 6 bits
        self.add_output(xreg[0:5])

        self.cx(xreg[1], xreg[0])
        self.cx(xreg[3], xreg[2])
        self.cx(xreg[5], xreg[4])

        self.cx(xreg[0], xreg[2])
        self.cx(xreg[5], xreg[3])
        self.x(xreg[4])
        self.ccx(xreg[1], xreg[3], xreg[5])
        self.cx(xreg[1], xreg[4])
        self.x(xreg[2])
        self.ccx(xreg[3], xreg[4], xreg[5])
        self.ccx(xreg[4], xreg[5], xreg[1])
        self.ccx(xreg[2], xreg[5], xreg[0])
        self.ccx(xreg[0], xreg[1], xreg[5])

        self.assert_anc(xreg[-1:])

    def validate_input(self, args: BitVector) -> bool:
        return args in _FUNCTION

    def validate_output(self, args: BitVector) -> bool:
        return args in _FUNCTION_REV

    def dummy_classical_function(self, args: BitVector) -> BitVector:
        return compress(args)

    def dummy_classical_function_inverse(self, args: BitVector) -> BitVector:
        return uncompress(args)


@dummify
@memoize
class Swapper(InvolutoryCircuit[tuple[BitVector, BitVector]]):
    """
    This circuit takes two inputs:

    - 2 bits of the form (00|10|11)
    - a compressed bit-string (resulting from compression)

    It swaps the two input bits with those at a certain position (0,1 or 2) in the
    compressed bit-string.
    """

    def __init__(self, i: int) -> None:
        """
        :param i: Position for swapping (0,1 or 2)
        :type i: int
        """
        super().__init__()
        if i not in [0, 1, 2]:
            raise CircuitParameterInvalid(self, i, "Should be 0, 1 or 2")
        self.i = i
        bb = self.add_input_output(2)
        xreg = self.add_input_output(5)
        (decomp_reg,) = self.append(Compressor().inverse(), xreg)
        # uses 1 ancilla qubit
        # swap bb0 and bb1 to positions
        self.swap(bb[0], decomp_reg[2 * i])
        self.swap(bb[1], decomp_reg[2 * i + 1])
        (recomp,) = self.append(Compressor(), decomp_reg)
        self.remap(bb, recomp)

    def validate_input(self, args: tuple[BitVector, BitVector]) -> bool:
        bb, bv = args
        return bb in _LIST and bv in _FUNCTION_REV

    def dummy_classical_function(
        self, args: tuple[BitVector, BitVector]
    ) -> tuple[BitVector, BitVector]:
        bb, bv = args
        decomp = uncompress(bv)
        new_bb = decomp[2 * self.i : (2 * self.i + 2)]
        decomp[2 * self.i] = bb[0]
        decomp[2 * self.i + 1] = bb[1]
        return new_bb, compress(decomp)


@dummify
@memoize
class Absorber(Circuit[tuple[BitVector, BitVector], BitVector]):
    """
    This circuit takes two inputs:

    - 2 bits of the form (00|10|11)
    - a compressed bit-string (resulting from compression)

    It assumes that the two bits at the given position in the compressed bit-string are
    0, and absorbs the two input bits into the compressed bit-string. (This is like
    Swapper, but with an additional assumption).
    """

    def __init__(self, i: int) -> None:
        """
        :param i: Position for swapping (0,1 or 2)
        :type i: int
        """
        super().__init__()
        if i not in [0, 1, 2]:
            raise CircuitParameterInvalid(self, i, "Should be 0, 1 or 2")
        self.i = i
        bb = self.add_input(2)
        xreg = self.add_input_output(5)
        (decomp_reg,) = self.append(Compressor().inverse(), xreg)
        # uses 1 ancilla qubit
        # swap bb0 and bb1 to positions
        self.swap(bb[0], decomp_reg[2 * i])
        self.swap(bb[1], decomp_reg[2 * i + 1])
        (recomp,) = self.append(Compressor(), decomp_reg)
        self.assert_anc(bb)
        self.remap(recomp)

    def validate_input(self, args: tuple[BitVector, BitVector]) -> bool:
        bb, bv = args
        return (
            bb in _LIST
            and bv in _FUNCTION_REV
            and uncompress(bv)[2 * self.i : (2 * self.i + 2)] == BitVector(0, 0)
        )

    def dummy_classical_function_inverse(
        self, args: BitVector
    ) -> tuple[BitVector, BitVector]:
        bv = args
        decomp = uncompress(bv)
        bb = BitVector(decomp[2 * self.i], decomp[2 * self.i + 1])
        decomp[2 * self.i] = 0
        decomp[2 * self.i + 1] = 0
        # output bb and put zeroes instead in the vector
        return bb, compress(decomp)

    def dummy_classical_function(self, args: tuple[BitVector, BitVector]) -> BitVector:
        bb, bv = args
        decomp = uncompress(bv)
        decomp[2 * self.i] = bb[0]
        decomp[2 * self.i + 1] = bb[1]
        return compress(decomp)
