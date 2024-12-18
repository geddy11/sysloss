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
import random
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

# off states
VINOFF_STATES = [False, True]


def close(a, b):
    """Check if results are close"""
    return np.allclose([a], [b])


#
# Source
#
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

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            ii = 0.0 if (vo == 0.0 or s) else ict[2]
            assert close(
                source._solv_inp_curr([ict[0]], ict[1], ict[2], ict[3], {}, state), ii
            ), "Check Source input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            v = 0.0 if (vo == 0.0 or s) else vo - rs * ovt[2]
            vs, vstate = source._solv_outp_volt(
                [ovt[0]], ovt[1], ovt[2], ovt[3], {}, state
            )
            assert close(vs, v), "Check Source output voltage"
            if vo == 0.0:
                assert vstate["off"][0] == True, "Check Source state"
            else:
                assert vstate["off"][0] == s, "Check Source state"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, eff, _, _ = source._solv_pwr_loss(
            [plt[0]], vo, plt[2], plt[3], 25.0, plt[4], {}
        )
        epwr = abs(vo * plt[3])
        assert close(pwr, epwr), "Check Source power"
        eloss = 0.0 if vo == 0.0 else rs * plt[3] * plt[3]
        assert close(loss, eloss), "Check Source loss"
        eeff = 100.0 if vo == 0.0 or plt[3] == 0.0 else 100 * (epwr - eloss) / epwr
        assert close(eff, eeff), "Check Source efficiency"


#
# RLoss
#
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

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            ii = 0.0 if (ict[0] == 0.0 or s) else ict[2]
            assert close(
                rloss._solv_inp_curr([ict[0]], ict[1], ict[2], ict[3], {}, state), ii
            ), "Check RLoss input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            v = 0.0 if (ovt[0] == 0.0) else ovt[0] - abs(rs) * ovt[2] * np.sign(ovt[0])
            if np.sign(v) != np.sign(ovt[0]) or s:
                v = 0.0
            if ovt[0] == -15 and name == "R pos" and not s:
                with pytest.raises(ValueError):
                    rloss._solv_outp_volt([ovt[0]], ovt[1], ovt[2], ovt[3], {}, state)
            else:
                vs, vstate = rloss._solv_outp_volt(
                    [ovt[0]], ovt[1], ovt[2], ovt[3], {}, state
                )
                assert close(vs, v), "Check RLoss output voltage"
                if ovt[0] == 0.0:
                    assert vstate["off"] == [True], "Check RLoss state"
                else:
                    assert vstate["off"] == [s], "Check RLoss state"
    for plt in PWR_LOSS_TESTS:
        pwr, los, eff, tr, tp = rloss._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], -55.0, plt[4], {}
        )
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
        if eloss * rt > 0.0:
            assert close(tp, -55.0 + eloss * rt), "Check RLoss peak temperature"


#
# VLoss
#
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

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            ii = 0.0 if ict[0] == 0.0 or s else ict[2]
            assert close(
                vloss._solv_inp_curr([ict[0]], ict[1], ict[2], ict[3], {}, state), ii
            ), "Check VLoss input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            v = 0.0 if ovt[0] == 0.0 else ovt[0] - abs(vdrop) * np.sign(ovt[0])
            if np.sign(v) != np.sign(ovt[0]) or s:
                v = 0.0
            if ovt[0] == 4.7 and name == "V pos" and not s:
                with pytest.raises(ValueError):
                    vloss._solv_outp_volt([ovt[0]], ovt[1], ovt[2], ovt[3], {}, state)
            else:
                vs, vstate = vloss._solv_outp_volt(
                    [ovt[0]], ovt[1], ovt[2], ovt[3], {}, state
                )
                assert close(vs, v), "Check VLoss output voltage"
                if ovt[0] == 0.0:
                    assert vstate["off"] == [True], "Check VLoss state"
                else:
                    assert vstate["off"] == [s], "Check VLoss state"
    for plt in PWR_LOSS_TESTS:
        pwr, los, eff, tr, tp = vloss._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], 85.0, plt[4], {}
        )
        vo = plt[0] - abs(vdrop) * np.sign(plt[0])
        valid = True if np.sign(vo) == np.sign(plt[0]) else False
        epwr = abs(plt[0] * plt[2]) if valid else 0.0
        assert close(pwr, epwr), "Check VLoss power"
        eloss = 0.0 if plt[0] == 0.0 or not valid else abs(plt[0] - vo) * plt[3]
        assert close(los, eloss), "Check VLoss loss"
        ef = 0.0
        if epwr > 0.0:
            ef = 100.0 * abs((epwr - eloss) / epwr)
        if not valid:
            ef = 0.0
        assert close(eff, ef), "Check VLoss efficiency"
        assert close(tr, los * rt), "Check VLoss temperature rise"
        if los * rt > 0.0:
            assert close(tp, 85.0 + los * rt), "Check VLoss peak temperature"


