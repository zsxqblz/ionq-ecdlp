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

from qarton.elliptic_curve import EC, AffPointType
from qarton.tests import auto_test_random

from .point_add import WindowAffAddSpaceOpt


def test_WindowAffAddSpaceOpt_large() -> None:
    """
    Construct the entire circuit for secp256k1 and check it on a few random inputs.
    Running this test could take some time.
    """

    print("Constructing circuit, this will take some time...")

    random.seed(0)

    q_cons = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    a_cons = 0x0000000000000000000000000000000000000000000000000000000000000000
    b_cons = 0x0000000000000000000000000000000000000000000000000000000000000007
    ec = EC(q_cons, a_cons, b_cons)
    gg = AffPointType(ec).random_value()
    l = (gg * 0, gg * 1, gg * 2, gg * 3)

    qc = WindowAffAddSpaceOpt(l, ec)

    print("Testing circuit...")

    auto_test_random(qc, nbr=4, stop_on_first_exception=False)
