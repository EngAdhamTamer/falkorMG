# falkorMG

A Python library that replicates mgtoolkit's metagraph features natively using FalkorDB as the storage backend. No FastAPI, no mgtoolkit dependency at runtime — just import and use.

## Requirements

- Python 3.10+
- FalkorDB running locally via Docker
- `falkordb` Python client

## Setup

**1. Install dependencies:**
```bash
pip install -r requirements.txt
```

**2. Start FalkorDB:**
```bash
docker run -p 6380:6379 -d falkordb/falkordb
```

## Usage

### Metagraph
```python
from falkorMG import Metagraph

mg = Metagraph({1, 2, 3, 4, 5})

mg.add_edge({1, 2}, {3}, label="e1")
mg.add_edge({3}, {4, 5}, label="e2")
mg.add_edge({2, 3}, {5}, label="e3")

mg.get_edges()
mg.adjacency_matrix()
mg.get_closure()
mg.get_all_metapaths_from({1}, {5})
mg.get_projection({1, 2, 3})
mg.get_inverse()
mg.get_efm({1, 2, 3})
mg.is_cutset(["e1"], {1}, {5})
mg.is_bridge(["e1"], {1}, {5})
mg.get_minimal_cutset({1}, {5})
mg.dominates(other_mg)
mg.equivalent(other_mg)

mg.delete()
```

### ConditionalMetagraph
```python
from falkorMG import ConditionalMetagraph

variables = {1, 2, 3, 4, 5}
propositions = {"p1", "p2"}

cmg = ConditionalMetagraph(variables, propositions)

cmg.add_edge({1, 2}, {3}, label="e1", conditions={"p1"})
cmg.add_edge({3}, {4, 5}, label="e2", conditions=set())
cmg.add_edge({2, 3}, {5}, label="e3", conditions={"p2"})

cmg.get_edges()
cmg.get_context(true_propositions={"p1"}, false_propositions={"p2"})
cmg.is_connected({1}, {5}, true_propositions={"p1"}, false_propositions=set())
cmg.is_fully_connected({1}, {4, 5}, true_propositions={"p1"}, false_propositions=set())
cmg.is_redundantly_connected({1}, {5}, true_propositions={"p1", "p2"}, false_propositions=set())
cmg.is_non_redundant(true_propositions={"p1"}, false_propositions=set())
cmg.has_conflicts("e1")
cmg.has_redundancies("e1")

cmg.delete()
```

## Validation

Runs all operations against known correct values and reports pass/fail:
```bash
python validate.py
```

Expected output:
```
✅ PASS | get_edges()
✅ PASS | adjacency_matrix()
✅ PASS | get_closure()
✅ PASS | get_all_metapaths_from() count
✅ PASS | get_projection()
✅ PASS | get_inverse()
✅ PASS | get_efm() elements
✅ PASS | get_efm() e1 row
✅ PASS | get_efm() e2 row
✅ PASS | get_efm() e3 row
✅ PASS | is_cutset() e1 cuts {1}->{5}
✅ PASS | is_cutset() e3 alone does not cut
✅ PASS | is_bridge() e1 is bridge
✅ PASS | is_bridge() e3 is not bridge
✅ PASS | get_minimal_cutset() size
✅ PASS | get_minimal_cutset() contains e1
✅ PASS | dominates()
✅ PASS | equivalent()
```

## Project Structure
```
falkorMG/
├── falkorMG/
│   ├── __init__.py
│   ├── connection.py
│   ├── metagraph.py
│   └── conditional_metagraph.py
├── mgtoolkit/          # reference implementation (Python 3 patched, used only in validate.py)
├── validate.py
├── test_basic.py
├── README.md
└── requirements.txt
```