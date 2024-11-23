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


from sysloss.components import *
from sysloss.components import _ComponentTypes, _ComponentInterface, _Component
from sysloss.components import LIMITS_DEFAULT
from sysloss.components import _Interp0d, _Interp1d, _Interp2d
import numpy as np
import pytest


def close(a, b):
    """Check if results are close"""
    return np.allclose([a], [b])


def test_classes():
    """Check informal interface on components"""
    assert issubclass(Source, _ComponentInterface), "subclass Source"
    assert issubclass(ILoad, _ComponentInterface), "subclass ILoad"
    assert issubclass(PLoad, _ComponentInterface), "subclass PLoad"
    assert issubclass(RLoad, _ComponentInterface), "subclass RLoad"
    assert issubclass(RLoss, _ComponentInterface), "subclass SLoss"
    assert issubclass(VLoss, _ComponentInterface), "subclass SLoss"
    assert issubclass(Converter, _ComponentInterface), "subclass Converter"
    assert issubclass(LinReg, _ComponentInterface), "subclass LinReg"
    assert issubclass(PSwitch, _ComponentInterface), "subclass PSwitch"


def test_source():
    """Check Source component"""
    sa = Source("Battery 3V", vo=3.0, rs=7e-3)
    assert sa._component_type == _ComponentTypes.SOURCE, "Source component type"
    assert _ComponentTypes.SOURCE not in list(sa._child_types), "Source child types"
    sb = Source.from_file("Battery 3V", fname="tests/data/source.toml")
    assert sa._params == sb._params, "Source parameters from file"
    assert sa._limits == sb._limits, "Source limits from file"
    assert isinstance(sa, _ComponentInterface), "instance Source"
    with pytest.raises(ValueError):
        sc = Source("Battery", vo=14.7, rs=3e-3, limits={"io": "invalid"})
    with pytest.raises(ValueError):
        sc = Source("Battery", vo=14.7, rs=3e-3, limits={"io": [1]})
    with pytest.raises(ValueError):
        sc = Source("Battery", vo=14.7, rs=3e-3, limits={"io": [1, 2, 3]})


def test_pload():
    """Check PLoad component"""
    pa = PLoad("Load 1", pwr=27e-3)
    assert pa._component_type == _ComponentTypes.LOAD, "PLoad component type"
    assert list(pa._child_types) == [None], "PLoad child types"
    pb = PLoad.from_file("Load 1", fname="tests/data/pload.toml")
    assert pa._params == pb._params, "PLoad parameters from file"
    assert pa._limits == pb._limits, "PLoad limits from file"
    assert isinstance(pa, _ComponentInterface), "instance PLoad"


def test_iload():
    """Check ILoad component"""
    ia = ILoad("Load 1", ii=15e-3, loss=True)
    assert ia._component_type == _ComponentTypes.LOAD, "ILoad component type"
    assert list(ia._child_types) == [None], "ILoad child types"
    ib = ILoad.from_file("Load 1", fname="tests/data/iload.toml")
    assert ia._params == ib._params, "ILoad parameters from file"
    assert ia._limits == ib._limits, "ILoad limits from file"
    assert isinstance(ia, _ComponentInterface), "instance ILoad"


def test_rload():
    """Check RLoad component"""
    ra = RLoad("Load 1", rs=200e3)
    assert ra._component_type == _ComponentTypes.LOAD, "RLoad component type"
    assert list(ra._child_types) == [None], "RLoad child types"
    rb = RLoad.from_file("Load 1", fname="tests/data/rload.toml")
    assert ra._params == rb._params, "RLoad parameters from file"
    assert ra._limits == rb._limits, "RLoad limits from file"
    assert isinstance(ra, _ComponentInterface), "instance ILoad"
    with pytest.raises(ValueError):
        ra = RLoad("Load 1", rs=0.0)


def test_rloss():
    """Check RLoss component"""
    la = RLoss("RLoss 1", rs=30e-3, limits=LIMITS_DEFAULT)
    assert la._component_type == _ComponentTypes.SLOSS, "RLoss component type"
    assert _ComponentTypes.SOURCE not in list(la._child_types), "RLoss child types"
    lb = RLoss.from_file("RLoss 1", fname="tests/data/rloss.toml")
    assert la._params == lb._params, "RLoss parameters from file"
    assert la._limits == lb._limits, "RLoss limits from file"
    assert isinstance(la, _ComponentInterface), "instance RLoss"


