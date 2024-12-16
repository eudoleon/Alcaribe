# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo.tests.common import TransactionCase
from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject


class TestBrowsableObject(TransactionCase):
    def test_browsable_object_allowed_values(self):
        """Tests that we cannot assign anything into the values of a browsable object,
        for security concerns.
        In addition, the dict of the browsable object must not be assignable,
        otherwise you could bypass the security mechanism.
        """
        # Values allowed
        for value in [
            123,
            12.3,
            'foo',
            (1, 2, 3, 4),
            [1, 2, 3, 4],
            set([1, 2, 3, 4]),
            {'1234'},
            datetime.datetime.now(),
            datetime.date.today(),
            datetime.time(1, 33, 7),
            self.env.user,
        ]:
            values = {'foo': value}
            obj = BrowsableObject(1, values, self.env)
            obj.dict['bar'] = value
            values['baz'] = value
            self.assertEqual(obj.foo, value)
            self.assertEqual(obj.bar, value)
            self.assertEqual(obj.baz, value)

        # Values forbidden, raising a warning
        for value in [
            str,
            int,
            float,
            bool,
            range,
            "foo".startswith,
            datetime.datetime.strftime,
        ]:
            values = {'foo': value}
            obj = BrowsableObject(1, values, self.env)
            obj.dict['bar'] = value
            values['baz'] = value
            with self.assertRaises(TypeError):
                obj.foo
            with self.assertRaises(TypeError):
                obj.bar
            with self.assertRaises(TypeError):
                obj.baz
