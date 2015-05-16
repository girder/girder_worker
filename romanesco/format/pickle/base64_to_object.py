import base64
from six.moves import cPickle
output = cPickle.loads(base64.b64decode(input))
