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
from sysloss.components import *

# [vi, vo, io, phase]
INP_CURR_TESTS = [
    [0.0, 0.0, 1.0, ""],
    [-0.0, -0.0, 1.0, ""],
    [-100, -90, 3.14, "Apple"],
    [10, 5, 0.0, ""],
    [3.3, 3.0, 1e-3, ""],
    [-24, -15, 0.0, "Apple"],
]
# [vi, ii, io, phase]
OUTP_VOLT_TESTS = [
    [0.0, 10, 10, ""],
    [-0.0, 0, 0, ""],
    [-15, 0.7, 0.7, ""],
    [230, 2.1, 2.0, "Apple"],
    [4.7, 0.0, 0.0, ""],
]
# [vi, vo, ii, io, phase]
PWR_LOSS_TESTS = [
    [0.0, 0.0, 0.5, 0.6, ""],
    [-10.0, -8.5, 0.25, 0.1, ""],
    [-200, 0.0, 0.0, 2, ""],
    [3.3, 100, 0.1, 1e-3, ""],
    [24, 0, 14, 0, "Apple"],
    [-0.0, 0.0, 0.0, 0.0, ""],
    [48, 48, 5, 4, ""],
]


def close(a, b):
    """Check if results are close"""
    return np.allclose([a], [b])


@pytest.fixture()
def source(name, vo, rs):
    """Return a Source object."""
    return Source(name, vo=vo, rs=rs)


@pytest.mark.parametrize(
    "name, vo, rs",
    [("test1", 5.0, 0.0), ("test 2", -12.0, 1.0), ("zero volt", 0.0, 10.0)],
)
def test_source(source, name, vo, rs):
    """Test Source object with different parameters"""
    assert source._params["name"] == name

    for ict in INP_CURR_TESTS:
        ii = 0.0 if (vo == 0.0) else ict[2]
        assert close(
            source._solv_inp_curr(ict[0], ict[1], ict[2], ict[3]), ii
        ), "Check Source input current"
    for ovt in OUTP_VOLT_TESTS:
        v = 0.0 if (vo == 0.0) else vo - rs * ovt[2]
        assert close(
            source._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3]), v
        ), "Check source output voltage"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, eff, tr = source._solv_pwr_loss(plt[0], vo, plt[2], plt[3], plt[4])
        epwr = abs(vo * plt[3])
        assert close(pwr, epwr), "Check Source power"
        eloss = 0.0 if vo == 0.0 else rs * plt[3] * plt[3]
        assert close(loss, eloss), "Check Source loss"
        eeff = 100.0 if vo == 0.0 or plt[3] == 0.0 else 100 * (epwr - eloss) / epwr
        assert close(eff, eeff), "Check Source efficiency"


@pytest.fixture()
def rloss(name, rs, rt):
    """Return a RLoss object."""
    return RLoss(name, rs=rs, rt=rt)


@pytest.mark.parametrize(
    "name, rs, rt",
    [("R pos", 25.0, 0.0), ("R neg", -1.77, 25.0), ("R zero", 0.0, 40.0)],
)
def test_rloss(rloss, name, rs, rt):
    """Test RLoss object with different parameters"""
    assert rloss._params["name"] == name

    for ict in INP_CURR_TESTS:
        ii = 0.0 if (ict[0] == 0.0) else ict[2]
        assert close(
            rloss._solv_inp_curr(ict[0], ict[1], ict[2], ict[3]), ii
        ), "Check RLoss input current"
    for ovt in OUTP_VOLT_TESTS:
        v = 0.0 if (ovt[0] == 0.0) else ovt[0] - abs(rs) * ovt[2] * np.sign(ovt[0])
        if np.sign(v) != np.sign(ovt[0]):
            v = 0.0
        if ovt[0] == -15 and name == "R pos":
            with pytest.raises(ValueError):
                rloss._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3])
        else:
            assert close(
                rloss._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3]), v
            ), "Check Loss output voltage"
    for plt in PWR_LOSS_TESTS:
        pwr, los, eff, tr = rloss._solv_pwr_loss(plt[0], plt[1], plt[2], plt[3], plt[4])
        vo = plt[0] - (plt[3] * abs(rs)) * np.sign(plt[0])
        valid = True if np.sign(vo) == np.sign(plt[0]) else False
        epwr = abs(plt[0] * plt[2]) if valid else 0.0
        assert close(pwr, epwr), "Check RLoss power"
        eloss = 0.0 if plt[0] == 0.0 or not valid else abs(plt[0] - vo) * plt[3]
        assert close(los, eloss), "Check RLoss loss"
        ef = 100.0
        if epwr > 0.0:
            ef = 100.0 * abs((epwr - eloss) / epwr)
        if not valid:
            ef = 0.0
        assert close(eff, ef), "Check RLoss efficiency"
        assert close(tr, eloss * rt), "Check RLoss temperature rise"


