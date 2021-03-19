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


def sorted_resources(resource):
    return ','.join(sorted(resource.split(',')))


class TestAllocationCandidate(base.BaseTestCase):
    VERSION = '1.10'

    def test_list_no_resource_specified_error(self):
        self.assertCommandFailed(
            'At least one --resource must be specified',
            self.openstack, 'allocation candidate list')

    def test_list_non_key_value_resource_specified_error(self):
        self.assertCommandFailed(
            'Arguments to --resource must be of form '
            '<resource_class>=<value>',
            self.openstack, 'allocation candidate list --resource VCPU')

    def test_list_empty(self):
        self.assertEqual([], self.allocation_candidate_list(
            resources=['MEMORY_MB=999999999']))

    def test_list_one(self):
        rp = self.resource_provider_create()
        self.resource_inventory_set(rp['uuid'], 'MEMORY_MB=1024')
        candidates = self.allocation_candidate_list(
            resources=('MEMORY_MB=256',))
        self.assertIn(
            rp['uuid'],
            [candidate['resource provider'] for candidate in candidates])

    def assertResourceEqual(self, r1, r2):
        self.assertEqual(sorted_resources(r1), sorted_resources(r2))

    def test_list_multiple(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_inventory_set(
            rp2['uuid'], 'MEMORY_MB=16384', 'DISK_GB=1024')
        candidates = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'))
        rps = {c['resource provider']: c for c in candidates}
        self.assertResourceEqual(
            'MEMORY_MB=1024,DISK_GB=80', rps[rp1['uuid']]['allocation'])
        self.assertResourceEqual(
            'MEMORY_MB=1024,DISK_GB=80', rps[rp2['uuid']]['allocation'])
        self.assertResourceEqual(
            'MEMORY_MB=0/8192,DISK_GB=0/512',
            rps[rp1['uuid']]['inventory used/capacity'])
        self.assertResourceEqual(
            'MEMORY_MB=0/16384,DISK_GB=0/1024',
            rps[rp2['uuid']]['inventory used/capacity'])

    def test_list_shared(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(rp1['uuid'], 'MEMORY_MB=8192')
        self.resource_inventory_set(rp2['uuid'], 'DISK_GB=1024')
        agg = str(uuid.uuid4())
        self.resource_provider_aggregate_set(rp1['uuid'], agg)
        self.resource_provider_aggregate_set(rp2['uuid'], agg)
        self.resource_provider_trait_set(
            rp2['uuid'], 'MISC_SHARES_VIA_AGGREGATE')
        candidates = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'))
        rps = {c['resource provider']: c for c in candidates}
        self.assertResourceEqual(
            'MEMORY_MB=1024', rps[rp1['uuid']]['allocation'])
        self.assertResourceEqual(
            'DISK_GB=80', rps[rp2['uuid']]['allocation'])
        self.assertResourceEqual(
            'MEMORY_MB=0/8192', rps[rp1['uuid']]['inventory used/capacity'])
        self.assertResourceEqual(
            'DISK_GB=0/1024', rps[rp2['uuid']]['inventory used/capacity'])
        self.assertEqual(
            rps[rp2['uuid']]['#'], rps[rp1['uuid']]['#'])

    def test_fail_if_unknown_rc(self):
        self.assertCommandFailed(
            'No such resource',
            self.allocation_candidate_list,
            resources=('UNKNOWN=10',))


class TestAllocationCandidate112(TestAllocationCandidate):
    VERSION = '1.12'


class TestAllocationCandidate116(base.BaseTestCase):
    VERSION = '1.16'

    def test_list_limit(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_inventory_set(
            rp2['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')

        unlimited = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'))
        self.assertTrue(len(set([row['#'] for row in unlimited])) > 1)

        limited = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'),
            limit=1)
        self.assertEqual(len(set([row['#'] for row in limited])), 1)


class TestAllocationCandidate117(base.BaseTestCase):
    VERSION = '1.17'

    # NOTE(cdent): The choice of traits here is important. We need to
    # make sure that we do not overlap with 'test_show_required_trait'
    # in TestResourceProvider118 which also creates some resource
    # providers. In a multi-process enviromment, the tests can race.
    def test_show_required_trait(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_inventory_set(
            rp2['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_provider_trait_set(
            rp1['uuid'], 'STORAGE_DISK_SSD', 'HW_NIC_SRIOV')
        self.resource_provider_trait_set(
            rp2['uuid'], 'STORAGE_DISK_HDD', 'HW_NIC_SRIOV')

        rps = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'),
            required=('STORAGE_DISK_SSD',))

        candidate_dict = {rp['resource provider']: rp for rp in rps}
        self.assertIn(rp1['uuid'], candidate_dict)
        self.assertNotIn(rp2['uuid'], candidate_dict)
        self.assertEqual(
            set(candidate_dict[rp1['uuid']]['traits'].split(',')),
            set(['STORAGE_DISK_SSD', 'HW_NIC_SRIOV']))

    # Prior to version 1.21 use the --aggregate-uuid arg should
    # be an errror.
    def test_fail_if_aggregate_uuid_wrong_version(self):
        self.assertCommandFailed(
            'Operation or argument is not supported with version 1.17',
            self.allocation_candidate_list,
            resources=('MEMORY_MB=1024', 'DISK_GB=80'),
            aggregate_uuids=[str(uuid.uuid4())])
        # ...so as --member_of option
        self.assertCommandFailed(
            'Operation or argument is not supported with version 1.17',
            self.allocation_candidate_list,
            resources=('MEMORY_MB=1024', 'DISK_GB=80'),
            member_of=[str(uuid.uuid4())])


class TestAllocationCandidate121(base.BaseTestCase):
    VERSION = '1.21'

    def test_return_properly_for_aggregate_uuid_request(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_inventory_set(
            rp2['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        agg = str(uuid.uuid4())

        self.resource_provider_aggregate_set(
            rp2['uuid'], agg, generation=1)

        # use --aggregate_uuids option
        rps, warning = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024',),
            aggregate_uuids=[agg, str(uuid.uuid4())],
            may_print_to_stderr=True)

        candidate_dict = {rp['resource provider']: rp for rp in rps}
        self.assertEqual(1, len(candidate_dict))
        self.assertIn(rp2['uuid'], candidate_dict)
        self.assertNotIn(rp1['uuid'], candidate_dict)
        self.assertIn('The --aggregate-uuid option is deprecated, '
                      'please use --member-of instead.', warning)

        # validate --member_of option works as expected
        rps = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024',),
            member_of=[agg])

        candidate_dict = {rp['resource provider']: rp for rp in rps}
        self.assertEqual(1, len(candidate_dict))
        self.assertIn(rp2['uuid'], candidate_dict)
        self.assertNotIn(rp1['uuid'], candidate_dict)

    # Specifying forbidden traits weren't available until version 1.22
    def test_fail_if_forbidden_trait_wrong_version(self):
        self.assertCommandFailed(
            'Operation or argument is not supported with version 1.21',
            self.allocation_candidate_list,
            resources=('MEMORY_MB=1024', 'DISK_GB=80'),
            forbidden=('STORAGE_DISK_HDD',))


class TestAllocationCandidate122(base.BaseTestCase):
    VERSION = '1.22'

    def test_hide_forbidden_trait(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        rp3 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'], 'MEMORY_MB=1024', 'DISK_GB=256')
        self.resource_inventory_set(
            rp2['uuid'], 'MEMORY_MB=1024', 'DISK_GB=256')
        self.resource_inventory_set(
            rp3['uuid'], 'MEMORY_MB=1024', 'DISK_GB=256')
        self.resource_provider_trait_set(
            rp1['uuid'], 'STORAGE_DISK_SSD', 'HW_CPU_X86_BMI')
        self.resource_provider_trait_set(
            rp2['uuid'], 'STORAGE_DISK_HDD', 'HW_CPU_X86_BMI')
        self.resource_provider_trait_set(
            rp3['uuid'], 'STORAGE_DISK_HDD', 'HW_CPU_X86_BMI')

        rps = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'),
            required=('HW_CPU_X86_BMI',),
            forbidden=('STORAGE_DISK_HDD',))

        self.assertEqual(1, len(rps))
        self.assertEqual(rp1['uuid'], rps[0]['resource provider'])

        rps = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'),
            required=('HW_CPU_X86_BMI',),
            forbidden=('STORAGE_DISK_SSD',))

        uuids = [rp['resource provider'] for rp in rps]

        self.assertEqual(2, len(uuids))
        self.assertNotIn(rp1['uuid'], uuids)
        self.assertIn(rp2['uuid'], uuids)
        self.assertIn(rp3['uuid'], uuids)


class TestAllocationCandidate124(base.BaseTestCase):
    VERSION = '1.24'

    def test_member_of(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_inventory_set(
            rp2['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        agg1 = str(uuid.uuid4())
        agg2 = str(uuid.uuid4())
        agg3 = str(uuid.uuid4())

        self.resource_provider_aggregate_set(
            rp1['uuid'], agg1, agg3, generation=1)
        self.resource_provider_aggregate_set(
            rp2['uuid'], agg2, agg3, generation=1)

        agg1and3 = [agg1, agg3]
        agg1or3 = [agg1 + ',' + agg3]
        agg1or3_and_agg2 = [agg1 + ',' + agg3, agg2]

        rps = self.allocation_candidate_list(resources=('MEMORY_MB=1024',),
                                             member_of=agg1and3)
        candidate_dict = {rp['resource provider']: rp for rp in rps}
        self.assertEqual(1, len(candidate_dict))
        self.assertIn(rp1['uuid'], candidate_dict)

        rps = self.allocation_candidate_list(resources=('MEMORY_MB=1024',),
                                             member_of=agg1or3)
        candidate_dict = {rp['resource provider']: rp for rp in rps}
        self.assertEqual(2, len(candidate_dict))
        self.assertIn(rp1['uuid'], candidate_dict)
        self.assertIn(rp2['uuid'], candidate_dict)

        rps = self.allocation_candidate_list(resources=('MEMORY_MB=1024',),
                                             member_of=agg1or3_and_agg2)
        candidate_dict = {rp['resource provider']: rp for rp in rps}
        self.assertEqual(1, len(candidate_dict))
        self.assertIn(rp2['uuid'], candidate_dict)

    def test_fail_granular_wrong_version(self):
        groups = {'1': {'resources': ('VCPU=3',)}}
        self.assertCommandFailed(
            'Operation or argument is not supported with version 1.24',
            self.allocation_candidate_granular, groups=groups)


class TestAllocationCandidate129(base.BaseTestCase):
    VERSION = '1.29'

    def setUp(self):
        super(TestAllocationCandidate129, self).setUp()

        self.rp1 = self.resource_provider_create()
        self.rp1_1 = self.resource_provider_create(
            parent_provider_uuid=self.rp1['uuid'])
        self.rp1_2 = self.resource_provider_create(
            parent_provider_uuid=self.rp1['uuid'])

        self.agg1 = str(uuid.uuid4())
        self.agg2 = str(uuid.uuid4())
        self.resource_provider_aggregate_set(
            self.rp1_1['uuid'], self.agg1, generation=0)
        self.resource_provider_aggregate_set(
            self.rp1_2['uuid'], self.agg2, generation=0)

        self.resource_inventory_set(self.rp1['uuid'], 'DISK_GB=512')
        self.resource_inventory_set(
            self.rp1_1['uuid'], 'VCPU=8', 'MEMORY_MB=8192')
        self.resource_inventory_set(
            self.rp1_2['uuid'], 'VCPU=16', 'MEMORY_MB=8192')

        self.resource_provider_trait_set(self.rp1_1['uuid'], 'HW_CPU_X86_AVX')
        self.resource_provider_trait_set(self.rp1_2['uuid'], 'HW_CPU_X86_SSE')

    def test_granular_one_group(self):
        groups = {
            '1': {'resources': ('VCPU=3',)}
        }
        rows = self.allocation_candidate_granular(groups=groups)
        self.assertEqual(2, len(rows))

        numbers = {row['#'] for row in rows}
        self.assertEqual(2, len(numbers))

        rps = {row['resource provider'] for row in rows}
        self.assertEqual(2, len(rps))
        self.assertIn(self.rp1_1['uuid'], rps)
        self.assertIn(self.rp1_2['uuid'], rps)

    def test_granular_two_groups(self):
        groups = {
            '1': {'resources': ('VCPU=3',)},
            '2': {'resources': ('VCPU=3',)}
        }
        rows = self.allocation_candidate_granular(groups=groups)
        self.assertEqual(6, len(rows))

        numbers = {row['#'] for row in rows}
        self.assertEqual(4, len(numbers))

        rps = {row['resource provider'] for row in rows}
        self.assertEqual(2, len(rps))
        self.assertIn(self.rp1_1['uuid'], rps)
        self.assertIn(self.rp1_2['uuid'], rps)

        rows = self.allocation_candidate_granular(groups=groups,
                                                  group_policy='isolate')
        self.assertEqual(4, len(rows))

        numbers = {row['#'] for row in rows}
        self.assertEqual(2, len(numbers))

        rps = {row['resource provider'] for row in rows}
        self.assertEqual(2, len(rps))
        self.assertIn(self.rp1_1['uuid'], rps)
        self.assertIn(self.rp1_2['uuid'], rps)

        rows = self.allocation_candidate_granular(groups=groups,
                                                  group_policy='isolate',
                                                  limit=1)
        self.assertEqual(2, len(rows))

        numbers = {row['#'] for row in rows}
        self.assertEqual(1, len(numbers))

        rps = {row['resource provider'] for row in rows}
        self.assertEqual(2, len(rps))
        self.assertIn(self.rp1_1['uuid'], rps)
        self.assertIn(self.rp1_2['uuid'], rps)

    def test_granular_traits1(self):
        groups = {
            '1': {'resources': ('VCPU=6',)},
            '2': {'resources': ('VCPU=10',),
                  'required': ['HW_CPU_X86_AVX']}
        }
        rows = self.allocation_candidate_granular(groups=groups,
                                                  group_policy='isolate')
        self.assertEqual(0, len(rows))

    def test_granular_traits2(self):
        groups = {
            '1': {'resources': ('VCPU=6',)},
            '2': {'resources': ('VCPU=10',),
                  'required': ['HW_CPU_X86_SSE']}
        }
        rows = self.allocation_candidate_granular(groups=groups,
                                                  group_policy='isolate')
        self.assertEqual(2, len(rows))

        numbers = {row['#'] for row in rows}
        self.assertEqual(1, len(numbers))

        rps = {row['resource provider'] for row in rows}
        self.assertEqual(2, len(rps))
        self.assertIn(self.rp1_1['uuid'], rps)
        self.assertIn(self.rp1_2['uuid'], rps)
