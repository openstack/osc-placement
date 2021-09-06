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

from osc_lib.command import command
from osc_lib import exceptions
from osc_lib import utils

from osc_placement import version


BASE_URL = '/allocations'


def parse_allocations(allocation_strings):
    allocations = {}
    for allocation_string in allocation_strings:
        if '=' not in allocation_string or ',' not in allocation_string:
            raise ValueError('Incorrect allocation string format')
        parsed = dict(kv.split('=') for kv in allocation_string.split(','))
        if 'rp' not in parsed:
            raise ValueError('Resource provider parameter is required '
                             'for allocation string')
        resources = {k: int(v) for k, v in parsed.items() if k != 'rp'}
        if parsed['rp'] not in allocations:
            allocations[parsed['rp']] = resources
        else:
            prev_rp = allocations[parsed['rp']]
            for resource, value in resources.items():
                if resource in prev_rp and prev_rp[resource] != value:
                    raise exceptions.CommandError(
                        'Conflict detected for '
                        'resource provider {} resource class {}'.format(
                            parsed['rp'], resource))
            allocations[parsed['rp']].update(resources)
    return allocations


class SetAllocation(command.Lister, version.CheckerMixin):
    """Replaces the set of resource allocation(s) for a given consumer.

    Note that this is a full replacement of the existing allocations. If you
    want to retain the existing allocations and add a new resource class
    allocation, you must specify all resource class allocations, old and new.

    From ``--os-placement-api-version 1.8`` it is required to specify
    ``--project-id`` and ``--user-id`` to set allocations. It is highly
    recommended to provide a ``--project-id`` and ``--user-id`` when setting
    allocations for accounting and data consistency reasons.

    Starting with ``--os-placement-api-version 1.12`` the API response
    contains the ``project_id`` and ``user_id`` of allocations which also
    appears in the CLI output.

    Starting with ``--os-placement-api-version 1.28`` a consumer generation is
    used which facilitates safe concurrent modification of an allocation.

    Starting with ``--os-placement-api-version 1.38`` it is required to specify
    ``--consumer-type`` to set allocations. It is helpful to provide a
    ``--consumer-type`` when setting allocations so that resource usages can be
    filtered on consumer types.
    """

    def get_parser(self, prog_name):
        parser = super(SetAllocation, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the consumer'
        )
        parser.add_argument(
            '--allocation',
            metavar='<rp=resource-provider-id,'
                    'resource-class-name=amount-of-resource-used>',
            action='append',
            default=[],
            help='Create (or update) an allocation of a resource class. '
                 'Specify option multiple times to set multiple allocations.'
        )
        parser.add_argument(
            '--project-id',
            metavar='project_id',
            help='ID of the consuming project. '
                 'This option is required starting from '
                 '``--os-placement-api-version 1.8``.',
            required=self.compare_version(version.ge('1.8'))
        )
        parser.add_argument(
            '--user-id',
            metavar='user_id',
            help='ID of the consuming user. '
                 'This option is required starting from '
                 '``--os-placement-api-version 1.8``.',
            required=self.compare_version(version.ge('1.8'))
        )
        parser.add_argument(
            '--consumer-type',
            metavar='consumer_type',
            help='The type of the consumer. '
                 'This option is required starting from '
                 '``--os-placement-api-version 1.38``.',
            required=self.compare_version(version.ge('1.38'))
        )
        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement
        url = BASE_URL + '/' + parsed_args.uuid

        # Determine if we need to honor consumer generations.
        supports_consumer_generation = self.compare_version(version.ge('1.28'))
        if supports_consumer_generation:
            # Get the existing consumer generation via GET.
            payload = http.request('GET', url).json()
            consumer_generation = payload.get('consumer_generation')

        allocations = parse_allocations(parsed_args.allocation)
        if not allocations:
            raise exceptions.CommandError(
                'At least one resource allocation must be specified')

        if self.compare_version(version.ge('1.12')):
            allocations = {
                rp: {'resources': resources}
                for rp, resources in allocations.items()}
        else:
            allocations = [
                {'resource_provider': {'uuid': rp}, 'resources': resources}
                for rp, resources in allocations.items()]

        payload = {'allocations': allocations}
        # Include consumer_generation for 1.28+. Note that if this is the
        # first set of allocations the consumer_generation will be None.
        if supports_consumer_generation:
            payload['consumer_generation'] = consumer_generation
        if self.compare_version(version.ge('1.8')):
            payload['project_id'] = parsed_args.project_id
            payload['user_id'] = parsed_args.user_id
        elif parsed_args.project_id or parsed_args.user_id:
            self.log.warning('--project-id and --user-id options do not '
                             'affect allocation for '
                             '--os-placement-api-version less than 1.8')
        if self.compare_version(version.ge('1.38')):
            payload['consumer_type'] = parsed_args.consumer_type
        elif parsed_args.consumer_type:
            self.log.warning('--consumer-type option does not affect '
                             'allocation for --os-placement-api-version less '
                             'than 1.38')
        http.request('PUT', url, json=payload)
        resp = http.request('GET', url).json()
        per_provider = resp['allocations'].items()
        props = {}

        fields = ('resource_provider', 'generation', 'resources')
        if self.compare_version(version.ge('1.12')):
            fields += ('project_id', 'user_id')
            props['project_id'] = resp['project_id']
            props['user_id'] = resp['user_id']
        if self.compare_version(version.ge('1.38')):
            fields += ('consumer_type',)
            props['consumer_type'] = resp['consumer_type']

        allocs = [dict(resource_provider=k, **props, **v)
                  for k, v in per_provider]
        rows = (utils.get_dict_properties(a, fields) for a in allocs)
        return fields, rows


