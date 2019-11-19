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

from distutils.version import StrictVersion
import operator


SUPPORTED_VERSIONS = [
    '1.0',
    '1.1',
    '1.2',
    '1.3',
    '1.4',
    '1.5',
    '1.6',
    '1.7',
    '1.8',
    '1.9',
    '1.10',
    '1.11',
    '1.12',
    '1.13',  # unused
    '1.14',
    '1.15',  # unused
    '1.16',
    '1.17',
    '1.18',
    '1.19',
    '1.20',  # unused
    '1.21',
    '1.22',
    '1.28',  # Added for provider allocation (un)set (Ussuri)
]


def _op(func, b, msg):
    return lambda a: func(StrictVersion(a), StrictVersion(b)) or msg


def lt(b):
    msg = 'requires version less than %s' % b
    return _op(operator.lt, b, msg)


def le(b):
    msg = 'requires at most version %s' % b
    return _op(operator.le, b, msg)


def eq(b):
    msg = 'requires version %s' % b
    return _op(operator.eq, b, msg)


def ne(b):
    msg = 'can not use version %s' % b
    return _op(operator.ne, b, msg)


def ge(b):
    msg = 'requires at least version %s' % b
    return _op(operator.ge, b, msg)


def gt(b):
    msg = 'requires version greater than %s' % b
    return _op(operator.gt, b, msg)


def _compare(ver, *predicates, **kwargs):
    func = kwargs.get('op', all)
    if func(p(ver) is True for p in predicates):
        return True
    # construct an error message if the requirement not satisfied
    err_msg = 'Operation or argument is not supported with version %s; ' % ver
    err_detail = [p(ver) for p in predicates if p(ver) is not True]
    logic = ', and ' if func is all else ', or '
    return err_msg + logic.join(err_detail)


def compare(ver, *predicates, **kwargs):
    """Validate version satisfies provided predicates.

    kwargs['exc'] - boolean whether exception should be raised
    kwargs['op'] - (all, any) how predicates should be checked

    Examples:
        compare('1.1', version.gt('1.2'), exc=False) - False
        compare('1.1', version.eq('1.0'), version.eq('1.1'), op=any) - True

    """
    exc = kwargs.get('exc', True)
    result = _compare(ver, *predicates, **kwargs)
    if result is not True:
        if exc:
            raise ValueError(result)
        return False
    return True


def check(*predicates, **check_kwargs):
    """Decorator for command object method.

    See `compare`

    """
    def wrapped(func):
        def inner(self, *args, **kwargs):
            compare(get_version(self), *predicates, **check_kwargs)
            return func(self, *args, **kwargs)
        return inner
    return wrapped


def get_version(obj):
    """Extract version from a command object."""
    try:
        version = obj.app.client_manager.placement.api_version
    except AttributeError:
        # resource does not have api_version attr when docs are generated
        # so let's use the minimal one
        version = SUPPORTED_VERSIONS[0]
    return version


class CheckerMixin(object):
    def check_version(self, *predicates, **kwargs):
        return compare(get_version(self), *predicates, **kwargs)

    def compare_version(self, *predicates, **kwargs):
        return compare(get_version(self), *predicates, exc=False, **kwargs)
