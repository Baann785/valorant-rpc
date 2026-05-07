import unittest

from src.localization.localization import Localizer
from src.startup import Startup


class StartupTests(unittest.TestCase):
    def test_webserver_does_not_start_with_default_join_settings(self):
        Localizer.config = {
            "presences": {
                "menu": {
                    "show_join_button_with_open_party": False,
                    "allow_join_requests": False,
                }
            }
        }

        self.assertFalse(Startup.should_start_webserver(object()))

    def test_webserver_starts_when_join_flow_is_enabled(self):
        Localizer.config = {
            "presences": {
                "menu": {
                    "show_join_button_with_open_party": True,
                    "allow_join_requests": False,
                }
            }
        }

        self.assertTrue(Startup.should_start_webserver(object()))
