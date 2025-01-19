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

"""Utilities.

sysLoss utility functions.
"""

RHO = 1.724e-8
"""Copper resistance, Ohm-meter (IPC spec for copper bulk resistivity at 20°C)"""
TCR = 0.00386
"""Copper temperature coefficient of resistance, Ohm/°C"""
MILS2MM = 0.0254
"""mils to mm conversion factor"""
OZ2MM = 0.034798
"""oz/ft^2 (copper ounce per square feet) to mm conversion factor"""


def trace_res(
    *,
    w1_mm: float,
    w2_mm: float,
    l_mm: float,
    t_mm: float,
    rho: float = RHO,
    temp: float = 20.0,
    tcr: float = TCR
) -> float:
    """Calculate PCB trace resistance.

    Trace resistance is calculated as :math:`R=\\frac{\\rho L}{A}`, where *A* is the cross-sectional
    area of the trace, *L* is trace length and :math:`\\rho` is material resistance.
    If the temperature is set to other than 20°C, the resistance value is adjusted
    with :math:`R_t = R \\cdot (1 + tcr \\cdot (temp - 20))`.


    Parameters
    ----------
    w1_mm : float
        Lower trace width in mm.
    w2_mm : float
        Upper trace width in mm.
    l_mm : float
        Trace length in mm.
    t_mm : float
        Trace thickness in mm.
    rho : float, optional
        Material resistance (Ohm-m), by default :py:attr:`~RHO`.
    temp: float, optional
        Ambient temperature, by default 20°C.
    tcr: float, optional
        Temperature coefficient of resistance (Ohm/°C), by default :py:attr:`~TCR`.

    Returns
    -------
    float
        Trace resistance (Ohm)

    Examples
    --------
    >>> rs = trace_res(w1_mm=1, w2_mm=1, l_mm=15, t_mm=35e-3)
    >>> # convert dimensions in mils and oz/ft^2 to mm by predefined constants:
    >>> rs = trace_res(w1_mm=7*MILS2MM, w2_mm=6*MILS2MM, l_mm=350*MILS2MM, t_mm=2*OZ2MM, temp=50)
    """

    a = 0.5 * (w1_mm + w2_mm) * t_mm / 1e3
    return (rho * l_mm / a) * (1 + tcr * (temp - 20.0))


def plane_res(
    *,
    w: float,
    l: float,
    t_mm: float,
    rho: float = RHO,
    temp: float = 20.0,
    tcr: float = TCR
) -> float:
    """Calculate PCB plane resistance.

    Plane (or sheet) resistance is calculated as :math:`R=R_s \\frac{L}{W}`, where *W* is the plane width,
    *L* is the plane length and *Rs* is the sheet resistance. *Rs* is calculated as :math:`R_s=\\frac{\\rho}{t}`,
    where :math:`\\rho` is material resistance and *t* is plane thickness.
    If the temperature is set to other than 20°C, the resistance value is adjusted
    with :math:`R_t = R \\cdot (1 + tcr \\cdot (temp - 20))`.


    Parameters
    ----------
    w : float
        Plane width (unitless).
    l : float
        Plane length (unitless).
    t_mm : float
        Plane thickness in mm.
    rho : float, optional
        Material resistance (Ohm-m), by default :py:attr:`~RHO`.
    temp: float, optional
        Ambient temperature, by default 20°C.
    tcr: float, optional
        Temperature coefficient of resistance (Ohm/°C), by default :py:attr:`~TCR`.

    Returns
    -------
    float
        Plane resistance (Ohm)

    Examples
    --------
    >>> rs = plane_res(w=25, l=80, t_mm=35e-3)
    >>> # convert dimension oz/ft^2 to mm by predefined constant:
    >>> rs = trace_res(w=800, l=500, t_mm==2*OZ2MM, temp=50)
    """

    rs = rho / (t_mm / 1e3)
    return (rs * l / w) * (1 + tcr * (temp - 20.0))
