import cardoon
import unittest

class TestTree(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            "name": "tree_copy",
            "inputs": [{"name": "a", "type": "tree", "format": "nested"}],
            "outputs": [{"name": "b", "type": "tree", "format": "nested"}],
            "script": "b = a"
        }
        self.analysis_vtk = {
            "name": "tree_copy",
            "inputs": [{"name": "a", "type": "tree", "format": "vtktree"}],
            "outputs": [{"name": "b", "type": "tree", "format": "vtktree"}],
            "script": "b = a"
        }
        self.analysis_r = {
            "name": "tree_copy_r",
            "inputs": [{"name": "a", "type": "tree", "format": "r.apetree"}],
            "outputs": [{"name": "b", "type": "tree", "format": "r.apetree"}],
            "script": "b <- a",
            "mode": "r"
        }
        self.newick = "((ahli:0,allogus:1):2,rubribarbus:3);"
        self.nexus = """#NEXUS


BEGIN TAXA;
    DIMENSIONS NTAX = 4;
    TAXLABELS
        A
        B
        C
        D
    ;
END;
BEGIN TREES;
    TRANSLATE
        1   A,
        2   B,
        3   C,
        4   D
    ;
    TREE * UNTITLED = [&R] ((1:1,2:1):1,(3:1,4:1):1);
END;"""

    def test_newick(self):
        outputs = cardoon.run(self.analysis,
            inputs={"a": {"format": "newick", "data": self.newick}},
            outputs={"b": {"format": "newick"}}
        )
        self.assertEqual(outputs["b"]["format"], "newick")
        self.assertEqual(outputs["b"]["data"], self.newick)

    def test_vtktree(self):
        outputs = cardoon.run(self.analysis_vtk,
            inputs={"a": {"format": "newick", "data": self.newick}},
            outputs={"b": {"format": "newick"}}
        )
        self.assertEqual(outputs["b"]["format"], "newick")
        self.assertEqual(outputs["b"]["data"], self.newick)

    def test_r_apetree(self):
        outputs = cardoon.run(self.analysis,
            inputs={"a": {"format": "newick", "data": self.newick}},
            outputs={"b": {"format": "r.apetree"}}
        )
        self.assertEqual(outputs["b"]["format"], "r.apetree")
        self.assertEqual(str(outputs["b"]["data"])[:52], '\nPhylogenetic tree with 3 tips and 2 internal nodes.')

    def test_r(self):
        outputs = cardoon.run(self.analysis_r,
            inputs={"a": {"format": "newick", "data": self.newick}},
            outputs={"b": {"format": "newick"}}
        )
        self.assertEqual(outputs["b"]["format"], "newick")
        self.assertEqual(outputs["b"]["data"], self.newick)

        outputs = cardoon.run(self.analysis_r,
            inputs={"a": {"format": "nexus", "data": self.nexus}},
            outputs={"b": {"format": "nexus"}}
        )
        self.assertEqual(outputs["b"]["format"], "nexus")

        # Ignore spaces vs. tabs, and skip timestamp comment on line 2
        out = "\n".join(outputs["b"]["data"].splitlines()[2:])
        out = " ".join(out.split())
        expected = "\n".join(self.nexus.splitlines()[2:])
        expected = " ".join(expected.split())
        self.assertEqual(out, expected)
