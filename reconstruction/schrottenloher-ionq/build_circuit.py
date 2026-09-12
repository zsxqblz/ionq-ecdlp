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

# type: ignore

"""
This script builds the entire point addition circuit for secp256k1 and tests it.

The tests use the Qarton simulator. Since the simulator is implemented in pure-python
(and quite slow), it does not simulate gate by gate. Instead, we use 'dummy functions'
for arithmetic building blocks.

Note that the circuits defined in this package (IPModMul, etc.), while they do have
'dummy functions', are *not* automatically dummified. Indeed, we must test their
robustness to errors. So, in the simulation, we only replace building blocks from
the Qarton library like non-modular adders, which are known to be exact. And the
simulation allows us to check if the circuit runs correctly or not.

Usage
-----

This script has three options:

* ``--generic_prime``: constructs the circuit assuming that the prime is not special (i.e.,
  not pseudo-Mersenne). The resulting circuit should work with any prime.

* ``--gate_efficient``: constructs the gate-efficient version of the circuit, with more
  qubits but less CCX gates. The gate-efficient and qubit-efficient versions of the circuit
  have the same probability of success, because they differ only in the implementation
  of exact arithmetic components (adders, comparators, etc).

* ``--test``: will test the circuit on 10 000 random inputs instead of just displaying the
  counts.


Building
--------

   python build_circuit.py

This will construct the qubit-optimized, special-prime version of the circuit and
display the number of qubits, the CCX count,
the number of various basic gates, as well as the proportion of CCX count from all
sub-circuits. (Note that the proportions don't add to 1, as there are sub-circuits
of sub-circuits, this is just to see what the dominating terms are).

Note that the number of *bits* of the circuit is greater than the number of *qubits*. This
is due to the use of Gidney's constant adder, which requires some classical space
during the venting of carries (and this happens at the most space-consuming moment). The
Qarton library knows this and should count the qubits correctly.

Testing
-------

   python build_circuit.py --test

This will run a parallelized test of 10000 random inputs. The inputs are determined
using the python built-in random module. In our run, we used NB_PROC=16. Since the seeds
of the sub-processes are deterministic, if you run with the same parameters, there
shouldn't be any error.

Note that this test can take up to a few hours.

Testing the generic version
---------------------------

   python build_circuit.py --test --generic_prime

This will run the same test, but on the variant of the circuit that works for
generic primes. Note that we still use the secp256k1 prime in all cases, the circuit just
differs because we don't use arithmetic optimizations specific to pseudo-Mersenne primes.



Results
-------

We have two versions of the same circuit (they differ only in exact arithmetic components,
so they have the same probability of success):

* A space-optimized circuit with 1193 qubits and 2385517 = 2^21.19 Toffoli gates
* A gate-optimized circuit with 1446 qubits and 1865521 = 2^20.83 Toffoli / AND gates

"""

import argparse
import random
from math import ceil, log2, sqrt
from multiprocessing import Process, Queue

from qarton.binary_operations import AndGate

AndGate.replace_by_ccx = True
# This is the flag we use to always replace AND gates by CCX gates. The circuits
# work the same, but the gate counting is simplified.

from qarton.circuit import AndFanoutResourceReporter, Circuit, QartonError  # noqa: E402
from qarton.elliptic_curve import EC, AffPointType  # noqa: E402
from qarton.tests import auto_test_random  # noqa: E402
from tqdm import tqdm  # noqa: E402

try:
    from .point_add.gcd_functions import ITERATIONS_VAR
    from .point_add.point_add import WindowAffAddSpaceOpt
except ImportError as _:
    from point_add.gcd_functions import (  # type: ignore
        ITERATIONS_VAR,  # type: ignore
    )
    from point_add.point_add import WindowAffAddSpaceOpt  # type: ignore

# -------------------------
# Parameters
# -------------------------

# For testing
NB_TESTS = 10000
NB_PROC = 16
UPDATE_EVERY = 1


# --------------------------------------------


def point_addition_worker(
    gate_efficient: bool,
    generic_prime: bool,
    worker_id: int,
    n_tests: int,
    seed: int,
    queue: Queue,
) -> int:

    random.seed(seed)
    failures = 0

    # Each worker constructs its circuit. No shared object.
    qc = construct_circuit(
        seed, gate_efficient=gate_efficient, generic_prime=generic_prime
    )

    for _ in range(n_tests):
        try:
            auto_test_random(qc, nbr=1, stop_on_first_exception=True)
        except AssertionError:
            failures += 1
        except QartonError:
            failures += 1
        queue.put(("", 1))

    queue.put(("done", failures))

    return failures


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
    return qc


def point_addition_test(
    nb_tests: int,
    gate_efficient: bool = False,
    generic_prime: bool = False,
    nb_proc: int = 1,
) -> None:

    queue = Queue()

    base_seed = 0
    # ----------------------------------------------------------------

    tests_per_process = nb_tests // nb_proc

    worker_args = [
        (gate_efficient, generic_prime, i, tests_per_process, base_seed + i + 1, queue)
        for i in range(nb_proc)
    ]

    processes = [
        Process(target=point_addition_worker, args=worker_args[i])
        for i in range(nb_proc)
    ]

    for p in processes:
        p.start()

    total_failures: int = 0
    done = 0

    with tqdm(total=tests_per_process * nb_proc) as pbar:
        while done < nb_proc:
            msg = queue.get()
            if msg[0] == "done":
                done += 1
                total_failures += msg[1]
            else:
                pbar.update(msg[1])

    for p in processes:
        p.join()

    print("Total failures:", total_failures, "/", tests_per_process * nb_proc)


def display_circuit(gate_efficient: bool = False, generic_prime: bool = False) -> None:
    qc = construct_circuit(
        seed=0, gate_efficient=gate_efficient, generic_prime=generic_prime
    )
    r = AndFanoutResourceReporter(qc)
    print("----- Circuit metrics:")
    print("Number of qubits:", qc.nbr_qubits())
    print("Number of classical bits:", qc.nbr_cbits())
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
    # print("Minimal theoretical size", 1.5 * expected_iterations)

    # d = r.sub_circuits_by_name()
    # for k in d:
    #    f = d[k]
    #    if Circuit.name_exists(k):
    #        rr = AndFanoutResourceReporter(Circuit.from_name(k))
    #        if rr.ccx_count() > 0:
    #            print(k, f, rr.ccx_count_log2() + log2(f))

    print("----- Proportion of the CCX cost for sub-circuits:")
    for k, f in r.ccx_by_class_proportion():
        if f > 0:
            print(k, f)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--gate_efficient",
        action="store_true",
        help="Use the gate-efficient implementation",
    )

    parser.add_argument(
        "--generic_prime",
        action="store_true",
        help="Use the generic-prime implementation",
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run tests instead of displaying the circuit",
    )

    parser.add_argument(
        "--small_test",
        action="store_true",
        help="Run a small test (1000 inputs) instead of displaying the circuit",
    )

    args = parser.parse_args()

    if args.small_test:
        point_addition_test(
            nb_tests=1000,
            gate_efficient=args.gate_efficient,
            generic_prime=args.generic_prime,
            nb_proc=NB_PROC,
        )
    elif args.test:
        point_addition_test(
            nb_tests=NB_TESTS,
            gate_efficient=args.gate_efficient,
            generic_prime=args.generic_prime,
            nb_proc=NB_PROC,
        )
    else:
        display_circuit(
            gate_efficient=args.gate_efficient,
            generic_prime=args.generic_prime,
        )


if __name__ == "__main__":
    main()
