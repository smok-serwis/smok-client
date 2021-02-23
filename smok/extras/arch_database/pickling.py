import pickle

from .base import BaseArchivesDatabase


class PicklingArchivesDatabase(BaseArchivesDatabase):
    """
    An archiving database basing off pickling things on disk

    :param path: path to the pickle. If does not exist, will be created
    """

    def on_archiving_data_sync(self, new_data) -> None:
        self.__data = new_data
        with open(self.__path, 'wb') as f_out:
            pickle.dump(self.__data, f_out, pickle.HIGHEST_PROTOCOL)

    def get_archiving_instructions(self) -> dict:
        return self.__data

    def __init__(self, path: str):
        self.__path = path
        try:
            with open(self.__path, 'rb') as f_in:
                self.__data = pickle.load(f_in)
        except (FileNotFoundError, pickle.UnpicklingError):
            self.__data = {}
