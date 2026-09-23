# generation A namespace scan

class SimpleNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
