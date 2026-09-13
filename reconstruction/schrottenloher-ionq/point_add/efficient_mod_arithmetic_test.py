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


import random

from qarton.arithmetic import (
    ControlledCDKMAdder,
    ControlledCDKMComparator,
    ControlledGidneyConstantAdder,
    ControlledGidneyConstantComparator,
    GidneyConstantAdder,
    GidneyConstantComparator,
)
from qarton.binary_operations import MCXWithBorrowedBits
from qarton.circuit import Circuit, QartonBool
from qarton.modular_arithmetic import ModInt
from qarton.tests import auto_test_random

from .efficient_mod_arithmetic import (
    EfficientControlledModularAdder,
    EfficientModularDouble,
)


def test_EfficientModularDouble() -> None:

    # secp256k1 curve
    p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    # p = 2**255 - 19
    # p = 17
    qc = EfficientModularDouble(p)
    auto_test_random(qc, 1000)

    # must also work for small vcalues
    assert qc.simulate(ModInt(0, p)) == qc.dummy_classical_function(ModInt(0, p))
    assert qc.simulate(ModInt(2, p)) == qc.dummy_classical_function(ModInt(2, p))


BACKENDS: frozenset[type[Circuit]] = frozenset(
    {
        GidneyConstantAdder,
        ControlledGidneyConstantAdder,
        GidneyConstantComparator,
        ControlledGidneyConstantComparator,
        ControlledCDKMComparator,
        ControlledCDKMAdder,
        MCXWithBorrowedBits,
    }
)


def test_EfficientControlledModularAdder() -> None:

    random.seed(0)

    p = 2**255 - 19
    p = 115792089237316195423570985008687907853269984665640564039457584007908834671663

    p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    # p = 2**255 + 2**254 + 3
    # p = 2**256 - 33354354778

    # p = 17
    #    qc = EfficientControlledModularAdder(p, padding=40, backends=BACKENDS)

    qc = EfficientControlledModularAdder(p, padding=40, backends=BACKENDS)
    auto_test_random(qc, 1000, stop_on_first_exception=True)

    x, y = (
        102460838300123673682830523352172395490853289673244954067382771620347541264381,
        13331250937192521740740461656515512362416694992395609972074812387561293407282,
    )
    t = QartonBool(1), ModInt(x, p), ModInt(y, p)

    assert qc.simulate(t) == qc.dummy_classical_function(t)
