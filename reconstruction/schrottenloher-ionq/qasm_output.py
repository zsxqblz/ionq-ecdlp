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
This script builds a variant of the point addition circuit, fully decomposed as a sequence
of gates, and outputs a QASM file.

The circuit is also tested (but since the simulation is very slow, we only do 1 test).

At the moment it uses around 2 GB of RAM, and outpus a very large QASM file (300 MB).

"""

import random
import time
from math import ceil, log2, sqrt

from qarton.binary_operations import AndGate
from qarton.tests import auto_test_random

AndGate.replace_by_ccx = True
# This is the flag we use to always replace AND gates by CCX gates. The circuits
# work the same, but the gate counting is simplified.

from qarton.circuit import (  # noqa: E402
    AndFanoutResourceReporter,
    Circuit,
    Decompose,
    PermuteClassicalLast,
)
from qarton.elliptic_curve import EC, AffPointType  # noqa: E402

try:
    from .point_add.gcd_functions import ITERATIONS_VAR
    from .point_add.point_add import WindowAffAddSpaceOpt
except ImportError as _:
    from point_add.gcd_functions import (  # type: ignore
        ITERATIONS_VAR,  # type: ignore
    )
    from point_add.point_add import WindowAffAddSpaceOpt  # type: ignore


def construct_circuit(
    seed: int, gate_efficient: bool = False, generic_prime: bool = False
) -> Circuit:
    random.seed(seed)

    # https://std.neuromancer.sk/secg/secp256k1
    q_cons = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    a_cons = 0x0000000000000000000000000000000000000000000000000000000000000000
    b_cons = 0x0000000000000000000000000000000000000000000000000000000000000007

    ec = EC(q_cons, a_cons, b_cons)
    gg = AffPointType(ec).random_value()
    # l = tuple(gg * i for i in range(2, 10))

    # with single point we don't have conditional operations
    l = (gg * 0, gg * 1)

    qc = WindowAffAddSpaceOpt(
        l, ec, gate_efficient=gate_efficient, special_prime=not generic_prime
    )
    return qc  # type: ignore


def write_circuit(gate_efficient: bool = False, generic_prime: bool = False) -> None:
    qc = construct_circuit(
        seed=0, gate_efficient=gate_efficient, generic_prime=generic_prime
    )
    r = AndFanoutResourceReporter(qc)
    print("----- Circuit metrics:")
    print("Number of qubits:", qc.nbr_qubits())
    print("CCX count:", r.ccx_count())
    print("CCX count in log2", r.ccx_count_log2())
    print("Basic gates:", r.basic_gate_counts())

    n = 256
    expected_iterations = ceil((1.413 * n + ITERATIONS_VAR * sqrt(n)) / 3) * 3

    print("----- On the size of the garbage register:")

    print("Number of iterations", expected_iterations)
    print("Size of the garbage register", ceil(expected_iterations / 3) * 5)
    print(
        "Minimal theoretical size (with ternary encoding)",
        ceil(log2(3) * expected_iterations),
    )

    print("Building decomposed circuit...")
    dec = PermuteClassicalLast(Decompose(qc, stream=True), stream=True)

    t1 = time.time()
    print("Testing... this should take 5 to 20 minutes")
    # testing the circuit on 1 input. This should take 5 to 20 minutes.
    auto_test_random(dec, nbr=1, match_with=qc)

    # building the QASM output. This should take 5 to 20 minutes.
    print("Elapsed time:", time.time() - t1)
    t1 = time.time()
    print("Outputting QASM code... this shuld take 5 to 20 minutes")
    dec.to_qasm_file("test.qasm")
    print("Elapsed time:", time.time() - t1)


if __name__ == "__main__":
    write_circuit(
        gate_efficient=True,
        generic_prime=False,
    )
