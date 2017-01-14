from six import StringIO
s = StringIO()
input.save(s, 'png')
output = s.getvalue()
