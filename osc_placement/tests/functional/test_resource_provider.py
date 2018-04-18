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

import operator
import subprocess
import uuid

import six

from osc_placement.tests.functional import base


class TestResourceProvider(base.BaseTestCase):
    def test_resource_provider_create(self):
        created = self.resource_provider_create('test_rp_creation')
        self.assertEqual('test_rp_creation', created['name'])

        retrieved = self.resource_provider_show(created['uuid'])
        self.assertEqual(created, retrieved)

    def test_resource_provider_delete(self):
        created = self.resource_provider_create()

        before_delete = self.resource_provider_list(uuid=created['uuid'])
        self.assertEqual([created['uuid']],
                         [rp['uuid'] for rp in before_delete])

        self.resource_provider_delete(created['uuid'])
        after_delete = self.resource_provider_list(uuid=created['uuid'])
        self.assertEqual([], after_delete)

    def test_resource_provider_delete_not_found(self):
        rp_uuid = six.text_type(uuid.uuid4())
        msg = 'No resource provider with uuid ' + rp_uuid + ' found'

        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_provider_delete, rp_uuid)
        self.assertIn(msg, exc.output.decode('utf-8'))

    def test_resource_provider_set(self):
        created = self.resource_provider_create(name='test_rp_orig_name')

        before_update = self.resource_provider_show(created['uuid'])
        self.assertEqual('test_rp_orig_name', before_update['name'])
        self.assertEqual(0, before_update['generation'])

        self.resource_provider_set(created['uuid'], name='test_rp_new_name')
        after_update = self.resource_provider_show(created['uuid'])
        self.assertEqual('test_rp_new_name', after_update['name'])
        self.assertEqual(0, after_update['generation'])

    def test_resource_provider_set_not_found(self):
        rp_uuid = six.text_type(uuid.uuid4())
        msg = 'No resource provider with uuid ' + rp_uuid + ' found'

        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_provider_set, rp_uuid, 'test')
        self.assertIn(msg, exc.output.decode('utf-8'))

    def test_resource_provider_show(self):
        created = self.resource_provider_create()

        retrieved = self.resource_provider_show(created['uuid'])
        self.assertEqual(created, retrieved)

    def test_resource_provider_show_allocations(self):
        consumer_uuid = str(uuid.uuid4())
        allocs = {consumer_uuid: {'resources': {'VCPU': 2}}}

        created = self.resource_provider_create()
        self.resource_inventory_set(created['uuid'],
                                    'VCPU=4', 'VCPU:max_unit=4')
        self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(created['uuid'])])

        expected = dict(created, allocations=allocs, generation=2)
        retrieved = self.resource_provider_show(created['uuid'],
                                                allocations=True)
        self.assertEqual(expected, retrieved)

    def test_resource_provider_show_allocations_empty(self):
        created = self.resource_provider_create()

        expected = dict(created, allocations={})
        retrieved = self.resource_provider_show(created['uuid'],
                                                allocations=True)
        self.assertEqual(expected, retrieved)

    def test_resource_provider_show_not_found(self):
        rp_uuid = six.text_type(uuid.uuid4())
        msg = 'No resource provider with uuid ' + rp_uuid + ' found'

        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_provider_show, rp_uuid)
        self.assertIn(msg, exc.output.decode('utf-8'))

    def test_resource_provider_list(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()

        expected_full = sorted([rp1, rp2], key=operator.itemgetter('uuid'))
        self.assertEqual(
            expected_full,
            sorted([rp for rp in self.resource_provider_list()
                    if rp['name'] in (rp1['name'], rp2['name'])],
                   key=operator.itemgetter('uuid'))
        )

    def test_resource_provider_list_by_name(self):
        rp1 = self.resource_provider_create()
        self.resource_provider_create()

        expected_filtered_by_name = [rp1]
        self.assertEqual(
            expected_filtered_by_name,
            [rp for rp in self.resource_provider_list(name=rp1['name'])]
        )

    def test_resource_provider_list_by_uuid(self):
        rp1 = self.resource_provider_create()
        self.resource_provider_create()

        expected_filtered_by_uuid = [rp1]
        self.assertEqual(
            expected_filtered_by_uuid,
            [rp for rp in self.resource_provider_list(uuid=rp1['uuid'])]
        )

    def test_resource_provider_list_empty(self):
        by_name = self.resource_provider_list(name='some_non_existing_name')
        self.assertEqual([], by_name)

        by_uuid = self.resource_provider_list(uuid=str(uuid.uuid4()))
        self.assertEqual([], by_uuid)

    def test_fail_if_incorrect_options(self):
        # aggregate_uuids param is available starting 1.3
        self.assertCommandFailed(
            'Operation or argument is not supported',
            self.resource_provider_list, aggregate_uuids=['1'])
        # resource param is available starting 1.4
        self.assertCommandFailed('Operation or argument is not supported',
                                 self.resource_provider_list, resources=['1'])


class TestResourceProvider14(base.BaseTestCase):
    VERSION = '1.4'

    def test_fail_if_incorrect_aggregate_uuid(self):
        # aggregate_uuid requires the uuid like format
        self.assertCommandFailed(
            'Invalid uuid value', self.resource_provider_list,
            aggregate_uuids=['fake_uuid'])

    def test_return_empty_list_for_nonexistent_aggregate(self):
        self.resource_provider_create()
        agg = str(uuid.uuid4())
        self.assertEqual([], self.resource_provider_list(
            aggregate_uuids=[agg]))

    def test_return_properly_for_aggregate_uuid_request(self):
        self.resource_provider_create()
        rp2 = self.resource_provider_create()
        agg = str(uuid.uuid4())
        self.resource_provider_aggregate_set(rp2['uuid'], agg)
        rps = self.resource_provider_list(
            aggregate_uuids=[agg, str(uuid.uuid4())])
        self.assertEqual(1, len(rps))
        self.assertEqual(rp2['uuid'], rps[0]['uuid'])

    def test_return_empty_list_if_no_resource(self):
        rp = self.resource_provider_create()
        self.assertEqual([], self.resource_provider_list(
            resources=['MEMORY_MB=256'], uuid=rp['uuid']))

    def test_return_properly_for_resource_request(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(rp1['uuid'], 'PCI_DEVICE=8')
        self.resource_inventory_set(rp2['uuid'], 'PCI_DEVICE=16')
        rps = self.resource_provider_list(resources=['PCI_DEVICE=16'])
        self.assertEqual(1, len(rps))
        self.assertEqual(rp2['uuid'], rps[0]['uuid'])
