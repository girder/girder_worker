import os
import romanesco
import vtk
import networkx as nx
from networkx.algorithms.isomorphism import is_isomorphic, numerical_edge_match
import unittest
from lxml import etree


def simpleVtkDiGraph():
    g = vtk.vtkMutableDirectedGraph()

    # Create 3 vertices
    v1 = g.AddVertex()
    v2 = g.AddVertex()
    v3 = g.AddVertex()

    # Create a fully connected graph
    g.AddGraphEdge(v1, v2)
    g.AddGraphEdge(v2, v3)
    g.AddGraphEdge(v1, v3)

    # Create the edge weight array
    weights = vtk.vtkDoubleArray()
    weights.SetNumberOfComponents(1)
    weights.SetName("Weights")

    # Set the edge weights
    weights.InsertNextValue(1.0)
    weights.InsertNextValue(1.0)
    weights.InsertNextValue(2.0)

    # Add the edge weight array to the graph
    g.GetEdgeData().AddArray(weights)

    return g


class TestGraph(unittest.TestCase):
    def setUp(self):
        self.GRAPHML_NS = '{http://graphml.graphdrawing.org/xmlns}'
        self.test_input = {
            'distances': {
                'format': 'networkx',
                'data': nx.Graph([
                    ('US', 'UK', {'distance': 4242}),
                    ('US', 'Australia', {'distance': 9429}),
                    ('UK', 'Australia', {'distance': 9443}),
                    ('US', 'Japan', {'distance': 6303})
                ])
            },
            'grants': {
                'format': 'networkx',
                'data': nx.DiGraph([
                    ('US', 'Foundations', {'amount': 3.4,
                                           'year': 2004}),
                    ('US', 'NGOs', {'amount': 9.7}),
                    ('US', 'Corporations', {'amount': 4.9})
                ])
            },
            'simpleVtkDiGraph': {
                'format': 'vtkgraph',
                'data': simpleVtkDiGraph()
            }
        }

    def test_vtkgraph(self):
        # Test vtkgraph -> vtkgraph.serialized on a simple digraph
        output = romanesco.convert('graph',
                                   self.test_input['simpleVtkDiGraph'],
                                   {'format': 'vtkgraph.serialized'})

        with open(os.path.join('tests', 'data', 'vtkDiGraph.txt'), 'rb') as fixture:
            self.assertEqual(output['data'], fixture.read())

        # Test networkx -> vtkgraph.serialized on an undirected
        # graph w/ edge data
        output = romanesco.convert('graph',
                                   self.test_input['distances'],
                                   {'format': 'vtkgraph.serialized'})

        with open(os.path.join('tests', 'data', 'vtkDistancesUndirectedGraph.txt'),
                  'rb') as fixture:
            self.assertEqual(output['data'], fixture.read())

        # Test networkx -> vtkgraph with missing edge attributes
        output = romanesco.convert('graph',
                                   self.test_input['grants'],
                                   {'format': 'vtkgraph.serialized'})

        with open(os.path.join('tests', 'data', 'vtkGrantsDirectedGraph.txt'),
                  'rb') as fixture:
            self.assertEqual(output['data'], fixture.read())

        # Test networkx -> vtkgraph throws errors for different types of metadata
        with self.assertRaises(Exception):
            output = romanesco.convert('graph',
                                       {'format': 'networkx',
                                        'data': nx.Graph([
                                            ('A', 'B', {'value': 10}),
                                            ('B', 'C', {'value': '10'})
                                        ])},
                                       {'format': 'vtkgraph'})


    def test_adjacencylist(self):
        output = romanesco.convert('graph',
                                   self.test_input['distances'],
                                   {'format': 'adjacencylist'})

        expected_edges = set(self.test_input['distances']['data'].edges())
        actual_edges = set()

        for line in output['data'].splitlines():
            parts = line.split(' ', 1)

            if len(parts) > 1:
                source, targets = parts

                for target in targets.split(' '):
                    edge = (source, target)
                    self.assertNotIn(edge, actual_edges)
                    actual_edges.add(edge)

        # @todo handle graceful notification that this is a LOSSY conversion
        self.assertEqual(expected_edges, actual_edges)

        output = romanesco.convert('graph',
                                   output,
                                   {'format': 'networkx'})

        # Don't take edges into consideration, because they were lost in the
        # original conversion
        self.assertTrue(
            is_isomorphic(output['data'],
                          self.test_input['distances']['data'],
                          edge_match=None))

    def test_graphml(self):
        # @todo i notice tests asserting output format,
        # is this covered somewhere else?
        output = romanesco.convert('graph',
                                   self.test_input['distances'],
                                   {'format': 'graphml'})
        expected_edges = set(self.test_input['distances']['data'].edges(
            data='distance'))
        actual_edges = set()

        # @todo covered by validator?
        self.assertIsInstance(output['data'], (str, unicode))
        tree = etree.fromstring(output['data'])
        self.assertEqual(len(tree), 2)
        self.assertEqual(tree[0].tag, self.GRAPHML_NS + 'key')
        self.assertEqual(tree[1].tag, self.GRAPHML_NS + 'graph')

        for edge in tree[1].findall(self.GRAPHML_NS + 'edge'):
            edge = (edge.attrib['source'],
                    edge.attrib['target'],
                    int(edge.find(self.GRAPHML_NS + 'data').text))

            self.assertNotIn(edge, actual_edges)
            actual_edges.add(edge)

        self.assertEqual(expected_edges, actual_edges)

        output = romanesco.convert('graph',
                                   output,
                                   {'format': 'networkx'})

        self.assertTrue(
            is_isomorphic(output['data'],
                          self.test_input['distances']['data'],
                          edge_match=numerical_edge_match('distance', 1)))

if __name__ == '__main__':
    unittest.main()
