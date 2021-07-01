from smok.exceptions import UnavailableError


class BAOB:
    """
    A Binary All-sized OBject.

    Note that a BAOB will not signal that it does not exist upon construction, it will rather do so
    when queried about version or value.

    To create a new BAOB, just get a BAOB from device with given name and assign any value to it.
    """

    __slots__ = 'device', 'key'

    def __init__(self, device: 'SMOKDevice', key: str):
        self.device = device
        self.key = key

    @property
    def version(self) -> int:
        """
        :return: version of this BAOB or -1 if does not exist.
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

        :raises KeyError: this BAOB does not exist
        """
        return self.device.baob_database.get_baob_value(self.key)

    @value.setter
    def value(self, new_data: bytes) -> None:
        """
        :raises UnavailableError: client was launched in a mode with BAOBs disabled
        """
        if self.device.dont_do_baobs:
            raise UnavailableError('Client was launched as not supporting BAOBs!')
        self.device.baob_database.set_baob_value(self.key, new_data, self.version + 1)
        self.device.getter.last_baob_synced = 1
        self.device.getter.data_to_update.notify()
