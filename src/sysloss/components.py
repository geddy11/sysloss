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

"""Components that can be added to the system.

Constants
---------
LIMITS_DEFAULT = {
    | "vi": [0.0, 1.0e6], # input voltage (V)
    | "vo": [0.0, 1.0e6], # output voltage (V)
    | "vd": [0.0, 1.0e6], # voltage difference, vi-vo (V)
    | "ii": [0.0, 1.0e6], # input current (A)
    | "io": [0.0, 1.0e6], # output current (A)
    | "pi": [0.0, 1.0e6], # input power (W)
    | "po": [0.0, 1.0e6], # output power (W)
    | "pl": [0.0, 1.0e6], # power loss (W)
    | "tr": [0.0, 1.0e6], # temperature rise (°C)
    | "tp": [-1.0e6, 1.0e6]} # peak temperature (°C)
"""

from enum import Enum, unique
import toml
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from warnings import warn

__all__ = [
    "Source",
    "ILoad",
    "PLoad",
    "RLoad",
    "RLoss",
    "VLoss",
    "Converter",
    "LinReg",
    "PSwitch",
    "PMux",
    "Rectifier",
]


@unique
class _ComponentTypes(Enum):
    """Component types"""

    SOURCE = 1
    LOAD = 2
    SLOSS = 3
    CONVERTER = 4
    LINREG = 5
    PSWITCH = 6
    PMUX = 7
    RECTIFIER = 8


MAX_DEFAULT = 1.0e6
IQ_DEFAULT = 0.0
IG_DEFAULT = 0.0
IIS_DEFAULT = 0.0
RS_DEFAULT = 0.0
RT_DEFAULT = 0.0
VDROP_DEFAULT = 0.0
PWRS_DEFAULT = 0.0
LIMITS_DEFAULT = {
    "vi": [0.0, MAX_DEFAULT],  # input voltage (V)
    "vo": [0.0, MAX_DEFAULT],  # output voltage (V)
    "vd": [0.0, MAX_DEFAULT],  # voltage difference, vi-vo (V)
    "ii": [0.0, MAX_DEFAULT],  # input current (A)
    "io": [0.0, MAX_DEFAULT],  # output current (A)
    "pi": [0.0, MAX_DEFAULT],  # input power (W)
    "po": [0.0, MAX_DEFAULT],  # output power (W)
    "pl": [0.0, MAX_DEFAULT],  # power loss (W)
    "tr": [0.0, MAX_DEFAULT],  # temperature rise (°C)
    "tp": [-MAX_DEFAULT, MAX_DEFAULT],  # peak temperature (°C)
}
STATE_DEFAULT = {"off": [False]}
STATE_OFF = {"off": [True]}


def _get_opt(params, key, default):
    """Get optional parameter from dict"""
    if key in params:
        return params[key]
    return default


def _get_lopt(params, key, idx, default):
    """Get optional parameter from dict"""
    if key in params:
        return params[key][idx]
    return default


def _get_mand(params, key):
    """Get mandatory parameter from dict"""
    if key in params:
        return params[key]
    raise KeyError("Parameter dict is missing entry for '{}'".format(key))


def _get_warns(limits, checks):
    """Check parameter values against limits"""
    warn = ""
    keys = list(checks.keys())
    for key in keys:
        lim = _get_opt(limits, key, LIMITS_DEFAULT[key])
        if key == "tp":
            if checks[key] > lim[1] or checks[key] < lim[0]:
                warn += key + " "
        else:
            if abs(checks[key]) > abs(lim[1]) or abs(checks[key]) < abs(lim[0]):
                warn += key + " "
    return warn.strip()


def _get_eff(ipwr, opwr, def_eff=100.0):
    """Calculate efficiency in %"""
    if ipwr > 0.0:
        return 100.0 * abs(opwr / ipwr)
    return def_eff


def _calc_inp_current(vo, i, pstate, psidx):
    """Calculate input current from vo and state vector"""
    if abs(vo) == 0.0 or _get_lopt(pstate, "off", psidx, False):
        return 0.0
    return i


def _check_limits(limits: dict):
    """Check that limits are valid format"""
    for key in LIMITS_DEFAULT:
        if key in limits:
            if type(limits[key]) is not list:
                raise ValueError('"{}" value is not a list!'.format(key))
            else:
                if len(limits[key]) != 2 or not (
                    all(isinstance(item, (int, float)) for item in limits[key])
                ):
                    raise ValueError(
                        '"{}" value is not a list of two numbers!'.format(key)
                    )
    return limits


def _check_interp(idata: dict, z: str):
    """Check interpolation data format"""
    keys = idata.keys()
    if not "vi" in keys or not "io" in keys or not z in keys:
        raise ValueError("interpolation data must contain vi, io and " + z)
    if not np.all(np.diff(idata["io"]) > 0):
        raise ValueError("io values must be monotonic increasing")
    vsh = np.array(idata["vi"]).shape
    ish = np.array(idata["io"]).shape
    zsh = np.array(idata[z]).shape
    if vsh[0] != zsh[0] or ish[0] != zsh[1]:
        raise ValueError("dimensions of interpolation data do not match")


class _Interp0d:
    """Dummy interpolator for constant"""

    def __init__(self, x: float):
        self._x = x

    def _interp(self, x: float, y: float) -> float:
        """Return constant"""
        return self._x


class _Interp1d:
    """1D interpolator, x must be monotonic rising"""

    def __init__(self, x, fx):
        self._x = np.abs(np.asarray(x))
        self._fx = np.abs(np.asarray(fx))

    def _interp(self, x: float, y: float) -> float:
        """1D interpolation"""
        return np.interp(np.abs(x), self._x, self._fx)


class _Interp2d:
    """2D interpolator"""

    def __init__(self, x, y, fxy):
        self._x = np.abs(x)
        self._y = np.abs(y)
        self._fxy = np.abs(fxy)
        self._xmin = min(self._x)
        self._xmax = max(self._x)
        self._ymin = min(self._y)
        self._ymax = max(self._y)
        self._intp = LinearNDInterpolator(list(zip(self._x, self._y)), self._fxy)

    def _interp(self, x: float, y: float) -> float:
        """2D interpolation"""
        fxy = self._intp([x], [y])[0]
        if not np.isnan(fxy):
            return fxy
        if x < self._xmin:
            if y < self._ymin:
                return self._intp([self._xmin], [self._ymin])[0]
            if y > self._ymax:
                return self._intp([self._xmin], [self._ymax])[0]
            return self._intp([self._xmin], [y])[0]
        if x > self._xmax:
            if y < self._ymin:
                return self._intp([self._xmax], [self._ymin])[0]
            if y > self._ymax:
                return self._intp([self._xmax], [self._ymax])[0]
            return self._intp([self._xmax], [y])[0]
        if y < self._ymin:
            return self._intp([x], [self._ymin])[0]
        return self._intp([x], [self._ymax])[0]


