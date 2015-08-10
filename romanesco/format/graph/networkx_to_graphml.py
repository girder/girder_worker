from networkx.readwrite.graphml import write_graphml
from StringIO import StringIO

io = StringIO()
write_graphml(input, io)
output = io.getvalue()
