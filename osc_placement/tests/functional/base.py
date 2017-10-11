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
    VERSION = None

    @classmethod
    def openstack(cls, cmd, may_fail=False, use_json=False):
        result = None
        try:
            to_exec = ['openstack'] + cmd.split()
            if use_json:
                to_exec += ['-f', 'json']
            if cls.VERSION is not None:
                to_exec += ['--os-placement-api-version', cls.VERSION]

            output = subprocess.check_output(to_exec, stderr=subprocess.STDOUT)
            result = (output or b'').decode('utf-8')
        except subprocess.CalledProcessError as e:
            msg = 'Command: "%s"\noutput: %s' % (' '.join(e.cmd), e.output)
            e.cmd = msg
            if not may_fail:
                raise

        if use_json and result:
            return json.loads(result)
        else:
            return result

    def assertCommandFailed(self, message, func, *args, **kwargs):
        signature = [func]
        signature.extend(args)
        try:
            func(*args, **kwargs)
            self.fail('Command does not fail as required (%s)' % signature)

        except subprocess.CalledProcessError as e:
            self.assertIn(
                message, e.output,
                'Command "%s" fails with different message' % e.cmd)

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

    def resource_provider_show(self, uuid, allocations=False):
        cmd = 'resource provider show ' + uuid
        if allocations:
            cmd = cmd + ' --allocations'

        return self.openstack(cmd, use_json=True)

    def resource_provider_list(self, uuid=None, name=None,
                               aggregate_uuids=None, resources=None):
        to_exec = 'resource provider list'
        if uuid:
            to_exec += ' --uuid ' + uuid
        if name:
            to_exec += ' --name ' + name
        if aggregate_uuids:
            to_exec += ' ' + ' '.join(
                '--aggregate-uuid %s' % a for a in aggregate_uuids)
        if resources:
            to_exec += ' ' + ' '.join('--resource %s' % r for r in resources)

        return self.openstack(to_exec, use_json=True)

    def resource_provider_delete(self, uuid):
        return self.openstack('resource provider delete ' + uuid)

    def resource_allocation_show(self, consumer_uuid):
        return self.openstack(
            'resource provider allocation show ' + consumer_uuid,
            use_json=True
        )

    def resource_allocation_set(self, consumer_uuid, allocations):
        cmd = 'resource provider allocation set {allocs} {uuid}'.format(
            uuid=consumer_uuid,
            allocs=' '.join('--allocation {}'.format(a) for a in allocations)
        )
        result = self.openstack(cmd, use_json=True)

        def cleanup(uuid):
            try:
                self.openstack('resource provider allocation delete ' + uuid)
            except subprocess.CalledProcessError as exc:
                # may have already been deleted by a test case
                if 'not found' in exc.output.decode('utf-8').lower():
                    pass
        self.addCleanup(cleanup, consumer_uuid)

        return result

    def resource_allocation_delete(self, consumer_uuid):
        cmd = 'resource provider allocation delete ' + consumer_uuid
        return self.openstack(cmd)

    def resource_inventory_show(self, uuid, resource_class):
        cmd = 'resource provider inventory show {uuid} {rc}'.format(
            uuid=uuid, rc=resource_class
        )
        return self.openstack(cmd, use_json=True)

    def resource_inventory_list(self, uuid):
        return self.openstack('resource provider inventory list ' + uuid,
                              use_json=True)

    def resource_inventory_delete(self, uuid, resource_class):
        cmd = 'resource provider inventory delete {uuid} {rc}'.format(
            uuid=uuid, rc=resource_class
        )
        self.openstack(cmd)

    def resource_inventory_set(self, uuid, *resources):
        cmd = 'resource provider inventory set {uuid} {resources}'.format(
            uuid=uuid, resources=' '.join(
                ['--resource %s' % r for r in resources]))
        return self.openstack(cmd, use_json=True)

    def resource_inventory_class_set(self, uuid, resource_class, **kwargs):
        opts = ['--%s=%s' % (k, v) for k, v in kwargs.items()]
        cmd = 'resource provider inventory class set {uuid} {rc} {opts}'.\
            format(uuid=uuid, rc=resource_class, opts=' '.join(opts))
        return self.openstack(cmd, use_json=True)

    def resource_provider_show_usage(self, uuid):
        return self.openstack('resource provider usage show ' + uuid,
                              use_json=True)

    def resource_provider_aggregate_list(self, uuid):
        return self.openstack('resource provider aggregate list ' + uuid,
                              use_json=True)

    def resource_provider_aggregate_set(self, uuid, *aggregates):
        cmd = 'resource provider aggregate set %s ' % uuid
        cmd += ' '.join('--aggregate %s' % aggregate
                        for aggregate in aggregates)
        return self.openstack(cmd, use_json=True)

    def resource_class_list(self):
        return self.openstack('resource class list', use_json=True)

    def resource_class_show(self, name):
        return self.openstack('resource class show ' + name, use_json=True)

    def resource_class_create(self, name):
        return self.openstack('resource class create ' + name)

    def resource_class_delete(self, name):
        return self.openstack('resource class delete ' + name)
