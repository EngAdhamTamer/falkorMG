from falkorMG import Metagraph

mg = Metagraph({1, 2, 3, 4, 5})

e1 = mg.add_edge({1, 2}, {3})
e2 = mg.add_edge({3}, {4, 5})
e3 = mg.add_edge({2, 3}, {5})

print("Edges:", mg.get_edges())
print("Adjacency:", mg.adjacency_matrix())
print("Closure:", mg.get_closure())
print("Metapaths:", mg.get_all_metapaths_from({1}, {5}))

mg.delete()
print("Deleted.")