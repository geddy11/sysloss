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

import os
from sysloss.system import System
from sysloss.components import *
from sysloss.diagram import get_conf, make_diag, _DEF_CONF


def test_case1():
    """Test get_config()"""
    conf = get_conf()
    assert conf == _DEF_CONF, "Default configuration"


def test_case2():
    """Test make_diag()"""
    tsys = System("Test system", Source("CR2032", vo=3.0, rs=1))
    tsys.add_comp("CR2032", comp=VLoss("Diode", vdrop=0.35))
    tsys.add_comp(
        "Diode",
        comp=Converter(
            "Buck 1.8V",
            vo=1.8,
            eff={
                "vi": [3.3, 5.0, 12.0],
                "io": [0.1, 0.5, 0.9],
                "eff": [[0.55, 0.78, 0.92], [0.5, 0.74, 0.83], [0.4, 0.6, 0.766]],
            },
        ),
    )
    tsys.add_comp("Buck 1.8V", comp=PLoad("MCU", pwr=13e-3))
    tsys.add_comp(
        "Diode",
        comp=Converter(
            "Boost:5V",
            vo=5.0,
            eff={"vi": [3.3], "io": [0.1, 0.5, 0.9], "eff": [[0.55, 0.78, 0.92]]},
        ),
    )
    tsys.add_comp("Boost:5V", comp=RLoss("RC filter", rs=6.8))
    tsys.add_comp(
        "Boost:5V", comp=LinReg("LDO", vo=3.0, ig=0.001, limits={"io": [0, 1.0]})
    )
    tsys.add_comp("LDO", comp=PSwitch("P-switch", rs=0.01))
    tsys.add_comp("P-switch", comp=ILoad("load 2", ii=0.2))
    tsys.add_comp("RC filter", comp=RLoad("Sensor", rs=866))
    my_conf = get_conf()
    my_conf["node"]["Source"] = {"shape": "circle", "fillcolor": "coral"}
    my_conf["node"]["Converter"] = {"fillcolor": "darkturquoise"}
    my_conf["node"]["ILoad"] = {"fillcolor": "darkgoldenrod1"}
    my_conf["node"]["PLoad"] = {"fillcolor": "darkgoldenrod2"}
    my_conf["node"]["RLoad"] = {"fillcolor": "darkgoldenrod3"}
    my_conf["node"]["VLoss"] = {"fillcolor": "deepskyblue"}
    my_conf["node"]["RLoss"] = {"fillcolor": "deeppink"}
    my_conf["node"]["LinReg"] = {"fillcolor": "darkorchid1"}
    my_conf["node"]["PSwitch"] = {"fillcolor": "aquamarine"}
    my_conf["edge"]["arrowhead"] = "none"
    my_conf["graph"]["rankdir"] = "LR"
    assert make_diag(tsys) != None, "Check image generation"
    ret = make_diag(tsys, fname="tests/unit/Test.svg")
    assert ret == None, "Check diagram to file"
    assert os.path.exists("tests/unit/Test.svg") == True, "Check svg file creation"
    assert make_diag(tsys, config=my_conf) != None, "Check image generation with config"
    assert get_conf() == _DEF_CONF, "Check default configuration"