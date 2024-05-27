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


def test_case1():
    """Check system consisting of all component types"""
    case1 = System("Case1 system", Source("3V coin", vo=3, rs=13e-3))
    case1.add_comp("3V coin", comp=Converter("1.8V buck", vo=1.8, eff=0.87, iq=12e-6))
    case1.add_comp("1.8V buck", comp=PLoad("MCU", pwr=27e-3))
    case1.add_comp("3V coin", comp=Converter("5V boost", vo=5, eff=0.91, iq=42e-6))
    case1.add_comp("5V boost", comp=ILoad("Sensor", ii=15e-3))
    case1.add_comp(parent="5V boost", comp=RLoss("RC filter", rs=33.0))
    case1.add_comp(parent="RC filter", comp=VLoss("Diode", vdrop=0.17))
    case1.add_comp("Diode", comp=LinReg("LDO 2.5V", vo=2.5, vdrop=0.27, iq=150e-6))
    case1.add_comp("LDO 2.5V", comp=PLoad("ADC", pwr=15e-3))
    case1.add_comp("5V boost", comp=RLoad("Res divider", rs=200e3))
    with pytest.raises(RuntimeError):
        case1.solve(maxiter=1)
    df = case1.solve(quiet=False)
    rows = 11
    assert df.shape[0] == rows, "Case1 solution row count"
    assert df.shape[1] == 11, "Case1 solution column count"
    df = case1.solve(tags={"Battery": "small", "Interval": "fast"})
    assert df.shape[0] == rows, "Case1 solution row count"
    assert df.shape[1] == 13, "Case1 solution column count"
    assert np.allclose(
        df[df["Component"] == "System total"]["Efficiency (%)"][rows - 1],
        79.4542,
        rtol=1e-6,
    ), "Case1 efficiency"
    assert (
        df[df["Component"] == "System total"]["Warnings"][rows - 1] == ""
    ), "Case 1 warnings"
    case1.save("tests/unit/case1.json")
    dfp = case1.params(limits=True)
    assert len(dfp) == rows - 1, "Case1 parameters row count"
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
    iqdata = {"vi": [5.0], "io": [0.1, 0.4, 0.6, 0.5], "iq": [[0.3, 0.4, 0.67, 0.89]]}
    with pytest.raises(ValueError):
        case5b.add_comp("5V system", comp=LinReg("LDO 3.3", vo=3.3, iq=iqdata))
    iqdata = {
        "vi": [5.0],
        "io": [0.0, 0.4, 0.6, 0.8],
        "iq": [[-0.3, -0.4, -0.67, -0.89]],
    }
    with pytest.raises(ValueError):
        case5b.add_comp("5V system", comp=LinReg("LDO 3.3", vo=3.3, iq=iqdata))
    iqdata = {"vi": [5.0], "io": [0.0, 0.1, 0.2, 0.3], "iq": [[1e-6, 1e-3, 2e-3, 3e-3]]}
    case5b.add_comp("5V system", comp=LinReg("LDO 3.3", vo=3.3, iq=iqdata))
    df = case5b.solve()
    rows = df.shape[0]
    assert np.allclose(
        df[df["Component"] == "System total"]["Iout (A)"][rows - 1],
        1e-6,
        rtol=1e-6,
    ), "Case5b current"
    iqdata = {
        "vi": [3.3, 5.0],
        "io": [0.0, 0.1, 0.2, 0.3],
        "iq": [[1e-6, 1e-3, 2e-3, 3e-3], [1e-6, 1e-3, 2e-3, 3e-3]],
    }
    case5b.change_comp("LDO 3.3", comp=LinReg("LDO 3.3", vo=3.3, iq=iqdata))
    df = case5b.solve()
    assert np.allclose(
        df[df["Component"] == "System total"]["Iout (A)"][rows - 1],
        1e-6,
        rtol=1e-6,
    ), "Case5b current"
    dfp = case5b.params()
    assert len(dfp) == 2, "Case5b parameters row count"


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
    case10.change_comp("Buck", comp=LinReg("LDO", vo=3.3))
    with pytest.raises(ValueError):
        case10.change_comp("LDO", comp=Source("5V", vo=5.0))
    with pytest.raises(ValueError):
        case10.change_comp("24V system", comp=LinReg("LDO2", vo=3.3))


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
    case13.add_comp("12V", comp=PLoad("Test", pwr=1.5))
    with pytest.raises(ValueError):
        case13.add_source(PLoad("Test2", pwr=1.5))
    case13.add_source(Source("3.3V aux", vo=3.3))
    df = case13.solve()
    assert len(df) == 9, "Case13 solution row count"
    assert df.shape[1] == 12, "Case13 column count"
    assert (
        df[df["Component"] == "System total"]["Warnings"][8] == "Yes"
    ), "Case 13 total warnings"
    assert (
        df[df["Component"] == "Subsystem 12V"]["Warnings"][6] == "Yes"
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
    assert dfp.shape[1] == 13, "Case13 parameter column count"
    phases = {"sleep": 3600, "active": 127}
    case13b.set_sys_phases(phases)
    dfp = case13b.phases()
    assert dfp.shape[1] == 8, "Case13 phases column count"


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
    case15.add_comp("5V", comp=Converter("Buck 3.3", vo=3.3, eff=0.88))
    case15.set_comp_phases("Buck 3.3", phase_conf=["active"])
    case15.add_comp("5V", comp=LinReg("LDO 1.8", vo=1.8))
    case15.set_comp_phases("LDO 1.8", phase_conf=["sleep"])
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
        case15.set_comp_phases("5V", {"active": 45e3})
    with pytest.raises(ValueError):
        case15.set_comp_phases("Resistor", {"active": 45e3})
    assert case15.phases() == None
    phases = {"sleep": 3600, "active": 127}
    case15.set_sys_phases(phases)
    assert phases == case15.get_sys_phases()
    df = case15.phases()
    expl = 15
    assert len(df) == expl, "Case15 phase report length"
    with pytest.raises(ValueError):
        case15.solve(phase="unknown")
    df = case15.solve(phase="sleep")
    assert len(df) == expl, "Case15 solution row count (one phase)"
    df = case15.solve(quiet=False)
    assert len(df) == 2 * expl + 1, "Case15 solution row count (all phases)"
    df = case15.solve(tags={"Tag1": "one"})
    assert df.shape[0] == 2 * expl + 1, "Case15 tagged solution row count (all phases)"
    assert df.shape[1] == 13, "Case15 tagged solution column count (all phases)"
    df = case15.solve(tags={"Tag1": "one"}, energy=True)
    assert df.shape[0] == 2 * expl + 1, "Case15 tagged solution row count (all phases)"
    assert (
        df.shape[1] == 14
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
    iqdata = {
        "vi": [5.0],
        "io": [0.0, 0.01, 0.02, 0.1],
        "iq": [[1e-6, 1e-3, 2e-3, 3e-3]],
    }
    case16.add_comp("12V", comp=LinReg("LinReg 1", vo=5.0, iq=iqdata))
    assert (
        type(case16.plot_interp("LinReg 1")) == matplotlib.figure.Figure
    ), "Case16 LinReg 1D figure"
    iqdata = {
        "vi": [2.5, 5.0],
        "io": [0.0, 0.01, 0.02, 0.1],
        "iq": [[0.12e-6, 0.51e-3, 1.52e-3, 2.3e-3], [1e-6, 1e-3, 2e-3, 3e-3]],
    }
    case16.add_comp("12V", comp=LinReg("LinReg 2", vo=5.0, iq=iqdata))
    assert (
        type(case16.plot_interp("LinReg 2", plot3d=True)) == matplotlib.figure.Figure
    ), "Case16 LinReg 2D figure"


cap = 0.15


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
    bdf = case17.batt_life("LiPo", cutoff=2.9, pfunc=probe, dfunc=deplete)
    assert bdf.shape[0] < 1000, "Case17 result columns with load phases"
