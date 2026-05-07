from InquirerPy import inquirer

from .locales import Locales


class Localizer:

    locale = "en-US"
    config = None

    @staticmethod
    def get_localized_text(*keys):
        localized = Localizer.get_nested_value(Locales.get(Localizer.locale), *keys)
        if localized is not None:
            return localized

        return Localizer.get_nested_value(Locales.get("en-US"), *keys)

    @staticmethod
    def get_nested_value(data, *keys):
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
                continue

            if isinstance(result, (list, tuple)) and isinstance(key, int):
                if key < 0 or key >= len(result):
                    return None
                result = result[key]
                continue

            return None
        return result

    @staticmethod
    def get_config_key(key):
        config_labels = Locales.get(Localizer.locale, {}).get("config", {})
        return config_labels.get(key, key)

    @staticmethod
    def unlocalize_key(key):
        for internal_key, localized_key in Locales.get(Localizer.locale, {}).get("config", {}).items():
            if localized_key == key:
                return internal_key
        return key

    @staticmethod
    def get_config_value(*keys):
        result = Localizer.get_nested_value(Localizer.config, *keys)
        if result is not None:
            return result

        localized_keys = [Localizer.get_config_key(key) for key in keys]
        result = Localizer.get_nested_value(Localizer.config, *localized_keys)
        if result is not None:
            return result

        raise KeyError(".".join(str(key) for key in keys))

    @staticmethod
    def get_config_value_or(default, *keys):
        try:
            return Localizer.get_config_value(*keys)
        except (KeyError, TypeError):
            return default

    @staticmethod
    def set_locale(config):
        if not isinstance(config, dict):
            return

        if isinstance(config, dict) and "locale" in config:
            locale = config["locale"][0]
            if locale in Locales and Locales[locale] != {}:
                Localizer.locale = locale
                return

        for data in Locales.values():
            if not data or "config" not in data:
                continue
            localized_locale_key = data["config"].get("locale")
            if localized_locale_key in config:
                locale = config[localized_locale_key][0]
                if locale in Locales and Locales[locale] != {}:
                    Localizer.locale = locale
                    return

    @staticmethod
    def prompt_locale(config):
        locale = config["locale"]
        current = locale[0]
        options = locale[1]
        choice = inquirer.select(
            message="select your locale (language)",
            default=current,
            choices={option: option for option in options},
            pointer=">",
        )
        choice = choice.execute()
        locale[0] = choice
        return config