@pytest.fixture()
def vloss(name, vdrop, rt):
    """Return a VLoss object."""
    return VLoss(name, vdrop=vdrop, rt=rt)


@pytest.mark.parametrize(
    "name, vdrop, rt",
    [("V pos", 5.0, 10.0), ("V neg", -1.77, 1.0), ("V zero", 0.0, 5.0)],
)
def test_vloss(vloss, name, vdrop, rt):
    """Test VLoss object with different parameters"""
    assert vloss._params["name"] == name

    for ict in INP_CURR_TESTS:
        ii = 0.0 if (ict[0] == 0.0) else ict[2]
        assert close(
            vloss._solv_inp_curr(ict[0], ict[1], ict[2], ict[3]), ii
        ), "Check VLoss input current"
    for ovt in OUTP_VOLT_TESTS:
        v = 0.0 if (ovt[0] == 0.0) else ovt[0] - abs(vdrop) * np.sign(ovt[0])
        if np.sign(v) != np.sign(ovt[0]):
            v = 0.0
        if ovt[0] == 4.7 and name == "V pos":
            with pytest.raises(ValueError):
                vloss._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3])
        else:
            assert close(
                vloss._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3]), v
            ), "Check VLoss output voltage"
    for plt in PWR_LOSS_TESTS:
        pwr, los, eff, tr = vloss._solv_pwr_loss(plt[0], plt[1], plt[2], plt[3], plt[4])
        vo = plt[0] - abs(vdrop) * np.sign(plt[0])
        valid = True if np.sign(vo) == np.sign(plt[0]) else False
        epwr = abs(plt[0] * plt[2]) if valid else 0.0
        assert close(pwr, epwr), "Check VLoss power"
        eloss = 0.0 if plt[0] == 0.0 or not valid else abs(plt[0] - vo) * plt[3]
        assert close(los, eloss), "Check VLoss loss"
        ef = 100.0
        if epwr > 0.0:
            ef = 100.0 * abs((epwr - eloss) / epwr)
        if not valid:
            ef = 0.0
        assert close(eff, ef), "Check VLoss efficiency"
        assert close(tr, los * rt), "Check VLoss temperature rise"


@pytest.fixture()
def pload(name, pwr, pwrs, rt, phase_loads):
    """Return a PLoad object."""
    return PLoad(name, pwr=pwr, pwrs=pwrs, rt=rt)


@pytest.mark.parametrize(
    "name, pwr, pwrs, rt, phase_loads",
    [
        ("No phase", 0.5, 0.001, 10.0, {}),
        ("On-phase", 0.5, 0.1, 3.5, {"Apple": 0.78}),
        ("Off-phase", 0.65, 0.13, 5.0, {"Pear": 0.9}),
    ],
)
def test_pload(pload, name, pwr, pwrs, rt, phase_loads):
    """Test PLoad object with different parameters"""
    assert pload._params["name"] == name

    for ict in INP_CURR_TESTS:
        if phase_loads == {}:
            p = pwr
        elif ict[3] in phase_loads:
            p = phase_loads[ict[3]]
        else:
            p = pwrs
        if ict[0] == 0.0:
            ii = 0.0
        else:
            ii = p / abs(ict[0])
        assert close(
            pload._solv_inp_curr(ict[0], ict[1], ict[2], ict[3], phase_loads), ii
        ), "Check PLoad input current"
    for ovt in OUTP_VOLT_TESTS:
        assert (
            pload._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3], phase_loads) == 0.0
        ), "Check PLoad output voltage"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, eff, tr = pload._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], plt[4], phase_loads
        )
        epwr = 0.0 if plt[0] == 0.0 else abs(plt[0] * plt[2])
        assert close(pwr, epwr), "Check PLoad power"
        assert 0.0 == loss, "Check PLoad loss"
        assert 100.0 == eff, "Check PLoad efficiency"
        assert close(tr, epwr * rt), "Check PLoad temperature rise"


@pytest.fixture()
def iload(name, ii, iis, rt, phase_loads):
    """Return a ILoad object."""
    return ILoad(name, ii=ii, iis=iis, rt=rt)


