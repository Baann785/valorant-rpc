import copy
import json
import os
import time
from json import JSONDecodeError

from valclient.client import Client

from ..filepath import Filepath
from ..logging import Logger
from ...localization.locales import Locales


APP_VERSION = "v3.2.7"
FALLBACK_REGIONS = ["na", "eu", "ap", "kr", "latam", "br"]


def fetch_regions():
    try:
        return Client.fetch_regions()
    except Exception:
        Logger.exception("Unable to fetch Valorant regions")
        return FALLBACK_REGIONS


def build_default_config():
    return {
        "version": APP_VERSION,
        "region": ["", fetch_regions()],
        "client_id": 811469787657928704,
        "presence_refresh_interval": 3,
        "locale": ["", [locale for locale, data in Locales.items() if data != {}]],
        "presences": {
            "menu": {
                "show_rank_in_comp_lobby": True,
                "show_join_button_with_open_party": False,
                "allow_join_requests": False,
            },
            "modes": {
                "all": {
                    "small_image": ["agent", ["rank", "agent", "map"]],
                    "large_image": ["map", ["rank", "agent", "map"]],
                },
                "range": {
                    "show_rank_in_range": False,
                },
            },
        },
        "startup": {
            "game_launch_timeout": 50,
            "presence_timeout": 60,
            "show_github_link": True,
            "auto_launch_skincli": True,
            "update_repository": "",
        },
        "webserver": {
            "port": 4100,
        },
    }


default_config = build_default_config()


class Config:

    @staticmethod
    def config_path():
        return Filepath.get_path(os.path.join(Filepath.get_appdata_folder(), "config.json"))

    @staticmethod
    def ensure_config_folder():
        os.makedirs(Filepath.get_appdata_folder(), exist_ok=True)

    @staticmethod
    def copy_default_config():
        config = copy.deepcopy(default_config)
        config["region"][1] = fetch_regions()
        return config

    @staticmethod
    def fetch_config():
        config_path = Config.config_path()
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            return Config.create_default_config()
        except JSONDecodeError:
            Config.backup_invalid_config(config_path)
            return Config.create_default_config()
        except OSError:
            Logger.exception("Unable to read config file")
            raise

        if not isinstance(config, dict):
            Config.backup_invalid_config(config_path)
            return Config.create_default_config()

        return config

    @staticmethod
    def backup_invalid_config(config_path):
        if not os.path.exists(config_path):
            return

        backup_path = f"{config_path}.invalid-{int(time.time())}"
        try:
            os.replace(config_path, backup_path)
            Logger.debug(f"Backed up invalid config to {backup_path}")
        except OSError:
            Logger.exception("Unable to back up invalid config")

    @staticmethod
    def modify_config(new_config):
        Config.ensure_config_folder()
        with open(Config.config_path(), "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)

        return Config.fetch_config()

    @staticmethod
    def check_config():
        migrated_config = Config.localize_config(Config.fetch_config(), True)
        default = Config.copy_default_config()

        def merge(blank, current, key_name=None):
            if key_name == "version":
                return copy.deepcopy(blank)

            if isinstance(blank, dict):
                if not isinstance(current, dict):
                    current = {}

                merged = {}
                for key, value in blank.items():
                    merged[key] = merge(value, current.get(key), key)
                return merged

            if isinstance(blank, list):
                default_choice = blank[0] if blank else None
                default_options = copy.deepcopy(blank[1]) if len(blank) > 1 else []

                current_choice = current[0] if isinstance(current, list) and current else default_choice
                if current_choice not in default_options:
                    current_choice = default_choice

                return [current_choice, default_options]

            if not isinstance(current, type(blank)):
                return copy.deepcopy(blank)

            return current

        config = merge(default, migrated_config)
        Config.modify_config(config)
        return config

    @staticmethod
    def localize_config(config, unlocalize=False):
        if not unlocalize:
            return config

        def migrate_value(value):
            if isinstance(value, dict):
                migrated = {}
                for key, child in value.items():
                    migrated[Config.unlocalize_key_any_locale(key)] = migrate_value(child)
                return migrated

            if isinstance(value, list):
                migrated = copy.deepcopy(value)
                if migrated and isinstance(migrated[0], str):
                    migrated[0] = Config.unlocalize_key_any_locale(migrated[0])
                if len(migrated) > 1 and isinstance(migrated[1], list):
                    migrated[1] = [
                        Config.unlocalize_key_any_locale(option) if isinstance(option, str) else option
                        for option in migrated[1]
                    ]
                return migrated

            return value

        return migrate_value(config)

    @staticmethod
    def unlocalize_key_any_locale(key):
        for data in Locales.values():
            if not data or "config" not in data:
                continue

            for internal_key, localized_key in data["config"].items():
                if key == localized_key:
                    return internal_key

        return key

    @staticmethod
    def create_default_config():
        config = Config.copy_default_config()
        Config.modify_config(config)
        return config
