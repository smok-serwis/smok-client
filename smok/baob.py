class BAOB:
    """
    A Binary All-sized OBject.
    """

    __slots__ = ('device', 'key')

    def __init__(self, device: 'SMOKDevice', key: str):
        self.device = device
        self.key = key

    @property
    def version(self) -> int:
        """
        :return: version of this BAOB
        """
        try:
            return self.device.baob_database.get_baob_version(self.key)
        except KeyError:
            return -1

    @property
    def value(self) -> bytes:
        """
        This property is both gettable and settable.

        :return: value of this BAOB
        """
        return self.device.baob_database.get_baob_value(self.key)

    @value.setter
    def value(self, new_data: bytes) -> None:
        self.device.baob_database.set_baob_value(self.key, new_data, self.version+1)
        self.device.getter.last_baob_synced = 0
        self.device.getter.data_to_update.notify()


