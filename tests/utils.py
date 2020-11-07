import typing as tp


class FakeResponse:
    def __init__(self, response):
        self.response = response

    def json(self):
        return self.response


class FakeCall:
    def __init__(self, url_to_response: tp.Dict[str, dict]):
        self.url_to_response = url_to_response

    def __call__(self, url, *args, **kwargs):
        for url_to_check in self.url_to_response:
            if url.endswith(url_to_check):
                return FakeResponse(self.url_to_response[url_to_check])

