from pypresence import Presence as PyPresence
from pypresence.exceptions import InvalidPipe
from InquirerPy.utils import color_print
import time, traceback, ctypes, ssl

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

from ..content.content_loader import Loader
from ..localization.localization import Localizer
from ..utilities.logging import Logger
from .presences import (ingame,menu,startup,pregame)

kernel32 = ctypes.WinDLL('kernel32')
user32 = ctypes.WinDLL('user32')
hWnd = kernel32.GetConsoleWindow()


class Presence:

    def __init__(self,config):
        self.config = config
        self.client = None
        self.saved_locale = None
        self.content_data = {}
        self.missing_presence_seconds = 0
        self.should_stop = False
        try:
            self.rpc = PyPresence(client_id=str(Localizer.get_config_value("client_id")))
            self.rpc.connect()
        except InvalidPipe as e:
            raise Exception(e)

    def main_loop(self):
        while not self.should_stop:
            refresh_interval = max(1, int(Localizer.get_config_value_or(3, "presence_refresh_interval")))
            presence_timeout = max(refresh_interval, int(Localizer.get_config_value_or(60, "startup", "presence_timeout")))

            try:
                presence_data = self.client.fetch_presence()
            except Exception:
                Logger.exception("Unable to fetch Riot presence")
                presence_data = None

            if presence_data is None:
                if not self.wait_for_presence_recovery(refresh_interval, presence_timeout):
                    return
                continue

            self.missing_presence_seconds = 0
            match_data = presence_data.get("matchPresenceData", {})
            session_loop_state = match_data.get("sessionLoopState") or presence_data.get("sessionLoopState", "MENUS")
            self.update_presence(session_loop_state, presence_data)

            if Localizer.locale != self.saved_locale:
                self.saved_locale = Localizer.locale
                self.content_data = Loader.load_all_content(self.client)

            time.sleep(refresh_interval)

    def wait_for_presence_recovery(self, refresh_interval, presence_timeout):
        self.missing_presence_seconds += refresh_interval
        Logger.debug(f"Riot presence missing for {self.missing_presence_seconds}s")

        if self.missing_presence_seconds >= presence_timeout:
            user32.ShowWindow(hWnd, 1)
            message = f"Timed out waiting for Riot Presence after {presence_timeout} seconds."
            color_print([("Red", message)])
            Logger.debug(message)
            try:
                self.rpc.clear()
            except Exception:
                Logger.exception("Unable to clear Discord presence")
            return False

        time.sleep(refresh_interval)
        return True

    def stop(self):
        self.should_stop = True
        try:
            self.rpc.clear()
        except Exception:
            Logger.exception("Unable to clear Discord presence")

    def init_loop(self):
        try:
            if self.should_stop:
                return
            self.content_data = Loader.load_all_content(self.client)
            color_print([("LimeGreen bold", Localizer.get_localized_text("prints","presence","presence_running"))])
            presence_data = self.client.fetch_presence()

            if presence_data is not None and not self.should_stop:
                match_data = presence_data.get("matchPresenceData", {})
                session_loop_state = match_data.get("sessionLoopState") or presence_data.get("sessionLoopState", "MENUS")
                self.update_presence(session_loop_state, presence_data)

            if not self.should_stop:
                self.main_loop()

        except Exception:
            user32.ShowWindow(hWnd, 1)
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4|0x80|0x20|0x2|0x10|0x1|0x40|0x100))
            color_print([("Red bold",Localizer.get_localized_text("prints","errors","error_message"))])
            traceback.print_exc()
            Logger.exception("Presence loop stopped")

    def update_presence(self,ptype,data=None):
        presence_types = {
            "startup": startup,
            "MENUS": menu,
            "PREGAME": pregame,
            "INGAME": ingame,
        }
        presence_type = presence_types.get(ptype)
        if presence_type is None:
            Logger.debug(f"Unknown presence type: {ptype}")
            return

        try:
            presence_type.presence(self.rpc,client=self.client,data=data,content_data=self.content_data,config=self.config)
        except Exception:
            Logger.exception(f"Unable to update Discord presence for {ptype}")
