import os

with open(os.path.join('data', 'flutrends_us_data.txt'), 'rb') as fixture:
    raw = fixture.read()

lines = raw.split('\n')
data = '\n'.join(lines[11:])
