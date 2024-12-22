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
import rich

import matplotlib
from sysloss.system import System
from sysloss.components import *
from sysloss.components import LIMITS_DEFAULT


def test_case1():
    """Check system consisting of all component types"""
    case1 = System(
        "Case1 system", Source("3V coin", vo=3, rs=13e-3), group="42", rail="SYS_3V"
    )
    case1.add_source(Source("USB", vo=5, rs=0.1))
    case1.add_comp("USB", comp=Rectifier("Bridge", vdrop=0.25))
    case1.add_comp(["SYS_3V", "Bridge"], comp=PMux("Pmux", rs=0.01))
    case1.add_comp("Pmux", comp=Converter("1.8V buck", vo=1.8, eff=0.87, iq=12e-6))
    case1.add_comp("1.8V buck", comp=PLoad("MCU", pwr=27e-3))
    case1.add_comp("Pmux", comp=Converter("5V boost", vo=5, eff=0.91, iq=42e-6))
    case1.add_comp("5V boost", comp=ILoad("Sensor", ii=15e-3))
    case1.add_comp(
        parent="5V boost", comp=RLoss("RC filter", rs=33.0, limits={"io": [0.0, 1.0]})
    )
    case1.add_comp(parent="RC filter", comp=VLoss("Diode", vdrop=0.17))
    case1.add_comp(
        "Diode", comp=LinReg("LDO 2.5V", vo=2.5, vdrop=0.27, ig=150e-6), rail="IO_2V5"
    )
    case1.add_comp("LDO 2.5V", comp=PLoad("ADC", pwr=15e-3), group="AFE")
    with pytest.warns(UserWarning):
        case1.add_comp("5V boost", comp=RLoad("Res divider", rs=200e3), rail="invalid")
    case1.add_comp("5V boost", comp=PSwitch("Load switch", rs=150e-3))
    case1.add_comp("Load switch", comp=PLoad("MCU 2", pwr=0.12))
    with pytest.raises(RuntimeError):
        case1.solve(maxiter=1)
    df = case1.solve(quiet=False)
    rows = 18
    assert df.shape[0] == rows, "Case1 solution row count"
    assert df.shape[1] == 14, "Case1 solution column count"
    df = case1.solve(tags={"Battery": "small", "Interval": "fast"})
    assert df.shape[0] == rows, "Case1 solution row count"
    assert df.shape[1] == 16, "Case1 solution column count"
    assert np.allclose(
        df[df["Component"] == "System total"]["Efficiency (%)"][rows - 1],
        84.82,
        rtol=1e-3,
    ), "Case1 efficiency"
    assert (
        df[df["Component"] == "System total"]["Warnings"][rows - 1] == ""
    ), "Case 1 warnings"
    case1.save("tests/unit/case1.json")
    dfp = case1.params(limits=True)
    assert len(dfp) == rows - 3, "Case1 parameters row count"
    assert case1.tree() == None, "Case1 tree output"
    with pytest.raises(ValueError):
        case1.tree("Dummy")
    assert case1.tree("5V boost") == None, "Case1 subtree output"
    edata = {"vi": [3.6], "io": [0.1, 0.4, 0.6, 0.9], "eff": [[0.3, 0.4, 0.67, 0.89]]}
    case1.change_comp(
        "1.8V buck", comp=Converter("1.8V buck", vo=1.8, eff=edata, iq=12e-6)
    )
    dfp = case1.params(limits=False)
    assert (
        dfp[dfp.Component == "1.8V buck"]["eff (%)"].tolist()[0] == "interp"
    ), "Case parameters interpolator"
    dfl = case1.limits()
    assert dfl.shape[1] == 2 + len(LIMITS_DEFAULT), "Case 1 limits column count"

    # reload system from json
    case1b = System.from_file("tests/unit/case1.json")
    df2 = case1b.solve()
    assert len(df2) == rows, "Case1b solution row count"

    assert np.allclose(
        df2[df2["Component"] == "System total"]["Efficiency (%)"][rows - 1],
        df[df["Component"] == "System total"]["Efficiency (%)"][rows - 1],
        rtol=1e-6,
    ), "Case1 vs case1b efficiency"

    assert np.allclose(
        df2[df2["Component"] == "System total"]["Power (W)"][rows - 1],
        df[df["Component"] == "System total"]["Power (W)"][rows - 1],
        rtol=1e-6,
    ), "Case1 vs case1b power"
    assert df2.shape[1] == 14, "Case1b solution column count"
    assert case1b._g.attrs["groups"]["3V coin"] == "42", "Case1 source group name"
    assert case1b._g.attrs["groups"]["ADC"] == "AFE", "Case1 ADC group name"


