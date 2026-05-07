from InquirerPy.utils import color_print
import sys, time, cursor, valclient, ctypes, traceback, os

from .utilities.killable_thread import Thread
from .utilities.config.app_config import Config
from .utilities.processes import Processes
from .utilities.systray import Systray
from .utilities.version_checker import Checker
from .utilities.logging import Logger
from .utilities.program_data import Program_Data

from .localization.localization import Localizer

from .presence.presence import Presence

from .webserver import server

# Console window management for the Windows tray application.
kernel32 = ctypes.WinDLL('kernel32')
user32 = ctypes.WinDLL('user32')
hWnd = kernel32.GetConsoleWindow()
kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4|0x80|0x20|0x2|0x10|0x1|0x00|0x100)) #disable inputs to console
kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7) #allow for ANSI sequences

class Startup:
    def __init__(self):
        self.client = None
        self.config = None
        self.installs = {}
        self.presence = None
        self.presence_thread = None
        self.systray = None
        self.systray_thread = None
        self.webserver_thread = None
        self.shutdown_requested = False

        if Processes.is_program_already_running():
            return

        cursor.hide()
        Logger.create_logger()
        Program_Data.update_file_location()

        self.config = Config.fetch_config()
        if "locale" in self.config.keys():
            if self.config["locale"][0] == "":
                config = Localizer.prompt_locale(self.config)
                Config.modify_config(config)
                Systray.restart()

        self.installs = Program_Data.fetch_installs()
        Localizer.set_locale(self.config)
        self.config = Config.check_config()
        Localizer.config = self.config

        Logger.debug(self.config)

        if Localizer.get_config_value("region",0) == "": # try to autodetect region on first launch
            if not self.check_region():
                self.wait_for_user_to_exit("Unable to autodetect Valorant region.")
                return

        ctypes.windll.kernel32.SetConsoleTitleW(f"valorant-rpc {Localizer.get_config_value('version')}") 

        color_print([("Red", Localizer.get_localized_text("prints","startup","wait_for_rpc"))])
        try:
            self.presence = Presence(self.config)
            Startup.clear_line()
        except Exception as e:
            Logger.exception("Unable to connect Discord presence")
            traceback.print_exc()
            color_print([("Cyan",f"{Localizer.get_localized_text('prints','startup','discord_not_detected')} ({e})")])
            if not Processes.are_processes_running():
                color_print([("Red", Localizer.get_localized_text("prints","startup","starting_valorant"))])
                self.start_game()
            self.wait_for_user_to_exit()
            return

        self.run()


    def run(self):
        self.presence.update_presence("startup")
        Checker.check_version(self.config)
        if not Processes.are_processes_running():
            color_print([("Red", Localizer.get_localized_text("prints","startup","starting_valorant"))])
            if not self.start_game():
                self.wait_for_user_to_exit()
                self.shutdown()
                return
        
        if not self.setup_client():
            self.wait_for_user_to_exit("Unable to activate Valorant client.")
            self.shutdown()
            return

        self.systray = Systray(self.client,self.config,on_exit=self.request_shutdown)
        self.dispatch_systray()
        
        try:
            current_presence = self.client.fetch_presence()
        except Exception:
            Logger.exception("Unable to fetch initial Riot presence")
            current_presence = None

        if current_presence is None and not self.wait_for_presence():
            self.wait_for_user_to_exit()
            self.shutdown()
            return

        self.check_run_cli()
        self.dispatch_webserver() 
        self.dispatch_presence()
        
        color_print([("LimeGreen",f"{Localizer.get_localized_text('prints','startup','startup_successful')}\n")])
        time.sleep(5)
        user32.ShowWindow(hWnd, 0) #hide window

        self.systray_thread.join()
        self.shutdown()
        

    def dispatch_webserver(self):
        if not self.should_start_webserver():
            Logger.debug("webserver disabled because join links are disabled")
            return

        server.client = self.client 
        server.config = self.config
        server.configure(self.client, self.config)
        port = Localizer.get_config_value_or(4100, "webserver", "port")
        self.webserver_thread = Thread(target=lambda: server.start(port=port),daemon=True)
        self.webserver_thread.start()

    def should_start_webserver(self):
        show_join = Localizer.get_config_value_or(False, "presences", "menu", "show_join_button_with_open_party")
        allow_requests = Localizer.get_config_value_or(False, "presences", "menu", "allow_join_requests")
        return bool(show_join or allow_requests)
        
    def dispatch_presence(self):
        self.presence_thread = Thread(target=self.presence.init_loop,daemon=True)
        self.presence_thread.start()

    def dispatch_systray(self):
        self.systray_thread = Thread(target=self.systray.run)
        self.systray_thread.start()

    def setup_client(self):
        try:
            self.client = valclient.Client(region=Localizer.get_config_value("region",0))
            self.client.activate()
            self.presence.client = self.client
            return True
        except Exception:
            Logger.exception("Unable to activate Valorant client")
            self.check_region()
            return False

    def wait_for_presence(self):
        presence_timeout = Localizer.get_config_value("startup","presence_timeout")
        presence_timer = 0 
        print()
        while not self.shutdown_requested:
            try:
                if self.client.fetch_presence() is not None:
                    Startup.clear_line()
                    Startup.clear_line()
                    return True
            except Exception:
                Logger.exception("Unable to fetch Riot presence while waiting for startup")

            Startup.clear_line()
            color_print([("Cyan", "["),("White",f"{presence_timer}"),("Cyan", f"] {Localizer.get_localized_text('prints','startup','waiting_for_presence')}")])
            presence_timer += 1
            # Check if Riot presence has been unavailable for too long.
            if presence_timer >= presence_timeout:
                print()
                color_print([("Red", f"Timed out waiting for Riot Presence after {presence_timeout} seconds.")])
                return False
            time.sleep(1)
        return False

    def start_game(self):
        launch_timeout = Localizer.get_config_value("startup","game_launch_timeout")
        launch_timer = 0
        
        try:
            Logger.debug("Attempting to launch Valorant via riotclient URI...")
            # os.startfile is the equivalent of double-clicking or running "start ..." in cmd
            # but handles the system association directly.
            # Using the URI scheme is more robust than finding the executable path manually.
            os.startfile("riotclient://launch-product?product=valorant&patchline=live")
        except Exception as e:
            color_print([("Red", f"Failed to launch Valorant: {e}")])
            Logger.debug(f"Failed to launch Valorant: {e}")

        print()
        while not Processes.are_processes_running():
            Startup.clear_line()
            color_print([("Cyan", "["),("White",f"{launch_timer}"),("Cyan", f"] {Localizer.get_localized_text('prints','startup','waiting_for_valorant')}")])
            launch_timer += 1
            if launch_timer >= launch_timeout:
                print()
                color_print([("Red", f"Timed out waiting for Valorant to start after {launch_timeout} seconds.")])
                color_print([("Yellow", "Please ensure Valorant is installed and can be launched manually.")])
                return False
            time.sleep(1)
        Startup.clear_line()
        return True

    def check_run_cli(self):
        if Localizer.get_config_value("startup","auto_launch_skincli"):
            skincli_path = self.installs.get("valorant-skin-cli")
            if skincli_path is not None:
                skincli_path = os.path.abspath(os.path.expandvars(skincli_path))
                if os.path.isfile(skincli_path):
                    os.startfile(skincli_path)
                else:
                    Logger.debug(f"valorant-skin-cli path does not exist: {skincli_path}")

    def request_shutdown(self):
        self.shutdown_requested = True

    def shutdown(self):
        self.shutdown_requested = True

        if self.presence is not None:
            self.presence.stop()

        if self.presence_thread is not None:
            self.presence_thread.stop()

        if self.webserver_thread is not None:
            try:
                server.stop()
            except Exception:
                Logger.exception("Unable to stop webserver")

        if self.systray is not None and getattr(self.systray, "systray", None) is not None:
            try:
                self.systray.systray.visible = False
                self.systray.systray.stop()
            except Exception:
                Logger.exception("Unable to stop systray")

    def wait_for_user_to_exit(self, message=None):
        user32.ShowWindow(hWnd, 1)
        if message:
            color_print([("Red", message)])
            Logger.debug(message)
        try:
            input(Localizer.get_localized_text("prints","errors","exit"))
        except EOFError:
            Logger.debug("No stdin available while waiting for exit")

    def check_region(self):
        color_print([("Red bold",Localizer.get_localized_text("prints","startup","autodetect_region"))])
        try:
            client = valclient.Client(region="na")
            client.activate()
            sessions = client.riotclient_session_fetch_sessions()
            for _,session in sessions.items():
                if session.get("productId") == "valorant":
                    launch_args = session.get("launchConfiguration", {}).get("arguments", [])
                    for arg in launch_args:
                        if "-ares-deployment" in arg:
                            region = arg.replace("-ares-deployment=","")
                            self.config["region"][0] = region
                            Config.modify_config(self.config)
                            color_print([("LimeGreen",f"{Localizer.get_localized_text('prints','startup','autodetected_region')} {Localizer.get_config_value('region',0)}")])
                            time.sleep(5)
                            Systray.restart()
                            return True
        except Exception:
            Logger.exception("Unable to autodetect Valorant region")
        return False

    @staticmethod
    def clear_line():
        sys.stdout.write("\033[F") # move cursor up one line
        sys.stdout.write("\r\033[K")
