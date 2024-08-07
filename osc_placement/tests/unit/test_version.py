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

from unittest import mock

import oslotest.base as base

from osc_placement import version


class TestVersion(base.BaseTestCase):
    def test_compare(self):
        self.assertTrue(version._compare('1.0', version.gt('0.9')))
        self.assertTrue(version._compare('1.0', version.ge('0.9')))
        self.assertTrue(version._compare('1.0', version.ge('1.0')))
        self.assertTrue(version._compare('1.0', version.eq('1.0')))
        self.assertTrue(version._compare('1.0', version.le('1.0')))
        self.assertTrue(version._compare('1.0', version.le('1.1')))
        self.assertTrue(version._compare('1.0', version.lt('1.1')))
        self.assertTrue(
            version._compare('1.1', version.gt('1.0'), version.lt('1.2')))
        self.assertTrue(
            version._compare(
                '0.3', version.eq('0.2'), version.eq('0.3'), op=any))

        # Test error message
        msg = 'Operation or argument is not supported with version 1.0; '
        self.assertEqual((msg + 'requires version greater than 1.0'),
                         version._compare('1.0', version.gt('1.0')))
        self.assertEqual((msg + 'requires at least version 1.1'),
                         version._compare('1.0', version.ge('1.1')))
        self.assertEqual((msg + 'requires version 1.1'),
                         version._compare('1.0', version.eq('1.1')))
        self.assertEqual((msg + 'requires at most version 0.9'),
                         version._compare('1.0', version.le('0.9')))
        self.assertEqual((msg + 'requires version less than 0.9'),
                         version._compare('1.0', version.lt('0.9')))

        self.assertRaises(
            ValueError, version._compare, 'abc', version.le('1.1'))
        self.assertRaises(
            ValueError, version._compare, '1.0', version.le('.0'))
        self.assertRaises(
            ValueError, version._compare, '1', version.le('2'))

        ex = self.assertRaises(
            ValueError, version.compare, '1.0', version.ge('1.1'))
        self.assertEqual(
            'Operation or argument is not supported with version 1.0; '
            'requires at least version 1.1', str(ex))
        ex = self.assertRaises(
            ValueError, version.compare, '1.0',
            version.eq('1.1'), version.eq('1.5'), op=any)
        self.assertEqual(
            'Operation or argument is not supported with version 1.0; '
            'requires version 1.1, or requires version 1.5', str(ex))

    def test_compare_with_exc(self):
        self.assertTrue(version.compare('1.05', version.gt('1.4')))
        self.assertFalse(version.compare('1.3', version.gt('1.4'), exc=False))
        self.assertRaisesRegex(
            ValueError,
            'Operation or argument is not supported',
            version.compare, '3.1', version.gt('3.2'))

    def test_check_decorator(self):
        fake_api = mock.Mock()
        fake_api_dec = version.check(version.gt('2.11'))(fake_api)
        obj = mock.Mock()
        obj.app.client_manager.placement.api_version = '2.12'
        fake_api_dec(obj, 1, 2, 3)
        fake_api.assert_called_once_with(obj, 1, 2, 3)
        fake_api.reset_mock()
        obj.app.client_manager.placement.api_version = '2.10'
        self.assertRaisesRegex(
            ValueError,
            'Operation or argument is not supported',
            fake_api_dec,
            obj, 1, 2, 3)
        fake_api.assert_not_called()

    def test_check_mixin(self):

        class Test(version.CheckerMixin):
            app = mock.Mock()
            app.client_manager.placement.api_version = '1.2'

        t = Test()
        self.assertTrue(t.compare_version(version.le('1.3')))
        self.assertTrue(t.check_version(version.ge('1.0')))
        self.assertRaisesRegex(
            ValueError,
            'Operation or argument is not supported',
            t.check_version, version.lt('1.2'))

    def test_max_version_consistency(self):
        def _convert_to_tuple(str):
            return tuple(map(int, str.split(".")))

        versions = [
            _convert_to_tuple(ver) for ver in version.SUPPORTED_MICROVERSIONS]
        max_ver = _convert_to_tuple(version.MAX_VERSION_NO_GAP)

        there_is_gap = False
        for i in range(len(versions) - 1):
            j = i + 1
            if versions[j][1] - versions[i][1] != 1:
                there_is_gap = True
                self.assertEqual(max_ver, versions[i])
                break
        if not there_is_gap:
            self.assertEqual(max_ver, versions[-1])

    def test_get_version_returns_max_no_gap_when_no_session(self):
        obj = mock.Mock()
        obj.app.client_manager.session = None
        ret = version.get_version(obj)
        self.assertEqual(version.MAX_VERSION_NO_GAP, ret)
        obj.app.client_manager.placement.api_version.assert_not_called()
