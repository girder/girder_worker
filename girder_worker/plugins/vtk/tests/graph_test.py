import os
from girder_worker.plugins.types import convert
import vtk
import networkx as nx
import unittest


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
    weights.SetName('Weights')

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
            }
        }

    def test_vtkgraph(self):
        # Test vtkgraph -> vtkgraph.serialized on a simple digraph
        output = convert(
            'graph', self.test_input['simpleVtkDiGraph'],
            {'format': 'vtkgraph.serialized'})

        with open(os.path.join(
                'tests', 'data', 'vtkDiGraph.txt'), 'rb') as fixture:
            self.assertEqual(output['data'].splitlines()[1:],
                             fixture.read().splitlines()[1:])

        # Test networkx -> vtkgraph.serialized on an undirected
        # graph w/ edge data
        output = convert(
            'graph', self.test_input['distances'],
            {'format': 'vtkgraph.serialized'})

        with open(os.path.join(
                'tests', 'data', 'vtkDistancesUndirectedGraph.txt'),
                'rb') as fixture:
            self.assertEqual(output['data'].splitlines()[1:],
                             fixture.read().splitlines()[1:])

        # Test networkx -> vtkgraph with missing edge attributes
        output = convert(
            'graph', self.test_input['grants'],
            {'format': 'vtkgraph.serialized'})

        with open(os.path.join('tests', 'data', 'vtkGrantsDirectedGraph.txt'),
                  'rb') as fixture:
            self.assertEqual(output['data'].splitlines()[1:],
                             fixture.read().splitlines()[1:])

        # Test networkx -> vtkgraph throws errors for different types
        # of metadata
        with self.assertRaises(Exception):
            output = convert(
                'graph', {'format': 'networkx', 'data': nx.Graph([
                    ('A', 'B', {'value': 10}),
                    ('B', 'C', {'value': '10'})
                ])}, {'format': 'vtkgraph'})

        # Test vtkgraph -> networkx
        output = convert(
            'graph', self.test_input['simpleVtkDiGraph'],
            {'format': 'networkx'})

        self.assertIsInstance(output['data'], nx.DiGraph)

        self.assertEqual(len(output['data'].nodes()), 3)
        self.assertEqual(len(output['data'].edges()), 3)
        self.assertEqual(sorted(output['data'].edges(data=True)),
                         [(0, 1, {'Weights': 1.0}),
                          (0, 2, {'Weights': 2.0}),
                          (1, 2, {'Weights': 1.0})])


if __name__ == '__main__':
    unittest.main()
