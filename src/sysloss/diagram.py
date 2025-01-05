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

"""Power tree diagrams.

Graphviz is used to render power tree diagrams in sysLoss. 
The diagrams can be customized with the full range of Graphviz attributes.
"""

from sysloss.system import System
import copy, io
import pydot
from PIL import Image
import pandas as pd
import numpy as np
import matplotlib as mpl


__all__ = ["get_conf", "make_diag", "make_hdiag"]


_DEF_GRAPH_CONF = {
    "rankdir": "TB",
    "ranksep": "0.3 equally",
    "splines": "line",
    "nodesep": "0.3",
    "overlap": "scale",
    "dpi": "120",
    "fontname": "arial",
    "fontcolor": "black",
}
_DEF_CLUSTER_CONF = {
    "default": {
        "rank": "same",
        "fillcolor": "white",
        "style": "filled",
        "penwidth": "1.5",
        "fontname": "arial",
        "fontcolor": "black",
    }
}
_DEF_NODE_CONF = {
    "default": {
        "fillcolor": "gray95",
        "style": "filled",
        "shape": "box",
        "penwidth": "1.5",
        "fontname": "arial",
        "fontcolor": "black",
    }
}
_DEF_EDGE_CONF = {
    "arrowhead": "none",
    "headport": "center",
    "tailport": "center",
    "color": "black",
}
_DEF_CONF = {
    "graph": _DEF_GRAPH_CONF,
    "cluster": _DEF_CLUSTER_CONF,
    "node": _DEF_NODE_CONF,
    "edge": _DEF_EDGE_CONF,
}
_COLD_RGB = "#2120ff"
_WARM_RGB = "#ff1210"
_DEF_GRADIENT = {
    "fillcolor": _COLD_RGB + ":" + _WARM_RGB,
    "style": "filled",
    "gradientangle": "90",
    "shape": "record",
    "penwidth": ".0",
    "fontcolor": "silver",
    "fontname": "arial",
}


def get_conf() -> dict:
    """Get default Graphviz configuration.

    The Graphviz attributes used by sysLoss to format the diagram are returned in a dictionary.
    By modifying the attributes in the dictionary or adding new ones, the rendered diagram can
    be customized. The modified dict is passed as an argument to :py:meth:`sysloss.diagram.make_diag`.

    Returns
    -------
    dict
        Default Graphviz configuration.

    Examples
    --------
    >>> my_conf = get_conf()
    >>> my_conf["graph"]["rankdir"] = 'LR' # use left-right orientation
    >>> make_diag(my_sys, config=my_conf)
    """
    return copy.deepcopy(_DEF_CONF)


def _gcolor(mix: float):
    """Calculate heat color from mix value (0-1)"""
    c1 = np.array(mpl.colors.to_rgb(_COLD_RGB))
    c2 = np.array(mpl.colors.to_rgb(_WARM_RGB))
    return mpl.colors.to_hex((1 - mix) * c1 + mix * c2)


