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

import json
import random
import string
import subprocess

from oslotest import base


RP_PREFIX = 'osc-placement-functional-tests-'


class BaseTestCase(base.BaseTestCase):
    @staticmethod
    def openstack(cmd, may_fail=False, use_json=False):
        try:
            to_exec = ['openstack'] + cmd.split()
            if use_json:
                to_exec += ['-f', 'json']

            output = subprocess.check_output(to_exec, stderr=subprocess.STDOUT)
            result = (output or b'').decode('utf-8')
        except subprocess.CalledProcessError:
            if not may_fail:
                raise

        if use_json:
            return json.loads(result)
        else:
            return result

    def resource_provider_create(self, name=''):
        if not name:
            random_part = ''.join(random.choice(string.ascii_letters)
                                  for i in range(10))
            name = RP_PREFIX + random_part

        res = self.openstack('resource provider create ' + name,
                             use_json=True)

        def cleanup():
            try:
                self.resource_provider_delete(res['uuid'])
            except subprocess.CalledProcessError as exc:
                # may have already been deleted by a test case
                err_message = exc.output.decode('utf-8').lower()
                if 'no resource provider' not in err_message:
                    raise
        self.addCleanup(cleanup)

        return res

    def resource_provider_set(self, uuid, name):
        to_exec = 'resource provider set ' + uuid + ' --name ' + name
        return self.openstack(to_exec, use_json=True)

    def resource_provider_show(self, uuid):
        return self.openstack('resource provider show ' + uuid, use_json=True)

    def resource_provider_list(self, uuid=None, name=None):
        to_exec = 'resource provider list'
        if uuid:
            to_exec += ' --uuid ' + uuid
        if name:
            to_exec += ' --name ' + name

        return self.openstack(to_exec, use_json=True)

    def resource_provider_delete(self, uuid):
        return self.openstack('resource provider delete ' + uuid)
