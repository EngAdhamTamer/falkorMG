"""
Validation script: compares mgtoolkit output vs falkorMG output.
Note: mgtoolkit adjacency_matrix(), get_closure(), get_all_metapaths_from(),
get_projection(), and get_inverse() are all broken on Python 3.14 due to numpy
incompatibilities. Those are validated against known correct values instead.
"""

from falkorMG import Metagraph as FalkorMG


def compare(label, a, b):
    match = a == b
    status = "✅ PASS" if match else "❌ FAIL"
    print(f"{status} | {label}")
    if not match:
        print(f"       expected : {a}")
        print(f"       falkorMG : {b}")


def run():
    generator_set = {1, 2, 3, 4, 5}

    mg_test = FalkorMG(generator_set)
    e1 = mg_test.add_edge({1, 2}, {3}, label="e1")
    e2 = mg_test.add_edge({3}, {4, 5}, label="e2")
    e3 = mg_test.add_edge({2, 3}, {5}, label="e3")

    # ── edges ────────────────────────────────────────────────────────────────
    expected_edges = {
        (frozenset({1, 2}), frozenset({3})),
        (frozenset({3}), frozenset({4, 5})),
        (frozenset({2, 3}), frozenset({5})),
    }
    test_edges = {(frozenset(e["invertex"]), frozenset(e["outvertex"])) for e in mg_test.get_edges()}
    compare("get_edges()", expected_edges, test_edges)

    # ── adjacency matrix ─────────────────────────────────────────────────────
    expected_adj = [
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 1],
        [0, 0, 0, 1, 1],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    test_adj = mg_test.adjacency_matrix()["matrix"]
    compare("adjacency_matrix()", expected_adj, test_adj)

    # ── closure ──────────────────────────────────────────────────────────────
    expected_closure = [
        [1, 0, 1, 1, 1],
        [0, 1, 1, 1, 1],
        [0, 0, 1, 1, 1],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1],
    ]
    test_closure = mg_test.get_closure()["matrix"]
    compare("get_closure()", expected_closure, test_closure)

    # ── metapaths ────────────────────────────────────────────────────────────
    expected_path_count = 2
    test_paths = mg_test.get_all_metapaths_from({1}, {5})
    compare("get_all_metapaths_from() count", expected_path_count, len(test_paths))

    # ── projection ───────────────────────────────────────────────────────────
    expected_proj_edges = {(frozenset({1, 2}), frozenset({3}))}
    test_proj = mg_test.get_projection({1, 2, 3})
    test_proj_edges = {(frozenset(e["invertex"]), frozenset(e["outvertex"])) for e in test_proj.get_edges()}
    compare("get_projection()", expected_proj_edges, test_proj_edges)

    # ── inverse ──────────────────────────────────────────────────────────────
    expected_inv_edges = {
        (frozenset({3}), frozenset({1, 2})),
        (frozenset({4, 5}), frozenset({3})),
        (frozenset({5}), frozenset({2, 3})),
    }
    test_inv = mg_test.get_inverse()
    test_inv_edges = {(frozenset(e["invertex"]), frozenset(e["outvertex"])) for e in test_inv.get_edges()}
    compare("get_inverse()", expected_inv_edges, test_inv_edges)

    # ── efm ──────────────────────────────────────────────────────────────────
    # subset {1,2,3}, elements sorted: [1,2,3]
    # e1: {1,2}->{3} => [-1,-1,+1]
    # e2: {3}->{4,5} => [0,0,-1] (3 in invertex, 4 and 5 not in subset)
    # e3: {2,3}->{5} => [0,-1,-1] wait -- {2,3} invertex, {5} outvertex
    #   2 in invertex -> -1, 3 in invertex -> -1, 5 not in subset -> 0
    efm_result = mg_test.get_efm({1, 2, 3})
    efm_by_edge = {row["edge_id"]: row["row"] for row in efm_result["efm"]}
    compare("get_efm() elements", [1, 2, 3], efm_result["elements"])
    compare("get_efm() e1 row", [-1, -1, 1], efm_by_edge.get("e1"))
    compare("get_efm() e2 row", [0, 0, -1], efm_by_edge.get("e2"))
    compare("get_efm() e3 row", [0, -1, -1], efm_by_edge.get("e3"))

    # ── is_cutset ────────────────────────────────────────────────────────────
    # removing e1 disconnects {1} from {5} since all paths go through e1
    compare("is_cutset() e1 cuts {1}->{5}", True, mg_test.is_cutset(["e1"], {1}, {5}))
    # removing e3 alone does NOT disconnect since e1->e2 still works
    compare("is_cutset() e3 alone does not cut", False, mg_test.is_cutset(["e3"], {1}, {5}))

    # ── is_bridge ────────────────────────────────────────────────────────────
    # e1 is a bridge since every path from {1} to {5} uses e1
    compare("is_bridge() e1 is bridge", True, mg_test.is_bridge(["e1"], {1}, {5}))
    # e3 is not a bridge since path e1->e2 doesn't use it
    compare("is_bridge() e3 is not bridge", False, mg_test.is_bridge(["e3"], {1}, {5}))

    # ── get_minimal_cutset ───────────────────────────────────────────────────
    # minimal cutset from {1} to {5} should be just [e1]
    minimal = mg_test.get_minimal_cutset({1}, {5})
    compare("get_minimal_cutset() size", 1, len(minimal))
    compare("get_minimal_cutset() contains e1", True, "e1" in minimal)

    # ── dominates ────────────────────────────────────────────────────────────
    mg_test2 = FalkorMG({1, 2, 3, 4, 5})
    mg_test2.add_edge({1, 2}, {3}, label="e1")
    compare("dominates()", True, mg_test.dominates(mg_test2))

    # ── equivalent ───────────────────────────────────────────────────────────
    compare("equivalent()", False, mg_test.equivalent(mg_test2))

    # ── cleanup ──────────────────────────────────────────────────────────────
    mg_test.delete()
    mg_test2.delete()
    test_proj.delete()
    test_inv.delete()
    print("\nDone.")


if __name__ == "__main__":
    run()