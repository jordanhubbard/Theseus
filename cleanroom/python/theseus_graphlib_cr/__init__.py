"""
theseus_graphlib_cr — Clean-room implementation of Python's graphlib module.

Implements TopologicalSorter and CycleError without importing the original
stdlib `graphlib` module. Uses only Python built-ins.
"""


# ---------------------------------------------------------------------------
# CycleError
# ---------------------------------------------------------------------------

class CycleError(ValueError):
    """Raised by TopologicalSorter.prepare() if a cycle is detected.

    The second element of args is a list of nodes describing the cycle, with
    the first node duplicated at the end (so adjacent pairs in the list form
    edges of the cycle).
    """

    def __init__(self, message, cycle):
        super().__init__(message, cycle)
        # Ensure args mirrors stdlib layout
        self.args = (message, cycle)


# ---------------------------------------------------------------------------
# Internal node bookkeeping
# ---------------------------------------------------------------------------

# Node lifecycle states
_NEW = 0       # added but not yet ready
_READY = 1     # passed out via get_ready()
_DONE = 2      # caller called done()

# DFS colors for cycle detection
_WHITE = 0     # unvisited
_GRAY = 1      # on the current DFS stack
_BLACK = 2     # fully explored


class _NodeInfo:
    __slots__ = ("node", "npredecessors", "successors", "state")

    def __init__(self, node):
        self.node = node
        # number of predecessors not yet completed
        self.npredecessors = 0
        # nodes that depend on this one (i.e. node -> successor edges)
        self.successors = []
        self.state = _NEW


# ---------------------------------------------------------------------------
# TopologicalSorter
# ---------------------------------------------------------------------------

class TopologicalSorter:
    """Provides functionality to topologically sort a graph of hashable nodes."""

    def __init__(self, graph=None):
        self._node2info = {}
        self._ready_nodes = None  # None until prepare() is called
        self._npassedout = 0
        self._nfinished = 0

        if graph is not None:
            for node, predecessors in graph.items():
                self.add(node, *predecessors)

    # -- internal helpers ------------------------------------------------

    def _get_nodeinfo(self, node):
        info = self._node2info.get(node)
        if info is None:
            info = _NodeInfo(node)
            self._node2info[node] = info
        return info

    # -- public API ------------------------------------------------------

    def add(self, node, *predecessors):
        """Add a node and zero or more predecessors that must come before it."""
        if self._ready_nodes is not None:
            raise ValueError(
                "Nodes cannot be added after a call to prepare()"
            )
        node_info = self._get_nodeinfo(node)
        node_info.npredecessors += len(predecessors)
        for pred in predecessors:
            pred_info = self._get_nodeinfo(pred)
            pred_info.successors.append(node)

    def prepare(self):
        """Mark the graph as finished and check for cycles.

        Raises CycleError if any cycle is found.
        """
        if self._ready_nodes is not None:
            raise ValueError("cannot prepare() more than once")

        cycle = self._find_cycle()
        if cycle is not None:
            raise CycleError("nodes are in a cycle", cycle)

        self._ready_nodes = [
            info.node
            for info in self._node2info.values()
            if info.npredecessors == 0
        ]

    def get_ready(self):
        """Return a tuple of nodes whose predecessors are all complete."""
        if self._ready_nodes is None:
            raise ValueError("prepare() must be called first")

        result = tuple(self._ready_nodes)
        n2i = self._node2info
        for node in result:
            n2i[node].state = _READY
        self._npassedout += len(result)
        self._ready_nodes = []
        return result

    def is_active(self):
        """Return True while there is still work to dispatch or complete."""
        if self._ready_nodes is None:
            raise ValueError("prepare() must be called first")
        return self._nfinished < self._npassedout or bool(self._ready_nodes)

    def __bool__(self):
        return self.is_active()

    def done(self, *nodes):
        """Mark previously-ready nodes as completed; release their successors."""
        if self._ready_nodes is None:
            raise ValueError("prepare() must be called first")

        n2i = self._node2info
        for node in nodes:
            info = n2i.get(node)
            if info is None:
                raise ValueError(
                    f"node {node!r} was not added using add()"
                )
            stat = info.state
            if stat != _READY:
                if stat == _DONE:
                    raise ValueError(
                        f"node {node!r} was already marked done"
                    )
                # _NEW -> never passed out
                raise ValueError(
                    f"node {node!r} was not passed out "
                    f"(still not ready)"
                )

            for succ in info.successors:
                succ_info = n2i[succ]
                succ_info.npredecessors -= 1
                if succ_info.npredecessors == 0:
                    self._ready_nodes.append(succ)
            self._nfinished += 1
            info.state = _DONE

    def static_order(self):
        """Yield nodes in a complete topological order."""
        self.prepare()
        while self.is_active():
            node_group = self.get_ready()
            yield from node_group
            self.done(*node_group)

    # -- cycle detection -------------------------------------------------

    def _find_cycle(self):
        """Iterative DFS that returns a cycle (list of nodes) or None."""
        n2i = self._node2info
        color = {n: _WHITE for n in n2i}

        for start in n2i:
            if color[start] != _WHITE:
                continue
            # Each stack frame: (node, iterator-over-successors)
            color[start] = _GRAY
            path = [start]
            stack = [(start, iter(n2i[start].successors))]

            while stack:
                node, succ_iter = stack[-1]
                advanced = False
                for succ in succ_iter:
                    c = color.get(succ, _WHITE)
                    if c == _GRAY:
                        # Found a back-edge -> cycle
                        try:
                            idx = path.index(succ)
                        except ValueError:
                            idx = 0
                        cycle = path[idx:]
                        cycle.append(succ)
                        return cycle
                    if c == _WHITE:
                        color[succ] = _GRAY
                        path.append(succ)
                        stack.append((succ, iter(n2i[succ].successors)))
                        advanced = True
                        break
                    # _BLACK: fully explored, ignore
                if not advanced:
                    color[node] = _BLACK
                    path.pop()
                    stack.pop()
        return None


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def _is_topo_order(order, deps):
    """Verify that `order` respects all (node -> predecessors) edges."""
    pos = {n: i for i, n in enumerate(order)}
    for node, preds in deps.items():
        if node not in pos:
            return False
        for pred in preds:
            if pred not in pos:
                return False
            if pos[pred] >= pos[node]:
                return False
    return True