def test_case2():
    """Check system consisting of only Source"""
    case2 = System("Case2 system", Source("12V input", vo=12.0))
    df = case2.solve()
    assert len(df) == 2, "Case2 solution row count"
    assert (
        df[df["Component"] == "System total"]["Efficiency (%)"][1] == 100.0
    ), "Case2 efficiency"


def test_case3():
    """Check system with negative output converter"""
    case3 = System("Case3 system", Source("5V USB", vo=5.0))
    case3.add_comp(
        "5V USB",
        comp=Converter("-12V inverter", vo=-12.0, eff=0.88),
    )
    case3.add_comp("-12V inverter", comp=RLoss("Resistor", rs=25.0))
    df = case3.solve()
    assert len(df) == 4, "Case3 solution row count"
    assert (
        df[df["Component"] == "System total"]["Efficiency (%)"][3] == 100.0
    ), "Case2 efficiency"


def test_case4():
    """Converter with zero input voltage"""
    case4 = System("Case4 system", Source("0V system", vo=0.0))
    case4.add_comp("0V system", comp=Converter("Buck", vo=3.3, eff=0.50))
    df = case4.solve()
    assert len(df) == 3, "Case4 solution row count"


def test_case5():
    """LinReg with zero input voltage"""
    case5 = System("Case5 system", Source("0V system", vo=0.0))
    case5.add_comp("0V system", comp=LinReg("LDO", vo=-3.3))
    df = case5.solve()
    assert len(df) == 3, "Case5 solution row count"


def test_case5b():
    """LinReg with interpolation parameter"""
    case5b = System("Case5b system", Source("5V system", vo=5.0))
    igdata = {"vi": [5.0], "io": [0.1, 0.4, 0.6, 0.5], "ig": [[0.3, 0.4, 0.67, 0.89]]}
    with pytest.raises(ValueError):
        case5b.add_comp("5V system", comp=LinReg("LDO 3.3", vo=3.3, ig=igdata))
    igdata = {
        "vi": [4.5],
        "io": [0.0, 0.3, 0.55, 0.75],
        "ig": [[-0.2, -0.3, -0.5, -0.78]],
    }
    with pytest.raises(ValueError):
        case5b.add_comp("5V system", comp=LinReg("LDO 3.3", vo=3.3, ig=igdata))
    igdata = {"vi": [5.0], "io": [0.0, 0.1, 0.2, 0.3], "ig": [[1e-6, 1e-3, 2e-3, 3e-3]]}
    case5b.add_comp("5V system", comp=LinReg("LDO 3.3", vo=3.3, ig=igdata))
    df = case5b.solve()
    rows = df.shape[0]
    assert np.allclose(
        df[df["Component"] == "System total"]["Iout (A)"][rows - 1],
        1e-6,
        rtol=1e-6,
    ), "Case5b current"
    igdata = {
        "vi": [3.3, 5.0],
        "io": [0.0, 0.1, 0.2, 0.3],
        "ig": [[1e-6, 1e-3, 2e-3, 3e-3], [1e-6, 1e-3, 2e-3, 3e-3]],
    }
    case5b.change_comp("LDO 3.3", comp=LinReg("LDO 3.3", vo=3.3, ig=igdata))
    df = case5b.solve()
    assert np.allclose(
        df[df["Component"] == "System total"]["Iout (A)"][rows - 1],
        1e-6,
        rtol=1e-6,
    ), "Case5b current"
    dfp = case5b.params()
    assert len(dfp) == 2, "Case5b parameters row count"


