"""
Validation script: compares mgtoolkit output vs falkorMG output
for the same metagraph operations.
"""

from mgtoolkit.library import Metagraph as MGToolkit, Edge
from falkorMG import Metagraph as FalkorMG


def compare(label, a, b):
    match = a == b
    status = "✅ PASS" if match else "❌ FAIL"
    print(f"{status} | {label}")
    if not match:
        print(f"       mgtoolkit : {a}")
        print(f"       falkorMG  : {b}")


def run():
    generator_set = {1, 2, 3, 4, 5}

    # ── mgtoolkit setup ──────────────────────────────────────────────────────
    mg_ref = MGToolkit(generator_set)
    mg_ref.add_edges_from([
        Edge({1, 2}, {3}),
        Edge({3}, {4, 5}),
        Edge({2, 3}, {5}),
    ])

    # ── falkorMG setup ───────────────────────────────────────────────────────
    mg_test = FalkorMG(generator_set)
    e1 = mg_test.add_edge({1, 2}, {3})
    e2 = mg_test.add_edge({3}, {4, 5})
    e3 = mg_test.add_edge({2, 3}, {5})

    # ── edges ────────────────────────────────────────────────────────────────
    ref_edges = {(frozenset(e.invertex), frozenset(e.outvertex)) for e in mg_ref.edges}
    test_edges = {(frozenset(e["invertex"]), frozenset(e["outvertex"])) for e in mg_test.get_edges()}
    compare("get_edges()", ref_edges, test_edges)

    # ── adjacency matrix ─────────────────────────────────────────────────────
    ref_adj = mg_ref.adjacency_matrix.tolist() if hasattr(mg_ref.adjacency_matrix, "tolist") else mg_ref.adjacency_matrix
    test_adj_result = mg_test.adjacency_matrix()
    test_adj = test_adj_result["matrix"]
    compare("adjacency_matrix()", ref_adj, test_adj)

    # ── closure ──────────────────────────────────────────────────────────────
    ref_closure = mg_ref.closure.tolist() if hasattr(mg_ref.closure, "tolist") else mg_ref.closure
    test_closure = mg_test.get_closure()["matrix"]
    compare("get_closure()", ref_closure, test_closure)

    # ── metapaths ────────────────────────────────────────────────────────────
    ref_paths = mg_ref.get_all_metapaths_from({1}, {5})
    test_paths = mg_test.get_all_metapaths_from({1}, {5})
    compare("get_all_metapaths_from() count", len(ref_paths), len(test_paths))

    # ── projection ───────────────────────────────────────────────────────────
    subset = {1, 2, 3}
    ref_proj = mg_ref.get_projection(subset)
    test_proj = mg_test.get_projection(subset)
    ref_proj_edges = {(frozenset(e.invertex), frozenset(e.outvertex)) for e in ref_proj.edges}
    test_proj_edges = {(frozenset(e["invertex"]), frozenset(e["outvertex"])) for e in test_proj.get_edges()}
    compare("get_projection()", ref_proj_edges, test_proj_edges)

    # ── inverse ──────────────────────────────────────────────────────────────
    ref_inv = mg_ref.get_inverse()
    test_inv = mg_test.get_inverse()
    ref_inv_edges = {(frozenset(e.invertex), frozenset(e.outvertex)) for e in ref_inv.edges}
    test_inv_edges = {(frozenset(e["invertex"]), frozenset(e["outvertex"])) for e in test_inv.get_edges()}
    compare("get_inverse()", ref_inv_edges, test_inv_edges)

    # ── dominates ────────────────────────────────────────────────────────────
    mg_test2 = FalkorMG({1, 2, 3, 4, 5})
    mg_test2.add_edge({1, 2}, {3})
    compare("dominates()", True, mg_test.dominates(mg_test2))

    # ── equivalent ───────────────────────────────────────────────────────────
    compare("equivalent()", False, mg_test.equivalent(mg_test2))

    # ── cleanup ──────────────────────────────────────────────────────────────
    mg_test.delete()
    mg_test2.delete()
    print("\nDone.")


if __name__ == "__main__":
    run()