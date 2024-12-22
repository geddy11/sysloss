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

from sysloss.system import System
from sysloss.components import *


@pytest.fixture(scope="class")
def sys1():
    """System 1 test fixture"""
    sys = System("sys1_fixture", Source("20V", vo=20))
    sys.add_source(Source("-24V", vo=-24, rs=0.05))
    sys.add_comp("-24V", comp=Rectifier("D-bridge", vdrop=0.3))
    sys.add_comp("20V", comp=Rectifier("M-bridge", rs=0.017, iq=1e-3, ig=2e-3))
    sys.add_comp(["D-bridge", "M-bridge"], comp=PMux("Pmux", rs=0.01), rail="Vsys")
    d1 = {"vi": [3.3], "io": [0.1, 0.5, 0.9], "vdrop": [[0.55, 0.78, 0.92]]}
    sys.add_comp("Vsys", comp=VLoss("Diode 1", vdrop=d1))
    sys.add_comp("Diode 1", comp=RLoss("R1", rs=1.247))
    sys.add_comp("R1", comp=ILoad("I-load 1", ii=0.125))
    e2 = {
        "vi": [3.3, 15.0, 48.0],
        "io": [0.1, 0.5, 0.9],
        "eff": [[0.55, 0.78, 0.92], [0.5, 0.74, 0.83], [0.4, 0.6, 0.766]],
    }
    sys.add_comp("Vsys", comp=Converter("Buck 5.0", vo=5.0, eff=e2))
    igdata = {
        "vi": [15, 50],
        "io": [0.0, 0.01, 0.02, 0.1],
        "ig": [[0.12e-6, 0.51e-3, 1.52e-3, 2.3e-3], [1e-6, 1e-3, 2e-3, 3e-3]],
    }
    sys.add_comp("Buck 5.0", comp=LinReg("LDO", vo=2.5, ig=igdata))
    sys.add_comp("LDO", comp=PLoad("Load 2", pwr=0.33))
    sys.add_comp("Vsys", comp=RLoad("Load 3", rs=1234))
    sys.add_comp("Vsys", comp=PSwitch("Sw1", rs=0.077))
    sys.add_comp("Sw1", comp=RLoss("R2", rs=10.247))
    sys.add_comp("R2", comp=PLoad("Load 4", pwr=0.099))
    sys.add_comp("R2", comp=RLoss("R3", rs=20.33))
    sys.add_comp("R3", comp=PLoad("Load 5", pwr=0.33))
    sys.add_comp("R3", comp=RLoss("R4", rs=15))
    sys.add_comp("R4", comp=PLoad("Load 6", pwr=1))
    sys_phases = {"one": 1, "two": 1}
    sys.set_sys_phases(sys_phases)
    sys.set_comp_phases("20V", phase_conf=["one"])
    sys.set_comp_phases("-24V", phase_conf=["two"])
    return sys


@pytest.fixture(scope="class")
def sys2():
    """System 2 test fixture"""
    sdc = System("Sensor Daisy chain", Source("Li-ion", vo=14.4, rs=0.2))
    sdc.add_comp("Li-ion", comp=Converter("Boost 48V", vo=48.0, eff=0.88))
    parent = "Boost 48V"
    for i in range(1, 17, 1):
        idx = " [{}]".format(i)
        sdc.add_comp(parent, comp=RLoss("Twisted pair" + idx, rs=4.3))
        sdc.add_comp("Twisted pair" + idx, comp=VLoss("Diode" + idx, vdrop=0.54))
        sdc.add_comp(
            "Diode" + idx, comp=PSwitch("Power switch" + idx, rs=0.03, ig=10e-6)
        )
        sdc.add_comp("Diode" + idx, comp=Converter("Buck 3.3V" + idx, vo=3.3, eff=0.72))
        sdc.add_comp("Buck 3.3V" + idx, comp=PLoad("Sensor unit" + idx, pwr=0.35))
        parent = "Power switch" + idx
    return sdc