def test_vloss():
    """Check VLoss component"""
    la = VLoss("VLoss 1", vdrop=1.7, limits=LIMITS_DEFAULT)
    assert la._component_type == _ComponentTypes.SLOSS, "VLoss component type"
    assert _ComponentTypes.SOURCE not in list(la._child_types), "VLoss child types"
    lb = VLoss.from_file("VLoss 1", fname="tests/data/vloss.toml")
    assert la._params == lb._params, "VLoss parameters from file"
    assert la._limits == lb._limits, "VLoss limits from file"
    assert isinstance(la, _ComponentInterface), "instance VLoss"
    vdata = {"vi": [4.5], "io": [0.1, 0.4, 0.6, 0.9], "vdrop": [[0.3, 0.4, 0.67, 0.89]]}
    lc = VLoss("Conv 1D", vdrop=vdata)
    assert close(lc._ipr._interp(0.25, 100), 0.35), "VLoss 1D interpolation"
    vdata["io"][-1] = 0.59
    with pytest.raises(ValueError):
        lc = VLoss("VLoss 1D interpolation, io non-monotonic", vdrop=vdata)
    vdata = {
        "vi": [4.5, 12],
        "io": [0.1, 0.4, 0.6],
        "vdrop": [[0.3, 0.4, 0.67], [0.4, 0.55, 0.78]],
    }
    lc = VLoss("VLoss 2D", vdrop=vdata)
    assert close(
        lc._ipr._interp(0.0, 100), vdata["vdrop"][1][0]
    ), "VLoss 2D interpolation"


def test_converter():
    """Check Converter component"""
    ca = Converter("Conv 1", vo=5.0, eff=0.87)
    assert ca._component_type == _ComponentTypes.CONVERTER, "Converter component type"
    assert _ComponentTypes.SOURCE not in list(ca._child_types), "Converter child types"
    with pytest.raises(ValueError):
        cb = Converter("Conv 1", vo=5.0, eff=1.000001)
    with pytest.raises(ValueError):
        cb = Converter("Conv 1", vo=5.0, eff=-0.000001)
    with pytest.raises(ValueError):
        cb = Converter("Conv 1", vo=5.0, eff=0.0)
    cb = Converter.from_file("Conv 1", fname="tests/data/converter.toml")
    assert ca._params == cb._params, "Converter parameters from file"
    assert ca._limits == cb._limits, "Converter limits from file"
    assert isinstance(ca, _ComponentInterface), "instance Converter"
    edata = {"vi": [4.5], "io": [0.1, 0.4, 0.6, 0.9], "eff": [[0.3, 0.4, 0.67, 0.89]]}
    ca = Converter("Conv 1D", vo=5.0, eff=edata)
    assert close(ca._ipr._interp(0.25, 100), 0.35), "Converter 1D interpolation"
    edata["eff"][0][-1] = 1.1
    with pytest.raises(ValueError):
        ca = Converter("Conv 1D interpolation, eff > 1.0", vo=5.0, eff=edata)
    edata["eff"][0][-1] = 0.0
    with pytest.raises(ValueError):
        ca = Converter("Conv 1D interpolation, eff = 0.0", vo=5.0, eff=edata)
    edata["io"][-1] = 0.59
    with pytest.raises(ValueError):
        ca = Converter("Conv 1D interpolation, io non-monotonic", vo=5.0, eff=edata)
    edata = {
        "vi": [4.5, 12],
        "io": [0.1, 0.4, 0.6],
        "eff": [[0.3, 0.4, 0.67], [0.4, 0.55, 0.78]],
    }
    ca = Converter("Conv 2D", vo=5.0, eff=edata)
    assert close(
        ca._ipr._interp(0.0, 100), edata["eff"][1][0]
    ), "Converter 2D interpolation"
    # check incorrect interpolation data format
    edata = {
        "vi": [6.7],
        "io": [0.15, 0.45, 0.65],
        "eff": [[0.31, 0.41, 0.671], [0.43, 0.553, 0.783]],
    }
    with pytest.raises(ValueError):
        Converter("Conv 2D 1", vo=5.5, eff=edata)
    edata = {
        "vi": [8.0, 16.0],
        "io": [0.19, 0.49, 0.69, 0.8],
        "eff": [[0.1, 0.4, 0.71], [0.3, 0.53, 0.83]],
    }
    with pytest.raises(ValueError):
        Converter("Conv 2D 2", vo=5.5, eff=edata)
    edata = {
        "vo": [3.5, 10],
        "io": [0.1, 0.4, 0.6],
        "eff": [[0.3, 0.4, 0.67], [0.4, 0.55, 0.78]],
    }
    with pytest.raises(ValueError):
        Converter("Conv 2D 3", vo=3.3, eff=edata)
    edata = {
        "vi": [5.5],
        "ii": [0.4, 0.5, 0.6],
        "eff": [[0.45, 0.65, 0.8]],
    }
    with pytest.raises(ValueError):
        Converter("Conv 2D 4", vo=1.8, eff=edata)
    edata = {
        "vi": [5.5],
        "io": [0.4, 0.6],
        "ef": [[0.65, 0.8]],
    }
    with pytest.raises(ValueError):
        Converter("Conv 2D 5", vo=1.8, eff=edata)


