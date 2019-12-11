import networkx as nx
import blossom5.pyMatch as pm
import graph_objects as go

"""
:param size:
:param plot_load:

 We define the unit cell, which contains two qubits, a star operator and plaquette operator.

    |       |
- Star  -  Q_0 -     also top (T) qubit
    |       |
-  Q_1  - Plaq  -    also down (D) qubit
    |       |

By doing so, we can define arrays the star and plaquette operators, where their index value define their position
  on the qubit lattice. For the qubit array, there is an extra dimension to store the two qubits per unit cell.

self.array stores the qubit values and has dimension [XZ_error{0,1}, Top_down{0,1}, size, size]
Qubit values are either 0 or 1, which is analogous to the -1, and 1 state, respectively
"""


class toric:
    def __init__(self, graph):
        self.graph = graph

    def get_stabs(self):
        verts, plaqs = [], []
        for stab in self.graph.S.values():
            if stab.state:
                if stab.sID[0] == 0:
                    verts.append(stab)
                else:
                    plaqs.append(stab)
        return verts, plaqs


    def get_edges(self, anyons):
        edges = []
        for i0, v0 in enumerate(anyons[:-1]):
            (_, y0, x0) = v0.sID
            for i1, v1 in enumerate(anyons[i0 + 1 :]):
                (_, y1, x1) = v1.sID
                wy = (y0 - y1) % (self.graph.size)
                wx = (x0 - x1) % (self.graph.size)
                weight = min([wy, self.graph.size - wy]) + min([wx, self.graph.size - wx])
                edges.append([i0, i1 + i0 + 1, weight])
        return edges

    def get_matching_networkx(self):
        """
        Uses the MWPM algorithm to get the matchings. A list of combinations of all the anyons and their respective weights are feeded to the blossom5 algorithm. To apply the matchings, we walk from each matching vertex to where their paths meet perpendicualarly, flipping the edges on the way over.
        """

        nxgraph = nx.Graph()

        verts, plaqs = self.get_stabs()

        def get_matching(anyons):
            edges = self.get_edges(anyons)
            for i0, i1, weight in edges:
                nxgraph.add_edge(i0, i1, weight=-weight)
            output = nx.algorithms.matching.max_weight_matching(nxgraph, maxcardinality=True)
            return [[anyons[i0], anyons[i1]] for i0, i1 in output]

        self.matching = []
        if verts:
            self.matching += get_matching(verts)
        if plaqs:
            self.matching += get_matching(plaqs)


    def get_matching_blossom5(self):
        """
        Uses the BlossomV algorithm to get the matchings. A list of combinations of all the anyons and their respective weights are feeded to the blossom5 algorithm. To apply the matchings, we walk from each matching vertex to where their paths meet perpendicualarly, flipping the edges on the way over.
        """
        verts, plaqs = self.get_stabs()

        def get_matching(anyons):
            output = pm.getMatching(len(anyons), self.get_edges(anyons))
            return [[anyons[i0], anyons[i1]] for i0, i1 in enumerate(output) if i0 > i1]

        self.matching = []
        if verts:
            self.matching += get_matching(verts)
        if plaqs:
            self.matching += get_matching(plaqs)


    def apply_matching(self):

        size = self.graph.size

        for v0, v1 in self.matching:  # Apply the matchings to the graph

            (_, y0, x0) = v0.sID
            (_, y1, x1) = v1.sID

            # Get distance between endpoints, take modulo to find min distance
            if self.graph.type == "toric":
                dy0 = (y0 - y1) % size
                dx0 = (x0 - x1) % size
                dy1 = (y1 - y0) % size
                dx1 = (x1 - x0) % size
            elif self.graph.type == "planar":
                dy0 = y0 - y1
                dx0 = x0 - x1
                dy1 = y1 - y0
                dx1 = x1 - x0

            if dy0 < dy1:  # Find closest path and walking direction
                dy = dy0
                yd = "u"
            else:
                dy = dy1
                yd = "d"
            if dx0 < dx1:
                dx = dx0
                xd = "r"
            else:
                dx = dx1
                xd = "l"

            ynext = v0  # walk vertically from v0
            for y in range(dy):
                (ynext, edge) = ynext.neighbors[yd]
                edge.state = not edge.state
                edge.matching = not edge.matching

            xnext = v1  # walk horizontally from v1
            for x in range(dx):
                (xnext, edge) = xnext.neighbors[xd]
                edge.state = not edge.state
                edge.matching = not edge.matching


class planar(toric):

    def get_stabs(self):
        verts, plaqs, tv, tp = [], [], [], []
        for stab in self.graph.S.values():
            type, y, x = stab.sID
            if stab.state:
                if type == 0:
                    verts.append(stab)
                    if x < self.graph.size/2:
                        tv.append(self.graph.B[(type, y, 0)])
                    else:
                        tv.append(self.graph.B[(type, y, self.graph.size)])
                else:
                    plaqs.append(stab)
                    if y < self.graph.size/2:
                        tp.append(self.graph.B[(type, -1, x)])
                    else:
                        tp.append(self.graph.B[(type, self.graph.size - 1, x)])
        verts += tv
        plaqs += tp
        return verts, plaqs


    def get_edges(self, anyons):

        edges = []
        mid = len(anyons)//2
        for i0, v0 in enumerate(anyons[:mid-1]):
            (_, y0, x0) = v0.sID
            for i1, v1 in enumerate(anyons[i0 + 1 :mid]):
                (_, y1, x1) = v1.sID
                wy = abs(y0 - y1)
                wx = abs(x0 - x1)
                weight = wy + wx
                edges.append([i0, i1 + i0 + 1, weight])


        for i0, v0 in enumerate(anyons[mid:-1], start=mid):
            for i1, v1 in enumerate(anyons[i0 + 1:], start=i0 + 1):
                edges.append([i0, i1, 0])


        for i in range(mid):
            (type, ys, xs) = anyons[i].sID
            (type, yb, xb) = anyons[mid + i].sID
            weight = abs(xb - xs) if type == 0 else abs(yb - ys)
            edges.append([i, mid + i, weight])

        return edges

    def remove_virtual(self):
        matching = []
        for V1, V2 in self.matching:

            if not (type(V1) == go.iBoundary and type(V2) == go.iBoundary):
                matching.append([V1, V2])
        self.matching = matching