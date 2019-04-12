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

import uuid

from osc_placement.tests.functional import base


class TestAggregate(base.BaseTestCase):
    VERSION = '1.1'

    def test_fail_if_no_rp(self):
        self.assertCommandFailed(
            base.ARGUMENTS_MISSING,
            self.openstack,
            'resource provider aggregate list')

    def test_fail_if_rp_not_found(self):
        self.assertCommandFailed(
            'No resource provider',
            self.resource_provider_aggregate_list,
            'fake-uuid')

    def test_return_empty_list_if_no_aggregates(self):
        rp = self.resource_provider_create()
        self.assertEqual(
            [], self.resource_provider_aggregate_list(rp['uuid']))

    def test_success_set_aggregate(self):
        rp = self.resource_provider_create()
        aggs = {str(uuid.uuid4()) for _ in range(2)}
        rows = self.resource_provider_aggregate_set(
            rp['uuid'], *aggs)

        self.assertEqual(aggs, {r['uuid'] for r in rows})
        rows = self.resource_provider_aggregate_list(rp['uuid'])
        self.assertEqual(aggs, {r['uuid'] for r in rows})
        self.resource_provider_aggregate_set(rp['uuid'])
        rows = self.resource_provider_aggregate_list(rp['uuid'])
        self.assertEqual([], rows)

    def test_set_aggregate_fail_if_no_rp(self):
        self.assertCommandFailed(
            base.ARGUMENTS_MISSING,
            self.openstack,
            'resource provider aggregate set')

    def test_success_set_multiple_aggregates(self):
        # each rp is associated with two aggregates
        rps = [self.resource_provider_create() for _ in range(2)]
        aggs = {str(uuid.uuid4()) for _ in range(2)}
        for rp in rps:
            rows = self.resource_provider_aggregate_set(rp['uuid'], *aggs)
            self.assertEqual(aggs, {r['uuid'] for r in rows})
        # remove association for the first aggregate
        rows = self.resource_provider_aggregate_set(rps[0]['uuid'])
        self.assertEqual([], rows)
        # second rp should be in aggregates
        rows = self.resource_provider_aggregate_list(rps[1]['uuid'])
        self.assertEqual(aggs, {r['uuid'] for r in rows})
        # cleanup
        rows = self.resource_provider_aggregate_set(rps[1]['uuid'])
        self.assertEqual([], rows)

    def test_success_set_large_number_aggregates(self):
        rp = self.resource_provider_create()
        aggs = {str(uuid.uuid4()) for _ in range(100)}
        rows = self.resource_provider_aggregate_set(
            rp['uuid'], *aggs)
        self.assertEqual(aggs, {r['uuid'] for r in rows})
        rows = self.resource_provider_aggregate_set(rp['uuid'])
        self.assertEqual([], rows)

    def test_fail_if_incorrect_aggregate_uuid(self):
        rp = self.resource_provider_create()
        aggs = ['abc', 'efg']
        self.assertCommandFailed(
            "is not a 'uuid'",
            self.resource_provider_aggregate_set,
            rp['uuid'], *aggs)

    # In version 1.1 a generation is not allowed.
    def test_fail_generation_arg_version_handling(self):
        rp = self.resource_provider_create()
        agg = str(uuid.uuid4())
        self.assertCommandFailed(
            "Operation or argument is not supported with version 1.1",
            self.resource_provider_aggregate_set,
            rp['uuid'], agg, generation=5)


class TestAggregate119(TestAggregate):
    VERSION = '1.19'

    def test_success_set_aggregate(self):
        rp = self.resource_provider_create()
        aggs = {str(uuid.uuid4()) for _ in range(2)}
        rows = self.resource_provider_aggregate_set(
            rp['uuid'], *aggs, generation=rp['generation'])

        self.assertEqual(aggs, {r['uuid'] for r in rows})
        rows = self.resource_provider_aggregate_list(rp['uuid'])
        self.assertEqual(aggs, {r['uuid'] for r in rows})
        self.resource_provider_aggregate_set(
            rp['uuid'], *[], generation=rp['generation'] + 1)
        rows = self.resource_provider_aggregate_list(rp['uuid'])
        self.assertEqual([], rows)

    def test_success_set_multiple_aggregates(self):
        # each rp is associated with two aggregates
        rps = [self.resource_provider_create() for _ in range(2)]
        aggs = {str(uuid.uuid4()) for _ in range(2)}
        for rp in rps:
            rows = self.resource_provider_aggregate_set(
                rp['uuid'], *aggs, generation=rp['generation'])
            self.assertEqual(aggs, {r['uuid'] for r in rows})
        # remove association for the first aggregate
        rows = self.resource_provider_aggregate_set(
            rps[0]['uuid'], *[], generation=rp['generation'] + 1)
        self.assertEqual([], rows)
        # second rp should be in aggregates
        rows = self.resource_provider_aggregate_list(rps[1]['uuid'])
        self.assertEqual(aggs, {r['uuid'] for r in rows})
        # cleanup
        rows = self.resource_provider_aggregate_set(
            rps[1]['uuid'], *[], generation=rp['generation'] + 1)
        self.assertEqual([], rows)

    def test_success_set_large_number_aggregates(self):
        rp = self.resource_provider_create()
        aggs = {str(uuid.uuid4()) for _ in range(100)}
        rows = self.resource_provider_aggregate_set(
            rp['uuid'], *aggs, generation=rp['generation'])
        self.assertEqual(aggs, {r['uuid'] for r in rows})
        rows = self.resource_provider_aggregate_set(
            rp['uuid'], *[], generation=rp['generation'] + 1)
        self.assertEqual([], rows)

    def test_fail_incorrect_generation(self):
        rp = self.resource_provider_create()
        agg = str(uuid.uuid4())
        self.assertCommandFailed(
            "Please update the generation and try again.",
            self.resource_provider_aggregate_set,
            rp['uuid'], agg, generation=99999)

    def test_fail_generation_not_int(self):
        rp = self.resource_provider_create()
        agg = str(uuid.uuid4())
        self.assertCommandFailed(
            "invalid int value",
            self.resource_provider_aggregate_set,
            rp['uuid'], agg, generation='barney')

    def test_fail_if_incorrect_aggregate_uuid(self):
        rp = self.resource_provider_create()
        aggs = ['abc', 'efg']
        self.assertCommandFailed(
            "is not a 'uuid'",
            self.resource_provider_aggregate_set,
            rp['uuid'], *aggs, generation=rp['generation'])

    # In version 1.19 a generation is required.
    def test_fail_generation_arg_version_handling(self):
        rp = self.resource_provider_create()
        agg = str(uuid.uuid4())
        self.assertCommandFailed(
            "A generation must be specified.",
            self.resource_provider_aggregate_set,
            rp['uuid'], agg)
