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

import six

from osc_placement.tests.functional import base


class TestAllocation(base.BaseTestCase):
    def setUp(self):
        super(TestAllocation, self).setUp()

        self.rp1 = self.resource_provider_create()
        self.resource_inventory_set(
            self.rp1['uuid'], 'VCPU=4', 'MEMORY_MB=1024')

    def test_allocation_show_not_found(self):
        consumer_uuid = str(uuid.uuid4())

        result = self.resource_allocation_show(consumer_uuid)
        self.assertEqual([], result)

    def test_allocation_create(self):
        consumer_uuid = str(uuid.uuid4())

        created_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])]
        )
        retrieved_alloc = self.resource_allocation_show(consumer_uuid)

        expected = [
            {'resource_provider': self.rp1['uuid'],
             'generation': 2,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512}}
        ]
        self.assertEqual(expected, created_alloc)
        self.assertEqual(expected, retrieved_alloc)

        # Test that specifying --project-id and --user-id before microversion
        # 1.8 does not result in an error but display a warning.
        output, warning = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])],
            project_id='fake-project', user_id='fake-user',
            may_print_to_stderr=True)
        expected = [
            {'resource_provider': self.rp1['uuid'],
             'generation': 3,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512}}
        ]
        self.assertEqual(expected, output)
        self.assertIn(
            '--project-id and --user-id options do not affect allocation for '
            '--os-placement-api-version less than 1.8', warning)

        # Test that specifying --consumer-type before microversion 1.38 does
        # not result in an error but display a warning.
        output, warning = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])],
            consumer_type='fake-type', may_print_to_stderr=True)
        expected = [
            {'resource_provider': self.rp1['uuid'],
             'generation': 4,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512}}
        ]
        self.assertEqual(expected, output)
        self.assertIn(
            '--consumer-type option does not affect allocation for '
            '--os-placement-api-version less than 1.38', warning)

    def test_allocation_create_empty(self):
        consumer_uuid = str(uuid.uuid4())

        exc = self.assertRaises(base.CommandException,
                                self.resource_allocation_set,
                                consumer_uuid, [])
        self.assertIn('At least one resource allocation must be specified',
                      six.text_type(exc))

    def test_allocation_delete(self):
        consumer_uuid = str(uuid.uuid4())

        self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])]
        )
        self.assertTrue(self.resource_allocation_show(consumer_uuid))

        self.resource_allocation_delete(consumer_uuid)
        self.assertEqual([], self.resource_allocation_show(consumer_uuid))

    def test_allocation_delete_not_found(self):
        consumer_uuid = str(uuid.uuid4())

        msg = "No allocations for consumer '{}'".format(consumer_uuid)
        exc = self.assertRaises(base.CommandException,
                                self.resource_allocation_delete, consumer_uuid)
        self.assertIn(msg, six.text_type(exc))


class TestAllocation18(base.BaseTestCase):
    VERSION = '1.8'

    def test_allocation_create(self):
        consumer_uuid = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        rp1 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'],
            'VCPU=4',
            'VCPU:max_unit=4',
            'MEMORY_MB=1024',
            'MEMORY_MB:max_unit=1024')
        created_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(rp1['uuid'])],
            project_id=project_id, user_id=user_id
        )
        retrieved_alloc = self.resource_allocation_show(consumer_uuid)

        expected = [
            {'resource_provider': rp1['uuid'],
             'generation': 2,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512}}
        ]
        self.assertEqual(expected, created_alloc)
        self.assertEqual(expected, retrieved_alloc)


class TestAllocation112(base.BaseTestCase):
    VERSION = '1.12'

    def setUp(self):
        super(TestAllocation112, self).setUp()

        self.rp1 = self.resource_provider_create()
        self.resource_inventory_set(
            self.rp1['uuid'], 'VCPU=4', 'MEMORY_MB=1024')

    def test_allocation_update(self):
        consumer_uuid = str(uuid.uuid4())
        project_uuid = str(uuid.uuid4())
        user_uuid = str(uuid.uuid4())

        created_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])],
            project_id=project_uuid, user_id=user_uuid
        )
        retrieved_alloc = self.resource_allocation_show(consumer_uuid)

        expected = [
            {'resource_provider': self.rp1['uuid'],
             'generation': 2,
             'project_id': project_uuid,
             'user_id': user_uuid,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512}}
        ]
        self.assertEqual(expected, created_alloc)
        self.assertEqual(expected, retrieved_alloc)

    def test_allocation_update_to_empty(self):
        consumer_uuid = str(uuid.uuid4())
        project_uuid = str(uuid.uuid4())
        user_uuid = str(uuid.uuid4())

        self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid'])],
            project_id=project_uuid,
            user_id=user_uuid,
        )

        result = self.resource_allocation_unset(
            consumer_uuid, columns=("resources",))

        self.assertEqual([], result)

    def test_allocation_show_empty(self):
        alloc = self.resource_allocation_show(
            str(uuid.uuid4()), columns=('resources',))
        self.assertEqual([], alloc)


