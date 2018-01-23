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


BASE_URL = '/allocations'
FIELDS = ('generation', 'resources')


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


class SetAllocation(command.Lister):
    """Replaces the set of resource allocation(s) for a given consumer

    Note that this is a full replacement of the existing allocations. If you
    want to retain the existing allocations and add a new resource class
    allocation, you must specify all resource class allocations, old and new.
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

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        allocations = parse_allocations(parsed_args.allocation)
        if not allocations:
            raise exceptions.CommandError(
                'At least one resource allocation must be specified')
        allocations = [
            {'resource_provider': {'uuid': rp}, 'resources': resources}
            for rp, resources in allocations.items()]

        url = BASE_URL + '/' + parsed_args.uuid
        http.request('PUT', url, json={'allocations': allocations})
        per_provider = http.request('GET', url).json()['allocations'].items()
        allocs = [dict(resource_provider=k, **v) for k, v in per_provider]

        fields_ext = ('resource_provider', ) + FIELDS
        rows = (utils.get_dict_properties(a, fields_ext) for a in allocs)
        return fields_ext, rows


class ShowAllocation(command.Lister):
    """Show resource allocations for a given consumer"""

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
        per_provider = http.request('GET', url).json()['allocations'].items()
        allocs = [dict(resource_provider=k, **v) for k, v in per_provider]

        fields_ext = ('resource_provider', ) + FIELDS
        rows = (utils.get_dict_properties(a, fields_ext) for a in allocs)
        return fields_ext, rows


class DeleteAllocation(command.Command):
    """Delete a resource allocation for a given consumer"""

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