class _ComponentMeta(type):
    """An component metaclass that will be used for component class creation."""

    def __instancecheck__(cls, instance):
        return cls.__subclasscheck__(type(instance))

    def __subclasscheck__(cls, subclass):
        return (
            hasattr(subclass, "_component_type")
            and hasattr(subclass, "_child_types")
            and hasattr(subclass, "from_file")
            and callable(subclass.from_file)
        )


class _ComponentInterface(metaclass=_ComponentMeta):
    """This interface is used for concrete component classes to inherit from.
    There is no need to define the ComponentMeta methods of any class
    as they are implicitly made available via .__subclasscheck__().
    """

    pass


class _Component:
    """Generic component"""

    @property
    def _component_type(self):
        """Defines the component type"""
        return None

    @property
    def _child_types(self):
        """Defines allowable child component types"""
        et = list(_ComponentTypes)
        return et

    _cparams = {
        "name": "component",
        "params": {"p": {"typ": [float], "opt": True, "def": 1.0e6}},
    }

    def __init__(self, name: str):
        self._params = {}
        self._params["name"] = name
        self._limits = LIMITS_DEFAULT
        self._ipr = None

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read component parameters from .toml file.

        Parameters
        ----------
        name : str
            Component name
        fname : str
            File name.

        Raises
        ------
        ValueError
            If parameter value is not of the correct type.

        """
        with open(fname, "r") as f:
            config = toml.load(f)

        fparams = {}
        for key in cls._cparams["params"]:
            if cls._cparams["params"][key]["opt"]:
                pval = _get_opt(
                    config[cls._cparams["name"]],
                    key,
                    cls._cparams["params"][key]["def"],
                )
            else:
                pval = _get_mand(config[cls._cparams["name"]], key)
            if type(pval) not in cls._cparams["params"][key]["typ"]:
                raise ValueError("Parameter {} is not of the correct type".format(key))
            fparams[key] = pval

        fparams["limits"] = _get_opt(config, "limits", LIMITS_DEFAULT)
        return cls(name, **fparams)

    def _get_pri_inp(self, pstate, v):
        """Determine which input is prioritized"""
        return 0

    def _get_inp_current(self, phase, phase_conf={}):
        """Get initial current value for solver"""
        return 0.0

    def _get_outp_voltage(self, phase, phase_conf={}):
        """Get initial voltage value for solver"""
        return 0.0

    def _get_state(self, phase, phase_conf={}):
        """Get initial state value for solver"""
        return STATE_DEFAULT

    def _get_annot(self):
        """Get interpolation figure annotations in format [xlabel, ylabel, title]"""
        return ["xlabel", "ylabel", "title"]

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        for param in pdict:
            if param in self._params:
                if isinstance(self._params[param], dict):
                    ret[param] = "interp"
                else:
                    ret[param] = self._params[param]
        return ret

    def _get_limits(self):
        """Get list of applicable limits"""
        lims = []
        for key in LIMITS_DEFAULT:
            lims += [key]
        return lims

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf):
        """Check for warnings"""
        if self._component_type not in [_ComponentTypes.SOURCE, _ComponentTypes.SLOSS]:
            if phase_conf:
                if phase not in phase_conf:
                    return ""
        pi, pl, _, tr, tp = self._solv_pwr_loss(vi, vo, ii, io, ta, phase, phase_conf)
        all_lims = {
            "vi": vi,
            "vo": vo,
            "vd": abs(vi) - abs(vo),
            "ii": ii,
            "io": io,
            "pi": pi,
            "po": pi - pl,
            "pl": pl,
            "tr": tr,
            "tp": tp,
        }
        lims = {}
        for lim in self._get_limits():
            lims[lim] = all_lims[lim]
        return _get_warns(self._limits, lims)


class Source(_Component):
    """Voltage source.

    The Source component must be the root of a system or subsystem.

    Parameters
    ----------
    name : str
        Source name.
    vo : float
        Output voltage (V).
    rs : float, optional
        Source resistance (Ohm), by default 0.0
    limits : dict, optional
        Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: io, po, pl.

    Raises
    ------
    ValueError
        If a limits value is not of the correct format.

    """

    @property
    def _component_type(self):
        """Defines the Source component type"""
        return _ComponentTypes.SOURCE

    @property
    def _child_types(self):
        """Defines allowable Source child component types"""
        et = list(_ComponentTypes)
        et.remove(_ComponentTypes.SOURCE)
        return et

    _cparams = {
        "name": "source",
        "params": {
            "vo": {"typ": [int, float], "opt": False},
            "rs": {"typ": [int, float], "opt": True, "def": RS_DEFAULT},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        vo: float,
        rs: float = 0.0,
        limits: dict = LIMITS_DEFAULT,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["vo"] = vo
        self._params["rs"] = abs(rs)
        self._params["rt"] = 0.0
        self._limits = _check_limits(limits)
        self._ipr = None

    def _get_state(self, phase, phase_conf={}):
        """Get initial state value for solver"""
        if abs(self._params["vo"]) == 0.0:
            return STATE_OFF
        if phase_conf and phase not in phase_conf:
            return STATE_OFF
        return STATE_DEFAULT

    def _get_outp_voltage(self, phase, phase_conf={}):
        """Get initial voltage value for solver"""
        if phase_conf and phase not in phase_conf:
            return 0.0
        return self._params["vo"]

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        """Calculate Source input current from vi, vo and io"""
        if phase_conf and phase not in phase_conf:
            return 0.0
        return _calc_inp_current(self._params["vo"], io, pstate, 0)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}, pstate={}):
        """Calculate Source output voltage from vi, ii and io"""
        if phase_conf and phase not in phase_conf:
            return 0.0, STATE_OFF
        if self._params["vo"] == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, STATE_OFF
        vo = self._params["vo"] - self._params["rs"] * io
        return vo, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf={}, pstate={}):
        """Calculate power and loss in Source"""
        if phase_conf and phase not in phase_conf:
            return 0.0, 0.0, 100.0, 0.0, 0.0
        if self._params["vo"] == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, 0.0, 100.0, 0.0, 0.0
        ipwr = abs(self._params["vo"] * io)
        loss = self._params["rs"] * io * io
        opwr = ipwr - loss
        return ipwr, loss, _get_eff(ipwr, opwr), 0.0, 0.0

    def _get_limits(self):
        """Applicable limits"""
        return ["io", "po", "pl"]


class PLoad(_Component):
    """Power load.

    A power load represents a constant power sink, referenced to 0V. Other components can not be connected to a PLoad.
    The load can optionally be configured as a loss.

    Parameters
    ----------
    name : str
        Load name.
    pwr : float
        Load power (W).
    limits : dict, optional
         Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, ii, tr, tp
    pwrs : float, optional
        Load sleep power (W), by default 0.0.
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.
    loss: bool, optional
        Count power as a loss, by default False

    Raises
    ------
    ValueError
        If a limits value is not of the correct format.

    """

    @property
    def _component_type(self):
        """Defines the Load component type"""
        return _ComponentTypes.LOAD

    @property
    def _child_types(self):
        """The Load component cannot have childs"""
        return [None]

    _cparams = {
        "name": "pload",
        "params": {
            "pwr": {"typ": [int, float], "opt": False},
            "pwrs": {"typ": [int, float], "opt": True, "def": PWRS_DEFAULT},
            "rt": {"typ": [int, float], "opt": True, "def": RT_DEFAULT},
            "loss": {"typ": [bool], "opt": True, "def": False},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        pwr: float,
        limits: dict = LIMITS_DEFAULT,
        pwrs: float = 0.0,
        rt: float = 0.0,
        loss: bool = False,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["pwr"] = abs(pwr)
        self._params["pwrs"] = abs(pwrs)
        self._params["rt"] = abs(rt)
        self._limits = _check_limits(limits)
        self._ipr = None
        self._params["loss"] = loss

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        """Calculate Load input current from vi, vo and io"""
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0
        if not phase_conf:
            p = self._params["pwr"]
        elif phase not in phase_conf:
            p = self._params["pwrs"]
        else:
            p = phase_conf[phase]

        return p / abs(vi[0])

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}, pstate={}):
        """Load output voltage is always 0"""
        if _get_lopt(pstate, "off", 0, False):
            return 0.0, STATE_OFF
        return 0.0, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf={}, pstate={}):
        """Calculate power and loss in Load"""
        if abs(vi) == 0.0 or _get_lopt(pstate, "off", 0, False):
            if self._params["loss"]:
                return 0.0, 0.0, 0.0, 0.0, 0.0
            else:
                return 0.0, 0.0, 100.0, 0.0, 0.0
        pi = abs(vi * ii)
        tr = pi * self._params["rt"]
        if self._params["loss"]:
            return 0.0, pi, 0.0, tr, tr + ta
        else:
            return pi, 0.0, 100.0, tr, tr + ta

    def _get_limits(self):
        """Applicable limits"""
        return ["vi", "ii", "tr", "tp"]


class ILoad(PLoad):
    """Current load.

    A current load represents a constant current sink, referenced to 0V. Other components can not be connected to an ILoad.
    The load can optionally be configured as a loss.

    Parameters
    ----------
    name : str
        Load name.
    ii : float
        Load current (A).
    limits : dict, optional
         Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, pi, tr, tp
    iis : float, optional
        Load sleep current (A), by default 0.0.
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.
    loss: bool, optional
        Count power as a loss, by default False

    Raises
    ------
    ValueError
        If a limits value is not of the correct format.

    """

    _cparams = {
        "name": "iload",
        "params": {
            "ii": {"typ": [int, float], "opt": False},
            "iis": {"typ": [int, float], "opt": True, "def": IIS_DEFAULT},
            "rt": {"typ": [int, float], "opt": True, "def": RT_DEFAULT},
            "loss": {"typ": [bool], "opt": True, "def": False},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        ii: float,
        limits: dict = LIMITS_DEFAULT,
        iis: float = 0.0,
        rt: float = 0.0,
        loss: bool = False,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["ii"] = abs(ii)
        self._limits = _check_limits(limits)
        self._params["iis"] = abs(iis)
        self._params["rt"] = abs(rt)
        self._ipr = None
        self._params["loss"] = loss

    def _get_inp_current(self, phase, phase_conf={}):
        """Get initial current value for solver"""
        return self._params["ii"]

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0
        if not phase_conf:
            i = self._params["ii"]
        elif phase not in phase_conf:
            i = self._params["iis"]
        else:
            i = phase_conf[phase]

        return abs(i)

    def _get_limits(self):
        """Applicable limits"""
        return ["vi", "pi", "tr", "tp"]


class RLoad(PLoad):
    """Resistive load.

    A resisitve load represents a constant resistance, referenced to 0V. Other components can not be connected to an RLoad.
    The load can optionally be configured as a loss.

    Parameters
    ----------
    name : str
        Load name.
    rs : float
        Load resistance (Ohm).
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.
    limits : dict, optional
         Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, ii, pi, tr, tp
    loss: bool, optional
        Count power as a loss, by default False

    Raises
    ------
    ValueError
        If rs==0.0 or a limits value is not of the correct format.

    """

    _cparams = {
        "name": "rload",
        "params": {
            "rs": {"typ": [int, float], "opt": False},
            "rt": {"typ": [int, float], "opt": True, "def": RT_DEFAULT},
            "loss": {"typ": [bool], "opt": True, "def": False},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        rs: float,
        rt: float = 0.0,
        limits: dict = LIMITS_DEFAULT,
        loss: bool = False,
    ):
        self._params = {}
        self._params["name"] = name
        if abs(rs) == 0.0:
            raise ValueError("rs must be > 0!")
        self._params["rs"] = abs(rs)
        self._params["rt"] = abs(rt)
        self._limits = _check_limits(limits)
        self._ipr = None
        self._params["loss"] = loss

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0
        r = self._params["rs"]
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            pass
        else:
            r = phase_conf[phase]
        return abs(vi[0]) / r

    def _get_limits(self):
        """Applicable limits"""
        return ["vi", "ii", "pi", "tr", "tp"]


class RLoss(_Component):
    """Resistive series loss.

    A series resisitve loss represents a constant resistance connected in series with other components.

    Parameters
    ----------
    name : str
        Loss name.
    rs : float
        Loss resistance (Ohm).
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.
    limits : dict, optional
         Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, vo, vd, ii, io, pi, po, pl, tr, tp

    Raises
    ------
    ValueError
        If a limits value is not of the correct format.

    """

    @property
    def _component_type(self):
        """Defines the Loss component type"""
        return _ComponentTypes.SLOSS

    @property
    def _child_types(self):
        """Defines allowable Loss child component types"""
        et = list(_ComponentTypes)
        et.remove(_ComponentTypes.SOURCE)
        return et

    _cparams = {
        "name": "rloss",
        "params": {
            "rs": {"typ": [int, float], "opt": False},
            "rt": {"typ": [int, float], "opt": True, "def": RT_DEFAULT},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        rs: float,
        rt: float = 0.0,
        limits: dict = LIMITS_DEFAULT,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["rs"] = abs(rs)
        self._params["rt"] = abs(rt)
        self._limits = _check_limits(limits)
        self._ipr = None

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        """Calculate RLoss input current from vi, vo and io"""
        return _calc_inp_current(vi[0], io, pstate, 0)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}, pstate={}):
        """Calculate RLoss output voltage from vi, ii and io"""
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, STATE_OFF
        vo = vi[0] - self._params["rs"] * io * np.sign(vi[0])
        if np.sign(vo) == np.sign(vi[0]):
            return vo, STATE_DEFAULT
        raise ValueError(
            "Unstable system: RLoss component '{}' has zero output voltage".format(
                self._params["name"]
            )
        )

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf={}, pstate={}):
        """Calculate power and loss in RLoss"""
        vout = vi - self._params["rs"] * io * np.sign(vi)
        if np.sign(vout) != np.sign(vi) or _get_lopt(pstate, "off", 0, False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        loss = abs(vi - vout) * io
        pwr = abs(vi * ii)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 100.0), tr, ta + tr


class VLoss(RLoss):
    """Voltage series loss.

    This voltage loss element is connected in series with other elements.
    The voltage drop can be either a constant (float) or interpolated.
    Interpolation data dict for voltage drop can be either 1D (function of output current only):

    ``vdrop= {"vi":[2.5], "io":[0.1, 0.5, 0.9], "vdrop":[[0.23, 0.41, 0.477]]}``

    Or 2D (function of input voltage and output current):

    ``vdrop = {"vi":[2.5, 5.0, 12.0], "io":[0.1, 0.5, 0.9], "vdrop":[[0.23, 0.34, 0.477], [0.27, 0.39, 0.51], [0.3, 0.41, 0.57]]}``

    Parameters
    ----------
    name : str
        Loss name.
    vdrop : float | dict
        Voltage drop (V), a constant value (float) or interpolation data (dict).
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.
    limits : dict, optional
         Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, vo, vd, ii, io, pi, po, pl, tr, tp

    Raises
    ------
    ValueError
        If a limits value is not of the correct format.

    """

    @property
    def _component_type(self):
        """Defines the Loss component type"""
        return _ComponentTypes.SLOSS

    @property
    def _child_types(self):
        """Defines allowable Loss child component types"""
        et = list(_ComponentTypes)
        et.remove(_ComponentTypes.SOURCE)
        return et

    _cparams = {
        "name": "vloss",
        "params": {
            "vdrop": {"typ": [int, float, dict], "opt": False},
            "rt": {"typ": [int, float], "opt": True, "def": RT_DEFAULT},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        vdrop: float | dict,
        rt: float = 0.0,
        limits: dict = LIMITS_DEFAULT,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["rt"] = abs(rt)
        if isinstance(vdrop, dict):
            _check_interp(vdrop, "vdrop")
            if len(vdrop["vi"]) == 1:
                self._ipr = _Interp1d(vdrop["io"], vdrop["vdrop"][0])
            else:
                cur = []
                volt = []
                for v in vdrop["vi"]:
                    cur += vdrop["io"]
                    volt += len(vdrop["io"]) * [v]
                    vd = np.asarray(vdrop["vdrop"]).reshape(1, -1)[0].tolist()
                self._ipr = _Interp2d(cur, volt, vd)
            self._params["vdrop"] = vdrop
        else:
            self._params["vdrop"] = abs(vdrop)
            self._ipr = _Interp0d(abs(vdrop))
        self._limits = _check_limits(limits)

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        """Calculate VLoss input current from vi, vo and io"""
        return _calc_inp_current(vi[0], io, pstate, 0)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}, pstate={}):
        """Calculate Vloss output voltage from vi, ii and io"""
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, STATE_OFF
        vo = vi[0] - self._ipr._interp(abs(io), abs(vi[0])) * np.sign(vi[0])
        if np.sign(vo) == np.sign(vi[0]):
            return vo, STATE_DEFAULT
        raise ValueError(
            "Unstable system: VLoss component '{}' has zero output voltage".format(
                self._params["name"]
            )
        )

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf={}, pstate={}):
        """Calculate power and loss in VLoss"""
        vout = vi - self._ipr._interp(abs(io), abs(vi)) * np.sign(vi)
        if np.sign(vout) != np.sign(vi) or _get_lopt(pstate, "off", 0, False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        loss = abs(vi - vout) * io
        pwr = abs(vi * ii)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, ta + tr

    def _get_annot(self):
        """Get VLoss interpolation figure annotations in format [xlabel, ylabel, title]"""
        if isinstance(self._ipr, _Interp1d):
            return [
                "Output current (A)",
                "Voltage drop (V)",
                "{} voltage drop".format(self._params["name"]),
            ]
        return [
            "Output current (A)",
            "Input voltage (V)",
            "{} voltage drop".format(self._params["name"]),
        ]


class Converter(_Component):
    """Voltage converter.

    The converter efficiency can be either a constant (float) or interpolated.
    Interpolation data dict for efficiency can be either 1D (function of output current only):

    ``eff = {"vi":[3.3], "io":[0.1, 0.5, 0.9], "eff":[[0.55, 0.78, 0.92]]}``

    Or 2D (function of input voltage and output current):

    ``eff = {"vi":[3.3, 5.0, 12.0], "io":[0.1, 0.5, 0.9], "eff":[[0.55, 0.78, 0.92], [0.5, 0.74, 0.83], [0.4, 0.6, 0.766]]}``

    Parameters
    ----------
    name : str
        Converter name.
    vo : float
        Output voltage (V).
    eff : float | dict
        Converter efficiency, a constant value (float) or interpolation data (dict).
    iq : float, optional
        Quiescent (no-load) current (A), by default 0.0.
    limits : dict, optional
        Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, vo, ii, io, pi, po, pl, tr, tp
    iis : float, optional
        Sleep (shut-down) current (A), by default 0.0.
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.

    Raises
    ------
    ValueError
        If efficiency is 0.0 or > 1.0 or limit value has invalid format.

    """

    @property
    def _component_type(self):
        """Defines the Converter component type"""
        return _ComponentTypes.CONVERTER

    @property
    def _child_types(self):
        """Defines allowable Converter child component types"""
        et = list(_ComponentTypes)
        et.remove(_ComponentTypes.SOURCE)
        return et

    _cparams = {
        "name": "converter",
        "params": {
            "vo": {"typ": [int, float], "opt": False},
            "eff": {"typ": [float, dict], "opt": False},
            "iq": {"typ": [int, float], "opt": True, "def": IQ_DEFAULT},
            "iis": {"typ": [int, float], "opt": True, "def": IIS_DEFAULT},
            "rt": {"typ": [int, float], "opt": True, "def": RT_DEFAULT},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        vo: float,
        eff: float | dict,
        iq: float = 0.0,
        limits: dict = LIMITS_DEFAULT,
        iis: float = 0.0,
        rt: float = 0.0,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["vo"] = vo
        if isinstance(eff, dict):
            _check_interp(eff, "eff")
            if np.min(eff["eff"]) <= 0.0:
                raise ValueError("Efficiency values must be > 0.0")
            if np.max(eff["eff"]) > 1.0:
                raise ValueError("Efficiency values must be <= 1.0")
            if len(eff["vi"]) == 1:
                self._ipr = _Interp1d(eff["io"], eff["eff"][0])
            else:
                cur = []
                volt = []
                for v in eff["vi"]:
                    cur += eff["io"]
                    volt += len(eff["io"]) * [v]
                    ef = np.asarray(eff["eff"]).reshape(1, -1)[0].tolist()
                self._ipr = _Interp2d(cur, volt, ef)
        else:
            if not (eff > 0.0):
                raise ValueError("Efficiency must be > 0.0")
            if not (eff <= 1.0):
                raise ValueError("Efficiency must be <= 1.0")
            self._ipr = _Interp0d(eff)
        self._params["eff"] = eff
        self._params["iq"] = abs(iq)
        self._params["iis"] = abs(iis)
        self._params["rt"] = abs(rt)
        self._limits = _check_limits(limits)

    def _get_inp_current(self, phase, phase_conf=[]):
        """Get initial current value for solver"""
        i = self._params["iq"]
        if phase_conf and phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _get_outp_voltage(self, phase, phase_conf=[]):
        """Get initial voltage value for solver"""
        v = self._params["vo"]
        if phase_conf and phase not in phase_conf:
            v = 0.0
        return v

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf=[], pstate={}):
        """Calculate Converter input current from vi, vo and io"""
        if (
            abs(vi[0]) == 0.0
            or self._params["vo"] == 0.0
            or _get_lopt(pstate, "off", 0, False)
        ):
            return 0.0
        ve = vi[0] * self._ipr._interp(abs(io), abs(vi[0]))
        if phase_conf and phase not in phase_conf:
            return self._params["iis"]
        if io == 0.0:
            return self._params["iq"]
        return abs(self._params["vo"] * io / ve)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf=[], pstate={}):
        """Calculate Converter output voltage from vi, ii and io"""
        v = self._params["vo"]
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, STATE_OFF
        if phase_conf and phase not in phase_conf:
            return 0.0, STATE_OFF
        return v, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf=[], pstate={}):
        """Calculate power and loss in Converter"""
        if abs(vi) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        if io == 0.0:
            loss = abs(self._params["iq"] * vi)
        else:
            loss = abs(ii * vi * (1.0 - self._ipr._interp(abs(io), abs(vi))))
        pwr = abs(vi * ii)
        if phase_conf and phase not in phase_conf:
            loss = abs(self._params["iis"] * vi)
            pwr = abs(self._params["iis"] * vi)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, ta + tr

    def _get_annot(self):
        """Get Converter interpolation figure annotations in format [xlabel, ylabel, title]"""
        if isinstance(self._ipr, _Interp1d):
            return [
                "Output current (A)",
                "Efficiency",
                "{} efficiency for Vo={}V".format(
                    self._params["name"], self._params["vo"]
                ),
            ]
        return [
            "Output current (A)",
            "Input voltage (V)",
            "{} efficiency for Vo={}V".format(self._params["name"], self._params["vo"]),
        ]

    def _get_limits(self):
        """Applicable limits"""
        return ["vi", "vo", "ii", "io", "pi", "po", "pl", "tr", "tp"]


class LinReg(_Component):
    """Linear voltage regulator.

    If vi - vo < vdrop, the output voltage is reduced to vi - vdrop during analysis.

    The regulator ground current (ig) can be either a constant (float) or interpolated.
    Interpolation data dict for ground current can be either 1D (function of output current only):

    ``ig = {"vi":[5.0], "io":[0.0, 0.05, 0.1], "ig":[[2.0e-6, 0.5e-3, 0.85e-3]]}``

    Or 2D (function of input voltage and output current):

    ``ig = {"vi":[2.5, 5.0], "io":[0.0, 0.05, 0.1], "ig":[[1.2e-6, 0.34e-3, 0.64e-3], [2.0e-6, 0.5e-3, 0.85e-3]]}``

    Parameters
    ----------
    name : str
        Converter name.
    vo : float
        Output voltage (V).
    vdrop : float, optional
        Dropout voltage (V), by default 0.0.
    iq : float | dict, optional
        Ground current (A), by default 0.0. iq is deprecated and will be removed in a future version, use ig instead.
    ig : float | dict, optional
        Ground current (A), by default 0.0.
    limits : dict, optional
        Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, vo, vd, ii, io, pi, po, pl, tr, tp
    iis : float, optional
        Sleep (shut-down) current (A), by default 0.0.
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.

    Raises
    ------
    ValueError
        If vdrop > vo or limit value has invalid format.

    """

    @property
    def _component_type(self):
        """Defines the LinReg component type"""
        return _ComponentTypes.LINREG

    @property
    def _child_types(self):
        """Defines allowable LinReg child component types"""
        et = list(_ComponentTypes)
        et.remove(_ComponentTypes.SOURCE)
        return et

    def __init__(
        self,
        name: str,
        *,
        vo: float,
        vdrop: float = 0.0,
        iq: float = 0.0,
        ig: float = 0.0,
        limits: dict = LIMITS_DEFAULT,
        iis: float = 0.0,
        rt: float = 0.0,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["vo"] = vo
        if not (abs(vdrop) < abs(vo)):
            raise ValueError("Voltage drop must be < vo")
        self._params["vdrop"] = abs(vdrop)
        if iq != 0.0:
            warn(
                "The iq parameter is deprecated, and will be removed in a future version.",
                DeprecationWarning,
                stacklevel=2,
            )
            igc = iq
            if isinstance(igc, dict):
                igc["ig"] = igc.pop("iq")
        else:
            igc = ig
        if isinstance(igc, dict):
            _check_interp(igc, "ig")
            if np.min(igc["ig"]) < 0.0:
                raise ValueError("ig values must be >= 0.0")
            if len(igc["vi"]) == 1:
                self._ipr = _Interp1d(igc["io"], igc["ig"][0])
            else:
                cur = []
                volt = []
                for v in igc["vi"]:
                    cur += igc["io"]
                    volt += len(igc["io"]) * [v]
                    igi = np.asarray(igc["ig"]).reshape(1, -1)[0].tolist()
                self._ipr = _Interp2d(cur, volt, igi)
        else:
            self._ipr = _Interp0d(abs(igc))
        self._params["ig"] = igc
        self._params["iis"] = abs(iis)
        self._params["rt"] = abs(rt)
        self._limits = _check_limits(limits)

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read LinReg parameters from .toml file.

        Parameters
        ----------
        name : str
            LinReg name
        fname : str
            File name.
        """
        with open(fname, "r") as f:
            config = toml.load(f)

        v = _get_mand(config["linreg"], "vo")
        vd = _get_opt(config["linreg"], "vdrop", VDROP_DEFAULT)
        iq = _get_opt(config["linreg"], "iq", IQ_DEFAULT)
        if iq != 0.0:
            warn(
                "The iq parameter is deprecated, and will be removed in a future version.",
                DeprecationWarning,
                stacklevel=2,
            )
            ig = iq
            if isinstance(ig, dict):
                ig["ig"] = ig.pop("iq")
        else:
            ig = _get_opt(config["linreg"], "ig", IG_DEFAULT)
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        iis = _get_opt(config["linreg"], "iis", IIS_DEFAULT)
        rt = _get_opt(config["linreg"], "rt", RT_DEFAULT)
        return cls(name, vo=v, vdrop=vd, ig=ig, limits=lim, iis=iis, rt=rt)

    def _get_inp_current(self, phase, phase_conf=[]):
        """Get initial current value for solver"""
        i = self._ipr._interp(0.0, 0.0)
        if phase_conf and phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _get_outp_voltage(self, phase, phase_conf=[]):
        """Get initial voltage value for solver"""
        v = self._params["vo"]
        if phase_conf and phase not in phase_conf:
            v = 0.0
        return v

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf=[], pstate={}):
        """Calculate LinReg input current from vi, vo and io"""
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0
        i = io + self._ipr._interp(abs(io), abs(vi[0]))
        if phase_conf and phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf=[], pstate={}):
        """Calculate LinReg output voltage from vi, ii and io"""
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, STATE_OFF
        v = min(abs(self._params["vo"]), max(abs(vi[0]) - self._params["vdrop"], 0.0))
        if phase_conf and phase not in phase_conf:
            return 0.0, STATE_OFF
        if self._params["vo"] >= 0.0:
            return v, STATE_DEFAULT
        return -v, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf=[], pstate={}):
        """Calculate power and loss in LinReg"""
        if abs(vi) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        v = min(abs(self._params["vo"]), max(abs(vi) - self._params["vdrop"], 0.0))
        loss = self._ipr._interp(abs(io), abs(vi)) * abs(vi)
        if abs(io) > 0.0:
            loss += (abs(vi) - abs(v)) * io
        pwr = abs(vi * ii)
        if phase_conf and phase not in phase_conf:
            loss = abs(self._params["iis"] * vi)
            pwr = abs(self._params["iis"] * vi)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, tr + ta

    def _get_annot(self):
        """Get LinReg interpolation figure annotations in format [xlabel, ylabel, title]"""
        if isinstance(self._ipr, _Interp1d):
            return [
                "Output current (A)",
                "Ground current (A)",
                "{} ground current for Vo={}V".format(
                    self._params["name"], self._params["vo"]
                ),
            ]
        return [
            "Output current (A)",
            "Input voltage (V)",
            "{} ground current for Vo={}V".format(
                self._params["name"], self._params["vo"]
            ),
        ]


