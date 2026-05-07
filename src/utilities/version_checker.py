from InquirerPy.utils import color_print

from .http_client import HTTPClient
from .logging import Logger
from ..localization.localization import Localizer


class Checker:
    @staticmethod
    def check_version(config):
        repository = Localizer.get_config_value_or("", "startup", "update_repository")
        if not repository:
            Logger.debug("Skipping update check because no update_repository is configured")
            return

        try:
            current_version = Localizer.get_config_value("version")
            data = HTTPClient.get_json(f"https://api.github.com/repos/{repository}/releases/latest")
            latest = data.get("tag_name")
            if latest and latest != current_version:
                release_url = f"https://github.com/{repository}/releases/tag/{latest}"
                color_print([
                    ("Yellow bold", f"({current_version} -> {latest}) {Localizer.get_localized_text('prints','version_checker','update_available')} "),
                    ("Cyan underline", release_url),
                ])
        except Exception:
            Logger.exception("Unable to check for updates")
            color_print([("Yellow bold", Localizer.get_localized_text("prints", "version_checker", "checker_error"))])
