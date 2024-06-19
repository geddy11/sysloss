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

"""Components that can be added to the system."""

from enum import Enum, unique
import toml
import numpy as np
from scipy.interpolate import LinearNDInterpolator

__all__ = ["Source", "ILoad", "PLoad", "RLoad", "RLoss", "VLoss", "Converter", "LinReg"]


@unique
class _ComponentTypes(Enum):
    """Component types"""

    SOURCE = 1
    LOAD = 2
    SLOSS = 3
    CONVERTER = 4
    LINREG = 5


MAX_DEFAULT = 1.0e6
IQ_DEFAULT = 0.0
IIS_DEFAULT = 0.0
RS_DEFAULT = 0.0
RT_DEFAULT = 0.0
VDROP_DEFAULT = 0.0
PWRS_DEFAULT = 0.0
LIMITS_DEFAULT = {
    "vi": [0.0, MAX_DEFAULT],
    "vo": [0.0, MAX_DEFAULT],
    "ii": [0.0, MAX_DEFAULT],
    "io": [0.0, MAX_DEFAULT],
    "pi": [0.0, MAX_DEFAULT],
    "po": [0.0, MAX_DEFAULT],
    "pl": [0.0, MAX_DEFAULT],
    "tr": [0.0, MAX_DEFAULT],
}


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
        lim = _get_opt(limits, key, [0, MAX_DEFAULT])
        if abs(checks[key]) > abs(lim[1]) or abs(checks[key]) < abs(lim[0]):
            warn += key + " "
    return warn.strip()


