import networkx as nx

class Tree :

    def __init__(self, graph, inplace=True) :
        if inplace :
            self.G = graph
        else :
            self.G = graph.copy()
        self.V = list(range(len(graph)))


    def construct_tree(self, seq) :
        '''
        adds edges to the graph
        according to Prüfer algorithm
        seq : list of length n-2
        '''

        nodes = list(self.G.nodes)
        P = seq.copy()
        V = self.V

        for i in range (len(V)-2) :
            k = 0
            while V[k] in P :
                k += 1
            self.G.add_edge(nodes[P[0]], nodes[V[k]])
            V.remove(V[k])
            P.remove(P[0])
        
        self.G.add_edge(nodes[V[0]], nodes[V[1]])

        nx.set_edge_attributes(self.G, 'a', 'direction')

        return self.G


