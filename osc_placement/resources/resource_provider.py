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
from osc_lib import utils

from osc_placement.resources import common
from osc_placement import version


BASE_URL = '/resource_providers'
ALLOCATIONS_URL = BASE_URL + '/{uuid}/allocations'
FIELDS = ('uuid', 'name', 'generation')


class CreateResourceProvider(command.ShowOne):
    """Create a new resource provider"""

    def get_parser(self, prog_name):
        parser = super(CreateResourceProvider, self).get_parser(prog_name)

        parser.add_argument(
            '--uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )
        parser.add_argument(
            'name',
            metavar='<name>',
            help='Name of the resource provider'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        data = {'name': parsed_args.name}

        if 'uuid' in parsed_args and parsed_args.uuid:
            data['uuid'] = parsed_args.uuid

        resp = http.request('POST', BASE_URL, json=data)
        resource = http.request('GET', resp.headers['Location']).json()
        return FIELDS, utils.get_dict_properties(resource, FIELDS)


class ListResourceProvider(command.Lister, version.CheckerMixin):
    """List resource providers"""

    def get_parser(self, prog_name):
        parser = super(ListResourceProvider, self).get_parser(prog_name)

        parser.add_argument(
            '--uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )
        parser.add_argument(
            '--name',
            metavar='<name>',
            help='Name of the resource provider'
        )
        parser.add_argument(
            '--aggregate-uuid',
            default=[],
            action='append',
            metavar='<aggregate_uuid>',
            help='UUID of the resource provider aggregate of which the '
                 'listed resource providers are a member. The returned '
                 'resource providers must be associated with at least one of '
                 'the aggregates identified by uuid. '
                 'May be repeated.\n\n'
                 'This param requires at least '
                 '``--os-placement-api-version 1.3``.'
        )
        parser.add_argument(
            '--resource',
            metavar='<resource_class>=<value>',
            default=[],
            action='append',
            help='A resource class value pair indicating an '
                 'amount of resource of a specified class that a provider '
                 'must have the capacity to serve. May be repeated.\n\n'
                 'This param requires at least '
                 '``--os-placement-api-version 1.4``.'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        filters = {}
        if parsed_args.name:
            filters['name'] = parsed_args.name
        if parsed_args.uuid:
            filters['uuid'] = parsed_args.uuid
        if parsed_args.aggregate_uuid:
            self.check_version(version.ge('1.3'))
            filters['member_of'] = 'in:' + ','.join(parsed_args.aggregate_uuid)
        if parsed_args.resource:
            self.check_version(version.ge('1.4'))
            filters['resources'] = ','.join(
                resource.replace('=', ':')
                for resource in parsed_args.resource)

        url = common.url_with_filters(BASE_URL, filters)
        resources = http.request('GET', url).json()['resource_providers']
        rows = (utils.get_dict_properties(r, FIELDS) for r in resources)
        return FIELDS, rows


class ShowResourceProvider(command.ShowOne):
    """Show resource provider details"""

    def get_parser(self, prog_name):
        parser = super(ShowResourceProvider, self).get_parser(prog_name)
        # TODO(avolkov): show by uuid or name
        parser.add_argument(
            '--allocations',
            action='store_true',
            help='include the info on allocations of the provider resources'
        )
        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL + '/' + parsed_args.uuid
        resource = http.request('GET', url).json()

        if parsed_args.allocations:
            allocs_url = ALLOCATIONS_URL.format(uuid=parsed_args.uuid)
            allocs = http.request('GET', allocs_url).json()['allocations']
            resource['allocations'] = allocs

            fields_ext = FIELDS + ('allocations', )
            return fields_ext, utils.get_dict_properties(resource, fields_ext)
        else:
            return FIELDS, utils.get_dict_properties(resource, FIELDS)


class SetResourceProvider(command.ShowOne):
    """Update an existing resource provider"""

    def get_parser(self, prog_name):
        parser = super(SetResourceProvider, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )
        parser.add_argument(
            '--name',
            metavar='<name>',
            help='A new name of the resource provider',
            required=True
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL + '/' + parsed_args.uuid
        resource = http.request('PUT', url,
                                json={'name': parsed_args.name}).json()
        return FIELDS, utils.get_dict_properties(resource, FIELDS)


class DeleteResourceProvider(command.Command):
    """Delete a resource provider"""

    def get_parser(self, prog_name):
        parser = super(DeleteResourceProvider, self).get_parser(prog_name)

        # TODO(avolkov): delete by uuid or name
        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL + '/' + parsed_args.uuid
        http.request('DELETE', url)
