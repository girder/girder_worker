import json

l = json.loads(input)
output = sc.parallelize(l)