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

import logging
import random

import fixtures
import six

from openstackclient import shell
from oslotest import base
from placement.tests.functional.fixtures import capture
from placement.tests.functional.fixtures import placement
import simplejson as json


# A list of logger names that will be reset to a log level
# of WARNING. Due (we think) to a poor interaction between the
# way osc does logging and oslo.logging, all packages are producing
# DEBUG logs. This results in test attachments (when capturing logs)
# that are sometimes larger than subunit.parser can deal with. The
# packages chosen here are ones that do not provide useful information.
RESET_LOGGING = [
    'keystoneauth.session',
    'oslo_policy.policy',
    'placement.objects.trait',
    'placement.objects.resource_class',
    'placement.objects.resource_provider',
    'oslo_concurrency.lockutils',
    'osc_lib.shell',
]

RP_PREFIX = 'osc-placement-functional-tests-'

ARGUMENTS_MISSING = 'the following arguments are required'
ARGUMENTS_REQUIRED = 'the following arguments are required: %s'


class CommandException(Exception):
    def __init__(self, *args, **kwargs):
        super(CommandException, self).__init__(args[0])
        self.cmd = kwargs['cmd']


class BaseTestCase(base.BaseTestCase):
    VERSION = None

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.useFixture(capture.Logging())
        self.placement = self.useFixture(placement.PlacementFixture())

        # Work around needing to reset the session's notion of where
        # we are going.
        def mock_get(obj, instance, owner):
            return obj.factory(instance)

        # NOTE(cdent): This is fragile, but is necessary to work around
        # the rather complex start up optimizations that are done in osc_lib.
        # If/when osc_lib changes this will at least fail fast.
        self.useFixture(fixtures.MonkeyPatch(
            'osc_lib.clientmanager.ClientCache.__get__',
            mock_get))

        # Reset log level on a set of packages. See comment on RESET_LOGGING
        # assigment, above.
        for name in RESET_LOGGING:
            logging.getLogger(name).setLevel(logging.WARNING)

    def openstack(self, cmd, may_fail=False, use_json=False,
                  may_print_to_stderr=False):
        to_exec = []
        # Make all requests as a noauth admin user.
        to_exec += [
            '--os-endpoint', self.placement.endpoint,
            '--os-token', self.placement.token,
            '--os-auth-type', 'admin_token',
        ]
        if self.VERSION is not None:
            to_exec += ['--os-placement-api-version', self.VERSION]
        to_exec += cmd.split()
        if use_json:
            to_exec += ['-f', 'json']

        # Context manager here instead of setUp because we only want
        # output trapping around the run().
        self.output = six.StringIO()
        self.error = six.StringIO()
        stdout_fix = fixtures.MonkeyPatch('sys.stdout', self.output)
        stderr_fix = fixtures.MonkeyPatch('sys.stderr', self.error)
        with stdout_fix, stderr_fix:
            try:
                os_shell = shell.OpenStackShell()
                return_code = os_shell.run(to_exec)
            # Catch SystemExit to trap some error responses, mostly from the
            # argparse lib which has a tendency to exit for you instead of
            # politely telling you it wants to.
            except SystemExit as exc:
                return_code = exc.code

        # We may have error/warning messages in stderr, so treat it
        # separately from the stdout.
        output = self.output.getvalue()
        error = self.error.getvalue()

        if return_code:
            msg = 'Command: "%s"\noutput: %s' % (' '.join(to_exec), error)
            if not may_fail:
                raise CommandException(msg, cmd=' '.join(to_exec))

        if use_json and output:
            output = json.loads(output)

        if may_print_to_stderr:
            return output, error

        if error:
            msg = ('Test code error - The command did not fail but it '
                   'has a warning message. Set the "may_print_to_stderr" '
                   'argument to true to get and validate the message:\n'
                   'Command: "%s"\nstderr: %s') % (
                ' '.join(to_exec), error)
            raise CommandException(msg, cmd=' '.join(to_exec))
        return output

    def rand_name(self, name='', prefix=None):
        """Generate a random name that includes a random number

        :param str name: The name that you want to include
        :param str prefix: The prefix that you want to include
        :return: a random name. The format is
                 '<prefix>-<name>-<random number>'.
                 (e.g. 'prefixfoo-namebar-154876201')
        :rtype: string
        """
        # NOTE(lajos katona): This method originally is in tempest-lib.
        randbits = str(random.randint(1, 0x7fffffff))
        rand_name = randbits
        if name:
            rand_name = name + '-' + rand_name
        if prefix:
            rand_name = prefix + '-' + rand_name
        return rand_name

    def assertCommandFailed(self, message, func, *args, **kwargs):
        signature = [func]
        signature.extend(args)
        try:
            func(*args, **kwargs)
            self.fail('Command does not fail as required (%s)' % signature)
        except CommandException as e:
            self.assertIn(
                message, six.text_type(e),
                'Command "%s" fails with different message' % e.cmd)

    def resource_provider_create(self,
                                 name='',
                                 parent_provider_uuid=None):
        if not name:
            name = self.rand_name(name='', prefix=RP_PREFIX)

        to_exec = 'resource provider create ' + name
        if parent_provider_uuid is not None:
            to_exec += ' --parent-provider ' + parent_provider_uuid
        res = self.openstack(to_exec, use_json=True)

        def cleanup():
            try:
                self.resource_provider_delete(res['uuid'])
            except CommandException as exc:
                # may have already been deleted by a test case
                err_message = six.text_type(exc).lower()
                if 'no resource provider' not in err_message:
                    raise
        self.addCleanup(cleanup)

        return res

    def resource_provider_set(self, uuid, name, parent_provider_uuid=None):
        to_exec = 'resource provider set ' + uuid + ' --name ' + name
        if parent_provider_uuid is not None:
            to_exec += ' --parent-provider ' + parent_provider_uuid
        return self.openstack(to_exec, use_json=True)

    def resource_provider_show(self, uuid, allocations=False):
        cmd = 'resource provider show ' + uuid
        if allocations:
            cmd = cmd + ' --allocations'

        return self.openstack(cmd, use_json=True)

    def resource_provider_list(self, uuid=None, name=None,
                               aggregate_uuids=None, resources=None,
                               in_tree=None, required=None, forbidden=None):
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
        if in_tree:
            to_exec += ' --in-tree ' + in_tree
        if required:
            to_exec += ' ' + ' '.join('--required %s' % t for t in required)
        if forbidden:
            to_exec += ' ' + ' '.join('--forbidden %s' % f for f in forbidden)

        return self.openstack(to_exec, use_json=True)

    def resource_provider_delete(self, uuid):
        return self.openstack('resource provider delete ' + uuid)

    def resource_allocation_show(self, consumer_uuid):
        return self.openstack(
            'resource provider allocation show ' + consumer_uuid,
            use_json=True
        )

    def resource_allocation_set(self, consumer_uuid, allocations,
                                project_id=None, user_id=None,
                                use_json=True, may_print_to_stderr=False):
        cmd = 'resource provider allocation set {allocs} {uuid}'.format(
            uuid=consumer_uuid,
            allocs=' '.join('--allocation {}'.format(a) for a in allocations)
        )
        if project_id:
            cmd += ' --project-id %s' % project_id
        if user_id:
            cmd += ' --user-id %s' % user_id
        result = self.openstack(cmd, use_json=use_json,
                                may_print_to_stderr=may_print_to_stderr)

        def cleanup(uuid):
            try:
                self.openstack('resource provider allocation delete ' + uuid)
            except CommandException as exc:
                # may have already been deleted by a test case
                if 'not found' in six.text_type(exc).lower():
                    pass
        self.addCleanup(cleanup, consumer_uuid)

        return result

    def resource_allocation_unset(self, consumer_uuid, provider=None,
                                  use_json=True):
        if provider:
            # --provider can be specified multiple times so if we only get
            # a single string value convert to a list.
            if isinstance(provider, six.string_types):
                provider = [provider]
            cmd = 'resource provider allocation unset %s %s' % (
                ' '.join('--provider %s' %
                         rp_uuid for rp_uuid in provider),
                consumer_uuid
            )
        else:
            cmd = 'resource provider allocation unset %s' % consumer_uuid
        result = self.openstack(cmd, use_json=use_json)

        def cleanup(uuid):
            try:
                self.openstack('resource provider allocation delete ' + uuid)
            except CommandException as exc:
                # may have already been deleted by a test case
                if 'not found' in six.text_type(exc).lower():
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

    def resource_inventory_delete(self, uuid, resource_class=None):
        cmd = 'resource provider inventory delete {uuid}'.format(uuid=uuid)
        if resource_class:
            cmd += ' --resource-class ' + resource_class
        self.openstack(cmd)

    def resource_inventory_set(self, uuid, *resources, **kwargs):
        opts = []
        if kwargs.get('aggregate'):
            opts.append('--aggregate')
        if kwargs.get('amend'):
            opts.append('--amend')
        if kwargs.get('dry_run'):
            opts.append('--dry-run')
        fmt = 'resource provider inventory set {uuid} {resources} {opts}'
        cmd = fmt.format(
            uuid=uuid,
            resources=' '.join(['--resource %s' % r for r in resources]),
            opts=' '.join(opts))
        return self.openstack(cmd, use_json=True)

    def resource_inventory_class_set(self, uuid, resource_class, **kwargs):
        opts = ['--%s=%s' % (k, v) for k, v in kwargs.items()]
        cmd = 'resource provider inventory class set {uuid} {rc} {opts}'.\
            format(uuid=uuid, rc=resource_class, opts=' '.join(opts))
        return self.openstack(cmd, use_json=True)

    def resource_provider_show_usage(self, uuid):
        return self.openstack('resource provider usage show ' + uuid,
                              use_json=True)

    def resource_show_usage(self, project_id, user_id=None):
        cmd = 'resource usage show %s' % project_id
        if user_id:
            cmd += ' --user-id %s' % user_id
        return self.openstack(cmd, use_json=True)

    def resource_provider_aggregate_list(self, uuid):
        return self.openstack('resource provider aggregate list ' + uuid,
                              use_json=True)

    def resource_provider_aggregate_set(self, uuid, *aggregates,
                                        **kwargs):
        generation = kwargs.get('generation')
        cmd = 'resource provider aggregate set %s ' % uuid
        cmd += ' '.join('--aggregate %s' % aggregate
                        for aggregate in aggregates)
        if generation is not None:
            cmd += ' --generation %s' % generation
        return self.openstack(cmd, use_json=True)

    def resource_class_list(self):
        return self.openstack('resource class list', use_json=True)

    def resource_class_show(self, name):
        return self.openstack('resource class show ' + name, use_json=True)

    def resource_class_create(self, name):
        return self.openstack('resource class create ' + name)

    def resource_class_set(self, name):
        return self.openstack('resource class set ' + name)

    def resource_class_delete(self, name):
        return self.openstack('resource class delete ' + name)

    def trait_list(self, name=None, associated=False):
        cmd = 'trait list'
        if name:
            cmd += ' --name ' + name
        if associated:
            cmd += ' --associated'
        return self.openstack(cmd, use_json=True)

    def trait_show(self, name):
        cmd = 'trait show %s' % name
        return self.openstack(cmd, use_json=True)

    def trait_create(self, name):
        cmd = 'trait create %s' % name
        self.openstack(cmd)

        def cleanup():
            try:
                self.trait_delete(name)
            except CommandException as exc:
                # may have already been deleted by a test case
                err_message = six.text_type(exc).lower()
                if 'http 404' not in err_message:
                    raise
        self.addCleanup(cleanup)

    def trait_delete(self, name):
        cmd = 'trait delete %s' % name
        self.openstack(cmd)

    def resource_provider_trait_list(self, uuid):
        cmd = 'resource provider trait list %s ' % uuid
        return self.openstack(cmd, use_json=True)

    def resource_provider_trait_set(self, uuid, *traits):
        cmd = 'resource provider trait set %s ' % uuid
        cmd += ' '.join('--trait %s' % trait for trait in traits)
        return self.openstack(cmd, use_json=True)

    def resource_provider_trait_delete(self, uuid):
        cmd = 'resource provider trait delete %s ' % uuid
        self.openstack(cmd)

    def allocation_candidate_list(self, resources, required=None,
                                  forbidden=None, limit=None,
                                  aggregate_uuids=None):
        cmd = 'allocation candidate list ' + ' '.join(
            '--resource %s' % resource for resource in resources)
        if required is not None:
            cmd += ''.join([' --required %s' % t for t in required])
        if forbidden:
            cmd += ' ' + ' '.join('--forbidden %s' % f for f in forbidden)
        if limit is not None:
            cmd += ' --limit %d' % limit
        if aggregate_uuids:
            cmd += ' ' + ' '.join(
                   '--aggregate-uuid %s' % a for a in aggregate_uuids)
        return self.openstack(cmd, use_json=True)
