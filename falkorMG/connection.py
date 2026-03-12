from falkordb import FalkorDB


class Connection:
    def __init__(self, host="localhost", port=6379):
        self.client = FalkorDB(host=host, port=port)

    def get_graph(self, graph_id: str):
        return self.client.select_graph(graph_id)

    def delete_graph(self, graph_id: str):
        graph = self.get_graph(graph_id)
        graph.delete()