import os
import pickle

from satella.coding import silence_excs
from satella.files import read_in_file, write_to_file

from .base import BaseBAOBDatabase


class PicklingBAOBDatabase(BaseBAOBDatabase):
    """
    :param path: path that has to be a directory where BAOB data will be stored.
        If that directory does not exist, it will be created
    """

    def get_baob_value(self, key: str) -> bytes:
        return read_in_file(os.path.join(self.__path, key))

    def set_baob_value(self, key: str, data: bytes, version: int):
        write_to_file(os.path.join(self.__path, key), data)
        self.versions[key] = version
        self.sync()

    def sync(self):
        with open(os.path.join(self.__path, 'metadata.pkl'), 'wb') as f_out:
            pickle.dump(self.versions, f_out, pickle.HIGHEST_PROTOCOL)

    @silence_excs(KeyError)
    def delete_baob(self, key: str) -> None:
        del self.versions[key]
        os.unlink(os.path.join(self.__path, key))
        self.sync()

    def get_baob_version(self, key: str) -> int:
        return self.versions[key]

    def __init__(self, path: str):
        self.__path = path
        if not os.path.exists(path):
            os.mkdir(path)
        try:
            with open(os.path.join(path, 'metadata.pkl', 'rb')) as f_in:
                self.versions = pickle.load(f_in)
        except (FileNotFoundError, pickle.UnpicklingError):
            self.versions = {}

    def get_all_keys(self):
        set_f = set(os.listdir(self.__path))
        with silence_excs(KeyError):
            set_f.remove('metadata.pkl')
        return iter(set_f)
