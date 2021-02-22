from smok.extras import BaseArchivesDatabase


class InMemoryArchivesDatabase(BaseArchivesDatabase):
    def on_archiving_data_sync(self, new_data: dict) -> None:
        self.data = new_data

    def get_archiving_instructions(self) -> dict:
        return self.data

    def __init__(self):
        self.data = {}
