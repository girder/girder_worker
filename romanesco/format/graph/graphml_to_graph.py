from networkx.readwrite.graphml import read_graphml
from StringIO import StringIO

output = read_graphml(StringIO(input))
