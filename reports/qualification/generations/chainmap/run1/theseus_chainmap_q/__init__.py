# generation A chain scan

class ChainMap(object):
    def __init__(self, *maps):
        self.maps = list(maps)

    def __getitem__(self, key):
        for mapping in self.maps:
            try:
                return mapping[key]
            except KeyError:
                continue
        raise KeyError(key)
