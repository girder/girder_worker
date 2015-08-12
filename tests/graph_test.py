import json
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
                'data': nx.MultiDiGraph([
                    ('US', 'Foundations', {'amount': 3.4,
                                           'year': 2004}),
                    ('US', 'Foundations', {'amount': 3.3,
                                           'year': 2005}),
                    ('US', 'NGOs', {'amount': 9.7}),
                    ('US', 'Corporations', {'amount': 4.9})
                ])
            },
            'simpleVtkDiGraph': {
                'format': 'vtkgraph',
                'data': simpleVtkDiGraph()
            },
            'alphabetGraph': {
                'format': 'clique.json'
            }
        }

        with open(os.path.join('tests', 'data', 'clique.json'), 'rb') as fixture:
            self.test_input['alphabetGraph']['data'] = fixture.read()

    def test_clique(self):
        output = romanesco.convert('graph',
                                   self.test_input['alphabetGraph'],
                                   {'format': 'networkx'})

        self.assertEqual(set([n[1]['name'] for n in output['data'].nodes(data=True)]),
                         set(['a', 'b', 'c', 'd']))
        self.assertEqual(len(output['data'].edges()), 3)
        self.assertEqual(output['data'].degree('55ba5019f8883b5bf35f3e30'), 0)

        output = romanesco.convert('graph',
                                   output,
                                   {'format': 'clique.json'})

        with open(os.path.join('tests', 'data', 'clique.json'), 'rb') as fixture:
            self.assertEqual(sorted(json.loads(fixture.read())),
                             sorted(json.loads(output['data'])))

    def test_vtkgraph(self):
        # Test vtkgraph -> vtkgraph.serialized on a simple digraph
        output = romanesco.convert('graph',
                                   self.test_input['simpleVtkDiGraph'],
                                   {'format': 'vtkgraph.serialized'})

        with open(os.path.join('tests', 'data', 'vtkDiGraph.txt'), 'rb') as fixture:
            self.assertEqual(output['data'].splitlines()[1:],
                             fixture.read().splitlines()[1:])

        # Test networkx -> vtkgraph.serialized on an undirected
        # graph w/ edge data
        output = romanesco.convert('graph',
                                   self.test_input['distances'],
                                   {'format': 'vtkgraph.serialized'})

        with open(os.path.join('tests', 'data', 'vtkDistancesUndirectedGraph.txt'),
                  'rb') as fixture:
            self.assertEqual(output['data'].splitlines()[1:],
                             fixture.read().splitlines()[1:])

        # Test networkx -> vtkgraph with missing edge attributes
        output = romanesco.convert('graph',
                                   self.test_input['grants'],
                                   {'format': 'vtkgraph.serialized'})

        with open(os.path.join('tests', 'data', 'vtkGrantsDirectedGraph.txt'),
                  'rb') as fixture:
            self.assertEqual(output['data'].splitlines()[1:],
                             fixture.read().splitlines()[1:])

        # Test networkx -> vtkgraph throws errors for different types of metadata
        with self.assertRaises(Exception):
            output = romanesco.convert('graph',
                                       {'format': 'networkx',
                                        'data': nx.Graph([
                                            ('A', 'B', {'value': 10}),
                                            ('B', 'C', {'value': '10'})
                                        ])},
                                       {'format': 'vtkgraph'})

        # Test vtkgraph -> networkx
        output = romanesco.convert('graph',
                                   self.test_input['simpleVtkDiGraph'],
                                   {'format': 'networkx'})

        self.assertIsInstance(output['data'], nx.DiGraph)

        self.assertEqual(len(output['data'].nodes()), 3)
        self.assertEqual(len(output['data'].edges()), 3)
        self.assertEqual(sorted(output['data'].edges(data=True)),
                         [(0, 1, {'Weights': 1.0}),
                          (0, 2, {'Weights': 2.0}),
                          (1, 2, {'Weights': 1.0})])

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
        output = romanesco.convert('graph',
                                   self.test_input['distances'],
                                   {'format': 'graphml'})
        expected_edges = set(self.test_input['distances']['data'].edges(
            data='distance'))
        actual_edges = set()

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
