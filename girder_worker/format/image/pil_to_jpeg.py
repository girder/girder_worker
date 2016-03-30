from six import StringIO
s = StringIO()
input.save(s, 'JPEG')
output = s.getvalue()
