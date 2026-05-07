import unittest
from unittest.mock import patch

from src.localization.localization import Localizer
from src.presence.presence_utilities import Utilities
from src.presence.presences import ingame, menu, pregame
from src.presence.presences.ingame_presences.range import Range_Session
from valclient.exceptions import PhaseError


class FakeRpc:
    def __init__(self):
        self.payloads = []

    def update(self, **payload):
        self.payloads.append(payload)


class FakePregameClient:
    puuid = "player-1"

    def pregame_fetch_player(self):
        return {"MatchID": "match-1"}

    def pregame_fetch_match(self, match_id):
        return {
            "AllyTeam": {"Players": [{"Subject": "someone-else"}]},
            "PhaseTimeRemainingNS": 0,
        }


class FakePregamePhaseClient:
    def pregame_fetch_player(self):
        raise PhaseError("not in pregame")


class FakeCoregameClient:
    puuid = "player-1"

    def coregame_fetch_player(self):
        return {}


class FakeJoinClient:
    region = "eu"
    puuid = "friend-1"


class FakeRangeClient:
    puuid = "player-1"

    def fetch_presence(self):
        return None

    def fetch_mmr(self):
        return {}


class FakeRankClient:
    def fetch_mmr(self):
        return {"QueueSkills": {"competitive": {"SeasonalInfoBySeasonID": {}}}}


class FakeRankedClient:
    def fetch_mmr(self):
        return {
            "QueueSkills": {
                "competitive": {
                    "SeasonalInfoBySeasonID": {
                        "season-1": {
                            "CompetitiveTier": 3,
                            "RankedRating": 42,
                            "LeaderboardRank": 0,
                        }
                    }
                }
            }
        }


