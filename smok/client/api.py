import logging
import json
import typing as tp

import minijson
import requests
from satella.files import read_in_file

from smok.basics import Environment
from smok.exceptions import ResponseError

logger = logging.getLogger(__name__)


class RequestsAPI:
    __slots__ = 'environment', 'base_url', 'cert'

    def __init__(self, device):
        self.environment = device.environment
        self.base_url = device.url

        # Prepare the certificate
        if self.environment == Environment.PRODUCTION:
            self.cert = device.temp_file_for_cert, device.temp_file_for_key
        elif self.environment == Environment.STAGING:
            self.cert = read_in_file(device.cert[0], 'utf-8').replace('\r\n', '\n').replace('\n',
                                                                                            '\t')
        else:
            self.cert = read_in_file('tests/dev.testing.crt', 'utf-8').replace('\r\n',
                                                                               '\n').replace('\n',
                                                                                             '\t')

    def request(self, request_type: str, url: str,
                direct_response: bool = False, **kwargs) -> tp.Union[dict, tp.Tuple[bytes, dict]]:
        """
        :param request_type: type of request, in lowercase
        :param url: URL to contact
        :param direct_response: if True then return a tuple of (
            response as is, headers), else it's JSON
        :param minijson: send provided dictionary as a MiniJSON

        :raises ResponseError: something went wrong
        """
        headers = kwargs.pop('headers', {})
        if 'json' in kwargs:
            kwargs['data'] = minijson.dumps(kwargs.pop('json'))
            headers['Content-Type'] = 'application/minijson'

        op = getattr(requests, request_type)
        try:
            if self.environment == Environment.PRODUCTION:
                resp = op(self.base_url + url, cert=self.cert, headers=headers, **kwargs)
            else:
                headers['X-SSL-Client-Certificate'] = self.cert
                resp = op(self.base_url + url, headers=headers, **kwargs)
        except requests.RequestException as e:
            logger.error('Requests error %s', e)
            raise ResponseError(599, 'Requests error: %s' % (str(e),)) from e

        if resp is None and self.environment == Environment.LOCAL_DEVELOPMENT:
            # special case for CI
            if direct_response:
                return '', 200
            else:
                return {}

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
            except json.decoder.JSONDecodeError as e:
                raise ResponseError(resp.status_code, resp.content) from e

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
