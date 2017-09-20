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


def _op(func, b):
    return lambda a: func(StrictVersion(a), StrictVersion(b))


def lt(b):
    return _op(operator.lt, b)


def le(b):
    return _op(operator.le, b)


def eq(b):
    return _op(operator.eq, b)


def ne(b):
    return _op(operator.ne, b)


def ge(b):
    return _op(operator.ge, b)


def gt(b):
    return _op(operator.gt, b)


def _compare(ver, *predicates, **kwargs):
    func = kwargs.get('op', all)
    return func(p(ver) for p in predicates)


def compare(ver, *predicates, **kwargs):
    exc = kwargs.get('exc', True)
    if not _compare(ver, *predicates, **kwargs):
        if exc:
            raise ValueError(
                'Operation or argument is not supported with version %s' % ver)
        return False
    return True


def check(*predicates, **check_kwargs):
    def wrapped(func):
        def inner(self, *args, **kwargs):
            version = self.app.client_manager.placement.api_version
            compare(version, *predicates, **check_kwargs)
            return func(self, *args, **kwargs)
        return inner
    return wrapped


class CheckerMixin(object):
    def check_version(self, *predicates, **kwargs):
        version = self.app.client_manager.placement.api_version
        return compare(version, *predicates, **kwargs)

    def compare_version(self, *predicates, **kwargs):
        version = self.app.client_manager.placement.api_version
        return compare(version, *predicates, exc=False, **kwargs)