class PresencePayloadTests(unittest.TestCase):
    def setUp(self):
        Localizer.locale = "en-US"
        Localizer.config = {
            "presences": {
                "menu": {"show_rank_in_comp_lobby": True},
                "modes": {
                    "range": {"show_rank_in_range": False},
                    "all": {
                        "small_image": ["agent", ["rank", "agent", "map"]],
                        "large_image": ["map", ["rank", "agent", "map"]],
                    },
                },
            },
            "presence_refresh_interval": 3,
        }

    def test_rpc_image_resolver_accepts_only_http_urls(self):
        self.assertEqual(
            Utilities.resolve_rpc_image("https://media.valorant-api.com/agents/agent-1/displayicon.png"),
            "https://media.valorant-api.com/agents/agent-1/displayicon.png",
        )
        self.assertIsNone(Utilities.resolve_rpc_image(""))
        self.assertIsNone(Utilities.resolve_rpc_image("agent_jett"))
        self.assertIsNone(Utilities.resolve_rpc_image("rank_3"))
        self.assertIsNone(Utilities.resolve_rpc_image("splash_ascent"))
        self.assertIsNone(Utilities.resolve_rpc_image("mode_unrated"))

    def test_rank_data_falls_back_when_season_missing(self):
        rank_image, rank_text = Utilities.fetch_rank_data(FakeRankClient(), {"season": {}, "comp_tiers": []})

        self.assertIsNone(rank_image)
        self.assertEqual(rank_text, "Rank not found")

    def test_rank_data_prefers_external_icon_url(self):
        rank_image, rank_text = Utilities.fetch_rank_data(
            FakeRankedClient(),
            {
                "season": {"season_uuid": "season-1"},
                "comp_tiers": [{
                    "id": 3,
                    "display_name_localized": "Iron 1",
                    "display_icon": "https://media.valorant-api.com/competitivetiers/set/3/largeicon.png",
                }],
            },
        )

        self.assertEqual(rank_image, "https://media.valorant-api.com/competitivetiers/set/3/largeicon.png")
        self.assertIn("Iron 1", rank_text)

    def test_rank_data_without_url_returns_no_image(self):
        rank_image, _ = Utilities.fetch_rank_data(
            FakeRankedClient(),
            {
                "season": {"season_uuid": "season-1"},
                "comp_tiers": [{
                    "id": 3,
                    "display_name_localized": "Iron 1",
                }],
            },
        )

        self.assertIsNone(rank_image)

    def test_mode_data_tolerates_missing_content_data(self):
        image, mode_name = Utilities.fetch_mode_data({"queueId": "swiftplay"}, None)

        self.assertIsNone(image)
        self.assertEqual(mode_name, "Swiftplay")

    def test_mode_data_uses_api_icon_alias(self):
        image, mode_name = Utilities.fetch_mode_data(
            {"queueId": "swiftplay"},
            {"queue_icon_aliases": {"swiftplay": "https://media.valorant-api.com/gamemodes/swiftplay/displayicon.png"}, "queue_aliases": {"swiftplay": "Swiftplay"}},
        )

        self.assertEqual(image, "https://media.valorant-api.com/gamemodes/swiftplay/displayicon.png")
        self.assertEqual(mode_name, "Swiftplay")

    def test_mode_data_rejects_local_asset_key(self):
        image, mode_name = Utilities.fetch_mode_data(
            {"queueId": "unrated"},
            {"queue_icon_aliases": {"unrated": "mode_unrated"}, "queue_aliases": {"unrated": "Unrated"}},
        )

        self.assertIsNone(image)
        self.assertEqual(mode_name, "Unrated")

    def test_map_data_prefers_external_splash_url(self):
        image, display_name, localized_name = Utilities.fetch_map_data(
            {"MapID": "/Game/Maps/Rook/Rook"},
            {"maps": [{
                "path": "/Game/Maps/Rook/Rook",
                "display_name": "Corrode",
                "display_name_localized": "Corrode",
                "display_icon": "https://media.valorant-api.com/maps/map-1/splash.png",
            }]},
        )

        self.assertEqual(image, "https://media.valorant-api.com/maps/map-1/splash.png")
        self.assertEqual(display_name, "Corrode")
        self.assertEqual(localized_name, "Corrode")

    def test_map_data_without_url_returns_no_image(self):
        image, _, _ = Utilities.fetch_map_data(
            {"MapID": "/Game/Maps/Rook/Rook"},
            {"maps": [{"path": "/Game/Maps/Rook/Rook"}]},
        )

        self.assertIsNone(image)

    def test_agent_data_prefers_external_icon_url(self):
        image, name = Utilities.fetch_agent_data(
            "agent-1",
            {"agents": [{
                "uuid": "agent-1",
                "display_icon": "https://media.valorant-api.com/agents/agent-1/displayicon.png",
                "display_name_localized": "KAY/O",
            }]},
        )

        self.assertEqual(image, "https://media.valorant-api.com/agents/agent-1/displayicon.png")
        self.assertEqual(name, "KAY/O")

    def test_agent_data_without_url_returns_no_image(self):
        image, name = Utilities.fetch_agent_data(
            "agent-1",
            {"agents": [{"uuid": "agent-1", "display_name_localized": "KAY/O"}]},
        )

        self.assertIsNone(image)
        self.assertEqual(name, "KAY/O")

    def test_pregame_payload_tolerates_missing_player_and_party_id(self):
        rpc = FakeRpc()

        pregame.presence(
            rpc,
            client=FakePregameClient(),
            data={"queueId": "unrated"},
            content_data={"agents": [], "queue_icon_aliases": {}, "queue_aliases": {"unrated": "Unrated"}},
            config={},
        )

        self.assertEqual(len(rpc.payloads), 1)
        self.assertEqual(rpc.payloads[0]["party_id"], "")

    def test_join_state_builds_open_party_confirmation_button_without_token(self):
        buttons = Utilities.get_join_state(
            FakeJoinClient(),
            {
                "webserver": {"port": 4100},
                "presences": {
                    "menu": {
                        "show_join_button_with_open_party": True,
                        "allow_join_requests": False,
                    }
                },
            },
            {"partyId": "party-1", "partyAccessibility": "OPEN"},
        )

        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0]["label"], "Join Party")
        self.assertEqual(buttons[0]["url"], "http://127.0.0.1:4100/valorant/confirm/join/party-1?region=eu")
        self.assertNotIn("token=", buttons[0]["url"])

    def test_join_state_builds_closed_party_request_button(self):
        buttons = Utilities.get_join_state(
            FakeJoinClient(),
            {
                "webserver": {"port": 4101},
                "presences": {
                    "menu": {
                        "show_join_button_with_open_party": True,
                        "allow_join_requests": True,
                    }
                },
            },
            {"partyId": "party-1", "partyAccessibility": "CLOSED"},
        )

        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0]["label"], "Request Join")
        self.assertEqual(buttons[0]["url"], "http://127.0.0.1:4101/valorant/confirm/request/party-1/friend-1?region=eu")

    def test_join_state_rejects_unsafe_party_id(self):
        buttons = Utilities.get_join_state(
            FakeJoinClient(),
            {
                "webserver": {"port": 4100},
                "presences": {
                    "menu": {
                        "show_join_button_with_open_party": True,
                        "allow_join_requests": True,
                    }
                },
            },
            {"partyId": "party 1", "partyAccessibility": "OPEN"},
        )

        self.assertIsNone(buttons)

    def test_pregame_phase_error_is_logged_without_payload(self):
        rpc = FakeRpc()

        with patch("src.presence.presences.pregame.Logger.debug") as debug:
            pregame.presence(rpc, client=FakePregamePhaseClient(), data={"queueId": "unrated"}, content_data={}, config={})

        self.assertEqual(rpc.payloads, [])
        debug.assert_called()

    def test_menu_payload_tolerates_partial_presence(self):
        rpc = FakeRpc()

        menu.presence(rpc, client=FakeRankClient(), data={}, content_data={}, config={})

        self.assertEqual(len(rpc.payloads), 1)
        self.assertEqual(rpc.payloads[0]["party_id"], "")

    def test_ingame_payload_tolerates_missing_match_id(self):
        rpc = FakeRpc()

        ingame.presence(rpc, client=FakeCoregameClient(), data={}, content_data={}, config={})

        self.assertEqual(rpc.payloads, [])

    def test_range_session_tolerates_missing_content(self):
        session = Range_Session(FakeRpc(), FakeRangeClient(), {}, "match-1", {}, {})

        self.assertIsNone(session.map_image)
        self.assertEqual(session.mode_name, "Range")
        self.assertIsNone(session.small_image)