#
# PLoad
#
@pytest.fixture()
def pload(name, pwr, pwrs, rt, loss, phase_loads):
    """Return a PLoad object."""
    return PLoad(name, pwr=pwr, pwrs=pwrs, rt=rt, loss=loss)


@pytest.mark.parametrize(
    "name, pwr, pwrs, rt, loss, phase_loads",
    [
        ("No phase", 0.5, 0.001, 10.0, False, {}),
        ("On-phase", 0.5, 0.1, 3.5, False, {"Apple": 0.78}),
        ("Off-phase", 0.65, 0.13, 5.0, False, {"Pear": 0.9}),
        ("No phase", 0.5, 0.001, 10.0, True, {}),
        ("On-phase", 0.5, 0.1, 3.5, True, {"Apple": 0.78}),
        ("Off-phase", 0.65, 0.13, 5.0, True, {"Pear": 0.9}),
    ],
)
def test_pload(pload, name, pwr, pwrs, rt, loss, phase_loads):
    """Test PLoad object with different parameters"""
    assert pload._params["name"] == name

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            if phase_loads == {}:
                p = pwr
            elif ict[3] in phase_loads:
                p = phase_loads[ict[3]]
            else:
                p = pwrs
            if ict[0] == 0.0 or s:
                ii = 0.0
            else:
                ii = p / abs(ict[0])
            assert close(
                pload._solv_inp_curr(
                    [ict[0]], ict[1], ict[2], ict[3], phase_loads, state
                ),
                ii,
            ), "Check PLoad input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            vs, vstate = pload._solv_outp_volt(
                [ovt[0]], ovt[1], ovt[2], ovt[3], phase_loads, state
            )
            assert vs == 0.0, "Check PLoad output voltage"
            assert vstate["off"] == [s], "Check PLoad state"
    for plt in PWR_LOSS_TESTS:
        pwr, ploss, eff, tr, tp = pload._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], 19.7, plt[4], phase_loads
        )
        epwr = 0.0 if plt[0] == 0.0 else abs(plt[0] * plt[2])
        if not loss:
            assert close(pwr, epwr), "Check PLoad power"
            assert 0.0 == ploss, "Check PLoad loss"
            assert 100.0 == eff, "Check PLoad efficiency"
        else:
            assert close(ploss, epwr), "Check PLoad loss (loss mode)"
            assert 0.0 == pwr, "Check PLoad power (loss mode)"
            assert 0.0 == eff, "Check PLoad efficiency (loss mode)"
        assert close(tr, epwr * rt), "Check PLoad temperature rise"
        if epwr * rt > 0.0:
            assert close(tp, 19.7 + epwr * rt), "Check PLoad peak temperature"


#
# ILoad
#
@pytest.fixture()
def iload(name, ii, iis, rt, loss, phase_loads):
    """Return a ILoad object."""
    return ILoad(name, ii=ii, iis=iis, rt=rt, loss=loss)


