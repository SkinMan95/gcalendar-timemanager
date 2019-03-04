import sys

class Settings:
    class __Settings:
        def __init__(self):
            self.settings = dict()
            self.settings["debug"] = False

        def setSetting(self, key, value):
            assert key is not None and value is not None
            self.settings[key] = value

        def getSetting(self, key):
            return self.settings.get(key)
        
    instance = None
    
    def __init__(self):
        if not Settings.instance:
            Settings.instance = Settings.__Settings()
            
    def __getattr__(self, name):
        return getattr(self.instance, name)


class Utilities:
    class __Utilities:
        def __init__(self):
            self.settings = Settings()

        def lprint(self, *args, **kwargs):
            """
            makes print for log
            """
            if self.settings.getSetting("debug"):
                print("[LOG] ", end="")
                print(*args, **kwargs)

        def eprint(self, *args2, **kwargs2):
            """
            makes print to stderr
            """
            print("[ERROR] ", end="", file=sys.stderr)
            print(*args2, file=sys.stderr, **kwargs2)
        
    instance = None
    
    def __init__(self):
        if not Utilities.instance:
            Utilities.instance = Utilities.__Utilities()
            
    def __getattr__(self, name):
        return getattr(self.instance, name)
