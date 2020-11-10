class Sensor:
    __slots__ = ('fqts', 'path', 'type_name')

    def __init__(self, fqts: str, path: str, type_name: str):
        self.fqts = fqts
        self.path = path
        self.type_name = type_name

