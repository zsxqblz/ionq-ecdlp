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
We used this script to obtain statistics on the GCD computation and check our
heuristic estimates.

We verify that on inputs of n bits:

- The number of iterations follows a normal law with average mu=1.413 * n and std=0.6 * sqrt(n)
- An amount of padding of order sqrt(n) ensures a very large probability of success

"""

import random
from math import ceil, log2, sqrt

import matplotlib.pyplot as plt  # type: ignore
import numpy as np
from scipy.stats import norm  # type: ignore
from tqdm import tqdm


def gcd_run(u: int, v: int) -> tuple[int, int]:
    """Runs the GCD algorithm and computes statistics:

    - how many iterations we need to finish
    - how many bits of 'padding' we must add to the u and v registers so that they
      never overlap with the garbage when doing register-sharing.

    :param u: Input integer
    :type u: int
    :param v: Input integer
    :type v: int
    :return: The number of iterations and the amount of padding for the (u,v) registers.
    :rtype: tuple[int, int]
    """
    assert u % 2 == 1
    n = max(u.bit_length(), v.bit_length())
    padding = 0.0  # amount of padding we need (for both u and v)
    it = 0  # number of iterations we need

    while v:
        it += 1
        b0 = v % 2
        b1 = u > v

        padding = max(padding, u.bit_length() - (n - it * 0.5 * (3 - log2(3))))
        padding = max(padding, v.bit_length() - (n - it * 0.5 * (3 - log2(3))))

        if b0 & b1:
            # v % 2 == 1 and u > v
            u, v = v, u
        if b0:
            # v % 2 == 1
            v -= u
        v >>= 1

    assert v == 0
    assert u == 1
    return (it, ceil(padding))


def compare_data_with_norm(
    data: list[float] | list[int],
    title: str,
    mu: float | None = None,
    std: float | None = None,
    fname: str | None = None,
) -> None:
    """
    Compare a data series with a normal distribution, and show the graph.

    :param data: Data series.
    :type data: list[float] | list[int]
    :param title: Title of the graph.
    :type title: str
    :param mu: Mean of the normal distribution (optional). If not set, we use the mean
        of the data series instead.
    :param std: Standard deviation of the normal distribution (optional). If not set,
        we use the standard deviation of the data series instead.
    :type mu: float
    :type std: float
    :param fname: File name to store the graph (optional). If not set, the graph is
        displayed instead.
    """
    if mu is None:
        mu = float(np.mean(data))
    if std is None:
        std = float(np.std(data))
    _, bins, _ = plt.hist(  # type: ignore
        data,
        bins=30,
        density=True,
        alpha=0.6,
        color="skyblue",
        edgecolor="black",
        label=title,
    )
    # Plot normal distribution curve
    x = np.linspace(min(bins), max(bins), 1000)  # type: ignore
    pdf = norm.pdf(x, mu, std)  # type: ignore
    plt.plot(x, pdf, "r--", label=f"Normal distribution\nμ={mu:.2f}, sigma={std:.2f}")  # type: ignore

    plt.legend()  # type: ignore
    plt.grid(True)  # type: ignore
    if fname is None:
        plt.show()  # type: ignore
    else:
        plt.savefig(fname)  # type: ignore
    plt.close()


def plot_data(
    data: list[float] | list[int],
    title: str,
    vline: float | None = None,
    vlinelabel: str | None = None,
    fname: str | None = None,
) -> None:
    """Plot a data series.

    :param data: Data series.
    :type data: list[float] | list[int]
    :param title: Title of the plot.
    :type title: str
    :param vline: If not None, add a vertical line at this position.
    :type vline: float | None, optional
    :param fname: If set, name of the file to save. If not set, display the graph instead.
         Defaults to None.
    :type fname: str | None, optional
    """
    _, _, _ = plt.hist(  # type: ignore
        data,
        bins=30,
        density=True,
        alpha=0.6,
        color="skyblue",
        edgecolor="black",
        label=title,
    )

    if vline is not None:
        plt.axvline(  # type: ignore
            x=vline,
            color="red",
            linestyle="--",
            linewidth=2,
            label=vlinelabel if vlinelabel is not None else f"x={vline}",
        )

    plt.legend()  # type: ignore
    plt.grid(True)  # type: ignore
    if fname is None:
        plt.show()  # type: ignore
    else:
        plt.savefig(fname)  # type: ignore
    plt.close()


def gcd_stats(n: int = 100, nb_trials: int = 1000, save_figs: bool = False) -> None:
    """Computes statistics on many iterations of the GCD algorithm. This produces
    two plots:

    - Number of iterations (compared with a normal law)
    - Number of bits of padding for the u / v registers

    :param n: Bit-size of integers, defaults to 100
    :type n: int, optional
    :param nb_trials: Number of trials to run, defaults to 1000
    :type nb_trials: int, optional
    :param save_figs: if True, will save the figures to files, defaults to False
    :type save_figs: bool, optional
    """

    data_iterations: list[int] = []
    data_padding: list[int] = []

    # p: int = randprime(1 << (n - 1), 1 << n)  # type: ignore
    p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F

    print("n = ", n)
    print("Number of trials = ", nb_trials)

    for _ in tqdm(range(nb_trials), desc="Running trials"):
        x = random.randrange(p)
        it, padding = gcd_run(p, x)
        data_iterations.append(it)
        data_padding.append(padding)

    # Display the number of iterations, and compare with a normal law of
    # average 1.413n and standard deviation 0.6 sqrt(n), which is what we heuristically
    # estimated.
    compare_data_with_norm(
        data_iterations,
        f"Number of iterations (histogram), n={n}, {nb_trials} trials",
        mu=1.413 * n,
        std=0.6 * sqrt(n),
        fname=f"number_iterations_{n}_{nb_trials}.pdf" if save_figs else None,
    )

    # Check that the number of bits of padding for p (and q) is below 2.3 sqrt(n) with
    # high probability.
    plot_data(
        data_padding,
        f"u / v register padding (histogram), n={n}, {nb_trials} trials",
        vline=2.3 * sqrt(n),
        vlinelabel="2.3 sqrt(n)",
        fname=f"uv_padding_{n}_{nb_trials}.pdf" if save_figs else None,
    )


if __name__ == "__main__":
    gcd_stats(n=256, nb_trials=10000, save_figs=False)