@pytest.mark.parametrize(
    "name, ii, iis, rt, loss, phase_loads",
    [
        ("No phase", 0.5, 0.001, 12.0, False, {}),
        ("On-phase", 0.5, 0.1, 11.66, False, {"Apple": 0.78}),
        ("Off-phase", 0.65, 0.13, 0.05, False, {"Pear": 0.9}),
        ("No phase", 0.5, 0.001, 12.0, True, {}),
        ("On-phase", 0.5, 0.1, 11.66, True, {"Apple": 0.78}),
        ("Off-phase", 0.65, 0.13, 0.05, True, {"Pear": 0.9}),
    ],
)
def test_iload(iload, name, ii, iis, rt, loss, phase_loads):
    """Test ILoad object with different parameters"""
    assert iload._params["name"] == name

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            if phase_loads == {}:
                i = ii
            elif ict[3] in phase_loads:
                i = phase_loads[ict[3]]
            else:
                i = iis
            if ict[0] == 0.0 or s:
                i = 0.0
            assert close(
                iload._solv_inp_curr(
                    [ict[0]], ict[1], ict[2], ict[3], phase_loads, state
                ),
                i,
            ), "Check ILoad input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            vs, vstate = iload._solv_outp_volt(
                [ovt[0]], ovt[1], ovt[2], ovt[3], phase_loads, state
            )
            assert vs == 0.0, "Check ILoad output voltage"
            assert vstate["off"] == [s], "Check ILoad state"
    for plt in PWR_LOSS_TESTS:
        pwr, ploss, eff, tr, tp = iload._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], -43.0, plt[4], phase_loads
        )
        epwr = 0.0 if plt[0] == 0.0 else abs(plt[0] * plt[2])
        if not loss:
            assert close(pwr, epwr), "Check ILoad power"
            assert 0.0 == ploss, "Check ILoad loss"
            assert 100.0 == eff, "Check ILoad efficiency"
        else:
            assert close(ploss, epwr), "Check ILoad loss (loss mode)"
            assert 0.0 == pwr, "Check ILoad power (loss mode)"
            assert 0.0 == eff, "Check ILoad efficiency (loss mode)"
        assert close(tr, epwr * rt), "Check ILoad temperature rise"
        if epwr * rt > 0.0:
            assert close(tp, -43.0 + epwr * rt), "Check ILoad peak temperature"


#
# RLoad
#
@pytest.fixture()
def rload(name, rs, rt, loss, phase_loads):
    """Return a RLoad object."""
    return RLoad(name, rs=rs, rt=rt, loss=loss)


@pytest.mark.parametrize(
    "name, rs, rt, loss, phase_loads",
    [
        ("No phase", 12, 0.77, False, {}),
        ("On-phase", 27, 45.9, False, {"Apple": 33, "Orange": 47}),
        ("Off-phase", 150, 200.0, False, {"Pear": 190}),
        ("No phase", 12, 0.77, True, {}),
        ("On-phase", 27, 45.9, True, {"Apple": 33, "Orange": 47}),
        ("Off-phase", 150, 200.0, True, {"Pear": 190}),
    ],
)
def test_rload(rload, name, rs, rt, loss, phase_loads):
    """Test RLoad object with different parameters"""
    assert rload._params["name"] == name

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            if phase_loads == {}:
                r = rs
            elif ict[3] in phase_loads:
                r = phase_loads[ict[3]]
            else:
                r = rs
            if ict[0] == 0.0 or s:
                i = 0.0
            else:
                i = abs(ict[0]) / r
            assert close(
                rload._solv_inp_curr(
                    [ict[0]], ict[1], ict[2], ict[3], phase_loads, state
                ),
                i,
            ), "Check RLoad input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            vs, vstate = rload._solv_outp_volt(
                [ovt[0]], ovt[1], ovt[2], ovt[3], phase_loads, state
            )
            assert vs == 0.0, "Check RLoad output voltage"
            assert vstate["off"] == [s], "Check RLoad state"
    for plt in PWR_LOSS_TESTS:
        pwr, ploss, eff, tr, tp = rload._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], 55.7, plt[4], phase_loads
        )
        epwr = 0.0 if plt[0] == 0.0 else abs(plt[0] * plt[2])
        if not loss:
            assert close(pwr, epwr), "Check RLoad power"
            assert 0.0 == loss, "Check RLoad loss"
            assert 100.0 == eff, "Check RLoad efficiency"
        else:
            assert close(ploss, epwr), "Check RLoad loss (loss mode)"
            assert 0.0 == pwr, "Check RLoad power (loss mode)"
            assert 0.0 == eff, "Check RLoad efficiency (loss mode)"
        assert close(tr, epwr * rt), "Check RLoad temperature rise"
        if epwr * rt > 0.0:
            assert close(tp, 55.7 + epwr * rt), "Check RLoad peak temperature"