@pytest.mark.parametrize(
    "name, ii, iis, rt, phase_loads",
    [
        ("No phase", 0.5, 0.001, 12.0, {}),
        ("On-phase", 0.5, 0.1, 11.66, {"Apple": 0.78}),
        ("Off-phase", 0.65, 0.13, 0.05, {"Pear": 0.9}),
    ],
)
def test_iload(iload, name, ii, iis, rt, phase_loads):
    """Test ILoad object with different parameters"""
    assert iload._params["name"] == name

    for ict in INP_CURR_TESTS:
        if phase_loads == {}:
            i = ii
        elif ict[3] in phase_loads:
            i = phase_loads[ict[3]]
        else:
            i = iis
        if ict[0] == 0.0:
            i = 0.0
        assert close(
            iload._solv_inp_curr(ict[0], ict[1], ict[2], ict[3], phase_loads), i
        ), "Check ILoad input current"
    for ovt in OUTP_VOLT_TESTS:
        assert (
            iload._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3], phase_loads) == 0.0
        ), "Check ILoad output voltage"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, eff, tr = iload._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], plt[4], phase_loads
        )
        epwr = 0.0 if plt[0] == 0.0 else abs(plt[0] * plt[2])
        assert close(pwr, epwr), "Check ILoad power"
        assert 0.0 == loss, "Check ILoad loss"
        assert 100.0 == eff, "Check ILoad efficiency"
        assert close(tr, epwr * rt), "Check ILoad temperature rise"


@pytest.fixture()
def rload(name, rs, rt, phase_loads):
    """Return a RLoad object."""
    return RLoad(name, rs=rs, rt=rt)


@pytest.mark.parametrize(
    "name, rs, rt, phase_loads",
    [
        ("No phase", 12, 0.77, {}),
        ("On-phase", 27, 45.9, {"Apple": 33, "Orange": 47}),
        ("Off-phase", 150, 200.0, {"Pear": 190}),
    ],
)
def test_rload(rload, name, rs, rt, phase_loads):
    """Test RLoad object with different parameters"""
    assert rload._params["name"] == name

    for ict in INP_CURR_TESTS:
        if phase_loads == {}:
            r = rs
        elif ict[3] in phase_loads:
            r = phase_loads[ict[3]]
        else:
            r = rs
        if ict[0] == 0.0:
            i = 0.0
        else:
            i = abs(ict[0]) / r
        assert close(
            rload._solv_inp_curr(ict[0], ict[1], ict[2], ict[3], phase_loads), i
        ), "Check RLoad input current"
    for ovt in OUTP_VOLT_TESTS:
        assert (
            rload._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3], phase_loads) == 0.0
        ), "Check RLoad output voltage"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, eff, tr = rload._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], plt[4], phase_loads
        )
        epwr = 0.0 if plt[0] == 0.0 else abs(plt[0] * plt[2])
        assert close(pwr, epwr), "Check RLoad power"
        assert 0.0 == loss, "Check RLoad loss"
        assert 100.0 == eff, "Check RLoad efficiency"
        assert close(tr, epwr * rt), "Check RLoad temperature rise"


@pytest.fixture()
def converter(name, vo, eff, iq, iis, rt, active_phases):
    """Return a Converter object."""
    return Converter(name, vo=vo, eff=eff, iq=iq, iis=iis, rt=rt)


