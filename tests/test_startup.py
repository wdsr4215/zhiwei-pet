import unittest
from unittest.mock import patch
from zhiwei import startup


class MemoryStore:
    def __init__(self):
        self.values = {}
    def get(self, key, default=None):
        return self.values.get(key, default)
    def set(self, key, value):
        self.values[key] = value


class StartupTests(unittest.TestCase):
    def test_first_launch_only(self):
        store = MemoryStore()
        with patch.object(startup, 'set_enabled') as setter:
            self.assertTrue(startup.initialize(store)[0])
            self.assertFalse(startup.initialize(store)[0])
            setter.assert_called_once_with(True)

    def test_failed_registration_not_saved(self):
        store = MemoryStore()
        with patch.object(startup, 'set_enabled', side_effect=OSError('denied')):
            first, message = startup.initialize(store)
        self.assertTrue(first)
        self.assertIn('未能', message)
        self.assertFalse(store.get('startup_initialized', False))

    def test_frozen_path_with_spaces(self):
        with patch.object(startup.sys, 'frozen', True, create=True), patch.object(startup.sys, 'executable', 'C:/My Apps/Zhiwei.exe'):
            self.assertEqual(startup.command().replace('\\', '/'), '"C:/My Apps/Zhiwei.exe" --autostart')
