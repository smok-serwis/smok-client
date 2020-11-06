import unittest

from smokclient.client import SMOKDevice


class TestClient(unittest.TestCase):
    def test_set_up(self):
        client = SMOKDevice('tests/dev.testing.crt', 'tests/dev.testing.key')