def _prep_loss(loss: pd.DataFrame, phases: dict = {}) -> pd.DataFrame:
    """Calculate loss and color for each component"""
    if phases != {}:
        df2 = loss[loss.Type != ""][["Component", "Loss (W)", "Phase"]]
        avg, w = np.zeros(len(df2) // len(phases), dtype=np.dtype(float)), 0.0
        for key in phases.keys():
            avg += phases[key] * df2[df2.Phase == key]["Loss (W)"].to_numpy().astype(
                np.dtype(float)
            )
            w += phases[key]
        avg = avg / w
        df = df2[df2.Phase == list(phases.keys())[0]].copy()
        df.update(pd.DataFrame(({"Loss (W)": avg})))
    else:
        df = loss[loss.Type != ""][["Component", "Loss (W)"]].copy()

    maxloss = df["Loss (W)"].max()
    if maxloss == 0.0:
        maxloss = 1.0
    df["Mix"] = df["Loss (W)"].to_numpy() / maxloss
    return df


def _nice_float(f):
    """Format floats with SI prefixes"""
    pwr = int("{:e}".format(f).split("e")[1])
    if pwr < -13 or pwr > 7:
        return "{:.2e}".format(f)
    elif pwr < -10:
        return "{}p".format(round(f * 1e12, 3 - (13 + pwr)))
    elif pwr < -7:
        return "{}n".format(round(f * 1e9, 3 - (10 + pwr)))
    elif pwr < -4:
        return "{}u".format(round(f * 1e6, 3 - (7 + pwr)))
    elif pwr < -1:
        return "{}m".format(round(f * 1e3, 3 - (4 + pwr)))
    elif pwr < 2:
        return "{}".format(round(f, 3 - (1 + pwr)))
    elif pwr < 5:
        return "{}k".format(round(f / 1e3, 5 - pwr))
    elif pwr < 8:
        return "{}M".format(round(f / 1e6, 8 - pwr))


def _diag(
    sys: System,
    *,
    fname: str = None,
    group: bool = True,
    config: dict = {},
    loss: pd.DataFrame = None
):
    """Create diagram"""
    if config == {}:
        bd_conf = copy.deepcopy(_DEF_CONF)
    else:
        bd_conf = copy.deepcopy(config)
    gname = sys._g.attrs["name"]
    if loss is not None:
        gname += " - Loss heat map"
    graph = pydot.Dot("sysLoss", label=gname, **bd_conf["graph"])

    def add_node(gr, name, attrs, ldf):
        comp = type(sys._g[sys._g.attrs["nodes"][name]]).__name__
        conf = copy.deepcopy(attrs["default"])
        # component type overrieds
        if comp in attrs:
            for key in attrs[comp]:
                conf[key] = attrs[comp][key]
        # component instance overrides
        if name in attrs:
            for key in attrs[name]:
                conf[key] = attrs[name][key]
        if ldf is not None:
            conf["fillcolor"] = _gcolor(ldf[ldf.Component == name]["Mix"].to_list()[0])
            conf["fontcolor"] = "silver"
            conf["label"] = "{}\n{}W".format(
                name, _nice_float(ldf[ldf.Component == name]["Loss (W)"].to_list()[0])
            )
        gr.add_node(pydot.Node(name, **conf))

    # heat diagram operations
    ldf = None
    if loss is not None:
        ldf = _prep_loss(loss, sys.get_sys_phases())

    # find groups
    groups = {}
    for n in sys._g.attrs["groups"].keys():
        g = sys._g.attrs["groups"][n]
        if g != "":
            groups[g] = 1
    # create clusters
    if group and groups != {}:
        for g in groups.keys():
            cconf = copy.deepcopy(bd_conf["cluster"]["default"])
            if g in bd_conf["cluster"]:
                for key in bd_conf["cluster"][g]:
                    cconf[key] = bd_conf["cluster"][g][key]
            sg = pydot.Subgraph("cluster_" + g, label=g, **cconf)
            for n in sys._g.attrs["nodes"]:
                if sys._g.attrs["groups"][n] == g:
                    add_node(sg, n, bd_conf["node"], ldf)
            graph.add_subgraph(sg)
    # non-clustered nodes
    for n in sys._g.attrs["nodes"]:
        if sys._g.attrs["groups"][n] == "" or not group:
            add_node(graph, n, bd_conf["node"], ldf)
    # color gradient
    if loss is not None:
        gconf = copy.deepcopy(_DEF_GRADIENT)
        gconf["label"] = "{}W|  |  | 0W".format(_nice_float(ldf["Loss (W)"].max()))
        rd = bd_conf["graph"]["rankdir"]
        if rd == "TB" or rd == "BT":
            gconf["label"] = "{" + gconf["label"] + "}"
        graph.add_node(pydot.Node("Scale", **gconf))
    # edges
    p = dict(zip(sys._g.attrs["nodes"].values(), sys._g.attrs["nodes"].keys()))
    for e in iter(sys._g.edge_indices()):
        ep = sys._g.get_edge_endpoints_by_index(e)
        graph.add_edge(pydot.Edge(p[ep[0]], p[ep[1]], **bd_conf["edge"]))
    # output image
    if fname == None:
        img = Image.open(io.BytesIO(graph.create_png(prog="dot")))
        return img
    graph.write(fname, prog="dot", format=fname.split(".")[-1])
    return None


def make_diag(sys: System, *, fname: str = None, group: bool = True, config: dict = {}):
    """Create power tree diagram.

    The default diagram is rendered as a top-bottom diagram with components represented
    as light-grey, square boxes. Shapes and colors can be configured using an attribute dict.

    Parameters
    ----------
    fname : str, optional
        Filename for output image. File extension defines image format.
    group : bool, optional
        Cluster components based on group names, by default True.
    config: dict, optional
        Graphviz configuration.

    Returns
    -------
    None
        If filename is given.
    PIL.Image
        If no filename is given

    Examples
    --------
    >>> img = make_diag(my_sys)
    >>> make_diag(my_sys, fname="system.svg") # write to file
    >>> # add custom colors to components
    >>> my_conf = get_conf()
    >>> my_conf["node"]["Source"] = {"fillcolor":"coral"}
    >>> my_conf["node"]["Converter"] = {"fillcolor":"darkturquoise"}
    >>> my_conf["node"]["ILoad"] = {"fillcolor":"darkgoldenrod1"}
    >>> my_conf["node"]["RLoss"] = {"fillcolor":"deeppink"}
    >>> my_conf["node"]["LinReg"] = {"fillcolor":"darkorchid1"}
    >>> my_conf["node"]["PSwitch"] = {"fillcolor":"aquamarine"}
    >>> make_diag(my_sys, fname="system.svg", config=my_conf)
    """
    return _diag(sys, fname=fname, group=group, config=config, loss=None)


def make_hdiag(
    sys: System, *, fname: str = None, group: bool = True, config: dict = {}
):
    """Create power tree heat diagram.

    The system is first solved to find the losses in each component. If the system has load phases
    defined, the time-weighted loss is used in the diagram.
    The default diagram is rendered as a top-bottom diagram with components represented
    as gradient-colored, square boxes. Shapes and colors can be configured using an attribute dict,
    although component (node) colors will be overridden by gradient color.

    Parameters
    ----------
    fname : str, optional
        Filename for output image. File extension defines image format.
    group : bool, optional
        Cluster components based on group names, by default True.
    config: dict, optional
        Graphviz configuration.

    Returns
    -------
    None
        If filename is given.
    PIL.Image
        If no filename is given

    Examples
    --------
    >>> img = make_hdiag(my_sys)
    >>> make_hdiag(my_sys, fname="system.svg") # write to file
    """
    df = sys.solve()
    return _diag(sys, fname=fname, group=group, config=config, loss=df)