class UnsetAllocation(command.Lister, version.CheckerMixin):
    """Removes one or more sets of provider allocations for a consumer.

    Note that omitting both the ``--provider`` and the ``--resource-class``
    option is equivalent to removing all allocations for the given consumer.

    This command requires ``--os-placement-api-version 1.12`` or greater. Use
    ``openstack resource provider allocation set`` for older versions.
    """

    def get_parser(self, prog_name):
        parser = super(UnsetAllocation, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<consumer_uuid>',
            help='UUID of the consumer. It is strongly recommended to use '
                 '``--os-placement-api-version 1.28`` or greater when using '
                 'this option to ensure the other allocation information is '
                 'retained. '
        )
        parser.add_argument(
            '--provider',
            metavar='provider_uuid',
            action='append',
            default=[],
            help='UUID of a specific resource provider from which to remove '
                 'allocations for the given consumer. This is useful when the '
                 'consumer has allocations on more than one provider, for '
                 'example after evacuating a server to another compute node '
                 'and you want to cleanup allocations on the source compute '
                 'node resource provider in order to delete it. Specify '
                 'multiple times to remove allocations against multiple '
                 'resource providers. Omit this option to remove all '
                 'allocations for the consumer, or to remove all allocations'
                 'of a specific resource class from all the resource provider '
                 'with the ``--resource_class`` option. '
        )
        parser.add_argument(
            '--resource-class',
            metavar='resource_class',
            action='append',
            default=[],
            help='Name of a resource class from which to remove allocations '
                 'for the given consumer. This is useful when the consumer '
                 'has allocations on more than one resource class. '
                 'By default, this will remove allocations for the given '
                 'resource class from all the providers. If ``--provider`` '
                 'option is also specified, allocations to remove will be '
                 'limited to that resource class of the given resource '
                 'provider.'
        )
        return parser

    # NOTE(mriedem): We require >= 1.12 because PUT requires project_id/user_id
    # since 1.8 but GET does not return project_id/user_id until 1.12 and we
    # do not want to add --project-id and --user-id options to this command
    # like in the set command. If someone needs to use an older microversion or
    # change the user/project they can use the set command.
    @version.check(version.ge('1.12'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement
        url = BASE_URL + '/' + parsed_args.uuid

        # Get the current allocations.
        payload = http.request('GET', url).json()
        allocations = payload['allocations']

        if parsed_args.resource_class:
            # Remove the given resource class. Do not error out if the
            # consumer does not have allocations against that resource
            # class.
            rp_uuids = set(allocations)
            if parsed_args.provider:
                # If providers are also specified, we limit to remove
                # allocations only from those providers
                rp_uuids &= set(parsed_args.provider)
            for rp_uuid in rp_uuids:
                for rc in parsed_args.resource_class:
                    allocations[rp_uuid]['resources'].pop(rc, None)
                if not allocations[rp_uuid]['resources']:
                    allocations.pop(rp_uuid, None)
        else:
            if parsed_args.provider:
                # Remove the given provider(s) from the allocations if it
                # exists. Do not error out if the consumer does not have
                # allocations against a provider in case we lost a race since
                # the allocations are in the state the user wants them in
                # anyway.
                for rp_uuid in parsed_args.provider:
                    allocations.pop(rp_uuid, None)
            else:
                # No --provider(s) specified so remove allocations from all
                # providers.
                allocations = {}

        supports_consumer_generation = self.compare_version(version.ge('1.28'))
        # 1.28+ allows PUTing an empty allocations dict as long as a
        # consumer_generation is specified.
        if allocations or supports_consumer_generation:
            payload['allocations'] = allocations
            http.request('PUT', url, json=payload)
        else:
            # The user must have removed all of the allocations so just DELETE
            # the allocations since we cannot PUT with an empty allocations
            # dict before 1.28.
            http.request('DELETE', url)

        resp = http.request('GET', url).json()
        per_provider = resp['allocations'].items()
        props = {}

        fields = ('resource_provider', 'generation', 'resources',
                  'project_id', 'user_id')
        if self.compare_version(version.ge('1.38')):
            fields += ('consumer_type',)
            props['consumer_type'] = resp.get('consumer_type')
        allocs = [dict(project_id=resp['project_id'], user_id=resp['user_id'],
                       resource_provider=k, **props, **v)
                  for k, v in per_provider]
        rows = (utils.get_dict_properties(a, fields) for a in allocs)
        return fields, rows


class ShowAllocation(command.Lister, version.CheckerMixin):
    """Show resource allocations for a given consumer.

    Starting with ``--os-placement-api-version 1.12`` the API response contains
    the ``project_id`` and ``user_id`` of allocations which also appears in the
    CLI output.

    Starting with ``--os-placement-api-version 1.38`` the API response contains
    the ``consumer_type`` of consumer which also appears in the CLI output.
    """

    def get_parser(self, prog_name):
        parser = super(ShowAllocation, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the consumer'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL + '/' + parsed_args.uuid
        resp = http.request('GET', url).json()
        per_provider = resp['allocations'].items()
        props = {}

        fields = ('resource_provider', 'generation', 'resources')
        if self.compare_version(version.ge('1.12')):
            fields += ('project_id', 'user_id')
            props['project_id'] = resp.get('project_id')
            props['user_id'] = resp.get('user_id')
        if self.compare_version(version.ge('1.38')):
            fields += ('consumer_type',)
            props['consumer_type'] = resp.get('consumer_type')

        allocs = [dict(resource_provider=k, **props, **v)
                  for k, v in per_provider]

        rows = (utils.get_dict_properties(a, fields) for a in allocs)
        return fields, rows


class DeleteAllocation(command.Command):
    """Delete all resource allocations for a given consumer."""

    def get_parser(self, prog_name):
        parser = super(DeleteAllocation, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the consumer'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL + '/' + parsed_args.uuid
        http.request('DELETE', url)