#
# Converter
#
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

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            if ict[0] == 0.0 or vo == 0.0 or s:
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
                converter._solv_inp_curr(
                    [ict[0]], ict[1], ict[2], ict[3], active_phases, state
                ),
                ii,
            ), "Check Converter input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            v = vo
            phase_off = False
            if ovt[0] == 0.0 or vo == 0.0 or s:
                v = 0.0
            elif active_phases != []:
                if ovt[3] not in active_phases:
                    v = 0.0
                    phase_off = True
            vs, vstate = converter._solv_outp_volt(
                [ovt[0]], ovt[1], ovt[2], ovt[3], active_phases, state
            )
            assert close(vs, v), "Check Converter output voltage"
            if ovt[0] == 0.0 or phase_off:
                assert vstate["off"] == [True], "Check Converter state"
            else:
                assert vstate["off"] == [s], "Check Converter state"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, ef, tr, tp = converter._solv_pwr_loss(
            plt[0], vo, plt[2], plt[3], 0.0, plt[4], active_phases
        )
        ipwr = abs(plt[0] * plt[2])
        eloss = abs(iq * plt[0]) if plt[3] == 0.0 else ipwr * (1.0 - eff)
        if active_phases != []:
            if plt[4] not in active_phases:
                eloss = abs(iis * plt[0])
                ipwr = abs(iis * plt[0])
        assert close(pwr, ipwr), "Check Converter power"
        assert close(loss, eloss), "Check Converter loss"
        if ipwr == 0.0 or vo == 0.0 or s:
            eeff = 0.0
        opwr = ipwr - eloss
        if ipwr == 0.0:
            eeff = 0.0
        else:
            eeff = 100.0 * abs(opwr / ipwr)
        assert close(ef, eeff), "Check Converter efficiency"
        assert close(tr, eloss * rt), "Check Converter temperature rise"
        if eloss * rt > 0.0:
            assert close(tp, 0.0 + eloss * rt), "Check Converter peak temperature"


#
# LinReg
#
@pytest.fixture()
def linreg(name, vo, vdrop, ig, iis, rt, active_phases):
    """Return a LinReg object."""
    return LinReg(name, vo=vo, vdrop=vdrop, ig=ig, iis=iis, rt=rt)


@pytest.mark.parametrize(
    "name, vo, vdrop, ig, iis, rt, active_phases",
    [
        ("No phase", 12.0, 1.2, 1e-5, 1e-6, 11.9, []),
        ("On-phase", -15, 0.88, 1.7e-4, 2e-5, 130.0, ["Apple", "Orange"]),
        ("Off-phase", 150, 0.67, 1e-3, 1.2e-4, 34.5, ["Pear"]),
    ],
)
def test_linreg(linreg, name, vo, vdrop, ig, iis, rt, active_phases):
    """Test LinReg object with different parameters"""
    assert linreg._params["name"] == name

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            if ict[0] == 0.0 or vo == 0.0 or s:
                ii = 0.0
            elif active_phases == []:
                ii = ict[2] + ig
            elif ict[3] in active_phases:
                ii = ict[2] + ig
            elif ict[3] not in active_phases:
                ii = iis
            assert close(
                linreg._solv_inp_curr(
                    [ict[0]], ict[1], ict[2], ict[3], active_phases, state
                ),
                ii,
            ), "Check LinReg input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            v = min(abs(vo), max(abs(ovt[0]) - vdrop, 0.0))
            phase_off = False
            if ovt[0] == 0.0 or vo == 0.0 or s:
                v = 0.0
            elif active_phases != []:
                if ovt[3] not in active_phases:
                    v = 0.0
                    phase_off = True
            vs, vstate = linreg._solv_outp_volt(
                [ovt[0]], ovt[1], ovt[2], ovt[3], active_phases, state
            )
            assert close(vs, v * np.sign(vo)), "Check LinReg output voltage"
            if ovt[0] == 0.0 or phase_off:
                assert vstate["off"] == [True], "Check LinReg state"
            else:
                assert vstate["off"] == [s], "Check LinReg state"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, eff, tr, tp = linreg._solv_pwr_loss(
            plt[0], vo, plt[2], plt[3], 125.0, plt[4], active_phases
        )
        ipwr = abs(plt[0] * plt[2])
        v = min(
            abs(linreg._params["vo"]),
            max(abs(plt[0]) - linreg._params["vdrop"], 0.0),
        )
        eloss = abs(ig * plt[0]) + (abs(plt[0]) - abs(v)) * plt[3]
        if active_phases != []:
            if plt[4] not in active_phases:
                ipwr = abs(iis * plt[0])
                eloss = abs(iis * plt[0])
        assert close(loss, eloss), "Check LinReg loss"
        assert close(pwr, ipwr), "Check LinReg power"
        if ipwr == 0.0 or v == 0.0:
            eeff = 0.0
        opwr = ipwr - eloss
        if ipwr == 0.0:
            eeff = 0.0
        else:
            eeff = 100.0 * abs(opwr / ipwr)
        assert close(eff, eeff), "Check LinReg efficiency"
        assert close(tr, eloss * rt), "Check LinReg temperature rise"
        if eloss * rt > 0.0:
            assert close(tp, 125.0 + eloss * rt), "Check LinReg peak temperature"


