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

""":py:class:`~system.System` is the primary class for power analysis."""


import rustworkx as rx
import numpy as np
from rich.tree import Tree
from rich import print
import json
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import LinearLocator
from scipy.interpolate import LinearNDInterpolator
from typing import Callable
import warnings
from packaging import version
from tqdm import TqdmExperimentalWarning
from warnings import warn

warnings.filterwarnings("ignore", category=TqdmExperimentalWarning)
from tqdm.autonotebook import tqdm

from sysloss.components import *
from sysloss.components import (
    _ComponentTypes,
    _get_opt,
    _get_mand,
    _get_eff,
    _Interp1d,
    _Interp2d,
    RS_DEFAULT,
    IG_DEFAULT,
    LIMITS_DEFAULT,
    STATE_DEFAULT,
)
import sysloss


class System:
    """System to be analyzed.

    The first component of a system must always be a :py:class:`~components.Source`.

    Parameters
    ----------
    name : str
        System name.
    source : Source
        Source component.
    group : str, optional
        Group name, for grouping components together.
    rail : str, optional
        Voltage rail name of output voltage.

    Raises
    ------
    ValueError
        If `source` is not a Source class.

    Examples
    --------
    >>> sys = System("System name", Source("Vin", vo=12.0))

    """

    def __init__(self, name: str, source: Source, *, group: str = "", rail: str = ""):
        """Class constructor"""
        self._g = None
        if not isinstance(source, Source):
            raise ValueError("First component of system must be a source!")

        self._g = rx.PyDAG(check_cycle=True, multigraph=False, attrs={})
        cidx = self._g.add_node(source)
        self._g.attrs["name"] = name
        self._g.attrs["phases"] = {}
        self._g.attrs["phase_conf"] = {}
        self._g.attrs["phase_conf"][source._params["name"]] = {}
        self._g.attrs["nodes"] = {}
        self._g.attrs["nodes"][source._params["name"]] = cidx
        self._g.attrs["groups"] = {}
        self._g.attrs["groups"][source._params["name"]] = group
        self._g.attrs["rails"] = {}
        self._g.attrs["rails"][source._params["name"]] = rail
        self._g.attrs["pnames"] = {}
        self._g.attrs["pnames"][cidx] = []

    @classmethod
    def from_file(cls, fname: str):
        """Load system from .json file.

        The .json file must previously have been saved with :py:meth:`~system.System.save`.

        Parameters
        ----------
        fname : str
            File name.

        Returns
        -------
        System
            A new `System` instance.

        Raises
        ------
        ValueError
            If file was created by a newer version of sysLoss.

        Examples
        --------
        >>> sys = System.from_file("my_system.json")

        """
        with open(fname, "r") as f:
            sys = json.load(f)

        entires = list(sys.keys())
        sysparams = _get_mand(sys, "system")
        sysname = _get_mand(sysparams, "name")
        ver = _get_mand(sysparams, "version")
        # check version compatability
        if version.parse(sysloss.__version__) < version.parse(ver):
            raise ValueError(
                '"{}" was created by sysLoss version {} - please update sysLoss to load this file'.format(
                    fname, ver
                )
            )
        # add sources/pmux
        for e in range(1, len(entires)):
            if sys[entires[e]]["type"] == "SOURCE":
                vo = _get_mand(sys[entires[e]]["params"], "vo")
            rs = _get_opt(sys[entires[e]]["params"], "rs", RS_DEFAULT)
            lim = _get_opt(sys[entires[e]], "limits", LIMITS_DEFAULT)
            if e == 1:
                self = cls(sysname, Source(entires[e], vo=vo, rs=rs, limits=lim))
            else:
                if sys[entires[e]]["type"] == "SOURCE":
                    self.add_source(Source(entires[e], vo=vo, rs=rs, limits=lim))
                else:
                    ig = _get_opt(sys[entires[e]]["params"], "ig", IG_DEFAULT)
                    iis = _get_opt(sys[entires[e]]["params"], "iis", 0.0)
                    rt = _get_opt(sys[entires[e]]["params"], "rt", 0.0)
                    self.add_comp(
                        sys[entires[e]]["parents"],
                        comp=PMux(entires[e], rs=rs, ig=ig, iis=iis, rt=rt, limits=lim),
                    )
            # add childs
            if sys[entires[e]]["childs"] != {}:
                for p in list(sys[entires[e]]["childs"].keys()):
                    for c in sys[entires[e]]["childs"][p]:
                        cname = _get_mand(c["params"], "name")
                        limits = _get_opt(c, "limits", LIMITS_DEFAULT)
                        iq = _get_opt(c["params"], "iq", 0.0)
                        ig = _get_opt(c["params"], "ig", 0.0)
                        rs = _get_opt(c["params"], "rs", 0.0)
                        iis = _get_opt(c["params"], "iis", 0.0)
                        rt = _get_opt(c["params"], "rt", 0.0)
                        if c["type"] == "CONVERTER":
                            vo = _get_mand(c["params"], "vo")
                            eff = _get_mand(c["params"], "eff")
                            self.add_comp(
                                p,
                                comp=Converter(
                                    cname,
                                    vo=vo,
                                    eff=eff,
                                    iq=iq,
                                    limits=limits,
                                    iis=iis,
                                    rt=rt,
                                ),
                            )
                        elif c["type"] == "LINREG":
                            vo = _get_mand(c["params"], "vo")
                            vdrop = _get_opt(c["params"], "vdrop", 0.0)
                            self.add_comp(
                                p,
                                comp=LinReg(
                                    cname,
                                    vo=vo,
                                    vdrop=vdrop,
                                    iq=iq,
                                    ig=ig,
                                    limits=limits,
                                    iis=iis,
                                    rt=rt,
                                ),
                            )
                        elif c["type"] == "SLOSS":
                            if "rs" in c["params"]:
                                rs = _get_mand(c["params"], "rs")
                                self.add_comp(
                                    p, comp=RLoss(cname, rs=rs, rt=rt, limits=limits)
                                )
                            else:
                                vdrop = _get_mand(c["params"], "vdrop")
                                self.add_comp(
                                    p,
                                    comp=VLoss(
                                        cname, vdrop=vdrop, rt=rt, limits=limits
                                    ),
                                )
                        elif c["type"] == "LOAD":
                            loss = _get_opt(c["params"], "loss", False)
                            if "pwr" in c["params"]:
                                pwr = _get_mand(c["params"], "pwr")
                                pwrs = _get_opt(c["params"], "pwrs", 0.0)
                                self.add_comp(
                                    p,
                                    comp=PLoad(
                                        cname,
                                        pwr=pwr,
                                        limits=limits,
                                        pwrs=pwrs,
                                        rt=rt,
                                        loss=loss,
                                    ),
                                )
                            elif "rs" in c["params"]:
                                rs = _get_mand(c["params"], "rs")
                                self.add_comp(
                                    p,
                                    comp=RLoad(
                                        cname, rs=rs, rt=rt, limits=limits, loss=loss
                                    ),
                                )
                            else:
                                ii = _get_mand(c["params"], "ii")
                                self.add_comp(
                                    p,
                                    comp=ILoad(
                                        cname,
                                        ii=ii,
                                        limits=limits,
                                        iis=iis,
                                        rt=rt,
                                        loss=loss,
                                    ),
                                )
                        elif c["type"] == "PSWITCH":
                            self.add_comp(
                                p,
                                comp=PSwitch(
                                    cname,
                                    rs=rs,
                                    ig=ig,
                                    limits=limits,
                                    iis=iis,
                                    rt=rt,
                                ),
                            )
                        elif c["type"] == "RECTIFIER":
                            vdrop = _get_opt(c["params"], "vdrop", 0.0)
                            self.add_comp(
                                p,
                                comp=Rectifier(
                                    cname,
                                    rs=rs,
                                    ig=ig,
                                    iq=iq,
                                    limits=limits,
                                    rt=rt,
                                ),
                            )
        phases = _get_opt(sysparams, "phases", {})
        self._g.attrs["phases"] = phases
        phase_conf = _get_mand(sysparams, "phase_conf")
        self._g.attrs["phase_conf"] = phase_conf
        groups = _get_opt(sysparams, "groups", {})
        if groups == {}:
            for key in phase_conf:
                groups[key] = ""
        self._g.attrs["groups"] = groups
        rails = _get_opt(sysparams, "rails", {})
        if rails == {}:
            for key in phase_conf:
                rails[key] = ""
        self._g.attrs["rails"] = rails

        return self

    def _get_index(self, name: str):
        """Get node index from component name"""
        if name in self._g.attrs["nodes"]:
            return self._g.attrs["nodes"][name]
        if name in self._g.attrs["rails"].values():
            cname = [
                i for i in self._g.attrs["rails"] if self._g.attrs["rails"][i] == name
            ]
            return self._g.attrs["nodes"][cname[0]]

        return -1

    def _chk_parent(self, parent: str):
        """Check if parent exists"""
        if (
            parent in self._g.attrs["nodes"].keys()
            or parent in self._g.attrs["rails"].values()
        ):
            return True

        raise ValueError('Parent name "{}" not found!'.format(parent))

    def _chk_comp(self, comp: str):
        """Check if component exists"""
        if not comp in self._g.attrs["nodes"].keys():
            raise ValueError('Component name "{}" not found!'.format(comp))

        return True

    def _chk_name(self, name: str, rail: str):
        """Check if component/rail name is valid"""
        if name in self._g.attrs["nodes"].keys() or (
            name in self._g.attrs["rails"].values()
        ):
            raise ValueError('Component name "{}" is already used!'.format(name))
        if rail != "":
            if name == rail:
                raise ValueError("Component name and rail name cannot be the same!")
            if (
                rail in self._g.attrs["nodes"].keys()
                or rail in self._g.attrs["rails"].values()
            ):
                raise ValueError('Rail name "{}" is already used!'.format(name))

        return True

    def _get_childs_tree(self, node: int):
        """Get dict of parent/childs"""
        childs = list(rx.bfs_successors(self._g, node))
        cdict = {}
        for c in childs:
            cs = []
            for l in c[1]:
                cs += [self._g.attrs["nodes"][l._params["name"]]]
            cdict[self._g.attrs["nodes"][c[0]._params["name"]]] = cs
        return cdict

    def _get_nodes(self):
        """Get list of nodes in system"""
        return [n for n in self._g.node_indices()]

    def _get_childs(self):
        """Get list of children of each node"""
        nodes = self._get_nodes()
        cs = list(-np.ones(max(nodes) + 1, dtype=np.int32))
        for n in nodes:
            if self._g.out_degree(n) > 0:
                ind = [i for i in self._g.successor_indices(n)]
                cs[n] = ind
        return cs

    def _get_parents(self):
        """Get list of parent of each node"""
        nodes = self._get_nodes()
        ps = list(-np.ones(max(nodes) + 1, dtype=np.int32))
        for n in nodes:
            if self._g.in_degree(n) > 0:
                ind = [i for i in self._g.predecessor_indices(n)]
                if len(ind) > 1:
                    for i in range(len(ind)):
                        ind[i] = self._get_index(self._g.attrs["pnames"][n][i])
                ps[n] = ind
        return ps

    def _get_sources(self):
        """Get list of sources"""
        tn = [n for n in rx.topological_sort(self._g)]
        return [n for n in tn if isinstance(self._g[n], Source)]

    def _get_pmux(self):
        """Get index of pmux"""
        tn = [n for n in rx.topological_sort(self._g)]
        pl = [n for n in tn if isinstance(self._g[n], PMux)]
        if pl == []:
            return -1
        return pl[0]

    def _get_topo_sort(self):
        """Get nodes topological sorted"""
        tps = rx.topological_sort(self._g)
        return [n for n in tps]

    def _sys_vars(self):
        """Get system variable lists"""
        vn = max(self._get_nodes()) + 1  # highest node index + 1
        self._g.attrs["hidx"] = vn
        v = np.zeros(vn)  # voltages
        i = np.zeros(vn)  # currents
        s = [{} for x in range(vn)]
        return v, i, s

    def _make_rtree(self, adj, node):
        """Create Rich tree"""
        tree = Tree(node)
        for child in adj.get(node, []):
            tree.add(self._make_rtree(adj, child))
        return tree

    def add_comp(self, parent: str | list, *, comp, group: str = "", rail: str = ""):
        """Add component to system.

        Parameters
        ----------
        parent : str | list
            Name of parent component(s) or power rail(s) to connect to.
        comp : component
            Component (from :py:mod:`~sysloss.components`).
        group : str, optional
            Group name, for grouping components together.
        rail : str, optional
            Voltage rail name of output voltage (not applicable on loads). Must be unique.

        Raises
        ------
        ValueError
            If parent does not allow connection to component, or name is already used.

        Examples
        --------
        >>> sys.add_comp("Vin", comp=Converter("Buck", vo=1.8, eff=0.87), rail="IO_1V8")
        >>> sys.add_comp("Buck", comp=PLoad("MCU", pwr=0.015), group="Main")
        >>> sys.add_comp(["Vbatt", "USB_5V"], comp=PMux("Power mux", rs=[0.35, 0.4]))

        """
        # check that parent(s) are valid
        if isinstance(parent, list):
            if len(parent) > len(set(parent)):
                raise ValueError("parent paramenter contains duplicates!")
            if comp._component_type != _ComponentTypes.PMUX:
                raise ValueError("only PMux component can have multiple inputs!")
            for p in parent:
                self._chk_parent(p)
            plist = parent
        else:
            self._chk_parent(parent)
            plist = [parent]
        # check that component name is unique
        self._chk_name(comp._params["name"], rail)
        # check that parent(s) allows component type as child
        pidx = []
        for p in plist:
            pidx += [self._get_index(p)]
            if not comp._component_type in self._g[pidx[-1]]._child_types:
                raise ValueError(
                    "Parent {} does not allow child of type {}!".format(
                        p, comp._component_type.name
                    )
                )
        # can only have one pmux
        if comp._component_type.name == "PMUX":
            for key in self._g.attrs["nodes"]:
                if self._g[self._g.attrs["nodes"][key]]._component_type.name == "PMUX":
                    raise ValueError("a system can only have one PMux")
        # all ok, add component
        cidx = self._g.add_child(pidx[0], comp, None)
        self._g.attrs["nodes"][comp._params["name"]] = cidx
        self._g.attrs["phase_conf"][comp._params["name"]] = {}
        self._g.attrs["groups"][comp._params["name"]] = group
        self._g.attrs["pnames"][cidx] = plist
        if comp._component_type == _ComponentTypes.LOAD and rail != "":
            warn(
                "rail parameter ignored, not applicable on loads",
                stacklevel=2,
            )
            self._g.attrs["rails"][comp._params["name"]] = ""
        else:
            self._g.attrs["rails"][comp._params["name"]] = rail
        if len(pidx) > 1:
            for p in range(1, len(pidx), 1):
                self._g.add_edge(pidx[p], cidx, None)

    def add_source(self, source: Source, *, group: str = "", rail: str = ""):
        """Add an additional Source to the system.

        Parameters
        ----------
        source : Source
            Source component.
        group : str, optional
            Group name, for grouping components together.
        rail : str, optional
            Voltage rail name of output voltage. Must be unique.

        Raises
        ------
        ValueError
            If `source` is not a Source class or name is already used.

        Examples
        --------
        >>> sys.add_source(Source("5V", vo=5.0, limits={"io": [0.0, 0.5]}))

        """
        self._chk_name(source._params["name"], rail)
        if not isinstance(source, Source):
            raise ValueError("Component must be a source!")

        cidx = self._g.add_node(source)
        self._g.attrs["nodes"][source._params["name"]] = cidx
        self._g.attrs["phase_conf"][source._params["name"]] = {}
        self._g.attrs["groups"][source._params["name"]] = group
        self._g.attrs["rails"][source._params["name"]] = rail
        self._g.attrs["pnames"][cidx] = []

    def change_comp(self, name: str, *, comp, group: str = "", rail: str = ""):
        """Replace component.

        The new component can be of same type (parameter change), or a new type
        given that the parent component accepts the connection.

        Parameters
        ----------
        name : str
            Name of component to be changed.
        comp : component
            Component (from :py:mod:`~sysloss.components`).
        group : str, optional
            Group name, for grouping components together.
        rail : str, optional
            Voltage rail name of output voltage (not applicable on loads). Must be unique.

        Raises
        ------
        ValueError
            If trying to change a `source` component to a different type, or
            if the target component does not exist or
            if the parent does not accept a connection to the new component or
            if the name is already used.

        Examples
        --------
        >>> sys.change_comp("Buck", comp=LinReg("LDO", vo=1.8))

        """
        # check that component exists
        self._chk_comp(name)
        # if component/rail name changes, check that it is unique
        if name != comp._params["name"]:
            self._chk_name(comp._params["name"], rail)

        eidx = self._get_index(name)
        # source can only be changed to source
        if self._g[eidx]._component_type == _ComponentTypes.SOURCE:
            if not isinstance(comp, Source):
                raise ValueError("Source cannot be changed to other type!")

        # pmux can only be changed to pmux
        if self._g[eidx]._component_type == _ComponentTypes.PMUX:
            if not isinstance(comp, PMux):
                raise ValueError("PMux cannot be changed to other type!")

        # check that parent allows component type as child
        parents = self._get_parents()
        if parents[eidx] != -1:
            if not comp._component_type in self._g[parents[eidx][0]]._child_types:
                raise ValueError(
                    "Parent does not allow child of type {}!".format(
                        comp._component_type.name
                    )
                )
        self._g[eidx] = comp
        # replace node name in graph dict
        del [self._g.attrs["nodes"][name]]
        self._g.attrs["nodes"][comp._params["name"]] = eidx
        # delete old phase config and set new default
        del [self._g.attrs["phase_conf"][name]]
        self._g.attrs["phase_conf"][comp._params["name"]] = {}
        # delete old group and set new
        del [self._g.attrs["groups"][name]]
        self._g.attrs["groups"][comp._params["name"]] = group
        # delete old rail and set new
        del [self._g.attrs["rails"][name]]
        if comp._component_type == _ComponentTypes.LOAD and rail != "":
            warn(
                "rail parameter ignored, not applicable on loads",
                stacklevel=2,
            )
            self._g.attrs["rails"][comp._params["name"]] = ""
        else:
            self._g.attrs["rails"][comp._params["name"]] = rail

    def del_comp(self, name: str, *, del_childs: bool = True):
        """Delete component.

        Deleting the last component (Source) in a system is not allowed.
        In a system with multiple sources, a source can only be deleted
        together with its child components.

        Parameters
        ----------
        name : str
            Name of component to delete.
        del_childs : bool, optional
            Delete all child components as well., by default True

        Raises
        ------
        ValueError
            If the component does not exist, is the last source or
            a source with `del_childs` set to False.

        Examples
        --------
        >>> sys.del_comp("Buck", del_childs=True)

        """
        eidx = self._get_index(name)
        if eidx == -1:
            raise ValueError("Component name does not exist!")
        parents = self._get_parents()
        if parents[eidx] == -1:  # source node
            if not del_childs:
                raise ValueError("Source must be deleted with its childs")
            if len(self._get_sources()) < 2:
                raise ValueError("Cannot delete the last source component!")
        childs = self._get_childs()
        # if not leaf, check if child type is allowed by parent type (not possible?)
        # if leaves[eidx] == 0:
        #     for c in childs[eidx]:
        #         if not self._g[c]._component_type in self._g[parents[eidx]]._child_types:
        #             raise ValueError(
        #                 "Parent and child of component are not compatible!"
        #             )
        # delete childs first if selected
        if del_childs:
            for c in rx.descendants(self._g, eidx):
                del [self._g.attrs["nodes"][self._g[c]._params["name"]]]
                del [self._g.attrs["phase_conf"][self._g[c]._params["name"]]]
                del [self._g.attrs["groups"][self._g[c]._params["name"]]]
                del [self._g.attrs["rails"][self._g[c]._params["name"]]]
                self._g.remove_node(c)
        # delete node
        self._g.remove_node(eidx)
        del [self._g.attrs["nodes"][name]]
        del [self._g.attrs["phase_conf"][name]]
        del [self._g.attrs["groups"][name]]
        del [self._g.attrs["rails"][name]]
        # restore links between new parent and childs, unless deleted
        if not del_childs:
            if childs[eidx] != -1:
                for c in childs[eidx]:
                    self._g.add_edge(parents[eidx][0], c, None)

    def tree(self, name=""):
        """Print the tree structure of the system.

        The tree object is generated with `Rich <https://rich.readthedocs.io>`_.

        Parameters
        ----------
        name : str, optional
            Name of component to start with. If not given, print the entire system., by default ""

        Raises
        ------
        ValueError
            If the component name is invalid.


        Examples
        --------
        >>> sys.tree()
        >>> sys.tree("5V")

        """
        if not name == "":
            if not name in self._g.attrs["nodes"].keys():
                raise ValueError("Component name is not valid!")
            root = [name]
        else:
            ridx = self._get_sources()
            root = [self._g[n]._params["name"] for n in ridx]

        t = Tree(self._g.attrs["name"])
        for n in root:
            adj = rx.bfs_successors(self._g, self._g.attrs["nodes"][n])
            ndict = {}
            for i in adj:
                c = []
                for j in i[1]:
                    c += [j._params["name"]]
                ndict[i[0]._params["name"]] = c
            t.add(self._make_rtree(ndict, n))
        print(t)

    def _set_phase_lkup(self):
        """Make lookup from node # to load phases"""
        self._phase_lkup = {}
        for c in self._g.attrs["phase_conf"].items():
            self._phase_lkup[self._get_index(c[0])] = c[1]

    def _sys_init(self, phase: str = ""):
        """Create vectors of init values for solver"""
        v, i, state = self._sys_vars()
        self._set_phase_lkup()
        for n in self._get_nodes():
            v[n] = self._g[n]._get_outp_voltage(phase, self._phase_lkup[n])
            i[n] = self._g[n]._get_inp_current(phase, self._phase_lkup[n])
            p = self._parents[n]
            if p != -1:
                state[n]["off"] = [
                    self._g[i]._get_state(phase, self._phase_lkup[i])["off"][0]
                    for i in p
                ]
            else:
                state[n] = self._g[n]._get_state(phase, self._phase_lkup[n])
        return v, i, state

    def _child_curr(self, node, i, v, state):
        """Find sum of currents into childs"""
        io, pstate = 0.0, {}
        for c in self._childs[node]:
            pp = self._parents[c]
            vc = [v[c]]
            pstate["off"] = state[node]["off"]
            if pp != -1:
                vc = [v[i] for i in pp]
                pstate["off"] = [state[i]["off"][0] for i in pp]
            pinp = self._g[c]._get_pri_inp(pstate, vc)
            if pinp != -1 and len(pp) > 1:
                if pp[pinp] == node:
                    io += i[c]
            else:
                io += i[c]
        return io

    def _fwd_prop(self, v: float, i: float, phase: str = "", state: list = []):
        """Forward propagation of voltages"""
        vo = np.zeros(self._g.attrs["hidx"])
        ostate = [{} for x in range(self._g.attrs["hidx"])]
        # update output voltages (per node)
        for n in self._topo_nodes:
            p = self._parents[n]
            phase_config = self._phase_lkup[n]
            vi, ii, io, pstate = [0.0], 0.0, 0.0, {}
            if p != -1:  # not root
                vi = [v[i] for i in p]
                ii = i[n]
                pstate["off"] = [state[i]["off"][0] for i in p]
            else:
                vi = [v[n]]
                pstate["off"] = state[n]["off"]
            if self._childs[n] != -1:  # not leaf
                # sum currents into childs
                io = self._child_curr(n, i, v, state)
            vo[n], ostate[n] = self._g[n]._solv_outp_volt(
                vi, ii, io, phase, phase_config, pstate
            )

        return vo, ostate

    def _back_prop(self, v: float, i: float, phase: str = "", state: list = []):
        """Backward propagation of currents"""
        ii = np.zeros(self._g.attrs["hidx"])
        # update input currents (per node)
        for n in self._topo_nodes[::-1]:
            p = self._parents[n]
            phase_config = self._phase_lkup[n]
            vi, vo, io, pstate = [0.0], 0.0, 0.0, {}
            if p == -1:  # root
                vi = [v[n]]
                pstate["off"] = state[n]["off"]
            else:
                vi = [v[i] for i in p]
                pstate["off"] = [state[i]["off"][0] for i in p]
            if self._childs[n] != -1:  # not leaf
                vo = v[n]
                # sum currents into childs
                io = self._child_curr(n, i, v, state)
            ii[n] = self._g[n]._solv_inp_curr(vi, vo, io, phase, phase_config, pstate)

        return ii

    def _rel_update(self):
        """Update lists with component relationships"""
        self._parents = self._get_parents()
        self._childs = self._get_childs()
        self._topo_nodes = self._get_topo_sort()

    def _get_parent_name(self, node):
        """Get parent name of node"""
        if self._parents[node] == -1:
            return ""
        return self._g[self._parents[node][0]]._params["name"]

    def _solve(self, vtol=1e-5, itol=1e-6, maxiter=10000, quiet=True, phase: str = ""):
        """Solver"""
        v, i, state = self._sys_init(phase)
        iters = 0
        while iters <= maxiter:
            vi, ostate = self._fwd_prop(v, i, phase, state)
            ii = self._back_prop(vi, i, phase, state)
            iters += 1
            if np.allclose(np.array(v), np.array(vi), rtol=vtol) and np.allclose(
                np.array(i), np.array(ii), rtol=itol
            ):
                if not quiet:
                    pname = ""
                    if phase != "":
                        pname = "'{}': ".format(phase)
                    print("{}Tolerances met after {} iterations".format(pname, iters))
                break
            v, i, state = vi, ii, ostate
        return v, i, iters, state

    def _calc_energy(self, phase, pwr):
        """Calculate energy per 24h"""
        if phase == "":
            return pwr * 24.0
        tot_time = 0.0
        for ph in self._g.attrs["phases"].keys():
            tot_time += self._g.attrs["phases"][ph]
        cycles = 24 * 3600.0 / tot_time
        return (self._g.attrs["phases"][phase] / 3600.0) * pwr * cycles

    def _find_domain(self, n, domain, v):
        """Find voltage domain"""
        if self._g[n]._component_type.name == "SOURCE":
            return self._g[n]._params["name"]
        elif self._g[n]._component_type.name == "PMUX":
            p = self._parents[n]
            vin = [v[i] for i in p]
            idx = 0
            for i in reversed(range(len(vin))):
                if abs(vin[i]) != 0.0:
                    idx = i
            an = rx.ancestors(self._g, p[idx])
            if an == set():
                return self._g[p[idx]]._params["name"]
            for i in an:
                if self._g.in_degree(i) == 0:
                    return self._g[i]._params["name"]
        return domain

    def solve(
        self,
        *,
        vtol: float = 1e-6,
        itol: float = 1e-6,
        maxiter: int = 10000,
        quiet: bool = True,
        phase: str = "",
        energy: bool = False,
        ta: float = 25.0,
        tags: dict = {},
    ) -> pd.DataFrame:
        """Analyze steady-state of system.

        Parameters
        ----------
        vtol : float, optional
            Voltage tolerance., by default 1e-6
        itol : float, optional
            Current tolerance., by default 1e-6
        maxiter : int, optional
            Maximum number of iterations., by default 10000
        quiet : bool, optional
            Do not print # of iterations used., by default True
        phase : str, optional
            Load phase to analyze (all if not specified), by default ""
        energy : bool, optional
            Show energy consumption per 24h., by default False
        ta :  float, optional
            Ambient temperature, by default 25.0°C
        tags: dict, optional
            Tag-value pairs that will be added to the results table

        Returns
        -------
        pd.DataFrame
            Analysis result.

        Raises
        ------
        ValueError
            If the specified phase is not defined. See :py:meth:`~system.System.set_phases`.
        RuntimeError
            If a steady-state solution has not been found after `maxiter` iterations.

        Examples
        --------
        >>> sys.solve()
        >>> sys.solve(energy=True)
        >>> sys.solve(itol=1.0e-7, tags={"Column name": value})

        """
        self._rel_update()
        phase_list = [""]
        if phase != "":
            if phase not in list(self._g.attrs["phases"].keys()):
                raise ValueError(
                    "The specified phase '{}' is not defined".format(phase)
                )
            phase_list = [phase]
        elif len(list(self._g.attrs["phases"].keys())) > 0:
            phase_list = list(self._g.attrs["phases"].keys())
        # solve
        ppwr, ploss, peff, ptime, pener, pcurr = [], [], [], [], [], []
        frames = []
        for ph in phase_list:
            v, i, iters, state = self._solve(vtol, itol, maxiter, quiet, ph)
            if iters > maxiter:
                raise RuntimeError(
                    "Steady-state not achieved after {} iterations".format(iters - 1)
                )
            # calculate results for each node
            names, parent, typ, pwr, loss, trise, tpeak = [], [], [], [], [], [], []
            eff, warn, vsi, iso, vso, isi = [], [], [], [], [], []
            domain, phases, ener, dname, group, rail = [], [], [], "none", [], []
            sources, dwarns, rail_in, pstate = {}, {}, [], {}
            show_trise = False
            for n in self._topo_nodes:  # [vi, vo, ii, io]
                phase_config = self._phase_lkup[n]
                name = self._g[n]._params["name"]
                names += [name]
                dname = self._find_domain(n, dname, v)
                domain += [dname]
                phases += [ph]
                group += [self._g.attrs["groups"][name]]
                rail += [self._g.attrs["rails"][name]]
                vi = v[n]
                vo = v[n]
                ii = i[n]
                io = i[n]
                p = self._parents[n]

                if p == -1:
                    pstate["off"] = state[n]["off"]
                    vv = [v[n]]
                else:
                    pstate["off"] = [state[i]["off"][0] for i in p]
                    vv = [v[i] for i in p]
                pn = self._get_parent_name(n)
                if p == -1:  # root
                    vi = v[n] + self._g[n]._params["rs"] * ii
                else:
                    pinp = self._g[n]._get_pri_inp(pstate, vv)
                    if pinp != -1 and len(p) > 1:
                        vi = v[p[pinp]]
                        pn = self._get_parent_name(p[pinp])
                    else:
                        vi = v[p[0]]
                    if self._childs[n] == -1:  # leaf
                        io = 0.0
                    else:
                        io = self._child_curr(n, i, v, state)

                parent += [pn]
                if pn != "":
                    rail_in += [self._g.attrs["rails"][pn]]
                else:
                    rail_in += [""]
                p, l, e, tr, tp = self._g[n]._solv_pwr_loss(
                    vi, vo, ii, io, ta, ph, phase_config
                )
                pwr += [p]
                loss += [l]
                if self._g[n]._component_type.name == "SOURCE":
                    trise += [""]
                    tpeak += [""]
                else:
                    trise += [tr]
                    tpeak += [tp]
                    if tr > 0.0:
                        show_trise = True
                eff += [e]
                typ += [self._g[n]._component_type.name]
                ener += [self._calc_energy(ph, p)]
                if self._g[n]._component_type.name == "SOURCE":
                    sources[dname] = vi
                    dwarns[dname] = 0
                w = self._g[n]._solv_get_warns(vi, vo, ii, io, ta, ph, phase_config)
                warn += [w]
                if w != "":
                    dwarns[dname] = 1
                vsi += [vi]
                iso += [io]
                vso += [v[n]]
                isi += [i[n]]

            # subsystems summary
            for d in range(len(sources)):
                names += ["Subsystem {}".format(list(sources.keys())[d])]
                typ += [""]
                parent += [""]
                domain += [""]
                phases += [ph]
                group += [""]
                rail += [""]
                rail_in += [""]
                vsi += [sources[list(sources.keys())[d]]]
                vso += [""]
                isi += [""]
                iso += [""]
                pwr += [""]
                loss += [""]
                trise += [""]
                tpeak += [""]
                eff += [""]
                ener += [""]
                if dwarns[list(sources.keys())[d]] > 0:
                    warn += ["Yes"]
                else:
                    warn += [""]

            # system total
            names += ["System total"]
            typ += [""]
            parent += [""]
            domain += [""]
            phases += [ph]
            group += [""]
            rail += [""]
            rail_in += [""]
            vsi += [""]
            vso += [""]
            isi += [""]
            iso += [""]
            pwr += [""]
            loss += [""]
            trise += [""]
            tpeak += [""]
            eff += [""]
            ener += [""]
            if any(warn):
                warn += ["Yes"]
            else:
                warn += [""]

            # report
            res = {}
            res["Component"] = names
            res["Type"] = typ
            if any(["" != x for x in rail]):
                res["Rail in"] = rail_in
            else:
                res["Parent"] = parent
            res["Domain"] = domain
            if any(["" != x for x in group]):
                res["Group"] = group
            if tags != {}:
                for key in tags.keys():
                    res[key] = [tags[key]] * len(names)
            if ph != "":
                res["Phase"] = phases
            res["Vin (V)"] = vsi
            res["Vout (V)"] = vso
            if any(["" != x for x in rail]):
                res["Rail out"] = rail
            res["Iin (A)"] = isi
            res["Iout (A)"] = iso
            res["Power (W)"] = pwr
            res["Loss (W)"] = loss
            res["Efficiency (%)"] = eff
            if show_trise:
                res["Temp. rise (°C)"] = trise
                res["Peak temp. (°C)"] = tpeak
            if energy:
                res["24h energy (Wh)"] = ener
            res["Warnings"] = warn
            df = pd.DataFrame(res)

            # update subsystem current/power/loss/efficiency/energy
            for d in range(len(sources)):
                src = list(sources.keys())[d]
                idx = df[df.Component == "Subsystem {}".format(src)].index[0]
                curr = df[(df.Domain == src) & (df.Type == "SOURCE")][
                    "Iout (A)"
                ].values[0]
                df.at[idx, "Iout (A)"] = curr
                pwr = df[(df.Domain == src) & (df.Type == "SOURCE")][
                    "Power (W)"
                ].values[0]
                df.at[idx, "Power (W)"] = pwr
                loss = df[df.Domain == src]["Loss (W)"].sum()
                df.at[idx, "Loss (W)"] = loss
                df.at[idx, "Efficiency (%)"] = _get_eff(pwr, pwr - loss)
                if energy:
                    df.at[idx, "24h energy (Wh)"] = self._calc_energy(ph, pwr)

            # update system total
            pwr = df[(df.Domain == "") & (df["Power (W)"] != "")]["Power (W)"].sum()
            idx = df.index[-1]
            df.at[idx, "Power (W)"] = pwr
            loss = df[(df.Domain == "") & (df["Loss (W)"] != "")]["Loss (W)"].sum()
            df.at[idx, "Loss (W)"] = loss
            df.at[idx, "Efficiency (%)"] = _get_eff(pwr, pwr - loss)
            if energy:
                df.at[idx, "24h energy (Wh)"] = self._calc_energy(ph, pwr)
            if len(sources) < 2:
                df.at[idx, "Iout (A)"] = curr
            if len(phase_list) > 1:
                ploss += [loss]
                ppwr += [pwr]
                peff += [_get_eff(pwr, pwr - loss)]
                pcurr += [curr]
                ptime += [self._g.attrs["phases"][ph]]
                pener += [self._calc_energy(ph, pwr)]
            # if only one subsystem, delete subsystem row and domain column
            if len(sources) < 2:
                df.drop(len(df) - 2, inplace=True)
                df.drop(columns="Domain", inplace=True)
                df.reset_index(inplace=True, drop=True)
            frames += [df]

        if len(phase_list) > 1:
            ttot = np.sum(np.asarray(ptime))
            apwr = np.sum(np.multiply(np.asarray(ppwr), np.asarray(ptime))) / ttot
            aloss = np.sum(np.multiply(np.asarray(ploss), np.asarray(ptime))) / ttot
            aeff = np.sum(np.multiply(np.asarray(peff), np.asarray(ptime))) / ttot
            acurr = np.sum(np.multiply(np.asarray(pcurr), np.asarray(ptime))) / ttot
            vals = ["System average", apwr, aloss, aeff]
            idxs = ["Component", "Power (W)", "Loss (W)", "Efficiency (%)"]
            if len(sources) < 2:
                vals += [acurr]
                idxs += ["Iout (A)"]
            if energy:
                vals += [self._calc_energy("", apwr)]
                idxs += ["24h energy (Wh)"]
            if tags != {}:
                for key in tags.keys():
                    idxs += [key]
                    vals += [tags[key]]
            avg = pd.Series(vals, index=idxs)
            frames += [avg.to_frame().T]
        dff = pd.concat(frames, ignore_index=True)
        return dff.replace(np.nan, "")

    def rail_rep(
        self,
        *,
        vtol: float = 1e-6,
        itol: float = 1e-6,
        maxiter: int = 10000,
        quiet: bool = True,
        phase: str = "",
        energy: bool = False,
        ta: float = 25.0,
        tags: dict = {},
    ) -> pd.DataFrame:
        """Voltage rail report.

        The rail report first calls .solve(), then summarizes current, power and losses
        per voltage rail.

        Parameters
        ----------
        * :
            Parameters are identical to :py:meth:`~system.System.solve`.

        Returns
        -------
        pd.DataFrame
            Analysis result. If no voltage rails have been defined, the result is identical
            to that returned by :py:meth:`~system.System.solve`.

        Raises
        ------
        ValueError
            If the specified phase is not defined. See :py:meth:`~system.System.set_phases`.
        RuntimeError
            If a steady-state solution has not been found after `maxiter` iterations.

        Examples
        --------
        >>> sys.rail_rep()
        """
        df = self.solve(
            vtol=vtol,
            itol=itol,
            maxiter=maxiter,
            quiet=quiet,
            phase=phase,
            energy=energy,
            ta=ta,
            tags=tags,
        )
        if "Phase" in df:
            phase_list = df["Phase"].unique().tolist()
            if "" in phase_list:
                phase_list.remove("")
        else:
            phase_list = [""]

        if "Rail in" in df:
            rails = df["Rail in"].unique().tolist()
            rails.remove("")
            rail, vin, iin, pwr, loss, eff = [], [], [], [], [], []
            warn, phases, res = [], [], {}
            if len(rails) > 0:
                for ph in phase_list:
                    for r in rails:
                        rail += [r]
                        phases += [ph]
                        if ph != "":
                            filt = (df["Rail in"] == r) & (df["Phase"] == ph)
                        else:
                            filt = df["Rail in"] == r
                        vin += [df[filt]["Vin (V)"].tolist()[0]]
                        iin += [sum(df[filt]["Iin (A)"])]
                        p = sum(df[filt]["Power (W)"])
                        pwr += [p]
                        l = sum(df[filt]["Loss (W)"])
                        loss += [l]
                        if l == 0.0:
                            eff += [100.0]
                        else:
                            eff += [100 * p / (p + l)]
                        w = list(set(df[filt]["Warnings"].tolist()))
                        if len(w) > 1:
                            if "" in w:
                                w.remove("")
                            warn += [", ".join(w)]
                        else:
                            warn += [""]
                if phase_list != [""]:
                    res["Phase"] = phases
                res["Rail"] = rail
                res["Voltage (V)"] = vin
                res["Current (A)"] = iin
                res["Power (W)"] = pwr
                res["Loss (W)"] = loss
                res["Efficiency (%)"] = eff
                res["Warnings"] = warn
                return pd.DataFrame(res)
        else:
            return df

    def _filt_lim(self, node: int, key: str) -> list:
        """Filter out default limit values"""
        limits = _get_opt(self._g[node]._limits, key, "")
        if limits == LIMITS_DEFAULT[key]:
            return ""
        return limits

    def _pars_and_limits(
        self, params: bool = True, limits: bool = False
    ) -> pd.DataFrame:
        """Return component parameters and limits"""
        self._rel_update()
        names, typ, vo, vdrop, ig, loss = [], [], [], [], [], []
        iq, rs, rt, eff, ii, pwr, iis, ltr, ltp = [], [], [], [], [], [], [], [], []
        lii, lio, lvi, lvo, lpi, lpo, lpl, pwrs = [], [], [], [], [], [], [], []
        lvd = []

        for n in self._topo_nodes:
            names += [self._g[n]._params["name"]]
            typ += [self._g[n]._component_type.name]
            if params:
                pdict = {
                    "vo": "",
                    "vdrop": "",
                    "ig": "",
                    "iq": "",
                    "rs": "",
                    "rt": "",
                    "eff": "",
                    "ii": "",
                    "pwr": "",
                    "iis": "",
                    "pwrs": "",
                    "loss": "",
                }
                cparams = self._g[n]._get_params(pdict)
                vo += [cparams["vo"]]
                vdrop += [cparams["vdrop"]]
                ig += [cparams["ig"]]
                iq += [cparams["iq"]]
                rs += [cparams["rs"]]
                rt += [cparams["rt"]]
                eff += [cparams["eff"]]
                ii += [cparams["ii"]]
                pwr += [cparams["pwr"]]
                iis += [cparams["iis"]]
                pwrs += [cparams["pwrs"]]
                loss += [cparams["loss"]]
            if limits:
                lii += [self._filt_lim(n, "ii")]
                lio += [self._filt_lim(n, "io")]
                lvi += [self._filt_lim(n, "vi")]
                lvo += [self._filt_lim(n, "vo")]
                lvd += [self._filt_lim(n, "vd")]
                lpi += [self._filt_lim(n, "pi")]
                lpo += [self._filt_lim(n, "po")]
                lpl += [self._filt_lim(n, "pl")]
                ltr += [self._filt_lim(n, "tr")]
                ltp += [self._filt_lim(n, "tp")]
        # report
        res = {}
        res["Component"] = names
        res["Type"] = typ
        limstr = ""
        if params:
            res["vo (V)"] = vo
            res["vdrop (V)"] = vdrop
            res["rs (Ohm)"] = rs
            res["rt (°C/W)"] = rt
            res["eff (%)"] = eff
            res["ig (A)"] = ig
            res["iq (A)"] = iq
            res["ii (A)"] = ii
            res["iis (A)"] = iis
            res["pwr (W)"] = pwr
            res["pwrs (W)"] = pwrs
            res["loss"] = loss
            limstr = "limit"
        if limits:
            res["vi {} (V)".format(limstr)] = lvi
            res["vo {} (V)".format(limstr)] = lvo
            res["vd {} (V)".format(limstr)] = lvd
            res["ii {} (A)".format(limstr)] = lii
            res["io {} (A)".format(limstr)] = lio
            res["pi {} (W)".format(limstr)] = lpi
            res["po {} (W)".format(limstr)] = lpo
            res["pl {} (W)".format(limstr)] = lpl
            res["tr {} (°C)".format(limstr)] = ltr
            res["tp {} (°C)".format(limstr)] = ltp
        return pd.DataFrame(res)

    def params(self, limits: bool = False) -> pd.DataFrame:
        """Return component parameters.

        Parameters
        ----------
        limits : bool, optional
            Include limits., by default False

        Returns
        -------
        pd.DataFrame
            System component parameters.

        Examples
        --------
        >>> sys.params()
        >>> sys.params(limits=True)

        """
        return self._pars_and_limits(params=True, limits=limits)

    def limits(self) -> pd.DataFrame:
        """Return component limits.

        A blank cell in the returned Pandas dataframe indicates that default limits apply.

        Returns
        -------
        pd.DataFrame
            System component limits.

        Examples
        --------
        >>> sys.limits()

        """
        return self._pars_and_limits(params=False, limits=True)

    def set_sys_phases(self, phases: dict):
        """Define system level load phases.

        Parameters
        ----------
        phases : dict
            A dict defining the system level load phases.
            Each entry in the form '"name": duration(s)'.

        Raises
        ------
        ValueError
            If the dict contains less than two load phases or 'N/A' is used as
            a phase name.

        Examples
        --------
        >>> sys.set_sys_phases({"sleep": 120.0, "transmit": 0.1, "move": 5.5})

        """
        if len(list(phases.keys())) < 2 and phases != {}:
            raise ValueError("There must be at least two phases!")
        if "N/A" in list(phases.keys()):
            raise ValueError('"N/A" is a reserved name!')
        self._g.attrs["phases"] = phases

    def get_sys_phases(self) -> dict:
        """Get the system level load phases.

        Returns
        -------
        dict
            System load phases. Empty dict if no phases have been defined.

        Examples
        --------
        >>> sys.get_sys_phases()
        {"sleep": 120.0, "transmit": 0.1, "move": 5.5}

        """
        return self._g.attrs["phases"]

    def set_comp_phases(self, name: str, phase_conf: dict | list):
        """Define component load phases.

        Components that have no load phases defined are always active.

        The :py:class:`~components.Source`, :py:class:`~components.Converter`, :py:class:`~components.Linreg`,
        :py:class:`~components.PSwitch` and :py:class:`~components.PMux`
        components support a list of active phases, and go
        into sleep mode if not active. In sleep mode, all components connected to the
        output are automatically turned off.

        The load components supports a dict with specific load values for each phase. If
        a phase is not included in the dict, the load is turned off in that phase.

        Parameters
        ----------
        name : str
            Component name.
        phase_conf : dict | list
            Phase configuration.

        Raises
        ------
        ValueError
            Component does not exist, or phase configuration is invalid.

        Examples
        --------
        >>> sys.set_comp_phases("Buck", ["transmit", "move"])
        >>> sys.set_comp_phases("MCU", {"sleep":1e-6, "transmit":0.15, "move":0.085})

        """
        cidx = self._get_index(name)
        if cidx == -1:
            raise ValueError("Component name does not exist!")
        if not isinstance(phase_conf, dict) and not isinstance(phase_conf, list):
            raise ValueError("phase_conf must be a dict or list!")
        if isinstance(self._g[cidx], RLoss) or isinstance(self._g[cidx], VLoss):
            raise ValueError("Loss components does not support load phases!")

        self._g.attrs["phase_conf"][name] = phase_conf

    def phases(self) -> pd.DataFrame:
        """Return load phases and parameters for all system components.

        Returns
        -------
        pd.DataFrame
            DataFrame with parameters and load phases.

        Examples
        --------
        >>> sys.phases()

        """
        self._rel_update()
        if self._g.attrs["phases"] == {}:
            return None
        names, typ, phase = [], [], []
        rs, ii, pwr = [], [], []
        domain, dname = [], "none"
        phase_names = list(self._g.attrs["phases"].keys())
        self._set_phase_lkup()
        src_cnt = 0
        for n in self._topo_nodes:
            tname = self._g[n]._component_type.name
            if tname == "SOURCE":
                dname = self._g[n]._params["name"]
                src_cnt += 1
            ph_names = []
            if tname == "SLOSS":
                ph_names += ["N/A"]
            elif (
                tname == "CONVERTER"
                or tname == "LINREG"
                or tname == "PSWITCH"
                or tname == "PMUX"
                or tname == "SOURCE"
            ):
                if len(self._phase_lkup[n]) > 0:
                    for p in phase_names:
                        if p in self._phase_lkup[n]:
                            ph_names += [p]
                if ph_names == []:
                    ph_names += ["N/A"]
            elif tname == "LOAD":
                if len(list(self._phase_lkup[n].keys())) > 0:
                    for p in phase_names:
                        if p in list(self._phase_lkup[n].keys()):
                            ph_names += [p]
                if ph_names == []:
                    ph_names += ["N/A"]

            for p in ph_names:
                names += [self._g[n]._params["name"]]
                typ += [tname]
                domain += [dname]
                phase += [p]
                if tname == "LOAD":
                    if "pwr" in self._g[n]._params:
                        rs += [""]
                        ii += [""]
                        if p == "N/A":
                            pwr += [self._g[n]._params["pwr"]]
                        else:
                            pwr += [self._phase_lkup[n][p]]
                    elif "rs" in self._g[n]._params:
                        ii += [""]
                        pwr += [""]
                        if p == "N/A":
                            rs += [self._g[n]._params["rs"]]
                        else:
                            rs += [self._phase_lkup[n][p]]
                    else:
                        rs += [""]
                        pwr += [""]
                        if p == "N/A":
                            ii += [self._g[n]._params["ii"]]
                        else:
                            ii += [self._phase_lkup[n][p]]
                else:
                    rs += [""]
                    ii += [""]
                    pwr += [""]

        # report
        res = {}
        res["Component"] = names
        res["Type"] = typ
        if src_cnt > 1:
            res["Domain"] = domain
        res["Active phase"] = phase
        res["rs (Ohm)"] = rs
        res["ii (A)"] = ii
        res["pwr (W)"] = pwr
        return pd.DataFrame(res)

    def _get_applims(self, idx):
        """Get applicable limits for component"""
        lims = self._g[idx]._get_limits()
        limits = {}
        for lim in lims:
            limits[lim] = _get_opt(self._g[idx]._limits, lim, LIMITS_DEFAULT[lim])
        return limits

    def save(self, fname: str, *, indent: int = 4):
        """Save system as a .json file.

        Parameters
        ----------
        fname : str
            Filename.
        indent : int, optional
            Indentation to use in .json file, by default 4

        Examples
        --------
        >>> sys.save("System 42.json", indent=3)

        """
        self._rel_update()
        sys = {
            "system": {
                "name": self._g.attrs["name"],
                "version": sysloss.__version__,
                "phases": self._g.attrs["phases"],
                "phase_conf": self._g.attrs["phase_conf"],
                "groups": self._g.attrs["groups"],
                "rails": self._g.attrs["rails"],
            }
        }
        ridx = self._get_sources()
        pidx = self._get_pmux()
        pdidx = []
        if pidx != -1:
            pdidx = rx.descendants(self._g, pidx)
        root = [self._g[n]._params["name"] for n in ridx]
        # components to pmux
        for r in range(len(ridx)):
            tree = self._get_childs_tree(ridx[r])
            cdict = {}
            if tree != {}:
                for e in tree:
                    childs = []
                    for c in tree[e]:
                        if c != pidx and c not in pdidx:
                            childs += [
                                {
                                    "type": self._g[c]._component_type.name,
                                    "params": self._g[c]._params,
                                    "limits": self._get_applims(c),
                                }
                            ]
                    cdict[self._g[e]._params["name"]] = childs
            sys[root[r]] = {
                "type": self._g[ridx[r]]._component_type.name,
                "params": self._g[ridx[r]]._params,
                "limits": self._get_applims(ridx[r]),
                "childs": cdict,
            }
        # pmux and childs
        if pidx != -1:
            tree = self._get_childs_tree(pidx)
            cdict = {}
            if tree != {}:
                for e in tree:
                    childs = []
                    for c in tree[e]:
                        childs += [
                            {
                                "type": self._g[c]._component_type.name,
                                "params": self._g[c]._params,
                                "limits": self._get_applims(c),
                            }
                        ]
                    cdict[self._g[e]._params["name"]] = childs
            sys[self._g[pidx]._params["name"]] = {
                "type": self._g[pidx]._component_type.name,
                "params": self._g[pidx]._params,
                "limits": self._get_applims(pidx),
                "childs": cdict,
                "parents": [self._g[n]._params["name"] for n in self._parents[pidx]],
            }

        with open(fname, "w") as f:
            json.dump(sys, f, indent=indent)

    def plot_interp(
        self,
        name: str,
        *,
        cmap: matplotlib.colors.Colormap = "viridis",
        inpdata: bool = True,
        plot3d: bool = False,
    ) -> matplotlib.figure.Figure | None:
        """Plot 1D or 2D interpolation data.

        If a component has a parameter defined as either 1D or 2D interpolation data,
        a figure is returned with linear interpolation shown. 1D data is plotted as an
        interpolated line. 2D data can be shown as 2D color map or 3D surface. The
        interpolated data is extended to +/-15% outside of input data points.

        Parameters
        ----------
        name : str
            Name of component.
        cmap : matplotlib.colors.Colormap, optional
            Colormap to use for 3D-plot., by default "viridis"
        inpdata : bool, optional
            Show input data (as red dots)., by default True
        plot3d : bool, optional
            Plot 3D surface (for 2D data), by default False

        Returns
        -------
        matplotlib.figure.Figure | None
            Interpolated parameter data figure. If the component does not have interpolation
            data, `None` is returned.

        Raises
        ------
        ValueError
            If component name is not found.

        Examples
        --------
        >>> fig1 = sys.plot_interp("Buck", cmap="magma")
        >>> fig2 = sys.plot_interp("Buck", inpdata=False, plot3d=True)

        """
        if not name in self._g.attrs["nodes"].keys():
            raise ValueError("Component name is not valid!")
        n = self._g.attrs["nodes"][name]
        if isinstance(self._g[n]._ipr, _Interp1d):
            annot = self._g[n]._get_annot()
            fig = plt.figure()
            xmin = max(self._g[n]._ipr._x[0] - 0.15 * max(self._g[n]._ipr._x), 0.0)
            xmax = 1.15 * max(self._g[n]._ipr._x)
            x = np.linspace(xmin, xmax, num=200)
            fx = np.interp(x, self._g[n]._ipr._x, self._g[n]._ipr._fx)
            plt.plot(x, fx, "-")
            if inpdata:
                plt.plot(
                    self._g[n]._ipr._x, self._g[n]._ipr._fx, ".r", label="input data"
                )
                plt.legend(loc="lower right")
            plt.xlabel(annot[0])
            plt.ylabel(annot[1])
            plt.title(annot[2])
            plt.rc("axes", axisbelow=True)
            plt.grid()
            return fig
        elif isinstance(self._g[n]._ipr, _Interp2d):
            annot = self._g[n]._get_annot()
            xmin = max(min(self._g[n]._ipr._x) - 0.15 * max(self._g[n]._ipr._x), 0.0)
            xmax = 1.15 * max(self._g[n]._ipr._x)
            X = np.linspace(xmin, xmax, num=100)
            ymin = max(min(self._g[n]._ipr._y) - 0.15 * max(self._g[n]._ipr._y), 0.0)
            ymax = 1.15 * max(self._g[n]._ipr._y)
            Y = np.linspace(ymin, ymax, num=100)
            X, Y = np.meshgrid(X, Y)
            interp = LinearNDInterpolator(
                list(zip(self._g[n]._ipr._x, self._g[n]._ipr._y)), self._g[n]._ipr._fxy
            )
            Z = interp(X, Y)
            for i in range(len(X)):
                for j in range(len(Y)):
                    if np.isnan(Z[i, j]):
                        Z[i, j] = self._g[n]._ipr._interp(X[i, j], Y[i, j])
            if not plot3d:
                fig = plt.figure()
                plt.pcolormesh(X, Y, Z, shading="auto", cmap=cmap)
                if inpdata:
                    plt.plot(
                        self._g[n]._ipr._x, self._g[n]._ipr._y, ".r", label="input data"
                    )
                    plt.legend(loc="upper left")
                plt.colorbar()
                plt.xlabel(annot[0])
                plt.ylabel(annot[1])
            else:
                fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
                surf = ax.plot_surface(
                    Y, X, Z, cmap=cmap, linewidth=0, antialiased=False
                )
                if self._g[n]._component_type.name == "CONVERTER":
                    ax.set_zlim(np.nanmin(Z), 1.0)
                else:
                    ax.set_zlim(np.nanmin(Z), np.nanmax(Z))
                ax.zaxis.set_major_locator(LinearLocator(10))
                ax.zaxis.set_major_formatter("{x:.02f}")
                if inpdata:
                    plt.plot(
                        self._g[n]._ipr._y,
                        self._g[n]._ipr._x,
                        self._g[n]._ipr._fxy,
                        ".r",
                        label="input data",
                    )
                    plt.legend(loc="upper left")
                fig.colorbar(surf, shrink=0.5, aspect=10, pad=0.1)
                # labels swapped
                plt.xlabel(annot[1])
                plt.ylabel(annot[0])
            plt.title(annot[2])
            return fig
        else:
            print("Component does not have interpolation data")
            return None

    def batt_life(
        self,
        battery: str,
        *,
        cutoff: float,
        pfunc: Callable[[], tuple[float, float, float]],
        dfunc: Callable[[float, float], tuple[float, float, float]],
        tags: dict = {},
    ) -> pd.DataFrame:
        """Estimate battery life.

        Battery life estimation requires an external battery model. The battery model is
        accessed using two callback functions - one for battery probing and one for
        battery depletion. If system load phases have been defined, the estimation process
        loops through the phases until the battery is depleted or the cutoff voltage has been
        reached. In a system without load phases the process depletes the battery in ~1000
        time steps.

        Parameters
        ----------
        battery : str
            Name of battery (source) to be depleted
        cutoff : float
            End simulation when battery voltage reaches cutoff or capacity is depleted,
            whichever comes first.
        pfunc : Callable[[], tuple[float, float, float]]
            Battery probe callback function, must return tuple with remaining capacity (Ah),
            battery voltage (V) and battery impedance (Ohm)
        dfunc : Callable[[float, float], tuple[float, float, float]]
            Battery deplete callback function. Function arguments are time (s) and
            current (A). Must return tuple with same format as pfunc.
        tags: dict, optional
            Tag-value pairs that will be added to the results table

        Returns
        -------
        pd.DataFrame
            Battery depletion data.

        Raises
        ------
        ValueError
            If battery name is not found or component is not a source.

        Examples
        --------
        >>> sys.batt_life("LiPo 3.7V", cutoff=2.9, pfunc=my_probe_func, dfunc=my_deplete_func)

        """
        # check for valid source
        self._chk_parent(battery)
        pidx = self._get_index(battery)
        if not isinstance(self._g[pidx], Source):
            raise ValueError("Battery must be a source!")
        # keep current source params
        vo_org = self._g[pidx]._params["vo"]
        rs_org = self._g[pidx]._params["rs"]
        # probe/deplete returns (capacity, voltage, rs)
        bstate = pfunc()
        t = [0.0]
        cap = [bstate[0]]
        volt = [bstate[1]]
        rs = [bstate[2]]
        phase_list = [""]
        if len(list(self._g.attrs["phases"].keys())) > 0:
            phase_list = list(self._g.attrs["phases"].keys())
        # deplete args: time, current
        unit, mult = "Ah", 1.0
        if bstate[0] < 100.0:
            unit, mult = "mAh", 1000.0
        self._rel_update()
        cdelta = 0.0
        phidx = 0
        with tqdm(
            range(int(mult * cap[0])),
            desc="Battery depletion ({})".format(unit),
            unit=unit,
            unit_scale=True,
            unit_divisor=1000,
        ) as pbar:
            while bstate[0] > 0.0 and bstate[1] > cutoff:
                self._g[pidx]._params["vo"] = bstate[1]
                self._g[pidx]._params["rs"] = bstate[2]
                _, i, _, _ = self._solve(phase=phase_list[phidx])
                if phase_list == [""]:
                    deltat = (cap[0] / i[pidx]) * 3.6
                else:
                    deltat = self._g.attrs["phases"][phase_list[phidx]]
                bstate = dfunc(deltat, i[pidx])
                cdelta += (cap[-1] - bstate[0]) * mult
                pbar.update(int(cdelta))
                cdelta -= int(cdelta)
                phidx = (phidx + 1) % len(phase_list)
                if bstate[0] > 0.0 and bstate[1] > cutoff:
                    t += [t[-1] + deltat]
                    cap += [bstate[0]]
                    volt += [bstate[1]]
                    rs += [bstate[2]]
            pbar.total = int(mult * cap[0] - cdelta)
            pbar.close()
        # restore source params
        self._g[pidx]._params["vo"] = vo_org
        self._g[pidx]._params["rs"] = rs_org
        # result
        res = {}
        res["Time (s)"] = t
        res["Capacity (Ah)"] = cap
        res["Voltage (V)"] = volt
        res["Resistance (Ohm)"] = rs
        if tags != {}:
            for key in tags.keys():
                res[key] = [tags[key]] * len(t)
        return pd.DataFrame(res)
