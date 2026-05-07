import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src.content.content_loader import Loader
from src.localization.localization import Localizer


class FakeContentClient:
    def fetch_content(self):
        return {"Seasons": []}


class ContentLoaderTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.appdata_patch = patch(
            "src.content.content_loader.Filepath.get_appdata_folder",
            return_value=self.tempdir.name,
        )
        self.appdata_patch.start()
        self.addCleanup(self.appdata_patch.stop)
        Localizer.locale = "fr-FR"

    def test_localized_field_falls_back_to_english(self):
        value = Loader.localized_field({"displayName": {"en-US": "Ascent"}}, "displayName")

        self.assertEqual(value, "Ascent")

    def test_load_all_content_stores_agent_display_icon_url(self):
        responses = {
            "/agents": {"data": [{
                "uuid": "agent-1",
                "displayName": {"en-US": "Iso"},
                "developerName": "Aggrobot",
                "displayIcon": "https://media.valorant-api.com/agents/agent-1/displayicon.png",
            }]},
            "/maps": {"data": []},
            "/gamemodes": {"data": []},
            "/competitivetiers": {"data": []},
        }

        with patch.object(Loader, "fetch", side_effect=lambda endpoint, params=None: responses[endpoint]):
            content = Loader.load_all_content(FakeContentClient())

        self.assertEqual(content["agents"][0]["display_icon"], "https://media.valorant-api.com/agents/agent-1/displayicon.png")

    def test_load_all_content_stores_rank_icon_url(self):
        responses = {
            "/agents": {"data": []},
            "/maps": {"data": []},
            "/gamemodes": {"data": []},
            "/competitivetiers": {"data": [{
                "tiers": [{
                    "tier": 3,
                    "tierName": {"en-US": "IRON 1"},
                    "largeIcon": "https://media.valorant-api.com/competitivetiers/set/3/largeicon.png",
                }]
            }]},
        }

        with patch.object(Loader, "fetch", side_effect=lambda endpoint, params=None: responses[endpoint]):
            content = Loader.load_all_content(FakeContentClient())

        self.assertEqual(content["comp_tiers"][0]["display_icon"], "https://media.valorant-api.com/competitivetiers/set/3/largeicon.png")

    def test_load_all_content_stores_map_splash_url(self):
        responses = {
            "/agents": {"data": []},
            "/maps": {"data": [{
                "uuid": "map-1",
                "displayName": {"en-US": "Corrode"},
                "mapUrl": "/Game/Maps/Rook/Rook",
                "splash": "https://media.valorant-api.com/maps/map-1/splash.png",
            }]},
            "/gamemodes": {"data": []},
            "/competitivetiers": {"data": []},
        }

        with patch.object(Loader, "fetch", side_effect=lambda endpoint, params=None: responses[endpoint]):
            content = Loader.load_all_content(FakeContentClient())

        self.assertEqual(content["maps"][0]["display_icon"], "https://media.valorant-api.com/maps/map-1/splash.png")

    def test_load_all_content_builds_queue_icon_aliases(self):
        responses = {
            "/agents": {"data": []},
            "/maps": {"data": []},
            "/gamemodes": {"data": [{
                "uuid": "mode-1",
                "displayName": {"en-US": "Swiftplay"},
                "displayIcon": "https://media.valorant-api.com/gamemodes/swiftplay/displayicon.png",
            }]},
            "/competitivetiers": {"data": []},
        }

        with patch.object(Loader, "fetch", side_effect=lambda endpoint, params=None: responses[endpoint]):
            content = Loader.load_all_content(FakeContentClient())

        self.assertEqual(content["queue_icon_aliases"]["swiftplay"], "https://media.valorant-api.com/gamemodes/swiftplay/displayicon.png")

    def test_load_all_content_uses_cache_when_network_fails(self):
        cached = Loader.build_base_content()
        cached["agents"].append({"uuid": "cached-agent"})
        with open(os.path.join(self.tempdir.name, Loader.CACHE_FILE), "w", encoding="utf-8") as f:
            json.dump(cached, f)

        with patch.object(Loader, "fetch", side_effect=RuntimeError("offline")), \
             patch("src.content.content_loader.Logger.exception"):
            content = Loader.load_all_content(FakeContentClient())

        self.assertEqual(content["agents"][0]["uuid"], "cached-agent")

    def test_load_all_content_returns_base_content_without_cache(self):
        with patch.object(Loader, "fetch", side_effect=RuntimeError("offline")), \
             patch("src.content.content_loader.Logger.exception"):
            content = Loader.load_all_content(FakeContentClient())

        self.assertIn("queue_aliases", content)
        self.assertEqual(content["agents"], [])
