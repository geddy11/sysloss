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
STATE_DEFAULT = {"off": False}
STATE_OFF = {"off": True}


def _get_opt(params, key, default):
    """Get optional parameter from dict"""
    if key in params:
        return params[key]
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


def _calc_inp_current(vo, i, pstate):
    """Calculate input current from vo and state vector"""
    if abs(vo) == 0.0 or _get_opt(pstate, "off", False):
        return 0.0
    return i


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


class Source:
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
        self._limits = limits
        self._ipr = None

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read source parameters from .toml file.

        Parameters
        ----------
        name : str
            Source name
        fname : str
            File name.
        """
        with open(fname, "r") as f:
            config = toml.load(f)

        v = _get_mand(config["source"], "vo")
        r = _get_opt(config["source"], "rs", RS_DEFAULT)
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        return cls(name, vo=v, rs=r, limits=lim)

    def _get_inp_current(self, phase, phase_conf={}):
        """Get initial current value for solver"""
        return 0.0

    def _get_outp_voltage(self, phase, phase_conf={}):
        """Get initial voltage value for solver"""
        return self._params["vo"]

    def _get_state(self, phase, phase_conf={}):
        """Get initial state value for solver"""
        return STATE_DEFAULT

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        """Calculate component input current from vi, vo and io"""
        return _calc_inp_current(self._params["vo"], io, pstate)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}, pstate={}):
        """Calculate component output voltage from vi, ii and io"""
        if self._params["vo"] == 0.0 or _get_opt(pstate, "off", False):
            return 0.0, STATE_OFF
        vo = self._params["vo"] - self._params["rs"] * io
        return vo, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf={}, pstate={}):
        """Calculate power and loss in component"""
        if self._params["vo"] == 0.0 or _get_opt(pstate, "off", False):
            return 0.0, 0.0, 100.0, 0.0, 0.0
        ipwr = abs(self._params["vo"] * io)
        loss = self._params["rs"] * io * io
        opwr = ipwr - loss
        return ipwr, loss, _get_eff(ipwr, opwr), 0.0, 0.0

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf={}):
        """Check limits"""
        return _get_warns(
            self._limits, {"io": io, "po": vo * io, "pl": self._params["rs"] * io * io}
        )

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        ret["vo"] = self._params["vo"]
        ret["rs"] = self._params["rs"]
        return ret


class PLoad:
    """Power load.

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

    """

    @property
    def _component_type(self):
        """Defines the Load component type"""
        return _ComponentTypes.LOAD

    @property
    def _child_types(self):
        """The Load component cannot have childs"""
        return [None]

    def __init__(
        self,
        name: str,
        *,
        pwr: float,
        limits: dict = LIMITS_DEFAULT,
        pwrs: float = 0.0,
        rt: float = 0.0,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["pwr"] = abs(pwr)
        self._params["pwrs"] = abs(pwrs)
        self._params["rt"] = abs(rt)
        self._limits = limits
        self._ipr = None

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read PLoad parameters from .toml file.

        Parameters
        ----------
        name : str
            Load name
        fname : str
            File name.
        """
        with open(fname, "r") as f:
            config = toml.load(f)

        p = _get_mand(config["pload"], "pwr")
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        pwrs = _get_opt(config["pload"], "pwrs", PWRS_DEFAULT)
        rt = _get_opt(config["pload"], "rt", RT_DEFAULT)
        return cls(name, pwr=p, limits=lim, pwrs=pwrs, rt=rt)

    def _get_inp_current(self, phase, phase_conf={}):
        """Get initial current value for solver"""
        return 0.0

    def _get_outp_voltage(self, phase, phase_conf={}):
        """Get initial voltage value for solver"""
        return 0.0

    def _get_state(self, phase, phase_conf={}):
        """Get initial state value for solver"""
        return STATE_DEFAULT

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        """Calculate component input current from vi, vo and io"""
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0
        if not phase_conf:
            p = self._params["pwr"]
        elif phase not in phase_conf:
            p = self._params["pwrs"]
        else:
            p = phase_conf[phase]

        return p / abs(vi)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}, pstate={}):
        """Load output voltage is always 0"""
        if _get_opt(pstate, "off", False):
            return 0.0, STATE_OFF
        return 0.0, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf={}, pstate={}):
        """Calculate power and loss in component"""
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0, 0.0, 100.0, 0.0, 0.0
        tr = abs(vi * ii) * self._params["rt"]
        return abs(vi * ii), 0.0, 100.0, tr, tr + ta

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf={}):
        """Check limits"""
        if phase_conf and phase != "":
            if phase not in phase_conf:
                return ""
        tr = vi * ii * self._params["rt"]
        tp = tr + ta
        return _get_warns(self._limits, {"vi": vi, "ii": ii, "tr": tr, "tp": tp})

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        ret["pwr"] = self._params["pwr"]
        ret["pwrs"] = self._params["pwrs"]
        ret["rt"] = self._params["rt"]
        return ret


