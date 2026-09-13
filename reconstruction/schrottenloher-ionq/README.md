
# Optimized Point Addition Circuits for Elliptic Curve Discrete Logarithms

This is the accompanying code of ``Optimized Point Addition Circuits for Elliptic Curve Discrete Logarithms``
(André Schrottenloher, 2026). We provide a full implementation of the elliptic curve
(windowed) point addition circuit described in the paper, which can be found [here](https://eprint.iacr.org/2026/1128.pdf).


## Structure

We provide two top-level scripts:

- ``gcd_stats.py`` which we used to compute statistics on the GCD algorithm
- ``build_circuit.py`` which is used to construct the entire circuit, perform resource
   estimation, and test it.

We also provide a script ``qasm_output.py`` which can be used to output a fully decomposed
version of the circuit, as a sequence of gates, in QASM language. However the script needs
a lot of memory.

The rest of the code implements the components of the circuit:

- ``compressor.py`` is the "compression" circuit that maps an input of the form (00|01|10)^3
   into a 5-bit string, used to pack / unpack the bits produced during the GCD iterations.

- ``gcd_functions.py`` defines the functions of the two-step GCD (the "dialog" method of
   Khattar et al.).

- ``gcd.py`` implements these functions as quantum circuits and defines the in-place
   modular multiplication circuit. This is where the most complex optimizations happen.

- ``point_add.py`` defines the windowed point addition circuit.

- ``efficient_mod_arithmetic.py`` defines optimized modular arithmetic circuits (for general primes)

- ``special_mod_arithmetic.py`` defines modular arithmetic circuits optimized for pseudo-Mersenne
   primes.


## Installation

The code requires the python library Qarton, which is available [here](https://gitlab.inria.fr/capsule/qarton)
and requires Python 3.12 at least (it also works with Python 3.13 and 3.14,
but older versions of python will fail). We provide two methods to install
and run the code.

### With a Python virtual environment

For this method, you need to have ``curl``, ``unzip`` and ``python3-venv``
installed. Run the ``install.sh`` script:

    chmod +x install.sh
    ./install.sh

After installation, you can activate the virtual environment using:

    source .venv-qarton/bin/activate

### With Docker

Alternatively, we provide a Dockerfile. To build the Docker image:

    docker build -t point_add .

Afterwards, to run the Docker image:

    docker run -it --rm point_add

### After installation

Whether you are in the python virtual environment or in the Docker image,
you can run the tests and execute the scripts using the commands given
below.

Note that this may take some time, depending on your machine.

## Testing

Run:

    cd point_add
    pytest .

To run all available unit tests.

## Reproducing the results

Run:

   python gcd_stats.py

To display some statistics on the GCD algorithm. These statistics are important for the
circuit construction.

Run:

   python build_circuit.py
   python build_circuit.py --gate_efficient

To build the two versions of the circuit for secp256k1, one optimized for space, the other one
optimized for gate count. Both versions have the same error rate, they differ only
in some parts which are exact arithmetic circuits.

Run:

   python build_circuit.py --generic_prime
   python build_circuit.py --gate_efficient --generic_prime

To build the circuit for a generic prime (although the built-in constant prime remains
the one of secp256k1). With the previous commands, this allows to recover Table 1
in the paper.

Run: 

   python build_circuit.py --test

To test the circuit on (roughly) 10000 random inputs. The test replaces the exact arithmetic
components (e.g., adder circuits) by their dummy functions. The parameters in the script
specify the number of random inputs to try, and the number of threads.

If you want a smaller test, run:

   python build_circuit.py --small_test
   
To test the circuit on (roughly) 1000 random inputs, in the same conditions.


## Going further

There are built-in constants which can be changed. First of all, one can instantiate the circuit
with other primes than the secp256k1 one. Second, the parameters:

* ``ITERATIONS_VAR`` in ``gcd_functions.py``
* ``U_PAD_VAR`` in ``gcd_functions.py``
* ``PADDING2`` in ``point_add.py``
* ``TRUNCATE``, ``ITER_CAN_BE_Q``, ``PADDING``

Are the built-in constants which determine the success probability of the algorithm. You can experiment
with different constants. For example, if I take ``ITERATIONS_VAR = 0.5`` and I run
``python build_circuit.py --small_test``, I get 185 failures.




