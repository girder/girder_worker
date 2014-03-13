from PIL import Image
from StringIO import StringIO
s = StringIO()
input.save(s, "png")
output = s.getvalue()
