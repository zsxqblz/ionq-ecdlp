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
This module defines the functions that we use for GCD computations. These functions
correspond to the implemented circuits:

- Euclidean algorithm (``to_bitvector``)
- Bézout reconstruction (``apply_bitvector``)

We also define some parameters on which the failure probability depends:

- ITERATIONS_VAR is a constant parameter that determines the variance in the number of
  iterations for the GCD computation
- U_PAD_VAR is a constant parameter that determines the amount of padding in the registers
  for u, v.

These parameters intervene only in the ``to_bitvector`` function.

"""

from math import ceil, log2, sqrt

from qarton.circuit import BitVector

from .compressor import (
    compress,
    uncompress,
)

# This is for very high success probability (1 fail out of 10 000 or 20 000)
ITERATIONS_VAR = 2.4
U_PAD_VAR = 2.3

def to_bitvector(u: int, v: int) -> BitVector:
    """Converts the pair (u,v) to a BitVector, which contains the information of the
    GCD steps. This is a kind of "dialog" representation, even though the representation
    itself is quite ad-hoc.

    The number of iterations is determined using the ITERATIONS_VAR variable. Then, the
    computation is done, and we use assertions to determine if it runs correctly:

    - if the computation is not finished after the iterations (v != 0 or u != 1) we fail
    - if the bit-length of u or v exceeds its theoretical amount (taking into account
      the U_PADDING amount) we fail.

    The idea is that, if the computation succeeds, then the quantum circuit should succeed as
    well (unless other errors occur in the arithmetic steps). We did observe cases in
    which there was no assertion failure here, but the computation still failed. Why this
    happened remains a mystery.

    :param u: Input integer.
    :type u: int
    :param v: Input integer.
    :type v: int
    :return: A BitVector representing the GCD steps.
    :rtype: BitVector
    """

    assert u % 2 == 1

    n = max(u.bit_length(), v.bit_length())
    # -----
    expected_iterations = ceil((1.413 * n + ITERATIONS_VAR * sqrt(n)) / 3) * 3

    u_padding = ceil(U_PAD_VAR * sqrt(n))
    expected_garbage = ceil(expected_iterations // 3) * 5

    garbage = BitVector.from_int(0, expected_garbage)
    for i in range(expected_iterations // 3):
        garbage[5 * i : 5 * (i + 1)] = compress(BitVector(0, 0, 0, 0, 0, 0))

    # otherwise this would be weird
    assert n - expected_iterations * 0.5 * 1.415 + u_padding >= 0

    # iterations = 0
    for i in range(expected_iterations):
        b0 = v % 2
        b1 = u > v

        # add b0 and b1 to the garbage
        garbage_small = garbage[(i // 3) * 5 : (i // 3 + 1) * 5]
        decomp = uncompress(garbage_small)
        assert decomp[2 * (i % 3)] == 0
        assert decomp[2 * (i % 3) + 1] == 0
        decomp[2 * (i % 3)] = b0
        decomp[2 * (i % 3) + 1] = b0 & b1
        garbage[(i // 3) * 5 : (i // 3 + 1) * 5] = compress(decomp)

        assert u.bit_length() < max(n - i * 0.5 * (3 - log2(3)) + u_padding, 0)
        assert v.bit_length() < max(n - i * 0.5 * (3 - log2(3)) + u_padding, 0)

        if b0 & b1:
            # v % 2 == 1 and u > v
            u, v = v, u
        if b0:
            # v % 2 == 1
            v -= u
        v >>= 1

    # Assertions will be false if the algorithm has not finished.
    assert v == 0
    assert u == 1
    return garbage


def from_bitvector(d: BitVector, nsteps: int) -> tuple[int, int]:
    """This is the reverse of ``to_bitvector``, which reconstructs
    the two integers from the Bitvector "garbage" representation of the GCD steps.

    :param d: Input bitvector
    :type d: BitVector
    :return: Pair of input integers
    :rtype: tuple[int, int]
    """
    u, v = 1, 0
    nsteps = (len(d) // 5) * 3

    for i in reversed(range(nsteps)):
        garbage_small = d[(i // 3) * 5 : (i // 3 + 1) * 5]
        decomp = uncompress(garbage_small)
        b0 = decomp[2 * (i % 3)]
        b0andb1 = decomp[2 * (i % 3) + 1]

        v *= 2
        if b0:
            v += u
        if b0andb1:
            u, v = v, u
    return u, v


def apply_bitvector(
    x: int, y: int, d: BitVector, p: int, nsteps: int
) -> tuple[int, int]:
    """This function "applies" the BitVector resulting from GCD computation to a pair
    of integers (x,y). This corresponds to the -- delayed -- computation of (r,s) in
    the extended Euclidean algorithm.

    By linearity of the operations (modulo p), when putting as input (z, 0), we will
    obtain (0, z v^{-1} mod p) where v is the original integer that we inverted using
    the GCD computation. This allows to perform in-place modular multiplication.

    :param x: Input integer
    :type x: int
    :param y: Input integer
    :type y: int
    :param d: BitVector representation of the GCD computation
    :type d: BitVector
    :param p: Modulus
    :type p: int
    :return: Updated pair of integers
    :rtype: tuple[int, int]
    """
    u, v = x, y
    nsteps = len(d) // 5 * 3
    for i in reversed(range(nsteps)):
        garbage_small = d[(i // 3) * 5 : (i // 3 + 1) * 5]
        decomp = uncompress(garbage_small)
        b0 = decomp[2 * (i % 3)]
        b0andb1 = decomp[2 * (i % 3) + 1]

        v *= 2
        v %= p
        if b0:
            v += u
            v %= p
        if b0andb1:
            u, v = v, u
    return u, v


def apply_bitvector_reverse(
    x: int, y: int, d: BitVector, p: int, nsteps: int
) -> tuple[int, int]:
    """This is the reverse of ``apply_bitvector`` where operations are simply
    performed in reverse.

    :param x: Input integer
    :type x: int
    :param y: Input integer
    :type y: int
    :param d: BitVector representation of the GCD computation
    :type d: BitVector
    :param p: Modulus
    :type p: int
    :return: Updated pair of integers
    :rtype: tuple[int, int]
    """
    u, v = x, y
    nsteps = len(d) // 5 * 3
    for i in range(nsteps):
        garbage_small = d[(i // 3) * 5 : (i // 3 + 1) * 5]
        decomp = uncompress(garbage_small)
        b0 = decomp[2 * (i % 3)]
        b0andb1 = decomp[2 * (i % 3) + 1]
        if b0andb1:
            u, v = v, u
        if b0:
            v -= u
            v %= p
        v = (v * pow(2, -1, p)) % p
    return u, v
