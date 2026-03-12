import uuid
from .metagraph import Metagraph


class ConditionalMetagraph(Metagraph):
    """
    Extends Metagraph with variables and propositions.
    Generator set = variables_set ∪ propositions_set.
    Edges can have conditions (propositions) attached to them.
    """

    def __init__(self, variables_set: set, propositions_set: set, graph_id: str = None,
                 host: str = "localhost", port: int = 6380):
        self.variables_set = set(variables_set)
        self.propositions_set = set(propositions_set)
        self._host = host
        self._port = port
        generator_set = variables_set | propositions_set

        super().__init__(generator_set, graph_id=graph_id, host=host, port=port)

        if graph_id is None:
            self._tag_roles()

    def _tag_roles(self):
        """Tag each element node with its role: variable or proposition."""
        for el in self.variables_set:
            safe = self._safe(el)
            self.graph.query(f"""
                MATCH (e:Element {{value: {safe}}})-[:IN_GENERATOR_SET]->(mg:Metagraph {{id: '{self.id}'}})
                SET e.role = 'variable'
            """)
        for el in self.propositions_set:
            safe = self._safe(el)
            self.graph.query(f"""
                MATCH (e:Element {{value: {safe}}})-[:IN_GENERATOR_SET]->(mg:Metagraph {{id: '{self.id}'}})
                SET e.role = 'proposition'
            """)

    def add_edge(self, invertex: set, outvertex: set, label: str = None, conditions: set = None):
        """
        Add an edge with optional conditions (propositions that must be true).
        conditions: set of proposition values that must hold for this edge to fire.
        """
        edge_id = super().add_edge(invertex, outvertex, label)

        if conditions:
            for cond in conditions:
                safe = self._safe(cond)
                self.graph.query(f"""
                    MATCH (e:Element {{value: {safe}}}), (me:MetagraphEdge {{id: '{edge_id}'}})
                    CREATE (e)-[:IS_CONDITION_OF]->(me)
                """)

        return edge_id

    def get_edges(self):
        """Returns edges with their conditions."""
        edges = super().get_edges()

        for edge in edges:
            result = self.graph.query(f"""
                MATCH (e:Element)-[:IS_CONDITION_OF]->(me:MetagraphEdge {{id: '{edge['edge_id']}'}})
                RETURN collect(e.value)
            """)
            conditions = set()
            if result.result_set:
                conditions = set(result.result_set[0][0])
            edge["conditions"] = conditions

        return edges

    def get_context(self, true_propositions: set, false_propositions: set):
        """
        Returns a new ConditionalMetagraph containing only edges whose
        conditions are satisfied by the given true/false proposition assignments.
        An edge is included if all its conditions are in true_propositions.
        """
        edges = self.get_edges()
        ctx = ConditionalMetagraph(
            self.variables_set,
            self.propositions_set,
            host=self._host,
            port=self._port
        )

        for edge in edges:
            conditions = edge.get("conditions", set())
            if not conditions or conditions.issubset(true_propositions):
                ctx.add_edge(edge["invertex"], edge["outvertex"], edge["label"])

        return ctx

    def get_all_metapaths_from(self, source: set, target: set, prop_subset: set = None):
        """
        Returns metapaths from source to target.
        If prop_subset is given, only edges whose conditions are within prop_subset are used.
        """
        edges = self.get_edges()

        if prop_subset is not None:
            edges = [
                e for e in edges
                if not e["conditions"] or e["conditions"].issubset(prop_subset)
            ]

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

    def is_connected(self, source: set, target: set, true_propositions: set, false_propositions: set):
        """
        Returns True if there exists at least one metapath from source to target
        given the proposition context.
        """
        ctx = self.get_context(true_propositions, false_propositions)
        paths = ctx.get_all_metapaths_from(source, target)
        ctx.delete()
        return len(paths) > 0

    def is_fully_connected(self, source: set, target: set, true_propositions: set, false_propositions: set):
        """
        Returns True if every element in target is reachable from source
        given the proposition context.
        """
        ctx = self.get_context(true_propositions, false_propositions)
        for t in target:
            paths = ctx.get_all_metapaths_from(source, {t})
            if not paths:
                ctx.delete()
                return False
        ctx.delete()
        return True

    def is_redundantly_connected(self, source: set, target: set, true_propositions: set, false_propositions: set):
        """
        Returns True if there are multiple metapaths from source to target,
        meaning the connection is redundant (resilient to edge removal).
        """
        ctx = self.get_context(true_propositions, false_propositions)
        paths = ctx.get_all_metapaths_from(source, target)
        ctx.delete()
        return len(paths) > 1

    def is_non_redundant(self, true_propositions: set, false_propositions: set):
        """
        Returns True if no pair of elements has more than one metapath between them.
        """
        ctx = self.get_context(true_propositions, false_propositions)
        edges = ctx.get_edges()
        all_elements = set()
        for e in edges:
            all_elements |= e["invertex"] | e["outvertex"]

        for src in all_elements:
            for tgt in all_elements:
                if src == tgt:
                    continue
                paths = ctx.get_all_metapaths_from({src}, {tgt})
                if len(paths) > 1:
                    ctx.delete()
                    return False
        ctx.delete()
        return True

    def has_conflicts(self, edge_id: str):
        """
        Returns True if the edge's conditions conflict —
        a condition appears as an outvertex of another edge,
        meaning it could be derived rather than assumed.
        """
        edges = self.get_edges()
        edge = next((e for e in edges if e["edge_id"] == edge_id), None)
        if not edge or not edge["conditions"]:
            return False

        for other in edges:
            if other["edge_id"] == edge_id:
                continue
            if other["outvertex"] & edge["conditions"]:
                return True
        return False

    def has_redundancies(self, edge_id: str):
        """
        Returns True if the edge is redundant — removing it still
        leaves at least one metapath from its invertex to its outvertex.
        """
        edges = self.get_edges()
        edge = next((e for e in edges if e["edge_id"] == edge_id), None)
        if not edge:
            return False

        remaining = [e for e in edges if e["edge_id"] != edge_id]
        source_set = edge["invertex"]
        target_set = edge["outvertex"]

        def dfs(current_set, visited_edges):
            if current_set & target_set:
                return True
            for e in remaining:
                if e["edge_id"] in visited_edges:
                    continue
                if e["invertex"] & current_set:
                    visited_edges.add(e["edge_id"])
                    if dfs(e["outvertex"], visited_edges):
                        return True
                    visited_edges.remove(e["edge_id"])
            return False

        return dfs(source_set, set())