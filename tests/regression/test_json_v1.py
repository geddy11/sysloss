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
import pandas as pd

from sysloss.system import System
from sysloss.components import *


def test_case1():
    """Check system saved to json v1 format"""
    with pytest.deprecated_call():
        case1 = System.from_file("tests/data/System v1.0.0.json")
    df = case1.solve()
    rows = df.shape[0]
    assert np.allclose(
        df[df["Component"] == "System average"]["Power (W)"][rows - 1],
        1.829633,
        rtol=1e-6,
    ), "Case1 power"
    assert np.allclose(
        df[df["Component"] == "System average"]["Loss (W)"][rows - 1],
        0.818211,
        rtol=1e-6,
    ), "Case1 loss"
    assert np.allclose(
        df[df["Component"] == "System average"]["Efficiency (%)"][rows - 1],
        54.747386,
        rtol=1e-6,
    ), "Case1 efficiency"
    assert (
        df[df["Component"] == "System total"]["Warnings"][rows - 2] == "Yes"
    ), "Case 1 warnings"
    dfp = case1.params()
    df_bool = dfp == "interp"
    assert df_bool.sum().sum() == 4, "Case 1 interp components"
