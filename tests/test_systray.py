import unittest
from unittest.mock import Mock

import src.utilities.systray as systray_module
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

        forced_exit = Mock()
        original_exit = getattr(systray_module.os, "_exit")
        try:
            setattr(systray_module.os, "_exit", forced_exit)
            tray.exit()
        finally:
            setattr(systray_module.os, "_exit", original_exit)

        self.assertFalse(tray.systray.visible)
        self.assertTrue(tray.systray.stopped)
        self.assertEqual(calls, ["exit"])
        forced_exit.assert_not_called()
