# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from . import test_common

class TestMerge(test_common.TestCommon):
    def test_generic_merge(self):
        self._create_rule('x_name', 'exact')

        rec = self._create_record('x_dm_test_model', x_name='toto')
        rec2 = self._create_record('x_dm_test_model', x_name='toto')
        ref = self._create_record('x_dm_test_model_ref', x_name='ref toto', x_test_id=rec2.id)
        self.MyModel.find_duplicates()

        groups = self.env['data_merge.group'].search([('model_id', '=', self.MyModel.id)])
        self.assertEqual(len(groups), 1, 'Should have found 1 group')

        group = groups[0]
        records = group.record_ids
        master_record = records.filtered('is_master')
        other_record = records - master_record

        self.assertEqual(master_record._original_records(), rec, "the 1st record created should be the master")
        self.assertEqual(ref.x_test_id, rec2, "The reference should be to rec2")

        group.merge_records()
        self.assertFalse(other_record.exists(), "record should be unlinked")
        self.assertEqual(ref.x_test_id, rec, "The reference should be to rec")

    def test_generic_insensitive_rule(self):
        self._create_rule('x_name', 'accent')
        for name in ('accentuée', 'accentuee', 'Accentuée', 'Accentué'):
            self._create_record('x_dm_test_model', x_name=name)
        self.MyModel.find_duplicates()

        groups = self.env['data_merge.group'].search([('model_id', '=', self.MyModel.id)])
        self.assertEqual(len(groups), 1, 'Should have found 1 group')
        self.assertEqual(len(groups.record_ids), 3, 'First group must contains three records: ("accentuée", "accentue", "Accentuée")')
        self.assertNotIn('Accentué', groups[0].record_ids.mapped('display_name'), 'Group must not contains "Accentué"')

    def test_mixed_case_fields(self):
        '''
            Tests mixed case fields query on _update_foreign_keys
        '''
        self.DMTestModel3 = self.env['ir.model'].create({
            'name': 'Test Model 3',
            'model': 'x_dm_test_model3',
            'field_id': [
                (0, 0, {'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
                (
                0, 0, {'name': 'x_studio_many2one_field_nKSEu', 'ttype': 'many2one', 'field_description': 'studio test',
                       'relation': 'x_dm_test_model', 'index': True}),
            ]
        })
        self.test_generic_merge()

    def test_cleanup_deleted_records(self):
        self._create_rule('x_name', 'exact')

        self._create_record('x_dm_test_model', x_name='toto')
        rec2 = self._create_record('x_dm_test_model', x_name='toto')
        rec3 = self._create_record('x_dm_test_model', x_name='toto')

        self.MyModel.find_duplicates()

        group = self.env['data_merge.group'].search([('model_id', '=', self.MyModel.id)])

        rec2.unlink()
        self.assertEqual(len(group.record_ids), 3, 'The group must contains 3 records')

        group._cleanup()
        self.assertEqual(len(group.record_ids), 2, 'The group must contains 2 records')

        rec3.unlink()
        group._cleanup()
        self.assertFalse(group.record_ids, 'The group should not contains any records')