class PSwitch(_Component):
    """Power switch.

    The power switch ground current (ig) can be either a constant (float) or interpolated.
    Interpolation data dict for ground current can be either 1D (function of output current only):

    ``ig = {"vi":[3.6], "io":[0.005, 0.05, 0.5], "ig":[[36e-6, 37e-6, 35e-6]]}``

    Or 2D (function of input voltage and output current):

    ``ig = {"vi":[0.9, 1.8, 3.6], "io":[0.005, 0.05, 0.5], "ig":[[5e-6, 5e-6, 5e-6], [7e-6, 7e-6, 7e-6], [36e-6, 37e-6, 35e-6]]}``

    Parameters
    ----------
    name : str
        Power switch name.
    rs : float, optional
        Switch resistance (Ohm), by default 0.0
    ig : float | dict, optional
        Ground current (A), by default 0.0.
    limits : dict, optional
        Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, vo, vd, ii, io, pi, po, pl, tr, tp
    iis : float, optional
        Sleep (shut-down) current (A), by default 0.0.
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.

    Raises
    ------
    ValueError
        If a limits value is not of the correct format.

    """

    @property
    def _component_type(self):
        """Defines the PSwitch component type"""
        return _ComponentTypes.PSWITCH

    @property
    def _child_types(self):
        """Defines allowable PSwitch child component types"""
        et = list(_ComponentTypes)
        et.remove(_ComponentTypes.SOURCE)
        return et

    _cparams = {
        "name": "pswitch",
        "params": {
            "rs": {"typ": [int, float], "opt": True, "def": RS_DEFAULT},
            "ig": {"typ": [int, float, dict], "opt": True, "def": IG_DEFAULT},
            "iis": {"typ": [int, float], "opt": True, "def": IIS_DEFAULT},
            "rt": {"typ": [int, float], "opt": True, "def": RT_DEFAULT},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        rs: float = 0.0,
        ig: float = 0.0,
        limits: dict = LIMITS_DEFAULT,
        iis: float = 0.0,
        rt: float = 0.0,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["rs"] = abs(rs)
        if isinstance(ig, dict):
            _check_interp(ig, "ig")
            if np.min(ig["ig"]) < 0.0:
                raise ValueError("ig values must be >= 0.0")
            if len(ig["vi"]) == 1:
                self._ipr = _Interp1d(ig["io"], ig["ig"][0])
            else:
                cur = []
                volt = []
                for v in ig["vi"]:
                    cur += ig["io"]
                    volt += len(ig["io"]) * [v]
                    igi = np.asarray(ig["ig"]).reshape(1, -1)[0].tolist()
                self._ipr = _Interp2d(cur, volt, igi)
        else:
            self._ipr = _Interp0d(abs(ig))
        self._params["ig"] = ig
        self._params["iis"] = abs(iis)
        self._params["rt"] = abs(rt)
        self._limits = _check_limits(limits)

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf=[], pstate={}):
        """Calculate PSwitch input current from vi, vo and io"""
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0
        i = io + self._ipr._interp(abs(io), abs(vi[0]))
        if phase_conf and phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf=[], pstate={}):
        """Calculate PSwitch output voltage from vi, ii and io"""
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, STATE_OFF
        v = abs(vi[0]) - self._params["rs"] * io
        if phase_conf and phase not in phase_conf:
            return 0.0, STATE_OFF
        if vi[0] >= 0.0:
            return v, STATE_DEFAULT
        return -v, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf=[], pstate={}):
        """Calculate power and loss in PSwitch"""
        if abs(vi) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        loss = self._ipr._interp(abs(io), abs(vi)) * abs(vi)
        if abs(io) > 0.0:
            loss += (abs(vi) - abs(vo)) * io
        pwr = abs(vi * ii)
        if phase_conf and phase not in phase_conf:
            loss = abs(self._params["iis"] * vi)
            pwr = abs(self._params["iis"] * vi)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, tr + ta

    def _get_annot(self):
        """Get PSwitch interpolation figure annotations in format [xlabel, ylabel, title]"""
        if isinstance(self._ipr, _Interp1d):
            return [
                "Output current (A)",
                "Ground current (A)",
                "{} ground current".format(self._params["name"]),
            ]
        return [
            "Output current (A)",
            "Input voltage (V)",
            "{} ground current".format(self._params["name"]),
        ]


