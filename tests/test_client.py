import unittest
import mock
from smok.basics import Environment
from smok.client import SMOKDevice

from .utils import FakeCall


class TestClient(unittest.TestCase):
    def test_set_up_smok_device(self):
        """Tests that basic constructor works"""
        client = SMOKDevice('tests/dev.testing.crt', 'tests/dev.testing.key',
                            'tests/evt_db.pickle')
        try:
            self.assertEqual(client.environment, Environment.LOCAL_DEVELOPMENT)
            self.assertEqual(client.device_id, '1')
        finally:
            client.close()

    @mock.patch('requests.get', FakeCall({'/v1/device': {
            'device_id': '1',
            'culture_context': {
                'timezone': 'Europe/Warsaw',
                'units': 'metric',
                'language': 'pl'
            },
            'verbose_name': 'Test device',
            'facets': ['smoke'],
            'slave_devices': [
                {'device_id': '1',
                 'master_controller': '1',
                 'configuration': 'rapid 1',
                 'responsible_service': 'rapid'
                 }
            ]
        }}))
    def test_device_info(self):
        """Tests that basic constructor works"""
        client = SMOKDevice('tests/dev.testing.crt', 'tests/dev.testing.key',
                            'tests/evt_db.pickle')
        try:
            dev = client.get_device_info()
            self.assertEqual(dev.slaves[0].responsible_service, 'rapid')
        finally:
            client.close()
