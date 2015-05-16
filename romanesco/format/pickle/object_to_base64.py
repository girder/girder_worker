import base64
from six.moves import cPickle
output = base64.b64encode(cPickle.dumps(input))
