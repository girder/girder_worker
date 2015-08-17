from networkx.readwrite.graphml import read_graphml
from six import StringIO

output = read_graphml(StringIO(input))
