==================
User Documentation
==================

This document describes various usage aspects of the *osc-placement* plugin
including but not limited to command line examples and explanations, references
and microversion usage.

The full Placement API reference can be found here:

  https://docs.openstack.org/api-ref/placement/

Microversion usage
------------------

By default, all commands are run with the 1.0 Placement API version. One can
specify a different microversion using the ``--os-placement-api-version``
option, for example::

  $ openstack resource provider aggregate list --os-placement-api-version 1.1 dc43b86a-1261-4f8b-8330-28289fe754e3
  +--------------------------------------+
  | uuid                                 |
  +--------------------------------------+
  | 42896e0d-205d-4fe3-bd1e-100924931787 |
  | 42896e0d-205d-4fe3-bd1e-100924931788 |
  +--------------------------------------+

Alternatively, the ``OS_PLACEMENT_API_VERSION`` environment variable can be
set, for example::

  $ export OS_PLACEMENT_API_VERSION=1.1
  $ openstack resource provider aggregate list dc43b86a-1261-4f8b-8330-28289fe754e3
  +--------------------------------------+
  | uuid                                 |
  +--------------------------------------+
  | 42896e0d-205d-4fe3-bd1e-100924931787 |
  | 42896e0d-205d-4fe3-bd1e-100924931788 |
  +--------------------------------------+

The Placement API version history can be found here:

  https://docs.openstack.org/nova/latest/user/placement.html#rest-api-version-history


Examples
--------

This section provides some common examples for command line usage.

To see the list of available commands for resource providers, run::

  $ openstack resource -h

Resource providers
~~~~~~~~~~~~~~~~~~

Resource provider command subset have a basic CRUD interface.
First, it can be easily created:

.. code-block:: console

  $ p=$(openstack resource provider create Baremetal_node_01 -c uuid -f value)

and renamed:

.. code-block:: console

  $ openstack resource provider set $p --name Baremetal_node_02
  +------------+--------------------------------------+
  | Field      | Value                                |
  +------------+--------------------------------------+
  | uuid       | c33caafc-b59c-46bc-b396-19f117171fec |
  | name       | Baremetal_node_02                    |
  | generation | 0                                    |
  +------------+--------------------------------------+

To get all allocations related to the resource provider use
an ``--allocations`` option for the show command:

.. code-block:: console

  $ openstack resource provider show $p --allocations
  +-------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | Field       | Value                                                                                                                                                                                                                |
  +-------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
  | uuid        | c33caafc-b59c-46bc-b396-19f117171fec                                                                                                                                                                                 |
  | name        | Baremetal_node_02                                                                                                                                                                                                    |
  | generation  | 4                                                                                                                                                                                                                    |
  | allocations | {u'45f4ccf9-36e3-4d13-8c6b-80fd6c66a195': {u'resources': {u'VCPU': 1, u'MEMORY_MB': 512, u'DISK_GB': 10}}, u'2892c6f6-6ee7-4a34-aa20-156b8216de3c': {u'resources': {u'VCPU': 1, u'MEMORY_MB': 512, u'DISK_GB': 10}}} |
  +-------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

A resource provider cannot be deleted if it has allocations,
otherwise just issue:

.. code-block:: console

  $ openstack resource provider delete $p

and it is done.

Allocations
~~~~~~~~~~~

One can set allocations against a resource provider for a given consumer
multiple ways.

When setting allocations against a single resource provider, it is generally
easiest to use something like::

  $ openstack resource provider allocation set 45f4ccf9-36e3-4d13-8c6b-80fd6c66a195 --allocation rp=dc43b86a-1261-4f8b-8330-28289fe754e3,DISK_GB=10,VCPU=1,MEMORY_MB=512
  +--------------------------------------+------------+-------------------------------------------------+
  | resource_provider                    | generation | resources                                       |
  +--------------------------------------+------------+-------------------------------------------------+
  | dc43b86a-1261-4f8b-8330-28289fe754e3 | 9          | {u'VCPU': 1, u'MEMORY_MB': 512, u'DISK_GB': 10} |
  +--------------------------------------+------------+-------------------------------------------------+

Alternatively one can set resource allocations against separate providers::

  $ openstack resource provider allocation set 45f4ccf9-36e3-4d13-8c6b-80fd6c66a195 --allocation rp=dc43b86a-1261-4f8b-8330-28289fe754e3,VCPU=1,MEMORY_MB=512 --allocation rp=762746bc-de0d-47a7-b47a-a14028643663,DISK_GB=10
  +--------------------------------------+------------+---------------------------------+
  | resource_provider                    | generation | resources                       |
  +--------------------------------------+------------+---------------------------------+
  | dc43b86a-1261-4f8b-8330-28289fe754e3 | 9          | {u'VCPU': 1, u'MEMORY_MB': 512} |
  | 762746bc-de0d-47a7-b47a-a14028643663 | 1          | {u'DISK_GB': 10}                |
  +--------------------------------------+------------+---------------------------------+

In this scenario, the consumer, 45f4ccf9-36e3-4d13-8c6b-80fd6c66a195, has
VCPU and MEMORY_MB allocations against one provider,
dc43b86a-1261-4f8b-8330-28289fe754e3, and DISK_GB allocations against another
provider, 762746bc-de0d-47a7-b47a-a14028643663.

.. note:: When setting allocations for a consumer, the command overwrites any
          existing allocations for that consumer. So if you want to add or
          change one resource class allocation but leave other existing
          resource class allocations unchanged, you must also specify those
          other existing unchanged allocations so they are not removed.

Resource classes
~~~~~~~~~~~~~~~~

There is a standard set of resource classes defined within the Placement
service itself. These standard resource classes cannot be modified.

Users can create and delete *custom* resource classes, which have a name
prefix of ``CUSTOM_``.
