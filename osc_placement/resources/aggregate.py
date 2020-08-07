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
from osc_placement import version


BASE_URL = '/resource_providers/{uuid}/aggregates'
FIELDS = ('uuid',)


class SetAggregate(command.Lister, version.CheckerMixin):

    """Associate a list of aggregates with the resource provider.

    Each request cleans up previously associated resource provider
    aggregates entirely and sets the new ones. Passing empty aggregate
    UUID list will remove all associations with aggregates for the
    particular resource provider.

    This command requires at least ``--os-placement-api-version 1.1``.
    """

    def get_parser(self, prog_name):
        parser = super(SetAggregate, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )

        parser.add_argument(
            '--aggregate',
            metavar='<aggregate_uuid>',
            help='UUID of the aggregate. Specify multiple times to associate '
                 'a resource provider with multiple aggregates.',
            action='append',
            default=[]
        )

        parser.add_argument(
            '--generation',
            metavar='<resource_provider_generation>',
            type=int,
            help='The generation of resource provider. Must match the server-'
                 'side generation of the resource provider or the operation '
                 'will fail.\n\n'
                 'This param requires at least '
                 '``--os-placement-api-version 1.19``.'
        )

        return parser

    @version.check(version.ge('1.1'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL.format(uuid=parsed_args.uuid)
        aggregate = parsed_args.aggregate
        generation = None
        if 'generation' in parsed_args and parsed_args.generation is not None:
            self.check_version(version.ge('1.19'))
            generation = parsed_args.generation

        if self.compare_version(version.lt('1.19')):
            resp = http.request('PUT', url, json=aggregate).json()
        # Microversion 1.19 and beyond a generation argument is
        # required to write aggregates.
        elif generation is not None:
            data = {'aggregates': aggregate,
                    'resource_provider_generation': generation}
            resp = http.request('PUT', url, json=data).json()
        else:
            raise exceptions.CommandError(
                'A generation must be specified.')

        return FIELDS, [[r] for r in resp['aggregates']]


class ListAggregate(command.Lister):

    """List resource provider aggregates.

    This command requires at least ``--os-placement-api-version 1.1``.
    """

    def get_parser(self, prog_name):
        parser = super(ListAggregate, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )

        return parser

    @version.check(version.ge('1.1'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL.format(uuid=parsed_args.uuid)
        resp = http.request('GET', url).json()
        return FIELDS, [[r] for r in resp['aggregates']]
