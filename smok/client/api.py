import json

import requests
from satella.files import read_in_file

from smok.basics import Environment
from smok.exceptions import ResponseError


class RequestsAPI:
    __slots__ = ('environment', 'base_url', 'cert')

    def __init__(self, device):
        self.environment = device.environment
        self.base_url = device.url
        if self.environment == Environment.STAGING:
            self.cert = read_in_file(device.cert[0], 'utf-8').replace('\n', '\t')
        else:
            self.cert = device.cert

    def request(self, request_type, url, **kwargs):
        op = getattr(requests, request_type)
        if self.environment == Environment.STAGING:
            resp = op(self.base_url + url, headers={
                'X-SSL-Client-Certificate': self.cert
            }, **kwargs)
        else:
            resp = op(self.base_url + url, cert=self.cert, **kwargs)
        if resp.status_code not in (200, 201):
            try:
                error_json = resp.json()['status']
            except (json.decoder.JSONDecodeError, ValueError):
                try:
                    error_json = resp.text
                except AttributeError:
                    error_json = repr(resp.content)
            raise ResponseError(resp.status_code, error_json)
        try:
            return resp.json()
        except json.decoder.JSONDecodeError:
            raise ResponseError(resp.status_code, resp.content)

    def get(self, url):
        return self.request('get', url)

    def post(self, url, **kwargs):
        return self.request('post', url, **kwargs)

    def put(self, url, **kwargs):
        return self.request('put', url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request('patch', url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request('delete', url, **kwargs)
