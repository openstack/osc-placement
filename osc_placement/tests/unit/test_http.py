# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import mock

import six

import keystoneauth1.exceptions.http as ks_exceptions
import osc_lib.exceptions as exceptions
import oslotest.base as base
import requests
import simplejson as json

from osc_placement import http
from osc_placement import version

from oslo_serialization import jsonutils


class FakeResponse(requests.Response):
    def __init__(self, status_code, content=None, headers=None):
        super(FakeResponse, self).__init__()
        self.status_code = status_code
        if content:
            self._content = content
        if headers:
            self.headers = headers


class TestSessionClient(base.BaseTestCase):
    def test_wrap_http_exceptions(self):
        def go():
            with http._wrap_http_exceptions():
                error = {
                    "errors": [
                        {"status": 404,
                         "detail": ("The resource could not be found.\n\n"
                                    "No resource provider with uuid 123 "
                                    "found for delete")}
                    ]
                }
                response = mock.Mock(content=json.dumps(error))
                raise ks_exceptions.NotFound(response=response)

        exc = self.assertRaises(exceptions.NotFound, go)
        self.assertEqual(404, exc.http_status)
        self.assertIn('No resource provider with uuid 123 found',
                      six.text_type(exc))

    def test_unexpected_response(self):
        def go():
            with http._wrap_http_exceptions():
                raise ks_exceptions.InternalServerError()

        exc = self.assertRaises(ks_exceptions.InternalServerError, go)
        self.assertEqual(500, exc.http_status)
        self.assertIn('Internal Server Error (HTTP 500)', six.text_type(exc))

    def test_session_client_version(self):
        session = mock.Mock()
        ks_filter = {'service_type': 'placement',
                     'region_name': 'mock_region',
                     'interface': 'mock_interface'}

        # 1. target to a specific version
        target_version = '1.23'
        client = http.SessionClient(
            session, ks_filter, api_version=target_version)
        self.assertEqual(client.api_version, target_version)

        # validate that the server side is not called
        session.request.assert_not_called()

        # 2. negotiation succeeds and have the client's highest version
        target_version = '1'
        session.request.return_value = FakeResponse(200)
        client = http.SessionClient(
            session, ks_filter, api_version=target_version)
        self.assertEqual(client.api_version, version.MAX_VERSION_NO_GAP)

        # validate that the server side is called
        expected_version = 'placement ' + version.MAX_VERSION_NO_GAP
        expected_headers = {'OpenStack-API-Version': expected_version,
                            'Accept': 'application/json'}
        session.request.assert_called_once_with(
            '/', 'GET', endpoint_filter=ks_filter,
            headers=expected_headers, raise_exc=False)
        session.reset_mock()

        # 3. negotiation fails and get the servers's highest version
        mock_server_version = '1.10'
        json_mock = {
            "errors": [{"status": 406,
                        "title": "Not Acceptable",
                        "min_version": "1.0",
                        "max_version": mock_server_version}]
        }
        session.request.return_value = FakeResponse(
            406, content=jsonutils.dump_as_bytes(json_mock))

        client = http.SessionClient(
            session, ks_filter, api_version=target_version)
        self.assertEqual(client.api_version, mock_server_version)

        # validate that the server side is called
        session.request.assert_called_once_with(
            '/', 'GET', endpoint_filter=ks_filter,
            headers=expected_headers, raise_exc=False)
