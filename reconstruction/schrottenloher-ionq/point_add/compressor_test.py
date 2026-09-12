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


from qarton.circuit import BitVector
from qarton.tests import auto_test

from .compressor import Absorber, Compressor, Swapper, uncompress


def test_uncompress() -> None:
    assert uncompress(BitVector(0, 0, 0, 0, 0)) == BitVector(0, 0, 1, 0, 1, 0)


def test_Compressor() -> None:

    qc = Compressor()
    # LateXCompiler(qc).compile("compressor.pdf")
    auto_test(qc)


def test_Swapper() -> None:
    for i in [0, 1, 2]:
        qc = Swapper(i)
        auto_test(qc, stop_on_first_exception=True)


def test_Absorber() -> None:
    for i in [0, 1, 2]:
        qc = Absorber(i)
        auto_test(qc, stop_on_first_exception=True)
