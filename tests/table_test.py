import cardoon
import os
import tempfile
import unittest

class TestTable(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            "name": "append_tables",
            "inputs": [{"name": "a", "type": "table", "format": "rows"}, {"name": "b", "type": "table", "format": "rows"}],
            "outputs": [{"name": "c", "type": "table", "format": "rows"}],
            "script": "c = a + b",
            "mode": "python"
        }
        self.analysis_r = {
            "name": "copy_table",
            "inputs": [{"name": "a", "type": "table", "format": "r.dataframe"}],
            "outputs": [{"name": "b", "type": "table", "format": "r.dataframe"}],
            "script": "b <- a",
            "mode": "r"
        }
        import pymongo, bson
        self.db = pymongo.MongoClient("mongodb://localhost")["test"]
        self.db["a"].drop()
        self.aobj = {'_id': bson.ObjectId('530cdb1add29bc5628984303'), 'bar': 2.0, 'foo': 1.0}
        self.db["a"].insert(self.aobj)
        self.db["b"].drop()
        self.bobj = {'_id': bson.ObjectId('530cdb23dd29bc5628984304'), 'bar': 4.0, 'foo': 3.0}
        self.db["b"].insert(self.bobj)

    def test_json(self):
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "rows.json", "data": '[{"aa": 1, "bb": 2}]'},
                "b": {"format": "rows.json", "data": '[{"aa": 3, "bb": 4}]'}
            },
            outputs={
                "c": {"format": "rows.json"}
            })
        self.assertEqual(outputs["c"]["format"], "rows.json")
        self.assertEqual(outputs["c"]["data"], '[{"aa": 1, "bb": 2}, {"aa": 3, "bb": 4}]')

    def test_bson(self):
        import pymongo
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "bson.rows", "uri": "mongodb://localhost/test/a"},
                "b": {"format": "bson.rows", "uri": "mongodb://localhost/test/b"}
            },
            outputs={
                "c": {"format": "bson.rows", "uri": "mongodb://localhost/test/temp"}
            })
        self.assertEqual(outputs["c"]["format"], "bson.rows")
        self.assertEqual([d for d in pymongo.MongoClient("mongodb://localhost")["test"]["temp"].find()], [self.aobj, self.bobj])

    def test_file(self):
        tmp = tempfile.mktemp()
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "rows.json", "data": '[{"aa": 1, "bb": 2}]'},
                "b": {"format": "rows.json", "data": '[{"aa": 3, "bb": 4}]'}
            },
            outputs={
                "c": {"format": "csv", "uri": "file://" + tmp}
            })
        with open(tmp, 'r') as fp:
            output = fp.read()
        os.remove(tmp)
        self.assertEqual(outputs["c"]["format"], "csv")
        self.assertEqual(output.splitlines(), ["aa,bb", "1,2", "3,4"])

    def test_csv(self):
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "csv", "data": 'a,b,c\n1,2,3'},
                "b": {"format": "csv", "data": 'a,b,c\n4,5,6'}
            },
            outputs={
                "c": {"format": "csv"}
            })
        self.assertEqual(outputs["c"]["format"], "csv")
        self.assertEqual(outputs["c"]["data"].splitlines(), ["a,b,c", "1,2,3", "4,5,6"])

    def test_vtktable(self):
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "rows.json", "data": '[{"aa": 1, "bb": 2}]'},
                "b": {"format": "rows.json", "data": '[{"aa": 3, "bb": 4}]'}
            },
            outputs={
                "c": {"format": "vtktable"}
            })
        self.assertEqual(outputs["c"]["format"], "vtktable")
        t = outputs["c"]["data"]
        self.assertEqual(t.GetNumberOfRows(), 2)
        self.assertEqual(t.GetNumberOfColumns(), 2)
        self.assertEqual(t.GetValueByName(0, "aa"), 1)
        self.assertEqual(t.GetValueByName(1, "aa"), 3)
        self.assertEqual(t.GetValueByName(0, "bb"), 2)
        self.assertEqual(t.GetValueByName(1, "bb"), 4)

    def test_mongo_to_python(self):
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "bson.rows", "uri": "mongodb://localhost/test/a"},
                "b": {"format": "bson.rows", "uri": "mongodb://localhost/test/b"}
            },
            outputs={
                "c": {"format": "rows"}
            })
        self.assertEqual(outputs["c"]["format"], "rows")
        self.assertEqual(outputs["c"]["data"], [self.aobj, self.bobj])

    def test_chaining(self):
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "rows", "data": [{"a": 1, "b": 2}]},
                "b": {"format": "rows", "data": [{"a": 3, "b": 4}]}
            },
            outputs={
                "c": {"format": "rows"}
            })

        outputs = cardoon.run(self.analysis,
            inputs={
                "a": outputs["c"],
                "b": {"format": "rows", "data": [{"a": 5, "b": 6}]}
            },
            outputs={
                "c": {"format": "rows"}
            })
        self.assertEqual(outputs["c"]["format"], "rows")
        self.assertEqual(outputs["c"]["data"], [{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}])

    def test_column_names(self):
        output = cardoon.convert("table", {"format": "rows", "data": [{"a": 6, "b": 5}]}, {"format": "column.names"})
        self.assertEqual(output["format"], "column.names")
        self.assertEqual(output["data"], ["a", "b"])

    def test_r_dataframe(self):
        outputs = cardoon.run(self.analysis_r,
            inputs={
                "a": {"format": "rows", "data": [{"aa": 1, "bb": 2}]}
            },
            outputs={
                "b": {"format": "rows"}
            })
        self.assertEqual(outputs["b"]["format"], "rows")
        self.assertEqual(outputs["b"]["data"], [{"aa": 1, "bb": 2}])


if __name__ == '__main__':
    unittest.main()

def test():

    tree_copy = {
        "name": "tree_copy",
        "inputs": [{"name": "a", "type": "tree", "format": "nested"}],
        "outputs": [{"name": "b", "type": "tree", "format": "nested"}],
        "script": "b = a"
    }

    outputs = cardoon.run(tree_copy,
        inputs={"a": {"format": "newick", "uri": "file://anolis.phy"}},
        outputs={"b": {"format": "r.apetree"}}
    )

    print outputs

    tree_copy_r = {
        "name": "tree_copy_r",
        "inputs": [{"name": "a", "type": "tree", "format": "r.apetree"}],
        "outputs": [{"name": "b", "type": "tree", "format": "r.apetree"}],
        "script": "b <- a",
        "mode": "r"
    }

    # outputs = cardoon.run(tree_copy,
    #     inputs={"a": {"format": "newick", "uri": "file://anolis.phy"}},
    #     outputs={"b": {"format": "newick"}}
    # )

    # print outputs

    # outputs = cardoon.run(tree_copy,
    #     inputs={"a": outputs["b"]},
    #     outputs={"b": {"format": "newick", "uri": "file://anolis.phy.copy"}}
    # )