#
# PSwitch
#
@pytest.fixture()
def pswitch(name, rs, ig, iis, rt, active_phases):
    """Return a PSwitch object."""
    return PSwitch(name, rs=rs, ig=ig, iis=iis, rt=rt)


@pytest.mark.parametrize(
    "name, rs, ig, iis, rt, active_phases",
    [
        ("No phase", 1.2, 1e-5, 1e-6, 11.9, []),
        ("On-phase", 0.88, 1.7e-4, 2e-5, 130.0, ["Apple", "Orange"]),
        ("Off-phase", 0.67, 1e-3, 1.2e-4, 34.5, ["Pear"]),
    ],
)
def test_pswitch(pswitch, name, rs, ig, iis, rt, active_phases):
    """Test PSwitch object with different parameters"""
    assert pswitch._params["name"] == name

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            if ict[0] == 0.0 or s:
                ii = 0.0
            elif active_phases == []:
                ii = ict[2] + ig
            elif ict[3] in active_phases:
                ii = ict[2] + ig
            elif ict[3] not in active_phases:
                ii = iis
            assert close(
                pswitch._solv_inp_curr(
                    [ict[0]], ict[1], ict[2], ict[3], active_phases, state
                ),
                ii,
            ), "Check PSwitch input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            if ovt[0] >= 0.0:
                v = ovt[0] - rs * ovt[2]
            else:
                v = ovt[0] + rs * ovt[2]
            phase_off = False
            if ovt[0] == 0.0 or s:
                v = 0.0
            elif active_phases != []:
                if ovt[3] not in active_phases:
                    v = 0.0
                    phase_off = True
            vs, vstate = pswitch._solv_outp_volt(
                [ovt[0]], ovt[1], ovt[2], ovt[3], active_phases, state
            )
            assert close(vs, v), "Check PSwitch output voltage"
            if ovt[0] == 0.0 or phase_off:
                assert vstate["off"] == [True], "Check PSwitch state"
            else:
                assert vstate["off"] == [s], "Check PSwitch state"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, eff, tr, tp = pswitch._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], 125.0, plt[4], active_phases
        )
        ipwr = abs(plt[0] * plt[2])
        if plt[0] >= 0.0:
            v = plt[0] - rs * ovt[2]
        else:
            v = plt[0] + rs * ovt[2]
        eloss = abs(ig * plt[0]) + (abs(plt[0]) - abs(plt[1])) * plt[3]
        if active_phases != []:
            if plt[4] not in active_phases:
                eloss = abs(iis * plt[0])
                ipwr = abs(iis * plt[0])
        assert close(pwr, ipwr), "Check PSwitch power"
        assert close(loss, eloss), "Check PSwitch loss"
        if ipwr == 0.0 or v == 0.0:
            eeff = 0.0
        opwr = ipwr - eloss
        if ipwr == 0.0:
            eeff = 0.0
        else:
            eeff = 100.0 * abs(opwr / ipwr)
        assert close(eff, eeff), "Check PSwitch efficiency"
        assert close(tr, eloss * rt), "Check PSwitch temperature rise"
        if eloss * rt > 0.0:
            assert close(tp, 125.0 + eloss * rt), "Check PSwitch peak temperature"


