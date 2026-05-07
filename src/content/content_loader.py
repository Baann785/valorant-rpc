import json
import os
from ..localization.localization import Localizer
from ..utilities.filepath import Filepath
from ..utilities.http_client import HTTPClient
from ..utilities.logging import Logger


class Loader:
    BASE_URL = "https://valorant-api.com/v1"
    CACHE_FILE = "content_cache.json"

    @staticmethod
    def fetch(endpoint="/", params=None):
        request_params = {"language": "all"}
        if params:
            request_params.update(params)
        return HTTPClient.get_json(f"{Loader.BASE_URL}{endpoint}", params=request_params)

    @staticmethod
    def cache_path():
        return Filepath.get_path(os.path.join(Filepath.get_appdata_folder(), Loader.CACHE_FILE))

    @staticmethod
    def build_base_content():
        return {
            "agents": [],
            "maps": [],
            "modes": [],
            "comp_tiers": [],
            "season": {},
            "queue_aliases": {
                "newmap": "New Map",
                "competitive": "Competitive",
                "unrated": "Unrated",
                "spikerush": "Spike Rush",
                "deathmatch": "Deathmatch",
                "ggteam": "Escalation",
                "onefa": "Replication",
                "custom": "Custom",
                "snowball": "Snowball Fight",
                "swiftplay": "Swiftplay",
                "hurm": "Team Deathmatch",
                "": "Custom",
            },
            "team_aliases": {
                "TeamOne": "Defender",
                "TeamTwo": "Attacker",
                "TeamSpectate": "Observer",
                "TeamOneCoaches": "Defender Coach",
                "TeamTwoCoaches": "Attacker Coach",
            },
            "queue_display_aliases": {
                "newmap": "Standard",
                "competitive": "Standard",
                "unrated": "Standard",
                "custom": "Standard",
                "spikerush": "Spike Rush",
                "deathmatch": "Deathmatch",
                "ggteam": "Escalation",
                "onefa": "Replication",
                "snowball": "Snowball Fight",
                "swiftplay": "Swiftplay",
                "hurm": "Team Deathmatch",
                "": "Standard",
            },
            "queue_icon_aliases": {},
        }

    @staticmethod
    def localized_field(data, field_name):
        values = data.get(field_name, {})
        if not isinstance(values, dict):
            return values or ""

        return values.get(Localizer.locale) or values.get("en-US") or next(iter(values.values()), "")

    @staticmethod
    def load_all_content(client):
        try:
            content_data = Loader.build_base_content()
            all_content = client.fetch_content()
            agents = Loader.fetch("/agents", params={"isPlayableCharacter": "true"}).get("data", [])
            maps = Loader.fetch("/maps").get("data", [])
            modes = Loader.fetch("/gamemodes").get("data", [])
            comp_tiers_data = Loader.fetch("/competitivetiers").get("data", [])
            comp_tiers = comp_tiers_data[-1].get("tiers", []) if comp_tiers_data else []

            for season in all_content.get("Seasons", []):
                if season.get("IsActive") and season.get("Type") == "act":
                    content_data["season"] = {
                        "competitive_uuid": season.get("ID", ""),
                        "season_uuid": season.get("ID", ""),
                        "display_name": season.get("Name", ""),
                    }

            for agent in agents:
                content_data["agents"].append({
                    "uuid": agent.get("uuid", ""),
                    "display_name": Loader.localized_field_for_locale(agent, "displayName", "en-US"),
                    "display_name_localized": Loader.localized_field(agent, "displayName"),
                    "internal_name": agent.get("developerName", ""),
                    "display_icon": agent.get("displayIcon") or agent.get("displayIconSmall") or "",
                })

            for game_map in maps:
                map_url = game_map.get("mapUrl", "")
                content_data["maps"].append({
                    "uuid": game_map.get("uuid", ""),
                    "display_name": Loader.localized_field_for_locale(game_map, "displayName", "en-US"),
                    "display_name_localized": Loader.localized_field(game_map, "displayName"),
                    "path": map_url,
                    "internal_name": map_url.split("/")[-1] if map_url else "",
                    "display_icon": game_map.get("splash") or game_map.get("displayIcon") or game_map.get("listViewIcon") or "",
                })

            for mode in modes:
                display_name = Loader.localized_field_for_locale(mode, "displayName", "en-US")
                content_data["modes"].append({
                    "uuid": mode.get("uuid", ""),
                    "display_name": display_name,
                    "display_name_localized": Loader.localized_field(mode, "displayName"),
                    "display_icon": mode.get("displayIcon") or "",
                })

            mode_icons_by_name = {
                mode.get("display_name", "").lower(): mode.get("display_icon")
                for mode in content_data["modes"]
                if mode.get("display_icon")
            }
            for queue_id, display_name in content_data["queue_display_aliases"].items():
                icon = mode_icons_by_name.get(display_name.lower())
                if icon:
                    content_data["queue_icon_aliases"][queue_id] = icon

            for tier in comp_tiers:
                content_data["comp_tiers"].append({
                    "display_name": Loader.localized_field_for_locale(tier, "tierName", "en-US"),
                    "display_name_localized": Loader.localized_field(tier, "tierName"),
                    "id": tier.get("tier", 0),
                    "display_icon": tier.get("largeIcon") or tier.get("smallIcon") or "",
                })

            Loader.write_cache(content_data)
            return content_data
        except Exception:
            Logger.exception("Unable to load Valorant content")
            cached = Loader.read_cache()
            if cached:
                return cached
            return Loader.build_base_content()

    @staticmethod
    def localized_field_for_locale(data, field_name, locale):
        values = data.get(field_name, {})
        if not isinstance(values, dict):
            return values or ""
        return values.get(locale) or values.get("en-US") or next(iter(values.values()), "")

    @staticmethod
    def read_cache():
        try:
            with open(Loader.cache_path(), encoding="utf-8") as f:
                cached = json.load(f)
            if isinstance(cached, dict):
                return cached
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            Logger.exception("Unable to read Valorant content cache")
        return None

    @staticmethod
    def write_cache(content_data):
        try:
            os.makedirs(Filepath.get_appdata_folder(), exist_ok=True)
            with open(Loader.cache_path(), "w", encoding="utf-8") as f:
                json.dump(content_data, f, ensure_ascii=False)
        except OSError:
            Logger.exception("Unable to write Valorant content cache")