@pytest.mark.parametrize(
    "name, vo, eff, iq, iis, rt, active_phases",
    [
        ("No phase", 12.0, 0.97, 1e-5, 1e-6, 120.0, []),
        ("On-phase", -15, 0.88, 1.7e-4, 2e-5, 34.7, ["Apple", "Orange"]),
        ("Off-phase", 150, 0.5, 1e-3, 1.2e-4, 20.0, ["Pear"]),
        ("zero volt", 0.0, 0.65, 3e-3, 1e-4, 4.8, []),
    ],
)
def test_converter(converter, name, vo, eff, iq, iis, rt, active_phases):
    """Test Converter object with different parameters"""
    assert converter._params["name"] == name

    for ict in INP_CURR_TESTS:
        if ict[0] == 0.0 or vo == 0.0:
            ii = 0.0
        elif active_phases == []:
            if ict[2] == 0.0:
                ii = iq
            else:
                ii = abs(vo * ict[2] / (eff * ict[0]))
        elif ict[3] in active_phases:
            if ict[2] == 0.0:
                ii = iq
            else:
                ii = abs(vo * ict[2] / (eff * ict[0]))
        elif ict[3] not in active_phases:
            ii = iis
        assert close(
            converter._solv_inp_curr(ict[0], ict[1], ict[2], ict[3], active_phases), ii
        ), "Check Converter input current"
    for ovt in OUTP_VOLT_TESTS:
        v = vo
        if ovt[0] == 0.0 or vo == 0.0:
            v = 0.0
        elif active_phases != []:
            if ovt[3] not in active_phases:
                v = 0.0
        assert close(
            converter._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3], active_phases), v
        ), "Check Converter output voltage"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, ef, tr = converter._solv_pwr_loss(
            plt[0], vo, plt[2], plt[3], plt[4], active_phases
        )
        ipwr = abs(plt[0] * plt[2])
        eloss = abs(iq * plt[0]) if plt[3] == 0.0 else ipwr * (1.0 - eff)
        if active_phases != []:
            if plt[4] not in active_phases:
                eloss = abs(iis * plt[0])
                ipwr = abs(iis * plt[0])
        assert close(pwr, ipwr), "Check Converter power"
        assert close(loss, eloss), "Check Converter loss"
        if ipwr == 0.0 or vo == 0.0:
            eeff = 0.0
        opwr = ipwr - eloss
        if ipwr == 0.0:
            eeff = 0.0
        else:
            eeff = 100.0 * abs(opwr / ipwr)
        assert close(ef, eeff), "Check Converter efficiency"
        assert close(tr, eloss * rt), "Check Converter temperature rise"


@pytest.fixture()
def linreg(name, vo, vdrop, iq, iis, rt, active_phases):
    """Return a LinReg object."""
    return LinReg(name, vo=vo, vdrop=vdrop, iq=iq, iis=iis, rt=rt)


@pytest.mark.parametrize(
    "name, vo, vdrop, iq, iis, rt, active_phases",
    [
        ("No phase", 12.0, 1.2, 1e-5, 1e-6, 11.9, []),
        ("On-phase", -15, 0.88, 1.7e-4, 2e-5, 130.0, ["Apple", "Orange"]),
        ("Off-phase", 150, 0.67, 1e-3, 1.2e-4, 34.5, ["Pear"]),
    ],
)
def test_linreg(linreg, name, vo, vdrop, iq, iis, rt, active_phases):
    """Test LinReg object with different parameters"""
    assert linreg._params["name"] == name

    for ict in INP_CURR_TESTS:
        if ict[0] == 0.0 or vo == 0.0:
            ii = 0.0
        elif active_phases == []:
            ii = ict[2] + iq
        elif ict[3] in active_phases:
            ii = ict[2] + iq
        elif ict[3] not in active_phases:
            ii = iis
        assert close(
            linreg._solv_inp_curr(ict[0], ict[1], ict[2], ict[3], active_phases), ii
        ), "Check Linreg input current"
    for ovt in OUTP_VOLT_TESTS:
        v = min(abs(vo), max(abs(ovt[0]) - vdrop, 0.0))
        if ovt[0] == 0.0 or vo == 0.0:
            v = 0.0
        elif active_phases != []:
            if ovt[3] not in active_phases:
                v = 0.0
        assert close(
            linreg._solv_outp_volt(ovt[0], ovt[1], ovt[2], ovt[3], active_phases),
            v * np.sign(vo),
        ), "Check Linreg output voltage"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, eff, tr = linreg._solv_pwr_loss(
            plt[0], vo, plt[2], plt[3], plt[4], active_phases
        )
        ipwr = abs(plt[0] * plt[2])
        v = min(
            abs(linreg._params["vo"]), max(abs(plt[0]) - linreg._params["vdrop"], 0.0)
        )
        eloss = abs(iq * plt[0]) + (abs(plt[0]) - abs(v)) * plt[3]
        if active_phases != []:
            if plt[4] not in active_phases:
                eloss = abs(iis * plt[0])
                ipwr = abs(iis * plt[0])
        assert close(pwr, ipwr), "Check LinReg power"
        assert close(loss, eloss), "Check LinReg loss"
        if ipwr == 0.0 or v == 0.0:
            eeff = 0.0
        opwr = ipwr - eloss
        if ipwr == 0.0:
            eeff = 0.0
        else:
            eeff = 100.0 * abs(opwr / ipwr)
        assert close(eff, eeff), "Check LinReg efficiency"
        assert close(tr, eloss * rt), "Check LinReg temperature rise"