def test_case5c():
    """PSwitch with invalid interpolation parameter"""
    case5c = System("Case5c system", Source("5V system", vo=5.0))
    igdata = {
        "vi": [3.3],
        "io": [0.11, 0.41, 0.61, 0.51],
        "ig": [[0.3, 0.4, 0.67, 0.89]],
    }
    with pytest.raises(ValueError):
        case5c.add_comp("5V system", comp=PSwitch("PSwitch", rs=3.3, ig=igdata))
    igdata = {
        "vi": [5.0],
        "io": [0.0, 0.4, 0.6, 0.8],
        "ig": [[-0.3, -0.4, -0.67, -0.89]],
    }
    with pytest.raises(ValueError):
        case5c.add_comp("5V system", comp=PSwitch("PSwitch", rs=1.3, ig=igdata))


def test_case6():
    """Create new system with root as non-Source"""
    with pytest.raises(ValueError):
        case6 = System("Case6 system", PLoad("Load", pwr=1))


def test_case7():
    """Add component to non-existing component"""
    case7 = System("Case7 system", Source("10V system", vo=10.0))
    with pytest.raises(ValueError):
        case7.add_comp("5V input", comp=Converter("Buck", vo=2.5, eff=0.75))


def test_case8():
    """Add component with already used name"""
    case8 = System("Case8 system", Source("10V system", vo=10.0))
    case8.add_comp("10V system", comp=Converter("Buck", vo=2.5, eff=0.75))
    with pytest.raises(ValueError):
        case8.add_comp("10V system", comp=Converter("Buck", vo=2.5, eff=0.75))


def test_case9():
    """Try adding component of wrong type"""
    case9 = System("Case9 system", Source("10V system", vo=10.0))
    with pytest.raises(ValueError):
        case9.add_comp("10V system", comp=Source("5V", vo=5.0))


def test_case10():
    """Change component"""
    case10 = System("Case10 system", Source("24V system", vo=24.0, rs=12e-3))
    case10.add_comp("24V system", comp=Converter("Buck", vo=3.3, eff=0.80))
    case10.add_comp("Buck", comp=PLoad("Load", pwr=0.5))
    case10.change_comp("Buck", comp=LinReg("LDO", vo=3.3))
    with pytest.raises(ValueError):
        case10.change_comp("LDO", comp=Source("5V", vo=5.0))
    with pytest.raises(ValueError):
        case10.change_comp("24V system", comp=LinReg("LDO2", vo=3.3))
    with pytest.raises(ValueError):
        case10.change_comp("Non-exist", comp=Source("5V", vo=5.0))
    df = case10.solve()
    assert len(df) == 4, "Case10 parameters row count"
    with pytest.warns(UserWarning):
        case10.change_comp("Load", comp=ILoad("Load", ii=0.5), rail="invalid")


def test_case11():
    """Delete component"""
    case11 = System("Case11 system", Source("CR2032", vo=3.0))
    case11.add_comp("CR2032", comp=Converter("1.8V buck", vo=1.8, eff=0.87))
    case11.add_comp("1.8V buck", comp=PLoad("MCU", pwr=27e-3))
    case11.del_comp("1.8V buck", del_childs=False)
    dfp = case11.params()
    assert len(dfp) == 2, "Case11 parameters row count"
    with pytest.raises(ValueError):
        case11.del_comp("CR2032")
    with pytest.raises(ValueError):
        case11.del_comp("Non-existent")
    case11.add_comp("CR2032", comp=Converter("1.8V buck", vo=1.8, eff=0.87))
    case11.add_comp("1.8V buck", comp=PLoad("MCU2", pwr=27e-3))
    case11.del_comp("1.8V buck")
    dfp = case11.params()
    assert len(dfp) == 2, "Case11 parameters row count"


def test_case12():
    """Warnings"""
    case12 = System(
        "Case12 system",
        Source(
            "6V",
            vo=6.0,
            limits={
                "io": [0.0, 0.101],
            },
        ),
    )
    case12.add_comp("6V", comp=ILoad("Overload", ii=0.1011))
    df = case12.solve()
    assert (
        df[df["Component"] == "System total"]["Warnings"][2] == "Yes"
    ), "Case 12 warnings"


