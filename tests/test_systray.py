import unittest
from unittest.mock import patch

from src.utilities.systray import Systray


class FakeTrayIcon:
    def __init__(self):
        self.visible = True
        self.stopped = False

    def stop(self):
        self.stopped = True


class SystrayTests(unittest.TestCase):
    def test_exit_stops_icon_and_calls_callback_without_forced_exit(self):
        calls = []
        tray = Systray(None, {}, on_exit=lambda: calls.append("exit"))
        tray.systray = FakeTrayIcon()

        with patch("src.utilities.systray.os._exit") as forced_exit:
            tray.exit()

        self.assertFalse(tray.systray.visible)
        self.assertTrue(tray.systray.stopped)
        self.assertEqual(calls, ["exit"])
        forced_exit.assert_not_called()
