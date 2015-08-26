import romanesco
import unittest
import os


class TestArbor(unittest.TestCase):

    def setUp(self):
        self.prevdir = os.getcwd()
        cur_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(cur_path)

        self.arbor_path = os.path.abspath(cur_path + "/../../../../" + "analysis/arbor")

    def test_pgls(self):
        pgls = romanesco.load(os.path.join(self.arbor_path, "pgls.json"))
        tree_file = os.path.join("data", "anolis.phy")
        table_file = os.path.join("data", "anolisDataAppended.csv")
        romanesco.run(
            pgls,
            {
                "tree": {"format": "newick", "url": "file://" + tree_file},
                "table": {"format": "csv", "url": "file://" + table_file},
                "correlation": {"format": "text", "data": "BM"},
                "ind_variable": {"format": "text", "data": "SVL"},
                "dep_variable": {"format": "text", "data": "PCI_limbs"}
            }
        )
        # print outputs

    # def test_fit_continuous(self):
    #     fit_continuous = romanesco.load(
    #         os.path.join(self.arbor_path, "fit_continuous.json"))
    #     tree_file = os.path.join("data", "anolis.phy")
    #     table_file = os.path.join("data", "anolisDataAppended.csv")
    #     outputs = romanesco.run(
    #         fit_continuous,
    #         {
    #             "tree": {"format": "newick", "url": "file://" + tree_file},
    #             "table": {"format": "csv", "url": "file://" + table_file},
    #             "column": {"format": "text", "data": "SVL"},
    #             "model": {"format": "text", "data": "BM"}
    #         }
    #     )
    #     # print outputs

    def test_cont2disc(self):
        cont2disc = romanesco.load(
            os.path.join(self.arbor_path, "continuous_to_discrete.json"))
        table_file = os.path.join("data", "anolisDataAppended.csv")
        romanesco.run(
            cont2disc,
            {
                "table": {"format": "csv", "url": "file://" + table_file},
                "column": {"format": "text", "data": "SVL"},
                "thresh": {"format": "number", "data": 3.5}
            },
            {
                "newtable": {"format": "rows"}
            }
        )
        # print outputs["newtable"]

    def test_mammal_tree(self):
        mammal = romanesco.load(
            os.path.join("data", "Mammal tree extraction.json"))
        romanesco.run(
            mammal,
            {
                "table": {
                    "format": "csv",
                    "url": "file://" +
                           os.path.join("data", "mammal_lnMass_tiny.csv")
                },
                "outRowCount": {"format": "number", "data": 19}
            },
            {
                "tree": {"format": "nested"}
            }
        )
        # print json.dumps(outputs["tree"], indent=2)

    def tearDown(self):
        os.chdir(self.prevdir)

if __name__ == '__main__':
    unittest.main()