def _get_eff(ipwr, opwr, def_eff=100.0):
    """Calculate efficiency in %"""
    if ipwr > 0.0:
        return 100.0 * abs(opwr / ipwr)
    return def_eff


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
    """The Source component must be the root of a system or subsystem.

    Parameters
    ----------
    name : str
        Source name.
    vo : float
        Output voltage.
    rs : float, optional
        Source resistance., by default 0.0
    limits : dict, optional
        Voltage, current and power limits., by default LIMITS_DEFAULT. The following limits apply: io, po, pl.
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
        rs: float = RS_DEFAULT,
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
        return 0.0

    def _get_outp_voltage(self, phase, phase_conf={}):
        return self._params["vo"]

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}):
        """Calculate component input current from vi, vo and io"""
        if self._params["vo"] == 0.0:
            return 0.0
        return io

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}):
        """Calculate component output voltage from vi, ii and io"""
        if self._params["vo"] == 0.0:
            return 0.0
        return self._params["vo"] - self._params["rs"] * io

    def _solv_pwr_loss(self, vi, vo, ii, io, phase, phase_conf={}):
        """Calculate power and loss in component"""
        if self._params["vo"] == 0.0:
            return 0.0, 0.0, 100.0, 0.0
        ipwr = abs(self._params["vo"] * io)
        loss = self._params["rs"] * io * io
        opwr = ipwr - loss
        return ipwr, loss, _get_eff(ipwr, opwr), 0.0

    def _solv_get_warns(self, vi, vo, ii, io, phase, phase_conf={}):
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
         Voltage, current and power limits., by default LIMITS_DEFAULT. The following limits apply: vi, ii, tr
    pwrs : float, optional
        Load sleep power (W), by default PWRS_DEFAULT
    rt : float, optional
        Thermal resistance (°C/W).
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
        pwrs: float = PWRS_DEFAULT,
        rt: float = RT_DEFAULT,
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
        return 0.0

    def _get_outp_voltage(self, phase, phase_conf={}):
        return 0.0

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}):
        """Calculate component input current from vi, vo and io"""
        if vi == 0.0:
            return 0.0
        if not phase_conf:
            p = self._params["pwr"]
        elif phase not in phase_conf:
            p = self._params["pwrs"]
        else:
            p = phase_conf[phase]

        return p / abs(vi)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}):
        """Load output voltage is always 0"""
        return 0.0

    def _solv_pwr_loss(self, vi, vo, ii, io, phase, phase_conf={}):
        """Calculate power and loss in component"""
        if vi == 0.0:
            return 0.0, 0.0, 100.0, 0.0
        return abs(vi * ii), 0.0, 100.0, abs(vi * ii) * self._params["rt"]

    def _solv_get_warns(self, vi, vo, ii, io, phase, phase_conf={}):
        """Check limits"""
        if phase_conf and phase != "":
            if phase not in phase_conf:
                return ""
        tr = vi * ii * self._params["rt"]
        return _get_warns(self._limits, {"vi": vi, "ii": ii, "tr": tr})

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
         Voltage, current and power limits., by default LIMITS_DEFAULT. The following limits apply: vi, pi, tr
    iis : float, optional
        Load sleep current (A), by default PWRS_DEFAULT
    rt : float, optional
        Thermal resistance (°C/W).
    """

    def __init__(
        self,
        name: str,
        *,
        ii: float,
        limits: dict = LIMITS_DEFAULT,
        iis: float = IIS_DEFAULT,
        rt: float = RT_DEFAULT,
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
        return self._params["ii"]

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}):
        if vi == 0.0:
            return 0.0
        if not phase_conf:
            i = self._params["ii"]
        elif phase not in phase_conf:
            i = self._params["iis"]
        else:
            i = phase_conf[phase]

        return abs(i)

    def _solv_get_warns(self, vi, vo, ii, io, phase, phase_conf={}):
        """Check limits"""
        if phase_conf and phase != "":
            if phase not in phase_conf:
                return ""
        tr = vi * ii * self._params["rt"]
        return _get_warns(self._limits, {"vi": vi, "pi": vi * ii, "tr": tr})

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
        Load resistance (ohm).
    rt : float, optional
        Thermal resistance (°C/W).
    limits : dict, optional
         Voltage, current and power limits., by default LIMITS_DEFAULT. The following limits apply: vi, ii, pi, tr
    """

    def __init__(
        self,
        name: str,
        *,
        rs: float,
        rt: float = RT_DEFAULT,
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

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}):
        r = self._params["rs"]
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            pass
        else:
            r = phase_conf[phase]
        return abs(vi) / r

    def _solv_get_warns(self, vi, vo, ii, io, phase, phase_conf={}):
        """Check limits"""
        if phase_conf and phase != "":
            if phase not in phase_conf:
                return ""
        tr = vi * ii * self._params["rt"]
        return _get_warns(self._limits, {"vi": vi, "ii": ii, "pi": vi * ii, "tr": tr})

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
        Loss resistance (ohm).
    rt : float, optional
        Thermal resistance (°C/W).
    limits : dict, optional
         Voltage, current and power limits., by default LIMITS_DEFAULT. The following limits apply: vi, vo, ii, io, pi, po, pl, tr
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
        rt: float = RT_DEFAULT,
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
        return 0.0

    def _get_outp_voltage(self, phase, phase_conf={}):
        return 0.0

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}):
        """Calculate component input current from vi, vo and io"""
        if abs(vi) == 0.0:
            return 0.0
        return io

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}):
        """Calculate component output voltage from vi, ii and io"""
        if abs(vi) == 0.0:
            return 0.0
        vo = vi - self._params["rs"] * io * np.sign(vi)
        if np.sign(vo) == np.sign(vi):
            return vo
        raise ValueError(
            "Unstable system: RLoss component '{}' has zero output voltage".format(
                self._params["name"]
            )
        )

    def _solv_pwr_loss(self, vi, vo, ii, io, phase, phase_conf={}):
        """Calculate power and loss in component"""
        vout = vi - self._params["rs"] * io * np.sign(vi)
        if np.sign(vout) != np.sign(vi):
            return 0.0, 0.0, 0.0, 0.0
        loss = abs(vi - vout) * io
        pwr = abs(vi * ii)
        return pwr, loss, _get_eff(pwr, pwr - loss, 100.0), loss * self._params["rt"]

    def _solv_get_warns(self, vi, vo, ii, io, phase, phase_conf={}):
        """Check limits"""
        pl = abs(vi) * ii - abs(vo) * io
        tr = pl * self._params["rt"]
        return _get_warns(
            self._limits,
            {
                "vi": vi,
                "vo": vo,
                "ii": ii,
                "io": io,
                "pi": abs(vi * ii),
                "po": abs(vo * io),
                "pl": pl,
                "tr": tr,
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

    Parameters
    ----------
    name : str
        Loss name.
    vdrop : float | dict
        Voltage drop (V), a constant value (float) or interpolation data (dict).
    rt : float, optional
        Thermal resistance (°C/W).
    limits : dict, optional
         Voltage, current and power limits., by default LIMITS_DEFAULT. The following limits apply: vi, vo, ii, io, pi, po, pl, tr
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
        rt: float = RT_DEFAULT,
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
        return 0.0

    def _get_outp_voltage(self, phase, phase_conf={}):
        return 0.0

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf={}):
        """Calculate component input current from vi, vo and io"""
        if abs(vi) == 0.0:
            return 0.0
        return io

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf={}):
        """Calculate component output voltage from vi, ii and io"""
        if abs(vi) == 0.0:
            return 0.0
        vo = vi - self._ipr._interp(abs(io), abs(vi)) * np.sign(vi)
        if np.sign(vo) == np.sign(vi):
            return vo
        raise ValueError(
            "Unstable system: VLoss component '{}' has zero output voltage".format(
                self._params["name"]
            )
        )

    def _solv_pwr_loss(self, vi, vo, ii, io, phase, phase_conf={}):
        """Calculate power and loss in component"""
        vout = vi - self._ipr._interp(abs(io), abs(vi)) * np.sign(vi)
        if np.sign(vout) != np.sign(vi):
            return 0.0, 0.0, 0.0, 0.0
        loss = abs(vi - vout) * io
        pwr = abs(vi * ii)
        return pwr, loss, _get_eff(pwr, pwr - loss, 100.0), loss * self._params["rt"]

    def _solv_get_warns(self, vi, vo, ii, io, phase, phase_conf={}):
        """Check limits"""
        pl = abs(vi) * ii - abs(vo) * io
        tr = pl * self._params["rt"]
        return _get_warns(
            self._limits,
            {
                "vi": vi,
                "vo": vo,
                "ii": ii,
                "io": io,
                "pi": abs(vi * ii),
                "po": abs(vo * io),
                "pl": pl,
                "tr": tr,
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

    Parameters
    ----------
    name : str
        Converter name.
    vo : float
        Output voltage (V).
    eff : float | dict
        Converter efficiency, a constant value (float) or interpolation data (dict).
    iq : float, optional
        Quiescent (no-load) current (A)., by default 0.0
    limits : dict, optional
        Voltage, current and power limits., by default LIMITS_DEFAULT. The following limits apply: vi, vo, ii, io, pi, po, pl, tr
    iis : float, optional
        Sleep (shut-down) current (A), by default 0.0
    rt : float, optional
        Thermal resistance (°C/W).

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
        iq: float = IQ_DEFAULT,
        limits: dict = LIMITS_DEFAULT,
        iis: float = IIS_DEFAULT,
        rt: float = RT_DEFAULT,
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
        i = self._params["iq"]
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _get_outp_voltage(self, phase, phase_conf=[]):
        v = self._params["vo"]
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            v = 0.0
        return v

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf=[]):
        """Calculate component input current from vi, vo and io"""
        if abs(vi) == 0.0 or self._params["vo"] == 0.0:
            return 0.0
        ve = vi * self._ipr._interp(abs(io), abs(vi))
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            return self._params["iis"]
        if io == 0.0:
            return self._params["iq"]
        return abs(self._params["vo"] * io / ve)

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf=[]):
        """Calculate component output voltage from vi, ii and io"""
        v = self._params["vo"]
        if vi == 0.0:
            v = 0.0
        if phase_conf:
            if phase not in phase_conf:
                v = 0.0
        return v

    def _solv_pwr_loss(self, vi, vo, ii, io, phase, phase_conf=[]):
        """Calculate power and loss in component"""
        if io == 0.0:
            loss = abs(self._params["iq"] * vi)
        else:
            loss = abs(ii * vi * (1.0 - self._ipr._interp(abs(io), abs(vi))))
        pwr = abs(vi * ii)
        if phase_conf:
            if phase not in phase_conf:
                loss = abs(self._params["iis"] * vi)
                pwr = abs(self._params["iis"] * vi)
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), loss * self._params["rt"]

    def _solv_get_warns(self, vi, vo, ii, io, phase, phase_conf=[]):
        """Check limits"""
        if phase_conf:
            if phase not in phase_conf:
                return ""
        pi, pl, _, tr = self._solv_pwr_loss(vi, vo, ii, io, phase, phase_conf=[])
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
    """Linear voltage converter.

    If vi - vo < vdrop, the output voltage is reduced to vi - vdrop during analysis.

    Parameters
    ----------
    name : str
        Converter name.
    vo : float
        Output voltage (V).
    vdrop : float
        Dropout voltage (V).
    iq : float | dict, optional
        Ground current (A)., by default 0.0
    limits : dict, optional
        Voltage, current and power limits., by default LIMITS_DEFAULT. The following limits apply: vi, vo, ii, io, pi, po, pl, tr
    iis : float, optional
        Sleep (shut-down) current (A), by default 0.0
    rt : float, optional
        Thermal resistance (°C/W).

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
        vdrop: float = VDROP_DEFAULT,
        iq: float = IQ_DEFAULT,
        limits: dict = LIMITS_DEFAULT,
        iis: float = IIS_DEFAULT,
        rt: float = RT_DEFAULT,
    ):
        self._params = {}
        self._params["name"] = name
        self._params["vo"] = vo
        if not (abs(vdrop) < abs(vo)):
            raise ValueError("Voltage drop must be < vo")
        self._params["vdrop"] = abs(vdrop)
        if isinstance(iq, dict):
            if not np.all(np.diff(iq["io"]) > 0):
                raise ValueError("iq values must be monotonic increasing")
            if np.min(iq["iq"]) < 0.0:
                raise ValueError("iq values must be >= 0.0")
            if len(iq["vi"]) == 1:
                self._ipr = _Interp1d(iq["io"], iq["iq"][0])
            else:
                cur = []
                volt = []
                for v in iq["vi"]:
                    cur += iq["io"]
                    volt += len(iq["io"]) * [v]
                    iqi = np.asarray(iq["iq"]).reshape(1, -1)[0].tolist()
                self._ipr = _Interp2d(cur, volt, iqi)
        else:
            self._ipr = _Interp0d(abs(iq))
        self._params["iq"] = iq
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
        lim = _get_opt(config, "limits", LIMITS_DEFAULT)
        iis = _get_opt(config["linreg"], "iis", IIS_DEFAULT)
        rt = _get_opt(config["linreg"], "rt", RT_DEFAULT)
        return cls(name, vo=v, vdrop=vd, iq=iq, limits=lim, iis=iis, rt=rt)

    def _get_inp_current(self, phase, phase_conf=[]):
        i = self._ipr._interp(0.0, 0.0)
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _get_outp_voltage(self, phase, phase_conf=[]):
        v = self._params["vo"]
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            v = 0.0
        return v

    def _solv_inp_curr(self, vi, vo, io, phase, phase_conf=[]):
        """Calculate component input current from vi, vo and io"""
        if abs(vi) == 0.0:
            return 0.0
        i = io + self._ipr._interp(abs(io), abs(vi))
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            i = self._params["iis"]
        return i

    def _solv_outp_volt(self, vi, ii, io, phase, phase_conf=[]):
        """Calculate component output voltage from vi, ii and io"""
        v = min(abs(self._params["vo"]), max(abs(vi) - self._params["vdrop"], 0.0))
        if not phase_conf:
            pass
        elif phase not in phase_conf:
            v = 0.0
        if self._params["vo"] >= 0.0:
            return v
        return -v

    def _solv_pwr_loss(self, vi, vo, ii, io, phase, phase_conf=[]):
        """Calculate power and loss in component"""
        v = min(abs(self._params["vo"]), max(abs(vi) - self._params["vdrop"], 0.0))
        if vi == 0.0 or v == 0.0:
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
        return pwr, loss, _get_eff(pwr, pwr - loss, 0.0), loss * self._params["rt"]

    def _solv_get_warns(self, vi, vo, ii, io, phase, phase_conf=[]):
        """Check limits"""
        if phase_conf:
            if phase not in phase_conf:
                return ""
        pi, pl, _, tr = self._solv_pwr_loss(vi, vo, ii, io, phase, phase_conf=[])
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
            ret["iq"] = abs(self._params["iq"])
        else:
            ret["iq"] = "interp"
        ret["iis"] = self._params["iis"]
        ret["rt"] = self._params["rt"]
        return ret
