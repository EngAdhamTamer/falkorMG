import uuid
from .connection import Connection


class Metagraph:
    def __init__(self, generator_set: set, graph_id: str = None, host: str = "localhost", port: int = 6380):
        self.conn = Connection(host=host, port=port)
        self.generator_set = set(generator_set)
        self.id = graph_id or str(uuid.uuid4())[:8]
        self.graph = self.conn.get_graph(self.id)

        if graph_id is None:
            self._initialize()

    def _initialize(self):
        self.graph.query(f"CREATE (:Metagraph {{id: '{self.id}', type: 'metagraph'}})")
        for element in self.generator_set:
            safe = self._safe(element)
            self.graph.query(f"CREATE (:Element {{value: {safe}}})")
            self.graph.query(f"""
                MATCH (e:Element {{value: {safe}}}), (mg:Metagraph {{id: '{self.id}'}})
                CREATE (e)-[:IN_GENERATOR_SET]->(mg)
            """)

    @staticmethod
    def _safe(value):
        return f"'{value}'" if isinstance(value, str) else str(value)

    # ─── Core ────────────────────────────────────────────────────────────────

    def add_edge(self, invertex: set, outvertex: set, label: str = None):
        edge_id = label or str(uuid.uuid4())[:8]

        self.graph.query(f"CREATE (:MetagraphEdge {{id: '{edge_id}'}})")

        for el in invertex:
            safe = self._safe(el)
            self.graph.query(f"""
                MATCH (e:Element {{value: {safe}}}), (me:MetagraphEdge {{id: '{edge_id}'}})
                CREATE (e)-[:IN_INVERTEX]->(me)
            """)

        for el in outvertex:
            safe = self._safe(el)
            self.graph.query(f"""
                MATCH (e:Element {{value: {safe}}}), (me:MetagraphEdge {{id: '{edge_id}'}})
                CREATE (me)-[:IN_OUTVERTEX]->(e)
            """)

        self.graph.query(f"""
            MATCH (me:MetagraphEdge {{id: '{edge_id}'}}), (mg:Metagraph {{id: '{self.id}'}})
            CREATE (me)-[:BELONGS_TO]->(mg)
        """)

        return edge_id

    def get_edges(self):
        result = self.graph.query(f"""
            MATCH (e:Element)-[:IN_INVERTEX]->(me:MetagraphEdge)-[:BELONGS_TO]->(mg:Metagraph {{id: '{self.id}'}})
            MATCH (me)-[:IN_OUTVERTEX]->(o:Element)
            RETURN me.id, collect(distinct e.value) as invertex, collect(distinct o.value) as outvertex
        """)

        edges = []
        for record in result.result_set:
            edges.append({
                "edge_id": record[0],
                "invertex": set(record[1]),
                "outvertex": set(record[2]),
                "label": record[0]
            })
        return edges

    def delete(self):
        self.conn.delete_graph(self.id)

    # ─── Matrix Operations ───────────────────────────────────────────────────

    def adjacency_matrix(self):
        edges = self.get_edges()
        elements = sorted(set(
            el for edge in edges for el in edge["invertex"] | edge["outvertex"]
        ))
        size = len(elements)
        index = {el: i for i, el in enumerate(elements)}
        matrix = [[0] * size for _ in range(size)]

        for edge in edges:
            for i in edge["invertex"]:
                for j in edge["outvertex"]:
                    matrix[index[i]][index[j]] = 1

        return {"elements": elements, "matrix": matrix}

    def get_closure(self):
        adj = self.adjacency_matrix()
        matrix = adj["matrix"]
        size = len(matrix)

        closure = [row[:] for row in matrix]
        for i in range(size):
            closure[i][i] = 1

        for k in range(size):
            for i in range(size):
                for j in range(size):
                    if closure[i][k] and closure[k][j]:
                        closure[i][j] = 1

        return {"elements": adj["elements"], "matrix": closure}

    # ─── Metapaths ───────────────────────────────────────────────────────────

    def get_all_metapaths_from(self, source: set, target: set):
        edges = self.get_edges()
        source_set = set(source)
        target_set = set(target)

        def dfs(current_set, visited_edges, path):
            results = []
            if current_set & target_set:
                results.append(path[:])
            for edge in edges:
                edge_id = edge["edge_id"]
                if edge_id in visited_edges:
                    continue
                if edge["invertex"] & current_set:
                    visited_edges.add(edge_id)
                    path.append(edge_id)
                    results += dfs(edge["outvertex"], visited_edges, path)
                    path.pop()
                    visited_edges.remove(edge_id)
            return results

        all_paths = dfs(source_set, set(), [])
        return [
            {"edges": path, "source": list(source), "target": list(target)}
            for path in all_paths
        ]

    # ─── Projection ──────────────────────────────────────────────────────────

    def get_projection(self, generator_subset: set):
        """
        Returns a new Metagraph restricted to the given generator subset.
        Only edges whose invertex and outvertex are fully within the subset are kept.
        """
        edges = self.get_edges()
        subset = set(generator_subset)

        mg = Metagraph(subset)
        for edge in edges:
            if edge["invertex"].issubset(subset) and edge["outvertex"].issubset(subset):
                mg.add_edge(edge["invertex"], edge["outvertex"], edge["label"])

        return mg

    # ─── Inverse ─────────────────────────────────────────────────────────────

    def get_inverse(self):
        """
        Returns a new Metagraph with all edges flipped (invertex <-> outvertex).
        """
        edges = self.get_edges()
        mg = Metagraph(self.generator_set)
        for edge in edges:
            mg.add_edge(edge["outvertex"], edge["invertex"], edge["label"])
        return mg

    # ─── EFM (Edge-to-Flow Matrix) ───────────────────────────────────────────

    def get_efm(self, generator_subset: set):
        """
        Returns the edge-flow matrix: for each edge, which elements of the subset
        appear in the invertex (input) vs outvertex (output).
        Rows = edges, Cols = elements in subset.
        Value: -1 = in invertex, +1 = in outvertex, 0 = not involved.
        """
        edges = self.get_edges()
        subset = sorted(set(generator_subset))
        index = {el: i for i, el in enumerate(subset)}
        efm = []

        for edge in edges:
            row = [0] * len(subset)
            for el in edge["invertex"]:
                if el in index:
                    row[index[el]] = -1
            for el in edge["outvertex"]:
                if el in index:
                    row[index[el]] = 1
            efm.append({"edge_id": edge["edge_id"], "row": row})

        return {"elements": subset, "efm": efm}

    # ─── Cutset / Bridge ─────────────────────────────────────────────────────

    def is_cutset(self, edge_list: list, source: set, target: set):
        """
        Returns True if removing the given edges disconnects all metapaths
        from source to target.
        """
        edges = self.get_edges()
        remaining = [e for e in edges if e["edge_id"] not in set(edge_list)]
        source_set = set(source)
        target_set = set(target)

        def dfs(current_set, visited_edges):
            if current_set & target_set:
                return True
            for edge in remaining:
                if edge["edge_id"] in visited_edges:
                    continue
                if edge["invertex"] & current_set:
                    visited_edges.add(edge["edge_id"])
                    if dfs(edge["outvertex"], visited_edges):
                        return True
                    visited_edges.remove(edge["edge_id"])
            return False

        return not dfs(source_set, set())

    def is_bridge(self, edge_list: list, source: set, target: set):
        """
        Returns True if the given edges form a bridge — meaning every metapath
        from source to target passes through at least one of them.
        """
        edges = self.get_edges()
        source_set = set(source)
        target_set = set(target)
        bridge_set = set(edge_list)

        def dfs(current_set, visited_edges, must_use_bridge):
            if current_set & target_set:
                return must_use_bridge
            for edge in edges:
                if edge["edge_id"] in visited_edges:
                    continue
                if edge["invertex"] & current_set:
                    visited_edges.add(edge["edge_id"])
                    used = must_use_bridge or (edge["edge_id"] in bridge_set)
                    if dfs(edge["outvertex"], visited_edges, used):
                        return True
                    visited_edges.remove(edge["edge_id"])
            return False

        # Check if every path that reaches target passed through a bridge edge
        edges_data = self.get_edges()
        source_set = set(source)
        target_set = set(target)

        def all_paths_use_bridge():
            def dfs2(current_set, visited_edges, used_bridge):
                if current_set & target_set:
                    return used_bridge  # this path only counts if bridge was used
                results = []
                for edge in edges_data:
                    if edge["edge_id"] in visited_edges:
                        continue
                    if edge["invertex"] & current_set:
                        visited_edges.add(edge["edge_id"])
                        hit_bridge = used_bridge or (edge["edge_id"] in bridge_set)
                        results.append(dfs2(edge["outvertex"], visited_edges, hit_bridge))
                        visited_edges.remove(edge["edge_id"])
                return all(results) if results else False

            return dfs2(source_set, set(), False)

        return all_paths_use_bridge()

    def get_minimal_cutset(self, source: set, target: set):
        """
        Returns the minimal set of edges whose removal disconnects source from target.
        Uses a greedy approach: tries removing one edge at a time.
        """
        edges = self.get_edges()
        for edge in edges:
            if self.is_cutset([edge["edge_id"]], source, target):
                return [edge["edge_id"]]

        # Try pairs
        edge_ids = [e["edge_id"] for e in edges]
        for i in range(len(edge_ids)):
            for j in range(i + 1, len(edge_ids)):
                pair = [edge_ids[i], edge_ids[j]]
                if self.is_cutset(pair, source, target):
                    return pair

        return edge_ids  # worst case: all edges

    # ─── Dominance / Equivalence ─────────────────────────────────────────────

    def dominates(self, other: "Metagraph"):
        """
        Returns True if this metagraph dominates other — meaning for every edge
        in other, there exists a metapath in self that covers it.
        """
        other_edges = other.get_edges()
        for edge in other_edges:
            paths = self.get_all_metapaths_from(edge["invertex"], edge["outvertex"])
            if not paths:
                return False
        return True

    def equivalent(self, other: "Metagraph"):
        """
        Two metagraphs are equivalent if each dominates the other.
        """
        return self.dominates(other) and other.dominates(self)