class TestAllocation128(TestAllocation112):
    """Tests allocation set command with --os-placement-api-version 1.28.

    The 1.28 microversion adds the consumer_generation parameter to the
    GET and PUT /allocations/{consumer_id} APIs.
    """
    VERSION = '1.28'

    def test_allocation_update(self):
        consumer_uuid = str(uuid.uuid4())
        project_uuid = str(uuid.uuid4())
        user_uuid = str(uuid.uuid4())
        # First create the initial set of allocations using rp1.
        created_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])],
            project_id=project_uuid, user_id=user_uuid
        )
        retrieved_alloc = self.resource_allocation_show(consumer_uuid)

        expected = [
            {'resource_provider': self.rp1['uuid'],
             'generation': 2,
             'project_id': project_uuid,
             'user_id': user_uuid,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512}}
        ]
        self.assertEqual(expected, created_alloc)
        self.assertEqual(expected, retrieved_alloc)
        # Now update the allocations which should use the consumer generation.
        updated_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=4'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=1024'.format(self.rp1['uuid'])],
            project_id=project_uuid, user_id=user_uuid
        )
        expected[0].update({
            'generation': expected[0]['generation'] + 1,
            'resources': {'VCPU': 4, 'MEMORY_MB': 1024}
        })
        self.assertEqual(expected, updated_alloc)


class TestAllocation138(TestAllocation128):
    """Tests allocation set command with --os-placement-api-version 1.38.

    The 1.38 microversion adds the consumer_type parameter to the
    GET and PUT /allocations/{consumer_id} APIs
    """
    VERSION = '1.38'

    def test_allocation_update(self):
        consumer_uuid = str(uuid.uuid4())
        project_uuid = str(uuid.uuid4())
        user_uuid = str(uuid.uuid4())
        # First create the initial set of allocations using rp1.
        created_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])],
            project_id=project_uuid, user_id=user_uuid,
            consumer_type='INSTANCE'
        )
        retrieved_alloc = self.resource_allocation_show(consumer_uuid)

        expected = [
            {'resource_provider': self.rp1['uuid'],
             'generation': 2,
             'project_id': project_uuid,
             'user_id': user_uuid,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512},
             'consumer_type': 'INSTANCE'}
        ]
        self.assertEqual(expected, created_alloc)
        self.assertEqual(expected, retrieved_alloc)
        # Now update the allocations which should use the consumer generation.
        updated_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=4'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=1024'.format(self.rp1['uuid'])],
            project_id=project_uuid, user_id=user_uuid,
            consumer_type='MIGRATION'
        )
        expected[0].update({
            'generation': expected[0]['generation'] + 1,
            'resources': {'VCPU': 4, 'MEMORY_MB': 1024},
            'consumer_type': 'MIGRATION'
        })
        self.assertEqual(expected, updated_alloc)

    def test_allocation_update_to_empty(self):
        consumer_uuid = str(uuid.uuid4())
        project_uuid = str(uuid.uuid4())
        user_uuid = str(uuid.uuid4())

        self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid'])],
            project_id=project_uuid,
            user_id=user_uuid,
            consumer_type="INSTANCE",
        )

        result = self.resource_allocation_unset(
            consumer_uuid, columns=('resources', 'consumer_type'))
        self.assertEqual([], result)


class TestAllocationUnsetOldVersion(base.BaseTestCase):

    def test_invalid_version(self):
        """Negative test to ensure the unset command requires >= 1.12."""
        consumer_uuid = str(uuid.uuid4())
        self.assertCommandFailed('requires at least version 1.12',
                                 self.resource_allocation_unset, consumer_uuid)