def test_case13():
    """Multi-source"""
    case13 = System("Case13 system", Source("3.3V", vo=3.3))
    case13.add_source(Source("12V", vo=12, limits={"io": [0, 1e-3]}))
    case13.add_comp("3.3V", comp=PLoad("MCU", pwr=0.2))
    case13.add_comp(
        "12V", comp=PLoad("Test", pwr=1.5, rt=10, limits={"tp": [-40.0, 39.0]})
    )
    with pytest.raises(ValueError):
        case13.add_source(PLoad("Test2", pwr=1.5))
    case13.add_source(Source("3.3V aux", vo=3.3))
    df = case13.solve()
    assert len(df) == 9, "Case13 solution row count"
    assert df.shape[1] == 14, "Case13 column count"
    assert (
        df[df["Component"] == "System total"]["Warnings"][8] == "Yes"
    ), "Case 13 total warnings"
    assert (
        df[df["Component"] == "Subsystem 12V"]["Warnings"][6] == "Yes"
    ), "Case 13 Subsystem 12V warnings"
    assert (
        df[df["Component"] == "Test"]["Warnings"][2] == "tp"
    ), "Case 13 Subsystem 12V warnings"
    case13.save("tests/unit/case13.json")
    with pytest.raises(ValueError):
        case13.del_comp("12V", del_childs=False)
    case13.del_comp("12V")
    df = case13.solve()
    assert len(df) == 6, "Case13 solution row count after delete 12V"
    case13.del_comp("3.3V aux")
    df = case13.solve()
    assert len(df) == 3, "Case13 solution row count after delete 3.3V aux"
    with pytest.raises(ValueError):
        case13.del_comp("3.3V")
    # reload case13 from file
    case13b = System.from_file("tests/unit/case13.json")
    dff = case13b.solve()
    assert len(dff) == 9, "Case13 solution row count"
    assert (
        dff[dff["Component"] == "System total"]["Warnings"][8] == "Yes"
    ), "Case 13 total warnings"
    assert (
        dff[dff["Component"] == "Subsystem 12V"]["Warnings"][6] == "Yes"
    ), "Case 13 Subsystem 12V warnings"
    assert (
        dff[dff["Component"] == "Subsystem 3.3V"]["Warnings"][5] == ""
    ), "Case 13 Subsystem 3.3V warnings"
    dfp = case13b.params()
    assert dfp.shape[1] == 14, "Case13 parameter column count"
    phases = {"sleep": 3600, "active": 127}
    case13b.set_sys_phases(phases)
    dfp = case13b.phases()
    assert dfp.shape[1] == 7, "Case13 phases column count"


def test_case14():
    """Zero output source"""
    case14 = System("Case14 system", Source("0V", vo=0.0))
    case14.add_comp("0V", comp=PLoad("MCU", pwr=0.2))
    case14.add_comp("0V", comp=ILoad("Test", ii=0.1))
    df = case14.solve()
    assert len(df) == 4, "Case14 solution row count"


