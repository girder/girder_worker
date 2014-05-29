import requests

raw = requests.get('https://www.google.org/flutrends/us/data.txt').text
lines = raw.split("\n")
data = "\n".join(lines[11:])
