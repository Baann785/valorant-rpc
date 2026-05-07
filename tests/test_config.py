import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src.localization.locales import Locales
from src.localization.localization import Localizer
from src.utilities.config.app_config import Config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.appdata_patch = patch(
            "src.utilities.config.app_config.Filepath.get_appdata_folder",
            return_value=self.tempdir.name,
        )
        self.regions_patch = patch(
            "src.utilities.config.app_config.fetch_regions",
            return_value=["na", "eu"],
        )
        self.appdata_patch.start()
        self.regions_patch.start()
        self.addCleanup(self.appdata_patch.stop)
        self.addCleanup(self.regions_patch.stop)
        Localizer.locale = "en-US"

    def test_missing_config_creates_internal_default(self):
        config = Config.fetch_config()

        self.assertEqual(config["version"], "v3.2.7")
        self.assertIn("show_join_button_with_open_party", config["presences"]["menu"])
        self.assertEqual(config["region"][1], ["na", "eu"])

    def test_corrupt_config_is_backed_up_and_recreated(self):
        config_path = os.path.join(self.tempdir.name, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("{broken")

        config = Config.fetch_config()

        self.assertEqual(config["version"], "v3.2.7")
        backups = [name for name in os.listdir(self.tempdir.name) if name.startswith("config.json.invalid-")]
        self.assertEqual(len(backups), 1)

    def test_localized_keys_are_migrated_to_internal_keys(self):
        localized_region = next(
            data["config"]["region"]
            for data in Locales.values()
            if data and data["config"].get("region") != "region"
        )
        migrated = Config.localize_config({localized_region: ["na", ["na", "eu"]]}, True)

        self.assertIn("region", migrated)
        self.assertEqual(migrated["region"][0], "na")

    def test_check_config_removes_unknown_keys_and_preserves_valid_values(self):
        config_path = os.path.join(self.tempdir.name, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"region": ["eu", ["eu"]], "unknown": True}, f)

        config = Config.check_config()

        self.assertEqual(config["region"][0], "eu")
        self.assertNotIn("unknown", config)

    def test_localizer_config_value_supports_list_indexes(self):
        Localizer.config = {"region": ["eu", ["na", "eu"]]}

        self.assertEqual(Localizer.get_config_value("region", 0), "eu")
        self.assertEqual(Localizer.get_config_value("region", 1), ["na", "eu"])
