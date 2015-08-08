from networkx.readwrite.adjlist import read_adjlist
from StringIO import StringIO

io = StringIO(input)
output = read_adjlist(io)