class ILoad(PLoad):
    """Current load.

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

    """

    def __init__(
        self,
        name: str,
        *,
        ii: float,
        limits: dict = LIMITS_DEFAULT,
        iis: float = 0.0,
        rt: float = 0.0,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["ii"] = abs(ii)
        self._limits = limits
        self._params["iis"] = abs(iis)
        self._params["rt"] = abs(rt)
        self._ipr = None

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read ILoad parameters from .toml file.

        Parameters
        ----------
        name : str
            Load name
        fname : str
            File name.
        """
        with open(fname, "r") as f:
            config = toml.load(f)

        i = _get_mand(config["iload"], "ii")
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        iis = _get_opt(config["iload"], "iis", IIS_DEFAULT)
        rt = _get_opt(config["iload"], "rt", RT_DEFAULT)
        return cls(name, ii=i, limits=lim, iis=iis, rt=rt)

    def _get_inp_current(self, phase, phase_conf={}):
        """Get initial current value for solver"""
        return self._params["ii"]

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0
        if not phase_conf:
            i = self._params["ii"]
        elif phase not in phase_conf:
            i = self._params["iis"]
        else:
            i = phase_conf[phase]

        return abs(i)

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf={}):
        """Check limits"""
        if phase_conf and phase != "":
            if phase not in phase_conf:
                return ""
        tr = vi * ii * self._params["rt"]
        tp = tr + ta
        return _get_warns(self._limits, {"vi": vi, "pi": vi * ii, "tr": tr, "tp": tp})

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        ret["ii"] = self._params["ii"]
        ret["iis"] = self._params["iis"]
        ret["rt"] = self._params["rt"]
        return ret


class RLoad(PLoad):
    """Resistive load.

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

    """

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
        if abs(rs) == 0.0:
            raise ValueError("rs must be > 0!")
        self._params["rs"] = abs(rs)
        self._params["rt"] = abs(rt)
        self._limits = limits
        self._ipr = None

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read RLoad parameters from .toml file.

        Parameters
        ----------
        name : str
            Load name
        fname : str
            File name.
        """
        with open(fname, "r") as f:
            config = toml.load(f)

        r = _get_mand(config["rload"], "rs")
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        rt = _get_opt(config["rload"], "rt", RT_DEFAULT)
        return cls(name, rs=r, rt=rt, limits=lim)

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0
        r = self._params["rs"]
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            pass
        else:
            r = phase_conf[phase]
        return abs(vi) / r

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf={}):
        """Check limits"""
        if phase_conf and phase != "":
            if phase not in phase_conf:
                return ""
        tr = vi * ii * self._params["rt"]
        tp = tr + ta
        return _get_warns(
            self._limits, {"vi": vi, "ii": ii, "pi": vi * ii, "tr": tr, "tp": tp}
        )

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        ret["rs"] = self._params["rs"]
        ret["rt"] = self._params["rt"]
        return ret


class RLoss:
    """Resistive loss.

    This loss element is connected in series with other elements.

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
        self._limits = limits
        self._ipr = None

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read RLoss parameters from .toml file.

        Parameters
        ----------
        name : str
            Loss name
        fname : str
            File name.
        """
        with open(fname, "r") as f:
            config = toml.load(f)

        r = _get_mand(config["rloss"], "rs")
        rt = _get_opt(config["rloss"], "rt", RT_DEFAULT)
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        return cls(name, rs=r, limits=lim, rt=rt)

    def _get_inp_current(self, phase, phase_conf={}):
        """Get initial current value for solver"""
        return 0.0

    def _get_outp_voltage(self, phase, phase_conf={}):
        """Get initial voltage value for solver"""
        return 0.0

    def _get_state(self, phase, phase_conf={}):
        """Get initial state value for solver"""
        return STATE_DEFAULT

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        """Calculate component input current from vi, vo and io"""
        return _calc_inp_current(vi, io, pstate)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}, pstate={}):
        """Calculate component output voltage from vi, ii and io"""
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0, STATE_OFF
        vo = vi - self._params["rs"] * io * np.sign(vi)
        if np.sign(vo) == np.sign(vi):
            return vo, STATE_DEFAULT
        raise ValueError(
            "Unstable system: RLoss component '{}' has zero output voltage".format(
                self._params["name"]
            )
        )

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf={}, pstate={}):
        """Calculate power and loss in component"""
        vout = vi - self._params["rs"] * io * np.sign(vi)
        if np.sign(vout) != np.sign(vi) or _get_opt(pstate, "off", False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        loss = abs(vi - vout) * io
        pwr = abs(vi * ii)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 100.0), tr, ta + tr

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf={}):
        """Check limits"""
        pl = abs(vi) * ii - abs(vo) * io
        tr = pl * self._params["rt"]
        tp = tr + ta
        return _get_warns(
            self._limits,
            {
                "vi": vi,
                "vo": vo,
                "vd": abs(vi - vo),
                "ii": ii,
                "io": io,
                "pi": abs(vi * ii),
                "po": abs(vo * io),
                "pl": pl,
                "tr": tr,
                "tp": tp,
            },
        )

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        ret["rs"] = self._params["rs"]
        ret["rt"] = self._params["rt"]
        return ret