def test_case15():
    """Load phases"""
    case15 = System("Case15 system", Source("5V", vo=5.0))
    case15.add_comp("5V", comp=Converter("Buck 3.3", vo=3.3, eff=0.88, rt=100.0))
    case15.set_comp_phases("Buck 3.3", phase_conf=["active"])
    case15.add_comp("5V", comp=LinReg("LDO 1.8", vo=1.8))
    case15.set_comp_phases("LDO 1.8", phase_conf=["sleep"])
    case15.add_comp("5V", comp=PSwitch("PSwitch 1", rs=0.55, ig=1e-3))
    case15.set_comp_phases("PSwitch 1", phase_conf=["active"])
    case15.add_comp("Buck 3.3", comp=PLoad("MCU", pwr=0.2))
    case15.set_comp_phases("MCU", phase_conf={"sleep": 1e-6, "active": 0.2})
    case15.add_comp("LDO 1.8", comp=ILoad("Sensor", ii=1.7e-3))
    case15.add_comp("LDO 1.8", comp=ILoad("Sensor2", ii=2.7e-3))
    case15.set_comp_phases("Sensor2", phase_conf={"sleep": 2.7e-3})
    case15.add_comp("LDO 1.8", comp=ILoad("Sensor2b", ii=1e-3))
    case15.set_comp_phases("Sensor2b", phase_conf={"active": 1e-3})
    case15.add_comp("LDO 1.8", comp=PLoad("Sensor3", pwr=1.7e-3))
    case15.add_comp("5V", comp=PLoad("Sensor3b", pwr=0.05))
    case15.set_comp_phases("Sensor3b", phase_conf={"active": 0.05})
    case15.add_comp("LDO 1.8", comp=RLoss("Resistor", rs=10e3))
    case15.add_comp("LDO 1.8", comp=RLoad("Sensor4", rs=25e3))
    case15.add_comp("LDO 1.8", comp=RLoad("Sensor5", rs=100e3))
    case15.set_comp_phases("Sensor5", phase_conf={"active": 45e3})
    case15.add_comp("5V", comp=Converter("Buck 3.0", vo=3.0, eff=0.83))
    case15.add_comp("5V", comp=LinReg("LDO 1.5", vo=1.5))
    with pytest.raises(ValueError):
        case15.set_comp_phases("Dummy", phase_conf={"active": 45e3})
    with pytest.raises(ValueError):
        case15.set_comp_phases("LDO 1.8", phase_conf=123.7)
    with pytest.raises(ValueError):
        case15.set_sys_phases({"sleep": 1000})
    with pytest.raises(ValueError):
        case15.set_sys_phases({"N/A": 100, "rest": 1})
    with pytest.raises(ValueError):
        case15.set_comp_phases("Resistor", {"active": 45e3})
    assert case15.phases() == None
    phases = {"sleep": 3600, "active": 127}
    case15.set_sys_phases(phases)
    assert phases == case15.get_sys_phases()
    df = case15.phases()
    expl = 16
    assert len(df) == expl, "Case15 phase report length"
    with pytest.raises(ValueError):
        case15.solve(phase="unknown")
    df = case15.solve(phase="sleep")
    assert len(df) == expl, "Case15 solution row count (one phase)"
    df = case15.solve(quiet=False)
    assert len(df) == 2 * expl + 1, "Case15 solution row count (all phases)"
    df = case15.solve(tags={"Tag1": "one"})
    assert df.shape[0] == 2 * expl + 1, "Case15 tagged solution row count (all phases)"
    assert df.shape[1] == 15, "Case15 tagged solution column count (all phases)"
    df = case15.solve(tags={"Tag1": "one"}, energy=True)
    assert df.shape[0] == 2 * expl + 1, "Case15 tagged solution row count (all phases)"
    assert (
        df.shape[1] == 16
    ), "Case15 tagged solution column count with energy (all phases)"


