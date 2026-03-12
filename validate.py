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
    mg_test.add_edge({1, 2}, {3})
    mg_test.add_edge({3}, {4, 5})
    mg_test.add_edge({2, 3}, {5})

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

    # ── dominates ────────────────────────────────────────────────────────────
    mg_test2 = FalkorMG({1, 2, 3, 4, 5})
    mg_test2.add_edge({1, 2}, {3})
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