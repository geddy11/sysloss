# MIT License
#
# Copyright (c) 2024, Geir Drange
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pytest
import numpy as np
from sysloss.utils import *


def test_case1():
    """Check trace_res()"""
    rs = trace_res(
        w1_mm=7 * MILS2MM, w2_mm=6 * MILS2MM, l_mm=6000 * MILS2MM, t_mm=1.2 * MILS2MM
    )
    assert np.allclose([rs], [0.5221078]), "Resistance at default temp"
    rs1 = trace_res(
        w1_mm=7 * MILS2MM,
        w2_mm=6 * MILS2MM,
        l_mm=6000 * MILS2MM,
        t_mm=1.2 * MILS2MM,
        temp=70,
    )
    assert np.allclose([rs1], [rs * (1 + 50 * TCR)]), "Resistance at 70C"