class VLoss:
    """Voltage loss.

    This loss element is connected in series with other elements.
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
            if not np.all(np.diff(vdrop["io"]) > 0):
                raise ValueError("io values must be monotonic increasing")
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
        self._limits = limits

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read VLoss parameters from .toml file.

        Parameters
        ----------
        name : str
            Loss name
        fname : str
            File name.
        """
        with open(fname, "r") as f:
            config = toml.load(f)

        vd = _get_mand(config["vloss"], "vdrop")
        rt = _get_opt(config["vloss"], "rt", RT_DEFAULT)
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        return cls(name, vdrop=vd, rt=rt, limits=lim)

    def _get_inp_current(self, phase, phase_conf={}):
        """Get initial current value for solver"""
        return 0.0

    def _get_outp_voltage(self, phase, phase_conf={}):
        """Get initial voltage value for solver"""
        return 0.0

    def _get_state(self, phase, phase_conf={}):
        """Get initial state value for solver"""
        return STATE_DEFAULT

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}, pstate={}):
        """Calculate component input current from vi, vo and io"""
        return _calc_inp_current(vi, io, pstate)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}, pstate={}):
        """Calculate component output voltage from vi, ii and io"""
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0, STATE_OFF
        vo = vi - self._ipr._interp(abs(io), abs(vi)) * np.sign(vi)
        if np.sign(vo) == np.sign(vi):
            return vo, STATE_DEFAULT
        raise ValueError(
            "Unstable system: VLoss component '{}' has zero output voltage".format(
                self._params["name"]
            )
        )

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf={}, pstate={}):
        """Calculate power and loss in component"""
        vout = vi - self._ipr._interp(abs(io), abs(vi)) * np.sign(vi)
        if np.sign(vout) != np.sign(vi) or _get_opt(pstate, "off", False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        loss = abs(vi - vout) * io
        pwr = abs(vi * ii)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 100.0), tr, ta + tr

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf={}):
        """Check limits"""
        pl = abs(vi) * ii - abs(vo) * io
        tr = pl * self._params["rt"]
        tp = tr + ta
        return _get_warns(
            self._limits,
            {
                "vi": vi,
                "vo": vo,
                "vd": abs(vi - vo),
                "ii": ii,
                "io": io,
                "pi": abs(vi * ii),
                "po": abs(vo * io),
                "pl": pl,
                "tr": tr,
                "tp": tp,
            },
        )

    def _get_annot(self):
        """Get interpolation figure annotations in format [xlabel, ylabel, title]"""
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

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        ret["rt"] = self._params["rt"]
        if isinstance(self._ipr, _Interp0d):
            ret["vdrop"] = abs(self._params["vdrop"])
        else:
            ret["vdrop"] = "interp"
        return ret


