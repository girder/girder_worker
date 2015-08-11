from networkx.readwrite.adjlist import read_adjlist
from six import StringIO

io = StringIO(input)
output = read_adjlist(io)
