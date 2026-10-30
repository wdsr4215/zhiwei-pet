import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from zhiwei.storage import Store
from zhiwei.activities import ActivityClock
from zhiwei.sprites import SpriteLibrary
from zhiwei.codex_usage import summarize
from zhiwei import ai

APP = QApplication.instance() or QApplication([])


class FeatureTests(unittest.TestCase):
    def test_animation_atlas_frames(self):
        library = SpriteLibrary(Path(__file__).resolve().parents[1] / 'assets/sprites')
        self.assertEqual(set(library.animations), {'idle','walk','sleep','eat','drink','play','drag','peek'})
        for name, (frames, fps) in library.animations.items():
            self.assertGreaterEqual(len(frames), 4)
            self.assertTrue(all(not f.isNull() for f in frames))
            self.assertTrue(all(f.hasAlphaChannel() for f in frames))
            self.assertEqual(len(set((f.width(), f.height()) for f in frames)), 1)

    def test_focus_completion_only_once_and_habit_reschedule(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp) / 'test.db')
            clock = ActivityClock(store)
            notices = []
            clock.notify.connect(lambda kind, text: notices.append(kind))
            with patch('zhiwei.activities.time.time', return_value=1000):
                clock.start_focus(1)
                store.set('habit_water', {'enabled': True, 'minutes': 30, 'next': 900})
                clock.tick()
                self.assertEqual(notices, ['water'])
            with patch('zhiwei.activities.time.time', return_value=1061):
                clock.tick()
                clock.tick()
                self.assertEqual(notices, ['water', 'focus'])
                self.assertIsNone(store.get('focus'))
            clock.timer.stop()
            store.db.close()

    def test_codex_missing_and_remaining_clamp(self):
        self.assertEqual(summarize({}), [])
        rows = summarize({'rateLimits': {'primary': {'usedPercent': 120}}})
        self.assertEqual(rows[0]['remaining'], 0)

    @patch('zhiwei.ai.get_key', return_value='test-admin')
    @patch('zhiwei.ai.request_json')
    def test_costs_paginate_and_currency_separation(self, request, key):
        request.side_effect = [
            {'data': [{'results': [{'amount': {'currency': 'usd', 'value': .1}}]}], 'has_more': True, 'next_page': 'cursor'},
            {'data': [{'results': [{'amount': {'currency': 'usd', 'value': .2}}]}], 'has_more': False}]
        self.assertEqual(ai.openai_monthly_costs(), {'USD':'0.3'})
        self.assertIn('page=cursor', request.call_args.args[1])