#
# PMux
#
# [vi, vo, io, phase]
PMUX_CURR_TESTS = [
    [[0.0], 0.0, 1.0, ""],
    [[-0.0], -0.0, 1.0, ""],
    [[-100, 23], -90, 3.14, "Apple"],
    [[10, 12, 15], 5, 0.0, ""],
    [[3.3, 3.7, 5.0, 6.0], 3.0, 1e-3, ""],
    [[-24, -12, -10, -18], -15, 0.0, "Apple"],
]
# [vi, ii, io, phase]
PMUX_VOLT_TESTS = [
    [[0.0], 10, 10, ""],
    [[-0.0], 0, 0, ""],
    [[-15, 12], 0.7, 0.7, ""],
    [[20, 24], 2.1, 2.0, "Apple"],
    [[4.7, 5.6, 6.7], 0.0, 0.0, ""],
    [[-5, 3.7, 2.1], 0.0, 0.0, "Apple"],
    [[4.7, 5.6, 6.7, 8.8], 0.0, 0.0, ""],
    [[-5, 3.7, 2.1, -33], 0.0, 0.0, "Apple"],
]


@pytest.fixture()
def pmux(name, rs, ig, iis, rt, active_phases):
    """Return a PMux object."""
    return PMux(name, rs=rs, ig=ig, iis=iis, rt=rt)


@pytest.mark.parametrize(
    "name, rs, ig, iis, rt, active_phases",
    [
        ("No phase", 1.2, 1e-5, 1e-6, 11.9, []),
        ("On-phase", [0.88, 0.32, 0.4, 0.5], 1.7e-4, 2e-5, 130.0, ["Apple", "Orange"]),
        ("Off-phase", 0.67, 1e-3, 1.2e-4, 34.5, ["Pear"]),
    ],
)
def test_pmux(pmux, name, rs, ig, iis, rt, active_phases):
    """Test PMux object with different parameters"""
    assert pmux._params["name"] == name

    state = {}
    for ict in PMUX_CURR_TESTS:
        inum = len(ict[0])
        for s in range(0, inum + 1, 1):
            state["off"] = [False for i in range(inum)]
            state["off"][:s] = [True for i in range(0, s, 1)]
            pinp = pmux._get_pri_inp(state, ict[0])

            if pinp == -1:
                ii = 0.0
            elif active_phases == []:
                ii = ict[2] + ig
            elif ict[3] in active_phases:
                ii = ict[2] + ig
            elif ict[3] not in active_phases:
                ii = iis
            assert close(
                pmux._solv_inp_curr(
                    ict[0], ict[1], ict[2], ict[3], active_phases, state
                ),
                ii,
            ), "Check PMux input current"

    if not isinstance(rs, list):
        r = [rs for i in range(inum)]
    else:
        r = rs

    for ovt in PMUX_VOLT_TESTS:
        inum = len(ovt[0])
        for s in range(0, inum + 1, 1):
            state["off"] = [False for i in range(inum)]
            state["off"][:s] = [True for i in range(0, s, 1)]
            pinp = pmux._get_pri_inp(state, ovt[0])

            if pinp == -1:
                v = 0.0
            elif ovt[0][pinp] >= 0.0:
                v = ovt[0][pinp] - r[pinp] * ovt[2]
            else:
                v = ovt[0][pinp] + r[pinp] * ovt[2]
            phase_off = False
            if active_phases != []:
                if ovt[3] not in active_phases:
                    v = 0.0
                    phase_off = True
            vs, vstate = pmux._solv_outp_volt(
                ovt[0], ovt[1], ovt[2], ovt[3], active_phases, state
            )
            assert close(vs, v), "Check PMux output voltage"
            ov = 0.0
            if pinp != -1:
                ov = ovt[0][pinp]
            if abs(ov) == 0.0 or phase_off or pinp == -1:
                assert vstate["off"] == [True], "Check PMux state"
            else:
                assert vstate["off"] == [False], "Check PMux state"
    for plt in PWR_LOSS_TESTS:
        for s in range(4):
            state["off"] = [False for i in range(s)]
            state["off"][:s] = [True for i in range(0, s, 1)]
            pinp = pmux._get_pri_inp(state, [plt[0] for i in range(s)])

            pwr, loss, eff, tr, tp = pmux._solv_pwr_loss(
                plt[0], plt[1], plt[2], plt[3], 125.0, plt[4], active_phases
            )
            ipwr = abs(plt[0] * plt[2])
            if plt[0] >= 0.0:
                v = plt[0] - r[pinp] * ovt[2]
            else:
                v = plt[0] + r[pinp] * ovt[2]
            eloss = abs(ig * plt[0]) + (abs(plt[0]) - abs(plt[1])) * plt[3]
            if active_phases != []:
                if plt[4] not in active_phases:
                    eloss = abs(iis * plt[0])
                    ipwr = abs(iis * plt[0])
            assert close(pwr, ipwr), "Check PMux power"
            assert close(loss, eloss), "Check PMux loss"
            if ipwr == 0.0 or v == 0.0:
                eeff = 0.0
            opwr = ipwr - eloss
            if ipwr == 0.0:
                eeff = 0.0
            else:
                eeff = 100.0 * abs(opwr / ipwr)
            assert close(eff, eeff), "Check PMux efficiency"
            assert close(tr, eloss * rt), "Check PMux temperature rise"
            if eloss * rt > 0.0:
                assert close(tp, 125.0 + eloss * rt), "Check PMux peak temperature"