def test_case16():
    """Plot interpolation data"""
    case16 = System("Case16 system", Source("12V", vo=12.0))
    case16.add_comp("12V", comp=Converter("Buck 5.0", vo=5.0, eff=0.88))
    with pytest.raises(ValueError):
        case16.plot_interp("Dummy")
    assert case16.plot_interp("Buck 5.0") == None, "Case16 - no interpolation data"
    d1 = {"vi": [3.3], "io": [0.1, 0.5, 0.9], "eff": [[0.55, 0.78, 0.92]]}
    case16.change_comp("Buck 5.0", comp=Converter("Buck 5.0", vo=5.0, eff=d1))
    assert (
        type(case16.plot_interp("Buck 5.0")) == matplotlib.figure.Figure
    ), "Case16 1D figure"
    d2 = {
        "vi": [-3.3, -5.0, -12],
        "io": [0.1, 0.5, 0.9],
        "eff": [[0.55, 0.78, 0.92], [0.5, 0.74, 0.83], [0.4, 0.6, 0.766]],
    }
    case16.add_comp("12V", comp=Converter("Buck 3.3", vo=3.3, eff=d2))
    assert (
        type(case16.plot_interp("Buck 3.3")) == matplotlib.figure.Figure
    ), "Case16 2D figure"
    assert (
        type(case16.plot_interp("Buck 3.3", plot3d=True)) == matplotlib.figure.Figure
    ), "Case16 3D figure"
    d1 = {"vi": [3.3], "io": [0.1, 0.5, 0.9], "vdrop": [[0.55, 0.78, 0.92]]}
    case16.add_comp("12V", comp=VLoss("Diode 1", vdrop=d1))
    assert (
        type(case16.plot_interp("Diode 1")) == matplotlib.figure.Figure
    ), "Case16 Diode 1D figure"
    d3 = {
        "vi": [1, 2, 3],
        "io": [0.1, 0.5, 0.9],
        "vdrop": [[0.55, 0.78, 0.92], [0.5, 0.74, 0.83], [0.4, 0.6, 0.766]],
    }
    case16.add_comp("12V", comp=VLoss("Diode 2", vdrop=d3))
    assert (
        type(case16.plot_interp("Diode 2")) == matplotlib.figure.Figure
    ), "Case16 Diode 2D figure"
    igdata = {
        "vi": [5.0],
        "io": [0.0, 0.01, 0.02, 0.1],
        "ig": [[1e-6, 1e-3, 2e-3, 3e-3]],
    }
    case16.add_comp("12V", comp=LinReg("LinReg 1", vo=5.0, ig=igdata))
    assert (
        type(case16.plot_interp("LinReg 1")) == matplotlib.figure.Figure
    ), "Case16 LinReg 1D figure"
    case16.add_comp("12V", comp=PSwitch("PSwitch 1", rs=1.0, ig=igdata))
    assert (
        type(case16.plot_interp("PSwitch 1")) == matplotlib.figure.Figure
    ), "Case16 PSwitch 1D figure"
    igdata = {
        "vi": [2.5, 5.0],
        "io": [0.0, 0.01, 0.02, 0.1],
        "ig": [[0.12e-6, 0.51e-3, 1.52e-3, 2.3e-3], [1e-6, 1e-3, 2e-3, 3e-3]],
    }
    case16.add_comp("12V", comp=LinReg("LinReg 2", vo=5.0, ig=igdata))
    assert (
        type(case16.plot_interp("LinReg 2", plot3d=True)) == matplotlib.figure.Figure
    ), "Case16 LinReg 2D figure"
    case16.add_comp("12V", comp=PSwitch("PSwitch 2", rs=0.1, ig=igdata))
    assert (
        type(case16.plot_interp("PSwitch 2", plot3d=True)) == matplotlib.figure.Figure
    ), "Case16 PSwitch 2D figure"
    dfp = case16.params()
    assert dfp.shape[0] == 9, "Case 16 solution row count"


cap = 0.15  # battery capacity in case17


def probe():
    global cap
    return (0.15, 3.6, 0.0)


def deplete(time, curr):
    global cap
    cap -= time * curr / 3600.0
    if cap < 0.0:
        cap = 0.0
        return (0.0, 0.0, 0.0)
    return (cap, 3.6, 0.0)


def test_case17():
    """Test battery life function"""
    case17 = System("Case17 system", Source("LiPo", vo=3.6))
    case17.add_comp("LiPo", comp=Converter("Buck 1.8V", vo=1.8, eff=0.91))
    case17.add_comp("Buck 1.8V", comp=PLoad("MCU", pwr=0.125))
    with pytest.raises(ValueError):
        cap = 0.15
        case17.batt_life("MCU", cutoff=2.9, pfunc=probe, dfunc=deplete)
    bdf = case17.batt_life("LiPo", cutoff=2.9, pfunc=probe, dfunc=deplete)
    assert bdf.shape[1] == 4, "Case17 result columns"
    assert bdf.shape[0] == 1000, "Case17 result rows"
    case17_phases = {"sleep": 120, "run": 45}
    case17.set_sys_phases(case17_phases)
    case17.set_comp_phases("MCU", phase_conf={"sleep": 0.05, "run": 0.13})
    cap = 0.15
    bdf = case17.batt_life(
        "LiPo", cutoff=2.9, pfunc=probe, dfunc=deplete, tags={"tag 1": 1}
    )
    assert bdf.shape[0] < 1000, "Case17 result rows with load phases"
    assert bdf.shape[1] == 5, "Case17 result columns with load phases"


