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


__all__ = ["get_conf", "make_diag"]


_DEF_GRAPH_CONF = {
    "rankdir": "TB",
    "ranksep": "0.3 equally",
    "splines": "line",
    "nodesep": "0.3",
    "overlap": "scale",
    "dpi": "100",
}
_DEF_CLUSTER_CONF = {
    "default": {
        "rank": "same",
        "fillcolor": "white",
        "style": "filled",
        "penwidth": "1.5",
    }
}
_DEF_NODE_CONF = {
    "default": {
        "fillcolor": "white",
        "style": "filled",
        "shape": "box",
        "penwidth": "1.5",
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


def make_diag(sys: System, *, fname: str = None, group: bool = True, config: dict = {}):
    """Create power tree diagram.

    The default diagram is rendered as a top-bottom diagram with components represented
    as white, square boxes. Shapes and colors can be configured using an attribute dict.

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

    if config == {}:
        bd_conf = copy.deepcopy(_DEF_CONF)
    else:
        bd_conf = copy.deepcopy(config)
    graph = pydot.Dot("sysLoss", label=sys._g.attrs["name"], **bd_conf["graph"])

    def add_node(gr, name, attrs):
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
        gr.add_node(pydot.Node(name, **conf))

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
                    add_node(sg, n, bd_conf["node"])
            graph.add_subgraph(sg)
    # non-clustered nodes
    for n in sys._g.attrs["nodes"]:
        if sys._g.attrs["groups"][n] == "" or not group:
            add_node(graph, n, bd_conf["node"])
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
