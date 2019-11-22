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
import collections

from osc_lib.command import command
from osc_lib import exceptions

from osc_placement import version


BASE_URL = '/allocation_candidates'


class GroupAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        group, = values
        namespace._current_group = group
        groups = namespace.__dict__.setdefault('groups', {})
        groups[group] = collections.defaultdict(list)


class AppendToGroup(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, '_current_group', None) is None:
            groups = namespace.__dict__.setdefault('groups', {})
            namespace._current_group = ''
            groups[''] = collections.defaultdict(list)
        namespace.groups[namespace._current_group][self.dest].append(values)


class ListAllocationCandidate(command.Lister, version.CheckerMixin):

    """List allocation candidates.

    Returns a representation of a collection of allocation requests and
    resource provider summaries. Each allocation request has information
    to issue an ``openstack resource provider allocation set`` request to claim
    resources against a related set of resource providers.

    As several allocation requests are available its necessary to select one.
    To make a decision, resource provider summaries are provided with the
    inventory/capacity information.

    For example::

      $ export OS_PLACEMENT_API_VERSION=1.10
      $ openstack allocation candidate list --resource VCPU=1
      +---+------------+-------------------------+-------------------------+
      | # | allocation | resource provider       | inventory used/capacity |
      +---+------------+-------------------------+-------------------------+
      | 1 | VCPU=1     | 66bcaca9-9263-45b1-a569 | VCPU=0/128              |
      |   |            | -ea708ff7a968           |                         |
      +---+------------+-------------------------+-------------------------+

    In this case, the user is looking for resource providers that can have
    capacity to allocate 1 ``VCPU`` resource class. There is one resource
    provider that can serve that allocation request and that resource providers
    current ``VCPU`` inventory used is 0 and available capacity is 128.

    This command requires at least ``--os-placement-api-version 1.10``.
    """

    def get_parser(self, prog_name):
        parser = super(ListAllocationCandidate, self).get_parser(prog_name)

        parser.add_argument(
            '--resource',
            metavar='<resource_class>=<value>',
            dest='resources',
            action=AppendToGroup,
            help='String indicating an amount of resource of a specified '
                 'class that providers in each allocation request must '
                 'collectively have the capacity and availability to serve. '
                 'Can be specified multiple times per resource class. '
                 'For example: '
                 '``--resource VCPU=4 --resource DISK_GB=64 '
                 '--resource MEMORY_MB=2048``'
        )
        parser.add_argument(
            '--limit',
            metavar='<limit>',
            help='A positive integer to limit '
                 'the maximum number of allocation candidates. '
                 'This option requires at least '
                 '``--os-placement-api-version 1.16``.'
        )
        parser.add_argument(
            '--required',
            metavar='<required>',
            action=AppendToGroup,
            help='A required trait. May be repeated. Allocation candidates '
                 'must collectively contain all of the required traits. '
                 'This option requires at least '
                 '``--os-placement-api-version 1.17``.'
        )
        parser.add_argument(
            '--forbidden',
            metavar='<forbidden>',
            action=AppendToGroup,
            help='A forbidden trait. May be repeated. Returned allocation '
                 'candidates must not contain any of the specified traits. '
                 'This option requires at least '
                 '``--os-placement-api-version 1.22``.'
        )
        # NOTE(tetsuro): --aggregate-uuid is deprecated in Jan 2020 in 1.x
        # release. Do not remove before Jan 2021 and a 2.x release.
        aggregate_group = parser.add_mutually_exclusive_group()
        aggregate_group.add_argument(
            "--member-of",
            action=AppendToGroup,
            metavar='<member_of>',
            help='A list of comma-separated UUIDs of the resource provider '
                 'aggregates. The returned allocation candidates must be '
                 'associated with at least one of the aggregates identified '
                 'by uuid. This param requires at least '
                 '``--os-placement-api-version 1.21`` and can be repeated to '
                 'add(restrict) the condition with '
                 '``--os-placement-api-version 1.24`` or greater. '
                 'For example, to get candidates in either of agg1 or agg2 '
                 'and definitely in agg3, specify:\n\n'
                 '``--member_of <agg1>,<agg2> --member_of <agg3>``'
        )
        aggregate_group.add_argument(
            '--aggregate-uuid',
            action=AppendToGroup,
            metavar='<aggregate_uuid>',
            help=argparse.SUPPRESS
        )
        parser.add_argument(
            '--group',
            action=GroupAction,
            metavar='<group>',
            help='An integer to group granular requests. If specified, '
                 'following given options of resources, required/forbidden '
                 'traits, and aggregate are associated to that group and will '
                 'be satisfied by the same resource provider in the response. '
                 'Can be repeated to get candidates from multiple resource '
                 'providers in the same resource provider tree. '
                 'For example, ``--group 1 --resource VCPU=3 --required '
                 'HW_CPU_X86_AVX --group 2 --resource VCPU=2 --required '
                 'HW_CPU_X86_SSE`` will provide candidates where three VCPUs '
                 'comes from a provider with ``HW_CPU_X86_AVX`` trait and '
                 'two VCPUs from a provider with ``HW_CPU_X86_SSE`` trait. '
                 'This option requires at least '
                 '``--os-placement-api-version 1.25`` or greater, but to have '
                 'placement server be aware of resource provider tree, use '
                 '``--os-placement-api-version 1.29`` or greater.'
        )
        parser.add_argument(
            '--group-policy',
            choices=['none', 'isolate'],
            default='none',
            metavar='<group_policy>',
            help='This indicates how the groups should interact when multiple '
                 'groups are supplied. With group_policy=none (default), '
                 'separate groups may or may not be satisfied by the same '
                 'provider. With group_policy=isolate, numbered groups are '
                 'guaranteed to be satisfied by different providers.'
        )

        return parser

    @version.check(version.ge('1.10'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        params = {}
        if 'groups' not in parsed_args:
            raise exceptions.CommandError(
                'At least one --resource must be specified.')

        if 'limit' in parsed_args and parsed_args.limit:
            # Fail if --limit but not high enough microversion.
            self.check_version(version.ge('1.16'))
            params['limit'] = int(parsed_args.limit)

        if any(parsed_args.groups):
            self.check_version(version.ge('1.25'))
            params['group_policy'] = parsed_args.group_policy

        for suffix, group in parsed_args.groups.items():
            def _get_key(name):
                return name + suffix

            if 'resources' not in group:
                raise exceptions.CommandError(
                    '--resources should be provided in group %s', suffix)
            for resource in group['resources']:
                if not len(resource.split('=')) == 2:
                    raise exceptions.CommandError(
                        'Arguments to --resource must be of form '
                        '<resource_class>=<value>')

            params[_get_key('resources')] = ','.join(
                resource.replace('=', ':') for resource in group['resources'])
            if 'required' in group and group['required']:
                # Fail if --required but not high enough microversion.
                self.check_version(version.ge('1.17'))
                params[_get_key('required')] = ','.join(group['required'])
            if 'forbidden' in group and group['forbidden']:
                self.check_version(version.ge('1.22'))
                forbidden_traits = ','.join(
                    ['!' + f for f in group['forbidden']])
                if 'required' in params:
                    params[_get_key('required')] += ',' + forbidden_traits
                else:
                    params[_get_key('required')] = forbidden_traits
            if 'aggregate_uuid' in group and group['aggregate_uuid']:
                # Fail if --aggregate_uuid but not high enough microversion.
                self.check_version(version.ge('1.21'))
                self.deprecated_option_warning(
                    "--aggregate-uuid", "--member-of")
                params[_get_key('member_of')] = 'in:' + ','.join(
                    group['aggregate_uuid'])
            if 'member_of' in group and group['member_of']:
                # Fail if --member-of but not high enough microversion.
                self.check_version(version.ge('1.21'))
                params[_get_key('member_of')] = [
                    'in:' + aggs for aggs in group['member_of']]

        resp = http.request('GET', BASE_URL, params=params).json()

        rp_resources = {}
        include_traits = self.compare_version(version.ge('1.17'))
        if include_traits:
            rp_traits = {}
        for rp_uuid, resources in resp['provider_summaries'].items():
            rp_resources[rp_uuid] = ','.join(
                '%s=%s/%s' % (rc, value['used'], value['capacity'])
                for rc, value in resources['resources'].items())
            if include_traits:
                rp_traits[rp_uuid] = ','.join(resources['traits'])

        rows = []
        if self.compare_version(version.ge('1.12')):
            for i, allocation_req in enumerate(resp['allocation_requests']):
                for rp, resources in allocation_req['allocations'].items():
                    req = ','.join(
                        '%s=%s' % (rc, value)
                        for rc, value in resources['resources'].items())
                    if include_traits:
                        row = [i + 1, req, rp, rp_resources[rp], rp_traits[rp]]
                    else:
                        row = [i + 1, req, rp, rp_resources[rp]]
                    rows.append(row)
        else:
            for i, allocation_req in enumerate(resp['allocation_requests']):
                for allocation in allocation_req['allocations']:
                    rp = allocation['resource_provider']['uuid']
                    req = ','.join(
                        '%s=%s' % (rc, value)
                        for rc, value in allocation['resources'].items())
                    rows.append([i + 1, req, rp, rp_resources[rp]])

        fields = ('#', 'allocation', 'resource provider',
                  'inventory used/capacity')
        if include_traits:
            fields += ('traits',)

        return fields, rows
