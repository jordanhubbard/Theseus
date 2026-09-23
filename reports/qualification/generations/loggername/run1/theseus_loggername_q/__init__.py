# generation A logger scan


class LoggerRecord(object):
    def __init__(self, name):
        self.name = name


def getLogger(name):
    return LoggerRecord(name)