class PMux(_Component):
    """Power multiplexer/switcher.

    The power mux can have up to 4 inputs and connects one of the inputs to the output in prioritized order.
    The first input that is active (not turned off) will be selected. If all inputs are off, the output will also be off.
    The ON resistance can be individually specified for each input. There can only be one PMux in a a system.

    The power mux ground current (ig) can be either a constant (float) or interpolated.
    Interpolation data dict for ground current can be either 1D (function of output current only):

    ``ig = {"vi":[5.0], "io":[0.005, 0.05, 0.5], "ig":[[36e-6, 37e-6, 35e-6]]}``

    Or 2D (function of input voltage and output current):

    ``ig = {"vi":[3.3, 5.0, 12.0], "io":[0.005, 0.05, 0.5], "ig":[[5e-6, 5e-6, 5e-6], [7e-6, 7e-6, 7e-6], [36e-6, 37e-6, 35e-6]]}``

    Parameters
    ----------
    name : str
        Power mux name.
    rs : float | list, optional
        Mux on-resistance (Ohm), by default 0.0
    ig : float | dict, optional
        Ground current (A), by default 0.0.
    limits : dict, optional
        Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, vo, vd, ii, io, pi, po, pl, tr, tp
    iis : float, optional
        Sleep (shut-down) current (A), by default 0.0.
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.

    Raises
    ------
    ValueError
        If a parameter value is not of the correct format.

    """

    @property
    def _component_type(self):
        """Defines the PMux component type"""
        return _ComponentTypes.PMUX

    @property
    def _child_types(self):
        """Defines allowable PMux child component types"""
        et = list(_ComponentTypes)
        et.remove(_ComponentTypes.SOURCE)
        return et

    _cparams = {
        "name": "pmux",
        "params": {
            "rs": {"typ": [int, float, list], "opt": True, "def": RS_DEFAULT},
            "ig": {"typ": [int, float, dict], "opt": True, "def": IG_DEFAULT},
            "iis": {"typ": [int, float], "opt": True, "def": IIS_DEFAULT},
            "rt": {"typ": [int, float], "opt": True, "def": RT_DEFAULT},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        rs: float = 0.0,
        ig: float = 0.0,
        limits: dict = LIMITS_DEFAULT,
        iis: float = 0.0,
        rt: float = 0.0,
    ):
        self._params = {}
        self._params["name"] = name
        if not isinstance(rs, list):
            self._params["rs"] = abs(rs)
        elif not all(isinstance(e, (int, float)) for e in rs):
            raise ValueError("rs values must be numbers!")
        self._params["rs"] = rs
        if isinstance(ig, dict):
            _check_interp(ig, "ig")
            if np.min(ig["ig"]) < 0.0:
                raise ValueError("ig values must be >= 0.0")
            if len(ig["vi"]) == 1:
                self._ipr = _Interp1d(ig["io"], ig["ig"][0])
            else:
                cur = []
                volt = []
                for v in ig["vi"]:
                    cur += ig["io"]
                    volt += len(ig["io"]) * [v]
                    igi = np.asarray(ig["ig"]).reshape(1, -1)[0].tolist()
                self._ipr = _Interp2d(cur, volt, igi)
        else:
            self._ipr = _Interp0d(abs(ig))
        self._params["ig"] = ig
        self._params["iis"] = abs(iis)
        self._params["rt"] = abs(rt)
        self._limits = _check_limits(limits)

    def _get_pri_inp(self, pstate, vi):
        """Determine which input is prioritized"""
        inp = -1
        for i in range(len(pstate["off"])):
            if pstate["off"][i] == False and abs(vi[i]) != 0.0:
                inp = i
                break
        return inp

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf=[], pstate={}):
        """Calculate PMux input current from vi, vo and io"""
        pinp = self._get_pri_inp(pstate, vi)
        if pinp == -1:
            return 0.0
        i = io + self._ipr._interp(abs(io), abs(vi[pinp]))
        if phase_conf and phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf=[], pstate={}):
        """Calculate PMux output voltage from vi, ii and io"""
        pinp = self._get_pri_inp(pstate, vi)
        if pinp == -1:
            return 0.0, STATE_OFF
        if isinstance(self._params["rs"], list):
            if len(self._params["rs"]) < len(vi):
                raise ValueError("rs list has too few elements")
            r = abs(self._params["rs"][pinp])
        else:
            r = self._params["rs"]
        v = abs(vi[pinp]) - r * io
        if phase_conf and phase not in phase_conf:
            return 0.0, STATE_OFF
        if vi[pinp] >= 0.0:
            return v, STATE_DEFAULT
        return -v, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf=[], pstate={}):
        """Calculate power and loss in PMux"""
        if abs(vi) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        loss = self._ipr._interp(abs(io), abs(vi)) * abs(vi)
        if abs(io) > 0.0:
            loss += (abs(vi) - abs(vo)) * io
        pwr = abs(vi * ii)
        if phase_conf and phase not in phase_conf:
            loss = abs(self._params["iis"] * vi)
            pwr = abs(self._params["iis"] * vi)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, tr + ta

    def _get_annot(self):
        """Get PMux interpolation figure annotations in format [xlabel, ylabel, title]"""
        if isinstance(self._ipr, _Interp1d):
            return [
                "Output current (A)",
                "Ground current (A)",
                "{} ground current".format(self._params["name"]),
            ]
        return [
            "Output current (A)",
            "Input voltage (V)",
            "{} ground current".format(self._params["name"]),
        ]


