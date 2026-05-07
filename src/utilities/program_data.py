import json
import os
import sys
from InquirerPy.utils import color_print

from .filepath import Filepath
from .logging import Logger

class Program_Data:

    installs_path = os.path.expandvars("%PROGRAMDATA%\\valorant-tools\\installs.json")

    @staticmethod
    def update_file_location():
        Program_Data.check_for_folder()
        if getattr(sys, 'frozen', False):
            path = sys.executable
        else:
            color_print([("Yellow","not running from a packaged executable; skipping installation path update")])
            path = None

        if path is not None:
            installs = Program_Data.fetch_installs()
            installs["valorant-rpc"] = path
            Program_Data.modify_installs(installs)


    @staticmethod
    def fetch_installs():
        try:
            with open(Program_Data.installs_path, encoding="utf-8") as f:
                installs = json.load(f)
                if not isinstance(installs, dict):
                    Logger.debug("ProgramData installs file is not a JSON object; recreating it")
                    return Program_Data.create_installs_file()
                return installs
        except FileNotFoundError:
            return Program_Data.create_installs_file()
        except (OSError, ValueError):
            Logger.exception("Unable to read ProgramData installs file; recreating it")
            return Program_Data.create_installs_file()

    @staticmethod
    def modify_installs(payload):
        with open(Program_Data.installs_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        return Program_Data.fetch_installs()

    @staticmethod
    def modify_isntalls(payload):
        return Program_Data.modify_installs(payload)

    @staticmethod
    def create_installs_file():
        Program_Data.check_for_folder()
        with open(Program_Data.installs_path, "w", encoding="utf-8") as f:
            payload = {}
            json.dump(payload, f)

        return Program_Data.fetch_installs()

    @staticmethod
    def check_for_folder():
        programdata_folder = Filepath.get_programdata_folder()
        if not os.path.isdir(programdata_folder):
            os.makedirs(programdata_folder)