class TestAllocationUnset112(base.BaseTestCase):
    VERSION = '1.12'

    def setUp(self):
        super(TestAllocationUnset112, self).setUp()
        # Create four providers with inventory.
        self.rp1 = self.resource_provider_create()
        self.rp2 = self.resource_provider_create()
        self.rp3 = self.resource_provider_create()
        self.rp4 = self.resource_provider_create()

        self.resource_inventory_set(
            self.rp1['uuid'], 'VCPU=4', 'MEMORY_MB=1024')
        self.resource_inventory_set(
            self.rp2['uuid'], 'VGPU=1')
        self.resource_inventory_set(
            self.rp3['uuid'], 'VCPU=4', 'MEMORY_MB=1024', 'VGPU=1')
        self.resource_inventory_set(
            self.rp4['uuid'], 'VCPU=4', 'MEMORY_MB=1024', 'VGPU=1')

        self.consumer_uuid1 = str(uuid.uuid4())
        self.consumer_uuid2 = str(uuid.uuid4())
        self.project_uuid = str(uuid.uuid4())
        self.user_uuid = str(uuid.uuid4())

        # Create allocations against rp1 and rp2 for consumer1.
        self.resource_allocation_set(
            self.consumer_uuid1,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid']),
             'rp={},VGPU=1'.format(self.rp2['uuid'])],
            project_id=self.project_uuid, user_id=self.user_uuid)

        # Create allocations against rp3 and rp4 for consumer1.
        self.resource_allocation_set(
            self.consumer_uuid2,
            ['rp={},VCPU=1'.format(self.rp3['uuid']),
             'rp={},MEMORY_MB=256'.format(self.rp3['uuid']),
             'rp={},VGPU=1'.format(self.rp3['uuid']),
             'rp={},VCPU=1'.format(self.rp4['uuid']),
             'rp={},MEMORY_MB=256'.format(self.rp4['uuid'])],
            project_id=self.project_uuid, user_id=self.user_uuid)

    def test_allocation_unset_one_provider(self):
        """Tests removing allocations for one specific provider."""
        # Remove the allocation for rp1.
        updated_allocs = self.resource_allocation_unset(
            self.consumer_uuid1, provider=self.rp1['uuid'])
        expected = [
            {'resource_provider': self.rp2['uuid'],
             'generation': 3,
             'project_id': self.project_uuid,
             'user_id': self.user_uuid,
             'resources': {'VGPU': 1}}
        ]
        self.assertEqual(expected, updated_allocs)

    def test_allocation_unset_one_resource_class(self):
        """Tests removing allocations for resource classes."""
        updated_allocs = self.resource_allocation_unset(
            self.consumer_uuid2, resource_class=['MEMORY_MB'])
        expected = [
            {'resource_provider': self.rp3['uuid'],
             'generation': 3,
             'project_id': self.project_uuid,
             'user_id': self.user_uuid,
             'resources': {'VCPU': 1, 'VGPU': 1}},
            {'resource_provider': self.rp4['uuid'],
             'generation': 3,
             'project_id': self.project_uuid,
             'user_id': self.user_uuid,
             'resources': {'VCPU': 1}}
        ]
        self.assertEqual(expected, updated_allocs)

    def test_allocation_unset_resource_classes(self):
        """Tests removing allocations for resource classes."""
        updated_allocs = self.resource_allocation_unset(
            self.consumer_uuid2, resource_class=['VCPU', 'MEMORY_MB'])
        expected = [
            {'resource_provider': self.rp3['uuid'],
             'generation': 3,
             'project_id': self.project_uuid,
             'user_id': self.user_uuid,
             'resources': {'VGPU': 1}}
        ]
        self.assertEqual(expected, updated_allocs)

    def test_allocation_unset_provider_and_rc(self):
        """Tests removing allocations of resource classes for a provider ."""
        updated_allocs = self.resource_allocation_unset(
            self.consumer_uuid2, provider=self.rp3['uuid'],
            resource_class=['VCPU', 'MEMORY_MB'])
        expected = [
            {'resource_provider': self.rp3['uuid'],
             'generation': 3,
             'project_id': self.project_uuid,
             'user_id': self.user_uuid,
             'resources': {'VGPU': 1}},
            {'resource_provider': self.rp4['uuid'],
             'generation': 3,
             'project_id': self.project_uuid,
             'user_id': self.user_uuid,
             'resources': {'VCPU': 1, 'MEMORY_MB': 256}},
        ]
        self.assertEqual(expected, updated_allocs)

    def test_allocation_unset_remove_all_providers(self):
        """Tests removing all allocations by omitting the --provider option."""
        # For this test pass use_json=False to make sure we get nothing back
        # in the output since there are no more allocations.
        updated_allocs = self.resource_allocation_unset(
            self.consumer_uuid1, use_json=False)
        self.assertEqual('', updated_allocs.strip())


class TestAllocationUnset128(TestAllocationUnset112):
    """Tests allocation unset command with --os-placement-api-version 1.28.

    The 1.28 microversion adds the consumer_generation parameter to the
    GET and PUT /allocations/{consumer_id} APIs.
    """
    VERSION = '1.28'