def graphlib2_topo():
    """Verify that TopologicalSorter produces a valid topological ordering."""
    deps = {
        2: {11},
        9: {11, 8},
        10: {11, 3},
        11: {7, 5},
        8: {7, 3},
    }
    ts = TopologicalSorter(deps)
    ts.prepare()
    order = []
    while ts.is_active():
        ready = ts.get_ready()
        if not ready:
            return False
        order.extend(ready)
        ts.done(*ready)

    # Every dependency must appear before its dependent
    if not _is_topo_order(order, deps):
        return False

    # All declared nodes (including bare predecessors) must appear exactly once
    expected_nodes = {2, 3, 5, 7, 8, 9, 10, 11}
    if set(order) != expected_nodes:
        return False
    if len(order) != len(expected_nodes):
        return False
    return True


def graphlib2_cycle():
    """Verify that prepare() raises CycleError on a cyclic graph."""
    # Direct 3-cycle
    ts = TopologicalSorter({1: {2}, 2: {3}, 3: {1}})
    try:
        ts.prepare()
        return False
    except CycleError as exc:
        cycle = exc.args[1]
        if not isinstance(cycle, list) or len(cycle) < 2:
            return False
        # First and last node should match (closed cycle representation)
        if cycle[0] != cycle[-1]:
            return False

    # Self-loop
    ts2 = TopologicalSorter({"x": {"x"}})
    try:
        ts2.prepare()
        return False
    except CycleError:
        pass

    # Acyclic graph should NOT raise
    ts3 = TopologicalSorter({"a": {"b"}, "b": {"c"}, "c": set()})
    try:
        ts3.prepare()
    except CycleError:
        return False
    return True


def graphlib2_static_order():
    """Verify static_order() yields a valid topological linearisation."""
    # Linear chain: c depends on b depends on a
    ts = TopologicalSorter()
    ts.add("a")
    ts.add("b", "a")
    ts.add("c", "b")
    order = list(ts.static_order())
    if order != ["a", "b", "c"]:
        return False

    # A more complex graph
    deps = {
        "build": {"compile", "link"},
        "compile": {"parse"},
        "link": {"compile"},
        "parse": set(),
    }
    ts2 = TopologicalSorter(deps)
    order2 = list(ts2.static_order())
    if not _is_topo_order(order2, deps):
        return False
    if set(order2) != {"build", "compile", "link", "parse"}:
        return False

    # static_order() on a cyclic graph must raise CycleError
    ts3 = TopologicalSorter({1: {2}, 2: {1}})
    try:
        list(ts3.static_order())
        return False
    except CycleError:
        pass

    return True


__all__ = [
    "TopologicalSorter",
    "CycleError",
    "graphlib2_topo",
    "graphlib2_cycle",
    "graphlib2_static_order",
]