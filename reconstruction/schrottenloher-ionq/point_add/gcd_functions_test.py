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

from .gcd_functions import (
    to_bitvector,
)


def test_efficient_to_bitvector() -> None:

    random.seed(0)
    p = 2**255 - 19

    fail = 0
    for _ in range(1000):
        x = random.randrange(p)
        try:
            _ = to_bitvector(p, x)
        except AssertionError:
            # raise e
            fail += 1
    print(fail)
    assert fail <= 10
