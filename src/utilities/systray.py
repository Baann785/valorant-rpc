from PIL import Image
from pystray import Icon as icon, Menu as menu, MenuItem as item
import ctypes, os, sys, time
from InquirerPy.utils import color_print

from .filepath import Filepath
from .config.modify_config import Config_Editor
from .logging import Logger
from ..localization.localization import Localizer

kernel32 = ctypes.WinDLL('kernel32')
user32 = ctypes.WinDLL('user32')
hWnd = kernel32.GetConsoleWindow()

window_shown = False


class Systray:

    def __init__(self, client, config, on_exit=None):
        self.client = client
        self.config = config
        self.on_exit = on_exit
        self.systray = None

    def run(self):
        global window_shown
        Systray.generate_icon()
        systray_image = Image.open(Filepath.get_path(os.path.join(Filepath.get_appdata_folder(), 'favicon.ico')))
        systray_menu = menu(
            item('show window', Systray.tray_window_toggle, checked=lambda item: window_shown),
            item('config', Systray.modify_config),
            item('reload', Systray.restart),
            item('exit', self.exit)
        )
        self.systray = icon("valorant-rpc", systray_image, "valorant-rpc", systray_menu)
        self.systray.run()

    def exit(self):
        if self.systray is not None:
            self.systray.visible = False
            self.systray.stop()
        if self.on_exit is not None:
            self.on_exit()

    @staticmethod
    def generate_icon():
        icon_path = Filepath.get_path(os.path.join(Filepath.get_appdata_folder(),'favicon.ico'))
        if os.path.exists(icon_path):
            return

        bundled_icon = Filepath.get_path("favicon.ico")
        if os.path.exists(bundled_icon):
            with open(bundled_icon, "rb") as source, open(icon_path, "wb") as target:
                target.write(source.read())
        else:
            Logger.debug("Bundled systray icon not found")

    @staticmethod 
    def modify_config():
        user32.ShowWindow(hWnd, 1)
        Config_Editor()
        if not window_shown:
            color_print([("LimeGreen",f"{Localizer.get_localized_text('prints','systray','hiding_window')}\n")])
            time.sleep(1)
            user32.ShowWindow(hWnd, 0)

    @staticmethod
    def restart():
        user32.ShowWindow(hWnd, 1)
        sys.stdout.write("\033c")
        sys.stdout.flush()
        if getattr(sys, "frozen", False):
            restart_args = [sys.executable, *sys.argv[1:]]
        else:
            entrypoint = sys.argv[0] if sys.argv and sys.argv[0] else os.path.join(os.path.dirname(__file__), "..", "..", "main.py")
            restart_args = [sys.executable, os.path.abspath(entrypoint), *sys.argv[1:]]

        os.execl(sys.executable, *restart_args)

    @staticmethod
    def tray_window_toggle(icon,item):
        global window_shown
        try:
            window_shown = not item.checked
            if window_shown:
                user32.ShowWindow(hWnd, 1)
            else:
                user32.ShowWindow(hWnd, 0)
        except Exception:
            Logger.exception("Unable to toggle tray window")
