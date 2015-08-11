from networkx.readwrite.graphml import write_graphml
from six import StringIO

io = StringIO()
write_graphml(input, io)
output = io.getvalue()
