# generation A cmd scan

class CmdContainer:
    def __init__(self):
        self.prompt = "(Cmd) "
        self.intro = None


class Cmd:
    def __init__(self):
        self._container = CmdContainer()
        self.prompt = self._container.prompt
        self.intro = self._container.intro
