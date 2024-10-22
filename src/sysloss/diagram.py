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
import copy
from rustworkx.visualization import graphviz_draw


__all__ = ["get_conf", "make_diag"]

_DEF_NODE_CONF = {
    "default": {
        "fillcolor": "white",
        "style": "filled",
        "shape": "box",
        "penwidth": "1.5",
    }
}

_DEF_GRAPH_CONF = {
    "rankdir": "TB",
    "ranksep": "equally",
    "splines": "line",
    "nodesep": "0.5",
    "overlap": "scale",
    "dpi": "100",
}
_DEF_EDGE_CONF = {"arrowhead": "none", "headport": "center", "tailport": "center"}

_DEF_CONF = {"graph": _DEF_GRAPH_CONF, "node": _DEF_NODE_CONF, "edge": _DEF_EDGE_CONF}


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


def make_diag(sys: System, *, fname: str = None, config: dict = {}):
    """Create power tree diagram.

    The default diagram is rendered as a top-bottom diagram with components represented
    as white, square boxes. Shapes and colors can be configured using an attribute dict.

    Parameters
    ----------
    fname : str, optional
        Filename for output image. File extension defines image format.
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

    def node_attr(node):
        conf = copy.deepcopy(bd_conf["node"]["default"])
        conf["label"] = node._params["name"]
        comp = type(node).__name__
        if comp in bd_conf["node"]:
            for key in bd_conf["node"][comp]:
                conf[key] = bd_conf["node"][comp][key]
        return conf

    def edge_attr(edge):
        return bd_conf["edge"]

    if fname == None:
        img_type = "png"
    else:
        img_type = fname.split(".")[-1]

    bd_conf["graph"]["label"] = '"' + sys._g.attrs["name"] + '"'

    return graphviz_draw(
        sys._g,
        node_attr_fn=node_attr,
        edge_attr_fn=edge_attr,
        graph_attr=bd_conf["graph"],
        filename=fname,
        image_type=img_type,
    )
