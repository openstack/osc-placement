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

import contextlib
import logging

import keystoneauth1.exceptions.http as ks_exceptions
import osc_lib.exceptions as exceptions
import simplejson as json
import six

from osc_placement import version


_http_error_to_exc = {
    cls.http_status: cls
    for cls in exceptions.ClientException.__subclasses__()
}


LOG = logging.getLogger(__name__)


@contextlib.contextmanager
def _wrap_http_exceptions():
    """Reraise osc-lib exceptions with detailed messages."""

    try:
        yield
    except ks_exceptions.HttpError as exc:
        if 400 <= exc.http_status < 500:
            detail = json.loads(exc.response.content)['errors'][0]['detail']
            msg = detail.split('\n')[-1].strip()
            exc_class = _http_error_to_exc.get(exc.http_status,
                                               exceptions.CommandError)
            six.raise_from(exc_class(exc.http_status, msg), exc)
        else:
            raise


class SessionClient(object):
    def __init__(self, session, ks_filter, api_version='1.0'):
        self.session = session
        self.ks_filter = ks_filter
        self.negotiate_api_version(api_version)

    def request(self, method, url, **kwargs):
        version = kwargs.pop('version', None)
        api_version = (self.ks_filter['service_type'] + ' '
                       + (version or self.api_version))
        headers = kwargs.pop('headers', {})
        headers.setdefault('OpenStack-API-Version', api_version)
        headers.setdefault('Accept', 'application/json')

        with _wrap_http_exceptions():
            return self.session.request(url, method,
                                        headers=headers,
                                        endpoint_filter=self.ks_filter,
                                        **kwargs)

    def negotiate_api_version(self, api_version):
        """Set api_version to self.

        If negotiate version (only majorversion) is given, talk to server to
        pick up max microversion supported both by client and by server.
        """
        if api_version not in version.NEGOTIATE_VERSIONS:
            self.api_version = api_version
            return
        client_ver = version.MAX_VERSION_NO_GAP
        self.api_version = client_ver
        resp = self.request('GET', '/', raise_exc=False)
        if resp.status_code == 406:
            server_ver = resp.json()['errors'][0]['max_version']
            self.api_version = server_ver
            LOG.debug('Microversion %s not supported in server. '
                      'Falling back to microversion %s',
                      client_ver, server_ver)
