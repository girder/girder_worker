import base64
from girder_worker.tasks import run
from girder_worker.plugins.types import convert
import math
import operator
import os
import tempfile
import unittest
from PIL import Image
from PIL.JpegImagePlugin import JpegImageFile
from six import StringIO


def compareImages(im1, im2):
    h1 = im1.histogram()
    h2 = im2.histogram()

    return math.sqrt(reduce(operator.add,
                     map(lambda a, b: (a-b)**2, h1, h2))/len(h1))


class TestImage(unittest.TestCase):

    def setUp(self):
        self.image = (
            'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6'
            'QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAKfSURBVDjL'
            'pZPrS1NhHMf9O3bOdmwDCWREIYKEUHsVJBI7mg3FvCxL09290jZj2EyLMnJexkg'
            'pLbPUanNOberU5taUMnHZUULMvelCtWF0sW/n7MVMEiN64AsPD8/n83uucQDi/i'
            'd/DBT4Dolypw/qsz0pTMbj/WHpiDgsdSUyUmeiPt2+V7SrIM+bSss8ySGdR4abQ'
            'Qv6lrui6VxsRonrGCS9VEjSQ9E7CtiqdOZ4UuTqnBHO1X7YXl6Daa4yGq7vWO1D'
            '40wVDtj4kWQbn94myPGkCDPdSesczE2sCZShwl8CzcwZ6NiUs6n2nYX99T1cnKq'
            'A2EKui6+TwphA5k4yqMayopU5mANV3lNQTBdCMVUA9VQh3GuDMHiVcLCS3J4jSL'
            'hCGmKCjBEx0xlshjXYhApfMZRP5CyYD+UkG08+xt+4wLVQZA1tzxthm2tEfD3Jx'
            'ARH7QkbD1ZuozaggdZbxK5kAIsf5qGaKMTY2lAU/rH5HW3PLsEwUYy+YCcERmIj'
            'JpDcpzb6l7th9KtQ69fi09ePUej9l7cx2DJbD7UrG3r3afQHOyCo+V3QQzE35pv'
            'QvnAZukk5zL5qRL59jsKbPzdheXoBZc4saFhBS6AO7V4zqCpiawuptwQG+UAa7C'
            't3UT0hh9p9EnXT5Vh6t4C22QaUDh6HwnECOmcO7K+6kW49DKqS2DrEZCtfuI+9G'
            'rNHg4fMHVSO5kE7nAPVkAxKBxcOzsajpS4Yh4ohUPPWKTUh3PaQEptIOr6BiJjc'
            'ZXCwktaAGfrRIpwblqOV3YKdhfXOIvBLeREWpnd8ynsaSJoyESFphwTtfjN6X1j'
            'RO2+FxWtCWksqBApeiFIR9K6fiTpPiigDoadqCEag5YUFKl6Yrciw0VOlhOivv/'
            'Ff8wtn0KzlebrUYwAAAABJRU5ErkJggg==')

        self.analysis = {
            'name': 'Image pixels',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'image',
                    'format': 'pil'
                }
            ],
            'outputs': [
                {
                    'name': 'pixels',
                    'type': 'number',
                    'format': 'number'
                }
            ],
            'script': 'pixels = a.size[0] * a.size[1]\n',
            'mode': 'python'
        }

    def test_base64(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'png.base64', 'data': self.image},
            })
        self.assertEqual(outputs['pixels']['format'], 'number')
        self.assertEqual(outputs['pixels']['data'], 256)

    def test_convert(self):
        tmp = tempfile.mktemp()

        output = convert('image', {
            'format': 'png.base64',
            'data': self.image
        }, {
            'format': 'png',
            'url': 'file://' + tmp,
            'mode': 'auto'
        })

        value = open(tmp).read()
        os.remove(tmp)
        self.assertEqual(output['format'], 'png')
        self.assertEqual(base64.b64encode(value), self.image)

        output = convert(
            'image',
            {'format': 'png.base64', 'data': self.image},
            {'format': 'pil'})

        tmp = tempfile.mktemp()

        output = convert(
            'image',
            output,
            {'format': 'png'})

        io1 = StringIO(base64.b64decode(self.image))
        im1 = Image.open(io1)
        io2 = StringIO(output['data'])
        im2 = Image.open(io2)
        self.assertEqual(compareImages(im1, im2), 0)

        output = convert('image', {
            'format': 'png.base64',
            'data': self.image
        }, {
            'format': 'jpeg'
        })
        data = StringIO(output['data'])
        jpeg = Image.open(data)
        self.assertTrue(isinstance(jpeg, JpegImageFile))


if __name__ == '__main__':
    unittest.main()
