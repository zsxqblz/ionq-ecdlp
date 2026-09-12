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

from qarton.circuit import AndFanoutResourceReporter
from qarton.tests import auto_test_random

from .gcd import (
    ApplyBitVector,
    IPModMul,
    ToBitVector,
)


def test_ToDialog_large() -> None:

    # test takes approximately one minute

    random.seed(0)
    p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    qc = ToBitVector(p)
    auto_test_random(qc, nbr=10, stop_on_first_exception=True)

    print(qc.nbr_qubits())

    r = AndFanoutResourceReporter(qc)
    print(r.ccx_count_log2())

    for k, f in r.sub_circuits_by_class_proportion():
        print(k, f)


def test_largedialog() -> None:

    random.seed(0)
    p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F

    # to check the dummy function
    ApplyBitVector.make_dummy()

    qc = IPModMul(p).inverse()
    # auto_test_random(qc, nbr=20, stop_on_first_exception=True)
    print(qc.nbr_qubits())
    print(qc.inverse().nbr_qubits())

    print(AndFanoutResourceReporter(qc).ccx_count_log2())
    auto_test_random(qc, nbr=10, stop_on_first_exception=False)