def test_linreg():
    """Check LinReg component"""
    la = LinReg(
        "LDO 1",
        vo=2.5,
        vdrop=0.3,
        ig={"vi": [5.0], "io": [0.0, 0.05, 0.1], "ig": [[2.0e-6, 0.5e-3, 0.85e-3]]},
    )
    assert la._component_type == _ComponentTypes.LINREG, "LinReg component type"
    assert _ComponentTypes.SOURCE not in list(la._child_types), "LinReg child types"
    with pytest.raises(ValueError):
        lb = LinReg("LDO 2", vo=1.8, vdrop=2.0)
    with pytest.raises(KeyError):
        lb = LinReg.from_file("LDO 1", fname="tests/data/linreg_bad.toml")
    with pytest.deprecated_call():
        lb = LinReg.from_file("LDO 1", fname="tests/data/linreg.toml")
    assert la._params == lb._params, "LinReg parameters from file"
    assert la._limits == lb._limits, "LinReg limits from file"
    assert isinstance(la, _ComponentInterface), "instance LinReg"
    lb2 = LinReg.from_file("LDO 1", fname="tests/data/linreg_new.toml")
    assert la._params == lb2._params, "LinReg parameters from new file"
    with pytest.deprecated_call():
        lc = LinReg(
            "LDO 3",
            vo=14.7,
            vdrop=0.3,
            iq={"vi": [5.0], "io": [0.0, 0.05, 0.1], "iq": [[2.0e-6, 0.5e-3, 0.85e-3]]},
        )


def test_pswitch():
    """Check PSwitch component"""
    la = PSwitch(
        "Load switch",
        rs=0.1,
        ig={
            "vi": [0.9, 1.8, 3.6],
            "io": [0.005, 0.05, 0.5],
            "ig": [[5e-6, 5e-6, 5e-6], [7e-6, 7e-6, 7e-6], [36e-6, 37e-6, 35e-6]],
        },
        iis=1.0e-6,
    )
    assert la._component_type == _ComponentTypes.PSWITCH, "PSwitch component type"
    assert _ComponentTypes.SOURCE not in list(la._child_types), "PSwitch child types"
    lb = PSwitch.from_file("Load switch", fname="tests/data/pswitch.toml")
    assert la._params == lb._params, "PSwitch parameters from file"
    assert la._limits == lb._limits, "PSwitch limits from file"
    assert isinstance(la, _ComponentInterface), "instance PSwitch"


def test_interpolators():
    """Check interpolators"""
    interp0d = _Interp0d(0.66)
    for i in range(10):
        rng = np.random.default_rng()
        assert interp0d._interp(rng.random(), rng.random()) == 0.66, "0D interpolator"
    x = [0.1, 0.5, 0.8, 1.2, 1.7]
    fx = [0.1, 0.2, 0.3, 0.5, 0.75]
    interp1d = _Interp1d(x, fx)
    for i in range(len(x)):
        assert close(
            interp1d._interp(x[i], 10 * rng.random()), fx[i]
        ), "1D interpolator"
    assert close(interp1d._interp(0, rng.random()), fx[0]), "1D below smallest x"
    assert close(interp1d._interp(100, rng.random()), fx[-1]), "1D above largest x"
    x = [0.1, 0.5, 0.9, 0.1, 0.5, 0.9, 0.1, 0.5, 0.9]
    y = [3.3, 3.3, 3.3, 5.0, 5.0, 5.0, 12, 12, 12]
    fxy = [0.55, 0.78, 0.92, 0.5, 0.74, 0.83, 0.4, 0.6, 0.766]
    interp2d = _Interp2d(x, y, fxy)
    for i in range(len(x)):
        assert close(interp2d._interp(x[i], y[i]), fxy[i]), "2D interpolator"
    assert close(interp2d._interp(0.0, 0.0), fxy[0]), "2D interpolator q0"
    assert close(interp2d._interp(0.0, 5.0), fxy[3]), "2D interpolator q1"
    assert close(interp2d._interp(0.0, 100.0), fxy[6]), "2D interpolator q2"
    assert close(interp2d._interp(0.5, 77.0), fxy[7]), "2D interpolator q3"
    assert close(interp2d._interp(11, 24.7), fxy[8]), "2D interpolator q4"
    assert close(interp2d._interp(1.7, 5), fxy[5]), "2D interpolator q5"
    assert close(interp2d._interp(1.7, 0.33), fxy[2]), "2D interpolator q6"
    assert close(interp2d._interp(0.5, 2.75), fxy[1]), "2D interpolator q7"


def test_component():
    """Check _Component class"""
    c = _Component("Test")
    assert c._component_type == None, "_Component component type"
    assert list(_ComponentTypes) == c._child_types, "_Component child types"
    assert isinstance(c, _ComponentInterface), "instance _Component"
    assert c._get_annot() == [
        "xlabel",
        "ylabel",
        "title",
    ], "Check _Component annotation labels"
    with pytest.raises(ValueError):
        _Component.from_file("Test", fname="tests/data/component.toml")
