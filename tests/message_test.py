
import json

from base import TestCase
from gaia.core import message

JSONMessage = message.registry['JSONMessage']


class ArrayMessage(JSONMessage):

    """A custom subclass of JSONMessage."""

    pass


class MessageTest(TestCase):

    """Test class for messages."""

    def test_message_registry(self):
        """Test the message class registry."""

        self.assertEqual(
            message.registry.get('ArrayMessage'),
            ArrayMessage
        )

    def test_message_serialize(self):
        """Test serialization of JSONMessage."""

        msg = JSONMessage()

        msg['a'] = 1
        msg['b'] = [1, True, None, "A string", 3.14159]

        self.assertEqual(
            json.loads(str(msg)),
            msg
        )
