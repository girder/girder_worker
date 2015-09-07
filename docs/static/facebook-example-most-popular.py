from networkx import degree

degrees = degree(G)
most_popular_person = max(degrees, key=degrees.get)