#
# Rectifier - Diode mode
#
@pytest.fixture()
def rectifier_d(name, vdrop, rt):
    """Return a Rectifier object."""
    return Rectifier(
        name,
        vdrop=vdrop,
        rs=random.uniform(0.0, 4.3),
        ig=random.uniform(0.0, 1.2e-3),
        iq=random.uniform(0.0, 1.5e-4),
        rt=rt,
    )


@pytest.mark.parametrize(
    "name, vdrop, rt",
    [("V pos", 5.0, 10.0), ("V neg", -1.77, 1.0), ("V almost zero", 0.1, 5.0)],
)
def test_rectifier_d(rectifier_d, name, vdrop, rt):
    """Test Rectifier(d) object with different parameters"""
    assert rectifier_d._params["name"] == name, "Check Rectifier(d) name"
    assert rectifier_d._params["type"] == "diode", "Check Rectifier(d) type"

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            ii = 0.0 if ict[0] == 0.0 or s else ict[2]
            assert close(
                rectifier_d._solv_inp_curr([ict[0]], ict[1], ict[2], ict[3], {}, state),
                ii,
            ), "Check Rectifier(d) input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            v = 0.0 if ovt[0] == 0.0 else ovt[0] - 2 * abs(vdrop) * np.sign(ovt[0])
            if np.sign(v) != np.sign(ovt[0]) or s:
                v = 0.0
            if ovt[0] == 4.7 and name == "V pos" and not s:
                with pytest.raises(ValueError):
                    rectifier_d._solv_outp_volt(
                        [ovt[0]], ovt[1], ovt[2], ovt[3], {}, state
                    )
            else:
                vs, vstate = rectifier_d._solv_outp_volt(
                    [ovt[0]], ovt[1], ovt[2], ovt[3], {}, state
                )
                assert close(vs, abs(v)), "Check Rectifier(d) output voltage"
                if ovt[0] == 0.0:
                    assert vstate["off"] == [True], "Check Rectifier(d) state"
                else:
                    assert vstate["off"] == [s], "Check Rectifier(d) state"
    for plt in PWR_LOSS_TESTS:
        pwr, los, eff, tr, tp = rectifier_d._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], 85.0, plt[4], {}
        )
        vo = plt[0] - 2 * abs(vdrop) * np.sign(plt[0])
        valid = True if np.sign(vo) == np.sign(plt[0]) else False
        epwr = abs(plt[0] * plt[2]) if valid else 0.0
        assert close(pwr, epwr), "Check Rectifier(d) power"
        eloss = 0.0 if plt[0] == 0.0 or not valid else abs(plt[0] - vo) * plt[3]
        assert close(los, eloss), "Check Rectifier(d) loss"
        ef = 0.0
        if epwr > 0.0:
            ef = 100.0 * abs((epwr - eloss) / epwr)
        if not valid:
            ef = 0.0
        assert close(eff, ef), "Check Rectifier(d) efficiency"
        assert close(tr, los * rt), "Check Rectifier(d) temperature rise"
        if los * rt > 0.0:
            assert close(tp, 85.0 + los * rt), "Check Rectifier(d) peak temperature"