def test_case18():
    """Test already used rail/component name"""
    case18 = System("Case18", Source("12V", vo=12), rail="12_sys")
    with pytest.raises(ValueError):
        case18.add_comp("12V", comp=Converter("Buck 9V", vo=9, eff=0.91), rail="12V")
    with pytest.raises(ValueError):
        case18.add_comp(
            "12V", comp=Converter("Buck 9V", vo=9, eff=0.91), rail="Buck 9V"
        )
    with pytest.raises(ValueError):
        case18.add_comp("12V", comp=Converter("12_sys", vo=9, eff=0.91))
    with pytest.raises(ValueError):
        case18.add_comp("12V", comp=Converter("Buck 9V", vo=9, eff=0.91), rail="12_sys")
    with pytest.raises(ValueError):
        case18.add_source(Source("3.3V aux", vo=3.3), rail="12_sys")
    case18.add_comp("12_sys", comp=Converter("Buck 9V", vo=9, eff=0.91), rail="9V")
    with pytest.raises(ValueError):
        case18.change_comp("12V", comp=Source("9V", vo=9))
    with pytest.raises(ValueError):
        case18.change_comp("12V", comp=Source("9V in", vo=9), rail="12_sys")


def test_case19():
    """Rail report"""
    case19 = System(
        "Bluetooth sensor", Source("CR2032", vo=3.0, rs=0), group="main", rail="Vbatt"
    )
    case19.add_comp(
        "Vbatt", comp=Converter("Buck 1.8V", vo=1.8, eff=0.88, limits={"vo": [2, 4]})
    )
    case19.add_comp("Buck 1.8V", comp=PLoad("MCU", pwr=13e-3))
    case19.add_comp(
        "Vbatt",
        comp=Converter(
            "Boost 5V",
            vo=5.0,
            eff=0.92,
            limits={"io": [0, 0.001]},
        ),
        rail="5V_sys",
    )
    case19.add_comp("Boost 5V", comp=RLoss("RC filter", rs=6.8))
    case19.add_comp(
        "5V_sys",
        comp=LinReg("LDO", vo=3.0, ig=0.001, limits={"io": [0, 1]}),
        rail="3V0",
    )
    case19.add_comp("3V0", comp=PSwitch("P-switch", rs=0.01), group="aux")
    case19.add_comp("P-switch", comp=ILoad("load 2", ii=0.2))
    case19.add_comp("RC filter", comp=ILoad("Sensor", ii=6e-3))
    df = case19.rail_rep()
    assert df.shape[0] == 3, "Case19 solution row count"
    assert df.shape[1] == 7, "Case19 solution column count"
    warn = df["Warnings"].to_list()
    assert "vo" in warn[0], "Case19 warnings (vo) column"
    assert "io" in warn[0], "Case19 warnings (io) column"
    case19_phases = {"sleep": 3600, "acquire": 2.5, "transmit": 2e-3}
    case19.set_sys_phases(case19_phases)
    case19.set_comp_phases("Boost 5V", phase_conf=["acquire"])
    mcu_pwr = {"sleep": 12e-6, "acquire": 15e-3, "transmit": 35e-3}
    case19.set_comp_phases("MCU", phase_conf=mcu_pwr)
    dfp = case19.rail_rep()
    assert dfp.shape[0] == 9, "Case19 solution row count (phases)"
    assert dfp.shape[1] == 8, "Case19 solution column count (phases)"
    warn = dfp["Warnings"].to_list()
    assert warn[0] == "vo", "Case19 sleep warning"
    assert "vo" in warn[3], "Case19 sleep warning (vo) column"
    assert "io" in warn[3], "Case19 sleep warning (io) column"
    dfp = case19.rail_rep(phase="acquire")
    assert dfp.shape[0] == 3, "Case19 solution row count (one phase)"
    assert dfp.shape[1] == 8, "Case19 solution column count (one phase)"
    case19b = System("Bluetooth sensor", Source("CR2032", vo=3.0, rs=0))
    case19b.add_comp("CR2032", comp=Converter("Buck 1.8V", vo=1.8, eff=0.88))
    dfs = case19b.solve()
    dfr = case19b.rail_rep()
    assert dfs.shape == dfr.shape, "Case19b no rails"


