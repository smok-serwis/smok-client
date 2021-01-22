import socket
import typing as tp
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

    def request(self, request_type: str, url: str,
                direct_response: bool = False, **kwargs) -> tp.Union[dict, tp.Tuple[bytes, dict]]:
        """
        :param request_type: type of request, in lowercase
        :param url: URL to contact
        :param direct_response: if True then return a tuple of (
            response as is, headers), else it's JSON

        :raises ResponseError: something went wrong
        """
        op = getattr(requests, request_type)
        try:
            if self.environment == Environment.STAGING:
                    resp = op(self.base_url + url, headers={
                        'X-SSL-Client-Certificate': self.cert
                    }, **kwargs)
            else:
                resp = op(self.base_url + url, cert=self.cert, **kwargs)
        except requests.RequestException as e:
            raise ResponseError(None, 'Requests error: %s' % (str(e), ))

        if resp.status_code not in (200, 201):
            if direct_response:
                return resp.content, resp.headers
            try:
                error_json = resp.json()['status']
            except (json.decoder.JSONDecodeError, ValueError):
                try:
                    error_json = resp.text
                except AttributeError:
                    error_json = repr(resp.content)
            raise ResponseError(resp.status_code, error_json)
        if direct_response:
            return resp.content, resp.headers
        else:
            try:
                return resp.json()
            except json.decoder.JSONDecodeError:
                raise ResponseError(resp.status_code, resp.content)

    def get(self, url: str, **kwargs):
        return self.request('get', url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request('post', url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request('put', url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request('patch', url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request('delete', url, **kwargs)