#
# Rectifier - mosfet mode
#
@pytest.fixture()
def rectifier_m(name, rs, ig, iq, rt):
    """Return a Rectifier(m) object."""
    return Rectifier(name, vdrop=0.0, rs=rs, ig=ig, iq=iq, rt=rt)


@pytest.mark.parametrize(
    "name, rs, ig, iq, rt",
    [
        ("One", 0.012, 1e-5, 1e-6, 11.9),
        ("Two", 0.88, 1.7e-4, 2e-5, 130.0),
        ("Three", 0.67, 1e-3, 1.2e-4, 34.5),
    ],
)
def test_rectifier_m(rectifier_m, name, rs, ig, iq, rt):
    """Test Rectifier(m) object with different parameters"""
    assert rectifier_m._params["name"] == name, "Check Rectifier(m) name"
    assert rectifier_m._params["type"] == "mosfet", "Check Rectifier(m) type"

    state = {}
    for ict in INP_CURR_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            if ict[0] == 0.0 or s:
                ii = 0.0
            elif ict[2] == 0.0:
                ii = iq
            else:
                ii = ict[2] + ig
            assert close(
                rectifier_m._solv_inp_curr([ict[0]], ict[1], ict[2], ict[3], {}, state),
                ii,
            ), "Check Rectifier(m) input current"
    for ovt in OUTP_VOLT_TESTS:
        for s in VINOFF_STATES:
            state["off"] = [s]
            if ovt[0] >= 0.0:
                v = ovt[0] - 2 * rs * ovt[2]
            else:
                v = ovt[0] + 2 * rs * ovt[2]
            if ovt[0] == 0.0 or s:
                v = 0.0
            vs, vstate = rectifier_m._solv_outp_volt(
                [ovt[0]], ovt[1], ovt[2], ovt[3], {}, state
            )
            assert close(vs, abs(v)), "Check Rectifier(m) output voltage"
            if ovt[0] == 0.0 or s:
                assert vstate["off"] == [True], "Check Rectifier(m) state"
            else:
                assert vstate["off"] == [s], "Check Rectifier(m) state"
    for plt in PWR_LOSS_TESTS:
        pwr, loss, eff, tr, tp = rectifier_m._solv_pwr_loss(
            plt[0], plt[1], plt[2], plt[3], 125.0, plt[4], {}
        )
        ipwr = abs(plt[0] * plt[2])
        if plt[0] >= 0.0:
            v = plt[0] - 2 * rs * ovt[2]
        else:
            v = plt[0] + 2 * rs * ovt[2]
        if plt[0] == 0.0:
            eloss = 0.0
        elif plt[3] == 0.0:
            eloss = abs(iq * plt[0])
        else:
            eloss = abs(ig * plt[0]) + 2 * rs * plt[3] ** 2
        assert close(pwr, ipwr), "Check Rectifier(m) power"
        assert close(loss, eloss), "Check Rectifier(m) loss"
        if ipwr == 0.0 or v == 0.0:
            eeff = 0.0
        opwr = ipwr - eloss
        if ipwr == 0.0:
            eeff = 0.0
        else:
            eeff = 100.0 * abs(opwr / ipwr)
        assert close(eff, eeff), "Check Rectifier(m) efficiency"
        assert close(tr, eloss * rt), "Check Rectifier(m) temperature rise"
        if eloss * rt > 0.0:
            assert close(tp, 125.0 + eloss * rt), "Check Rectifier(m) peak temperature"
