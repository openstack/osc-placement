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

import argparse

from osc_lib.command import command
from osc_lib import utils

from osc_placement.resources import common
from osc_placement import version


BASE_URL = '/resource_providers'
ALLOCATIONS_URL = BASE_URL + '/{uuid}/allocations'


class CreateResourceProvider(command.ShowOne, version.CheckerMixin):
    """Create a new resource provider"""

    def get_parser(self, prog_name):
        parser = super(CreateResourceProvider, self).get_parser(prog_name)

        parser.add_argument(
            '--parent-provider',
            metavar='<parent_provider>',
            help='UUID of the parent provider.'
                 ' Omit for no parent.'
                 ' This option requires at least'
                 ' ``--os-placement-api-version 1.14``.'
        )
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
        if ('parent_provider' in parsed_args
                and parsed_args.parent_provider):
            self.check_version(version.ge('1.14'))
            data['parent_provider_uuid'] = parsed_args.parent_provider

        resp = http.request('POST', BASE_URL, json=data)
        resource = http.request('GET', resp.headers['Location']).json()

        fields = ('uuid', 'name', 'generation')
        if self.compare_version(version.ge('1.14')):
            fields += ('root_provider_uuid', 'parent_provider_uuid')

        return fields, utils.get_dict_properties(resource, fields)


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
        parser.add_argument(
            '--in-tree',
            metavar='<in_tree>',
            help='Restrict listing to the same "provider tree"'
                 ' as the specified provider UUID.'
                 ' This option requires at least'
                 ' ``--os-placement-api-version 1.14``.'
        )
        parser.add_argument(
            '--required',
            metavar='<required>',
            action='append',
            default=[],
            help='A required trait. May be repeated. Resource providers '
                 'must collectively contain all of the required traits. '
                 'This option requires at least '
                 '``--os-placement-api-version 1.18``. '
                 'Since ``--os-placement-api-version 1.39`` the value of '
                 'this parameter can be a comma separated list of trait names '
                 'to express OR relationship between those traits.'
        )
        parser.add_argument(
            '--forbidden',
            metavar='<forbidden>',
            action='append',
            default=[],
            help='A forbidden trait. May be repeated. Returned resource '
                 'providers must not contain any of the specified traits. '
                 'This option requires at least '
                 '``--os-placement-api-version 1.22``.'
        )
        # NOTE(tetsuro): --aggregate-uuid is deprecated in Jan 2020 in 1.x
        # release. Do not remove before Jan 2021 and a 2.x release.
        aggregate_group = parser.add_mutually_exclusive_group()
        aggregate_group.add_argument(
            "--member-of",
            default=[],
            action='append',
            metavar='<member_of>',
            help='A list of comma-separated UUIDs of the resource provider '
                 'aggregates. The returned resource providers must be '
                 'associated with at least one of the aggregates identified '
                 'by uuid. This param requires at least '
                 '``--os-placement-api-version 1.3`` and can be repeated to '
                 'add(restrict) the condition with '
                 '``--os-placement-api-version 1.24`` or greater. '
                 'For example, to get candidates either in agg1 or in agg2 '
                 'and definitely in agg3, specify:\n\n'
                 '``--member_of <agg1>,<agg2> --member_of <agg3>``'
        )
        aggregate_group.add_argument(
            '--aggregate-uuid',
            default=[],
            action='append',
            metavar='<aggregate_uuid>',
            help=argparse.SUPPRESS
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
            self.deprecated_option_warning("--aggregate-uuid", "--member-of")
            filters['member_of'] = 'in:' + ','.join(parsed_args.aggregate_uuid)
        if parsed_args.resource:
            self.check_version(version.ge('1.4'))
            filters['resources'] = ','.join(
                resource.replace('=', ':')
                for resource in parsed_args.resource)
        if 'in_tree' in parsed_args and parsed_args.in_tree:
            self.check_version(version.ge('1.14'))
            filters['in_tree'] = parsed_args.in_tree

        # We need to handle required and forbidden together as they all end up
        # in the same query param on the API.
        # First just check that the requested feature is aligned with the
        # request microversion
        required_traits = []
        if 'required' in parsed_args and parsed_args.required:
            self.check_version(version.ge('1.18'))
            if any(',' in required for required in parsed_args.required):
                self.check_version(version.ge('1.39'))
            required_traits = parsed_args.required

        forbidden_traits = []
        if 'forbidden' in parsed_args and parsed_args.forbidden:
            self.check_version(version.ge('1.22'))
            forbidden_traits = ['!' + f for f in parsed_args.forbidden]

        # Then collect the required query params containing both required and
        # forbidden traits
        filters['required'] = common.get_required_query_param_from_args(
            required_traits, forbidden_traits)

        if 'member_of' in parsed_args and parsed_args.member_of:
            # Fail if --member-of but not high enough microversion.
            self.check_version(version.ge('1.3'))
            filters['member_of'] = [
                'in:' + aggs for aggs in parsed_args.member_of]

        resources = http.request(
            'GET', BASE_URL, params=filters).json()['resource_providers']

        fields = ('uuid', 'name', 'generation')
        if self.compare_version(version.ge('1.14')):
            fields += ('root_provider_uuid', 'parent_provider_uuid')

        rows = (utils.get_dict_properties(r, fields) for r in resources)
        return fields, rows


class ShowResourceProvider(command.ShowOne, version.CheckerMixin):
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

        fields = ('uuid', 'name', 'generation')
        if self.compare_version(version.ge('1.14')):
            fields += ('root_provider_uuid', 'parent_provider_uuid')

        if parsed_args.allocations:
            allocs_url = ALLOCATIONS_URL.format(uuid=parsed_args.uuid)
            allocs = http.request('GET', allocs_url).json()['allocations']
            resource['allocations'] = allocs
            fields += ('allocations',)

        return fields, utils.get_dict_properties(resource, fields)


class SetResourceProvider(command.ShowOne, version.CheckerMixin):
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
        parser.add_argument(
            '--parent-provider',
            metavar='<parent_provider>',
            help='UUID of the parent provider.'
                 ' Can only be set if the resource provider has no parent yet.'
                 ' This option requires at least'
                 ' ``--os-placement-api-version 1.14``.'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL + '/' + parsed_args.uuid
        data = dict(name=parsed_args.name)
        # Not knowing the previous state of a resource the client cannot catch
        # it, but if the user tries to re-parent a resource provider the server
        # returns an easy to understand error:
        #     Unable to save resource provider RP-ID:
        #     Object action update failed because:
        #     re-parenting a provider is not currently allowed.
        #     (HTTP 400)
        if ('parent_provider' in parsed_args
                and parsed_args.parent_provider):
            self.check_version(version.ge('1.14'))
            data['parent_provider_uuid'] = parsed_args.parent_provider
        resource = http.request('PUT', url, json=data).json()

        fields = ('uuid', 'name', 'generation')
        if self.compare_version(version.ge('1.14')):
            fields += ('root_provider_uuid', 'parent_provider_uuid')

        return fields, utils.get_dict_properties(resource, fields)


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