class Converter:
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
        If efficiency is 0.0 or > 1.0.

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
            if not np.all(np.diff(eff["io"]) > 0):
                raise ValueError("io values must be monotonic increasing")
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
        self._limits = limits

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read Converter parameters from .toml file.

        Parameters
        ----------
        name : str
            Converter name
        fname : str
            File name.

        """
        with open(fname, "r") as f:
            config = toml.load(f)

        v = _get_mand(config["converter"], "vo")
        e = _get_mand(config["converter"], "eff")
        iq = _get_opt(config["converter"], "iq", IQ_DEFAULT)
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        iis = _get_opt(config["converter"], "iis", IIS_DEFAULT)
        rt = _get_opt(config["converter"], "rt", RT_DEFAULT)
        return cls(name, vo=v, eff=e, iq=iq, limits=lim, iis=iis, rt=rt)

    def _get_inp_current(self, phase, phase_conf=[]):
        """Get initial current value for solver"""
        i = self._params["iq"]
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _get_outp_voltage(self, phase, phase_conf=[]):
        """Get initial voltage value for solver"""
        v = self._params["vo"]
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            v = 0.0
        return v

    def _get_state(self, phase, phase_conf={}):
        """Get initial state value for solver"""
        return STATE_DEFAULT

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf=[], pstate={}):
        """Calculate component input current from vi, vo and io"""
        if (
            abs(vi) == 0.0
            or self._params["vo"] == 0.0
            or _get_opt(pstate, "off", False)
        ):
            return 0.0
        ve = vi * self._ipr._interp(abs(io), abs(vi))
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            return self._params["iis"]
        if io == 0.0:
            return self._params["iq"]
        return abs(self._params["vo"] * io / ve)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf=[], pstate={}):
        """Calculate component output voltage from vi, ii and io"""
        v = self._params["vo"]
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0, STATE_OFF
        if phase_conf:
            if phase not in phase_conf:
                return 0.0, STATE_OFF
        return v, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf=[], pstate={}):
        """Calculate power and loss in component"""
        if _get_opt(pstate, "off", False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        if io == 0.0:
            loss = abs(self._params["iq"] * vi)
        else:
            loss = abs(ii * vi * (1.0 - self._ipr._interp(abs(io), abs(vi))))
        pwr = abs(vi * ii)
        if phase_conf:
            if phase not in phase_conf:
                loss = abs(self._params["iis"] * vi)
                pwr = abs(self._params["iis"] * vi)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, ta + tr

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf=[]):
        """Check limits"""
        if phase_conf:
            if phase not in phase_conf:
                return ""
        pi, pl, _, tr, tp = self._solv_pwr_loss(
            vi, vo, ii, io, ta, phase, phase_conf=[]
        )
        tp = tr + ta
        return _get_warns(
            self._limits,
            {
                "vi": vi,
                "vo": vo,
                "ii": ii,
                "io": io,
                "pi": pi,
                "po": pi - pl,
                "pl": pl,
                "tr": tr,
                "tp": tp,
            },
        )

    def _get_annot(self):
        """Get interpolation figure annotations in format [xlabel, ylabel, title]"""
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

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        ret["vo"] = self._params["vo"]
        ret["iq"] = self._params["iq"]
        if isinstance(self._ipr, _Interp0d):
            ret["eff"] = abs(self._params["eff"])
        else:
            ret["eff"] = "interp"
        ret["iis"] = self._params["iis"]
        ret["rt"] = self._params["rt"]
        return ret


class LinReg:
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
        If vdrop > vo.

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
            if not np.all(np.diff(igc["io"]) > 0):
                raise ValueError("ig values must be monotonic increasing")
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
        self._limits = limits

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
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _get_outp_voltage(self, phase, phase_conf=[]):
        """Get initial voltage value for solver"""
        v = self._params["vo"]
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            v = 0.0
        return v

    def _get_state(self, phase, phase_conf={}):
        """Get initial state value for solver"""
        return STATE_DEFAULT

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf=[], pstate={}):
        """Calculate component input current from vi, vo and io"""
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0
        i = io + self._ipr._interp(abs(io), abs(vi))
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf=[], pstate={}):
        """Calculate component output voltage from vi, ii and io"""
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0, STATE_OFF
        v = min(abs(self._params["vo"]), max(abs(vi) - self._params["vdrop"], 0.0))
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            return 0.0, STATE_OFF
        if self._params["vo"] >= 0.0:
            return v, STATE_DEFAULT
        return -v, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf=[], pstate={}):
        """Calculate power and loss in component"""
        if _get_opt(pstate, "off", False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        v = min(abs(self._params["vo"]), max(abs(vi) - self._params["vdrop"], 0.0))
        if abs(vi) == 0.0 or v == 0.0:
            loss = 0.0
        else:
            loss = self._ipr._interp(abs(io), abs(vi)) * abs(vi)
        if abs(io) > 0.0:
            loss += (abs(vi) - abs(v)) * io
        pwr = abs(vi * ii)
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            loss = abs(self._params["iis"] * vi)
            pwr = abs(self._params["iis"] * vi)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, tr + ta

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf=[]):
        """Check limits"""
        if phase_conf:
            if phase not in phase_conf:
                return ""
        pi, pl, _, tr, tp = self._solv_pwr_loss(
            vi, vo, ii, io, ta, phase, phase_conf=[]
        )
        tp = tr + ta
        return _get_warns(
            self._limits,
            {
                "vi": vi,
                "vo": vo,
                "vd": abs(vi - vo),
                "ii": ii,
                "io": io,
                "pi": pi,
                "po": pi - pl,
                "pl": pl,
                "tr": tr,
                "tp": tp,
            },
        )

    def _get_annot(self):
        """Get interpolation figure annotations in format [xlabel, ylabel, title]"""
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

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        ret["vo"] = self._params["vo"]
        ret["vdrop"] = self._params["vdrop"]
        if isinstance(self._ipr, _Interp0d):
            ret["ig"] = abs(self._params["ig"])
        else:
            ret["ig"] = "interp"
        ret["iis"] = self._params["iis"]
        ret["rt"] = self._params["rt"]
        return ret


class PSwitch:
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
            if not np.all(np.diff(ig["io"]) > 0):
                raise ValueError("ig values must be monotonic increasing")
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
        self._limits = limits

    @classmethod
    def from_file(cls, name: str, *, fname: str):
        """Read PSwitch parameters from .toml file.

        Parameters
        ----------
        name : str
            PSwitch name
        fname : str
            File name.
        """
        with open(fname, "r") as f:
            config = toml.load(f)

        rs = _get_opt(config["pswitch"], "rs", RS_DEFAULT)
        ig = _get_opt(config["pswitch"], "ig", IG_DEFAULT)
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        iis = _get_opt(config["pswitch"], "iis", IIS_DEFAULT)
        rt = _get_opt(config["pswitch"], "rt", RT_DEFAULT)
        return cls(name, rs=rs, ig=ig, limits=lim, iis=iis, rt=rt)

    def _get_inp_current(self, phase, phase_conf=[]):
        """Get initial current value for solver"""
        i = self._ipr._interp(0.0, 0.0)
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _get_outp_voltage(self, phase, phase_conf=[]):
        """Get initial voltage value for solver"""
        return 0.0

    def _get_state(self, phase, phase_conf={}):
        """Get initial state value for solver"""
        return STATE_DEFAULT

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf=[], pstate={}):
        """Calculate component input current from vi, vo and io"""
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0
        i = io + self._ipr._interp(abs(io), abs(vi))
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf=[], pstate={}):
        """Calculate component output voltage from vi, ii and io"""
        if abs(vi) == 0.0 or _get_opt(pstate, "off", False):
            return 0.0, STATE_OFF
        v = abs(vi) - self._params["rs"] * io
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            return 0.0, STATE_OFF
        if vi >= 0.0:
            return v, STATE_DEFAULT
        return -v, STATE_DEFAULT

    def _solv_pwr_loss(self, vi, vo, ii, io, ta, phase, phase_conf=[], pstate={}):
        """Calculate power and loss in component"""
        if _get_opt(pstate, "off", False):
            return 0.0, 0.0, 0.0, 0.0, 0.0
        if abs(vi) == 0.0:
            loss = 0.0
        else:
            loss = self._ipr._interp(abs(io), abs(vi)) * abs(vi)
        if abs(io) > 0.0:
            loss += (abs(vi) - abs(vo)) * io
        pwr = abs(vi * ii)
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            loss = abs(self._params["iis"] * vi)
            pwr = abs(self._params["iis"] * vi)
        tr = loss * self._params["rt"]
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), tr, tr + ta

    def _solv_get_warns(self, vi, vo, ii, io, ta, phase, phase_conf=[]):
        """Check limits"""
        if phase_conf:
            if phase not in phase_conf:
                return ""
        pi, pl, _, tr, tp = self._solv_pwr_loss(
            vi, vo, ii, io, ta, phase, phase_conf=[]
        )
        tp = tr + ta
        return _get_warns(
            self._limits,
            {
                "vi": vi,
                "vo": vo,
                "vd": abs(vi - vo),
                "ii": ii,
                "io": io,
                "pi": pi,
                "po": pi - pl,
                "pl": pl,
                "tr": tr,
                "tp": tp,
            },
        )

    def _get_annot(self):
        """Get interpolation figure annotations in format [xlabel, ylabel, title]"""
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

    def _get_params(self, pdict):
        """Return dict with component parameters"""
        ret = pdict
        ret["rs"] = self._params["rs"]
        if isinstance(self._ipr, _Interp0d):
            ret["ig"] = abs(self._params["ig"])
        else:
            ret["ig"] = "interp"
        ret["iis"] = self._params["iis"]
        ret["rt"] = self._params["rt"]
        return ret
