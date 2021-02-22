class SensorWriteEvent:
    """
    An event describing a situation wherein a sensor was written

    :param timestamp: in milliseconds
    """
    __slots__ = ('timestamp', 'who', 'hr_sensor', 'hr_value',
                 'fqts', 'value', 'reason')

    def __hash__(self):
        return hash(self.timestamp)

    def __eq__(self, other):
        return self.timestamp == other.timestamp and self.fqts == other.fqts

    def __init__(self, timestamp: int, who: str, hr_sensor: str, hr_value: str,
                 fqts: str, value: str, reason: str):
        self.timestamp = timestamp
        self.who = who
        self.hr_sensor = hr_sensor
        self.hr_value = hr_value
        self.fqts = fqts
        self.value = value
        self.reason = reason

    def to_json(self):
        return {'timestamp': self.timestamp,
                'who': self.who, 'hr_sensor': self.hr_sensor, 'hr_value': self.hr_value,
                'fqts': self.fqts, 'value': self.value, 'reason': self.reason}
