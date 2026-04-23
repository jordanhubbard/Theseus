"""
theseus_graphlib_cr — Clean-room graphlib module.
No import of the standard `graphlib` module.
"""


class CycleError(ValueError):
    def __init__(self, message, cycle):
        super().__init__(message, cycle)
        self.args = (message, cycle)


_ACTIVE = 1
_DONE = 2


class TopologicalSorter:
    def __init__(self, graph=None):
        self._graph = {}
        self._node2info = {}
        self._ready_nodes = []
        self._npassedout = 0
        self._nfinished = 0
        self._prepared = False

        if graph is not None:
            for node, predecessors in graph.items():
                self.add(node, *predecessors)

    def add(self, node, *predecessors):
        if self._prepared:
            raise ValueError("nodes cannot be added after prepare()")
        if node not in self._graph:
            self._graph[node] = set()
        for pred in predecessors:
            self._graph[node].add(pred)
            if pred not in self._graph:
                self._graph[pred] = set()

    def prepare(self):
        if self._prepared:
            raise ValueError("cannot prepare() more than once")
        self._prepared = True
        # Compute in-degrees
        indegree = {n: 0 for n in self._graph}
        for node, preds in self._graph.items():
            for pred in preds:
                pass  # pred already in graph from add()
        # Build reverse adjacency and indegree
        self._rev = {n: set() for n in self._graph}
        self._indegree = {n: 0 for n in self._graph}
        for node, preds in self._graph.items():
            for pred in preds:
                self._rev[pred].add(node)
                self._indegree[node] += 1
        # Start with zero-indegree nodes
        self._ready_nodes = [n for n, d in self._indegree.items() if d == 0]
        # Check for cycles using DFS
        self._detect_cycles()

    def _detect_cycles(self):
        state = {}
        path = []

        def dfs(node):
            state[node] = _ACTIVE
            path.append(node)
            for pred in self._graph.get(node, set()):
                if pred not in state:
                    dfs(pred)
                elif state[pred] == _ACTIVE:
                    cycle_start = path.index(pred)
                    cycle = path[cycle_start:] + [pred]
                    raise CycleError(f"nodes are in a cycle", cycle)
            state[node] = _DONE
            path.pop()

        for node in self._graph:
            if node not in state:
                dfs(node)

    def get_ready(self):
        if not self._prepared:
            raise ValueError("prepare() must be called first")
        result = list(self._ready_nodes)
        self._npassedout += len(result)
        self._ready_nodes = []
        return result

    def done(self, *nodes):
        if not self._prepared:
            raise ValueError("prepare() must be called first")
        for node in nodes:
            self._nfinished += 1
            for successor in self._rev.get(node, set()):
                self._indegree[successor] -= 1
                if self._indegree[successor] == 0:
                    self._ready_nodes.append(successor)

    def is_active(self):
        if not self._prepared:
            raise ValueError("prepare() must be called first")
        return self._nfinished < len(self._graph)

    def __bool__(self):
        return self.is_active()

    def static_order(self):
        self.prepare()
        while self.is_active():
            node_group = self.get_ready()
            if not node_group:
                raise CycleError("nodes are in a cycle", [])
            for node in node_group:
                yield node
                self.done(node)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def graphlib2_topo():
    """TopologicalSorter produces correct topological order; returns True."""
    ts = TopologicalSorter({'c': ['a', 'b'], 'b': ['a'], 'a': []})
    ts.prepare()
    order = []
    while ts.is_active():
        ready = ts.get_ready()
        order.extend(ready)
        ts.done(*ready)
    # 'a' must come before 'b' and 'c', 'b' before 'c'
    return (order.index('a') < order.index('b') and
            order.index('b') < order.index('c'))


def graphlib2_cycle():
    """TopologicalSorter raises CycleError on cycles; returns True."""
    ts = TopologicalSorter({'a': ['b'], 'b': ['a']})
    try:
        ts.prepare()
        return False
    except CycleError:
        return True


def graphlib2_static_order():
    """static_order() yields nodes in dependency order; returns True."""
    ts = TopologicalSorter({'c': ['b'], 'b': ['a'], 'a': []})
    order = list(ts.static_order())
    return order.index('a') < order.index('b') < order.index('c')


__all__ = [
    'TopologicalSorter', 'CycleError',
    'graphlib2_topo', 'graphlib2_cycle', 'graphlib2_static_order',
]