class Rectifier(_Component):
    """Full bridge rectifier.

    If the voltage drop (vdrop) is set to non-zero, a diode rectifier will be modelled. The rs, ig, iq and iis
    parameters are then ignored. Note that vdrop represents the forward voltage of a single diode. Total voltage drop
    will be 2 x vdrop. The voltage drop can be either a constant (float) or interpolated.
    Interpolation data dict for voltage drop can be either 1D (function of output current only):

    ``vdrop= {"vi":[2.5], "io":[0.1, 0.5, 0.9], "vdrop":[[0.23, 0.41, 0.477]]}``

    Or 2D (function of input voltage and output current):

    ``vdrop = {"vi":[2.5, 5.0, 12.0], "io":[0.1, 0.5, 0.9], "vdrop":[[0.23, 0.34, 0.477], [0.27, 0.39, 0.51], [0.3, 0.41, 0.57]]}``

    If the vdrop parameter is zero, a MOSFET bridge will be modelled. The parameters rs, ig, iq and iis then apply. Note that rs
    represents the resistance in a single MOSFET. Total resistance in bridge will be 2 x rs. The rectifier ground current (ig) can
    be either a constant (float) or interpolated.
    Interpolation data dict for ground current can be either 1D (function of output current only):

    ``ig = {"vi":[5.0], "io":[0.005, 0.05, 0.5], "ig":[[36e-6, 37e-6, 35e-6]]}``

    Or 2D (function of input voltage and output current):

    ``ig = {"vi":[3.3, 5.0, 12.0], "io":[0.005, 0.05, 0.5], "ig":[[5e-6, 5e-6, 5e-6], [7e-6, 7e-6, 7e-6], [36e-6, 37e-6, 35e-6]]}``

    The output voltage of the rectifier is always positive (or zero).

    Parameters
    ----------
    name : str
        Rectifier name.
    vdrop : float | dict
        Diode (each) voltage drop (V), a constant value (float) or interpolation data (dict).
    rs : float | list, optional
        MOSFET (each) on-resistance (Ohm), by default 0.0
    ig : float | dict, optional
        Total ground current (A), by default 0.0.
    iq : float, optional
        Quiescent (no-load) current (A), by default 0.0.
    limits : dict, optional
        Voltage, current and power limits, by default LIMITS_DEFAULT. The following limits apply: vi, vo, vd, ii, io, pi, po, pl, tr, tp
    rt : float, optional
        Thermal resistance (°C/W), by default 0.0.

    Raises
    ------
    ValueError
        If a parameter value is not of the correct format.

    """

    @property
    def _component_type(self):
        """Defines the Rectifier component type"""
        return _ComponentTypes.RECTIFIER

    @property
    def _child_types(self):
        """Defines allowable Rectifier child component types"""
        et = list(_ComponentTypes)
        et.remove(_ComponentTypes.SOURCE)
        return et

    _cparams = {
        "name": "rectifier",
        "params": {
            "vdrop": {"typ": [int, float, dict], "opt": False},
            "rs": {"typ": [int, float, list], "opt": True, "def": RS_DEFAULT},
            "ig": {"typ": [int, float, dict], "opt": True, "def": IG_DEFAULT},
            "iq": {"typ": [int, float], "opt": True, "def": IQ_DEFAULT},
            "rt": {"typ": [int, float], "opt": True, "def": RT_DEFAULT},
        },
    }

    def __init__(
        self,
        name: str,
        *,
        vdrop: float | dict = 0.0,
        rs: float = 0.0,
        ig: float = 0.0,
        iq: float = 0.0,
        limits: dict = LIMITS_DEFAULT,
        rt: float = 0.0,
    ):
        self._params = {}
        self._params["name"] = name
        if vdrop != 0.0:
            self._params["type"] = "diode"
            if isinstance(vdrop, dict):
                _check_interp(vdrop, "vdrop")
                if len(vdrop["vi"]) == 1:
                    self._ipr = _Interp1d(vdrop["io"], vdrop["vdrop"][0])
                else:
                    cur = []
                    volt = []
                    for v in vdrop["vi"]:
                        cur += vdrop["io"]
                        volt += len(vdrop["io"]) * [v]
                        vd = np.asarray(vdrop["vdrop"]).reshape(1, -1)[0].tolist()
                    self._ipr = _Interp2d(cur, volt, vd)
                self._params["vdrop"] = vdrop
            else:
                self._params["vdrop"] = abs(vdrop)
                self._ipr = _Interp0d(abs(vdrop))
        else:
            self._params["type"] = "mosfet"
            if not isinstance(rs, list):
                if not isinstance(rs, (int, float)):
                    raise ValueError("rs values must be numbers!")
                self._params["rs"] = abs(rs)
            elif not all(isinstance(e, (int, float)) for e in rs):
                raise ValueError("rs values must be numbers!")
            self._params["rs"] = rs
            if isinstance(ig, dict):
                _check_interp(ig, "ig")
                if np.min(ig["ig"]) < 0.0:
                    raise ValueError("ig values must be >= 0.0")
                if len(ig["vi"]) == 1:
                    self._ipr = _Interp1d(ig["io"], ig["ig"][0])
                else:
                    cur = []
                    volt = []
                    for v in ig["vi"]:
                        cur += ig["io"]
                        volt += len(ig["io"]) * [v]
                        igi = np.asarray(ig["ig"]).reshape(1, -1)[0].tolist()
                    self._ipr = _Interp2d(cur, volt, igi)
            else:
                self._ipr = _Interp0d(abs(ig))
            self._params["ig"] = ig
            self._params["iq"] = abs(iq)
        # common params
        self._params["rt"] = abs(rt)
        self._limits = _check_limits(limits)

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        """Calculate Rectifier input current from vi, vo and io"""
        if self._params["type"] == "diode":
            return _calc_inp_current(vi[0], io, pstate, 0)
        if io == 0.0:
            i = self._params["iq"]
        else:
            i = io + self._ipr._interp(abs(io), abs(vi[0]))
        return _calc_inp_current(vi[0], i, pstate, 0)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}, pstate={}):
        """Calculate Rectifier output voltage from vi, ii and io"""
        if abs(vi[0]) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, STATE_OFF
        if self._params["type"] == "diode":
            vo = vi[0] - 2 * self._ipr._interp(abs(io), abs(vi[0])) * np.sign(vi[0])
            if np.sign(vo) == np.sign(vi[0]):
                return abs(vo), STATE_DEFAULT
            raise ValueError(
                "Unstable system: Rectifier component '{}' has zero output voltage".format(
                    self._params["name"]
                )
            )
        # mosfet mode
        v = abs(vi[0]) - 2 * self._params["rs"] * io
        return abs(v), STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf=[], pstate={}):
        """Calculate power and loss in Rectifier"""
        if abs(vi) == 0.0 or _get_lopt(pstate, "off", 0, False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        if self._params["type"] == "diode":
            vout = vi - 2 * self._ipr._interp(abs(io), abs(vi)) * np.sign(vi)
            if np.sign(vout) != np.sign(vi) or _get_lopt(pstate, "off", 0, False):
                return 0.0, 0.0, 0.0, 0.0, 0.0
            loss = abs(vi - vout) * io
            pwr = abs(vi * ii)
            tr = loss * self._params["rt"]
            return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, ta + tr
        # mosfet mode
        if abs(io) == 0.0:
            loss = self._params["iq"] * abs(vi)
        else:
            loss = self._ipr._interp(abs(io), abs(vi)) * abs(vi)
            loss += 2 * self._params["rs"] * abs(io) ** 2
        pwr = abs(vi * ii)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, tr + ta

    def _get_annot(self):
        """Get Rectifier interpolation figure annotations in format [xlabel, ylabel, title]"""
        if self._params["type"] == "mosfet":
            if isinstance(self._ipr, _Interp1d):
                return [
                    "Output current (A)",
                    "Ground current (A)",
                    "{} ground current".format(self._params["name"]),
                ]
            return [
                "Output current (A)",
                "Input voltage (V)",
                "{} ground current".format(self._params["name"]),
            ]
        if isinstance(self._ipr, _Interp1d):
            return [
                "Output current (A)",
                "Voltage drop (V)",
                "{} voltage drop".format(self._params["name"]),
            ]
        return [
            "Output current (A)",
            "Input voltage (V)",
            "{} voltage drop".format(self._params["name"]),
        ]