def test_case20():
    """Test PMux corner cases"""
    pm = System("Test", Source("12V", vo=12), rail="sys")
    pm.add_comp("sys", comp=RLoss("R1", rs=1))
    pm.add_comp("sys", comp=RLoss("R2", rs=2))
    pm.add_comp("sys", comp=RLoss("R3", rs=3))
    pm.add_comp("sys", comp=RLoss("R4", rs=4))
    pm.add_comp("sys", comp=RLoss("R5", rs=5))
    pm.add_comp(["R1", "R2", "R3", "R4"], comp=PMux("pmux 1", rs=0.1), rail="12v")
    pm.add_comp("12v", comp=PLoad("MCU", pwr=1))
    with pytest.raises(ValueError):
        pm.change_comp("pmux 1", comp=PLoad("MCU4", pwr=1))
    df = pm.solve()
    rl = df["Loss (W)"].to_list()
    assert rl[1] + rl[2] + rl[3] + rl[4] == 0.0, "Only R1 dissipates power"
    for t in range(4):
        pn = System("Test 2", Source("S3", vo=15))
        for i in range(3):
            if i < t:
                pn.add_source(Source("S{}".format(i), vo=0))
            else:
                pn.add_source(Source("S{}".format(i), vo=12 + i))
        pn.add_comp(["S0", "S1", "S2", "S3"], comp=PMux("PMux", rs=0.1))
        pn.add_comp("PMux", comp=PLoad("load", pwr=1))
        df = pn.solve()
        assert df[df.Component == "PMux"]["Domain"][4] == "S{}".format(t), "Domain name"
    pm.del_comp("pmux 1")
    df = pm.solve()
    assert (
        df[df.Component == "System total"]["Iout (A)"][6] == 0.0
    ), "no pmux - no current"
    po = System("Test 3", Source("S0", vo=12), rail="sys")
    po.add_source(Source("S1", vo=5))
    with pytest.raises(ValueError):
        po.add_comp(["S0", "S0", "S1"], comp=PMux("PMux", rs=0.2))
    with pytest.raises(ValueError):
        po.add_comp(["S0", "S1"], comp=PLoad("load", pwr=1))
    po.add_comp(["S0", "S1"], comp=PMux("PMux 1", rs=0.2))
    with pytest.raises(ValueError):
        po.add_comp(["S0", "S1"], comp=PMux("PMux 2", rs=0.2))


def test_case21():
    """Load phases on sources with pmux"""
    c21 = System("Case 21", Source("12V", vo=12, rs=0.01))
    c21.add_source(Source("12V spare", vo=12, rs=0.05))
    c21.add_comp(["12V", "12V spare"], comp=PMux("inp mux", rs=0.025))
    c21.add_comp("inp mux", comp=PLoad("Load", pwr=2))
    c21_phases = {"one": 1, "two": 2, "three": 3}
    c21.set_sys_phases(c21_phases)
    c21.set_comp_phases("12V", phase_conf=["one"])
    c21.set_comp_phases("12V spare", phase_conf=["three"])
    df = c21.solve()
    rdf = df[df.Component.str.startswith("S")].reset_index()
    l1 = rdf[rdf.Component == "Subsystem 12V spare"]["Power (W)"].to_list()
    assert l1[0] == 0.0 and l1[1] == 0.0, "case21: 12V spare phase one, two"
    assert np.allclose(l1[2], 2.002086), "case21: 12V spare phase three"
    l2 = rdf[rdf.Component == "Subsystem 12V"]["Power (W)"].to_list()
    assert l2[1] == 0.0 and l2[2] == 0.0, "case21: 12V phase two, three"
    assert np.allclose(l2[0], 2.000973), "case21: 12V phase one"
    l3 = rdf[rdf.Component == "System total"]["Power (W)"].to_list()
    assert l3[1] == 0.0, "case21: total phase two"
    assert np.allclose(l3[0], 2.000973), "case21: total phase one"
    assert np.allclose(l3[2], 2.002086), "case21: total phase three"
    pdf = c21.phases()
    assert len(pdf) == 4, "Phase report rows"
