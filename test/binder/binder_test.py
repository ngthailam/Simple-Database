import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lib.binder.binder import Binder
from lib.data.catalog import Catalog
from lib.data.pager import Pager
from lib.data.schema import ColumnDef, ColumnType
from lib.query.commands import (
    SelectCommand,
    InsertCommand,
    CreateTableCommand,
    DropTableCommand,
    UpdateCommand,
    DeleteCommand,
)


class BinderTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.remove(self.db_path)  # Pager creates the file itself

        self.pager = Pager(self.db_path)
        self.catalog = Catalog(self.pager)
        self.binder = Binder(catalog=self.catalog)

        self.catalog.create_table(
            name='users',
            columns=[
                ColumnDef(name='id', type=ColumnType.INT, size=4),
                ColumnDef(name='username', type=ColumnType.TEXT, size=32),
            ],
            root_page=self.pager.allocate_new_page(),
        )

    def tearDown(self):
        self.pager.close()
        os.remove(self.db_path)

    def test_select_existing_table_and_columns(self):
        command = SelectCommand(
            table='users', columns=['id', 'username'], where_column=None, where_value=None,
        )
        self.assertTrue(self.binder.resolve(command))

    def test_select_star_existing_table(self):
        command = SelectCommand(table='users', columns=['*'], where_column=None, where_value=None)
        self.assertTrue(self.binder.resolve(command))

    def test_select_nonexistent_table(self):
        command = SelectCommand(table='ghost', columns=['*'], where_column=None, where_value=None)
        self.assertFalse(self.binder.resolve(command))

    def test_select_nonexistent_column(self):
        command = SelectCommand(table='users', columns=['ghost_col'], where_column=None, where_value=None)
        self.assertFalse(self.binder.resolve(command))

    def test_select_nonexistent_where_column(self):
        command = SelectCommand(table='users', columns=['id'], where_column='ghost_col', where_value=1)
        self.assertFalse(self.binder.resolve(command))

    def test_select_valid_where_column(self):
        command = SelectCommand(table='users', columns=['id'], where_column='id', where_value=1)
        self.assertTrue(self.binder.resolve(command))

    def test_insert_existing_table(self):
        command = InsertCommand(table='users', values=[1, 'alice'])
        self.assertTrue(self.binder.resolve(command))

    def test_insert_nonexistent_table(self):
        command = InsertCommand(table='ghost', values=[1, 'alice'])
        self.assertFalse(self.binder.resolve(command))

    def test_create_table_does_not_need_to_exist(self):
        # CREATE TABLE defines a new table, so the binder should not reject
        # it just because it isn't in the catalog yet.
        command = CreateTableCommand(
            table='brand_new',
            columns=[ColumnDef(name='id', type=ColumnType.INT, size=4)],
        )
        self.assertTrue(self.binder.resolve(command))

    def test_create_table_ignores_name_clash_with_existing_table(self):
        # Binder only checks existence/columns, not name clashes -
        # that's the catalog's job at actual creation time.
        command = CreateTableCommand(
            table='users',
            columns=[ColumnDef(name='id', type=ColumnType.INT, size=4)],
        )
        self.assertTrue(self.binder.resolve(command))

    def test_drop_table_existing(self):
        command = DropTableCommand(table='users')
        self.assertTrue(self.binder.resolve(command))

    def test_drop_table_nonexistent(self):
        command = DropTableCommand(table='ghost')
        self.assertFalse(self.binder.resolve(command))

    def test_update_valid_set_and_where_column(self):
        command = UpdateCommand(
            table='users', set_column='username', set_value='bob',
            where_column='id', where_value=1,
        )
        self.assertTrue(self.binder.resolve(command))

    def test_update_invalid_set_column(self):
        command = UpdateCommand(
            table='users', set_column='ghost_col', set_value='bob',
            where_column='id', where_value=1,
        )
        self.assertFalse(self.binder.resolve(command))

    def test_update_invalid_where_column(self):
        command = UpdateCommand(
            table='users', set_column='username', set_value='bob',
            where_column='ghost_col', where_value=1,
        )
        self.assertFalse(self.binder.resolve(command))

    def test_update_nonexistent_table(self):
        command = UpdateCommand(
            table='ghost', set_column='username', set_value='bob',
            where_column=None, where_value=None,
        )
        self.assertFalse(self.binder.resolve(command))

    def test_delete_existing_table_no_where(self):
        command = DeleteCommand(table='users', where_column=None, where_value=None)
        self.assertTrue(self.binder.resolve(command))

    def test_delete_valid_where_column(self):
        command = DeleteCommand(table='users', where_column='id', where_value=1)
        self.assertTrue(self.binder.resolve(command))

    def test_delete_invalid_where_column(self):
        command = DeleteCommand(table='users', where_column='ghost_col', where_value=1)
        self.assertFalse(self.binder.resolve(command))

    def test_delete_nonexistent_table(self):
        command = DeleteCommand(table='ghost', where_column=None, where_value=None)
        self.assertFalse(self.binder.resolve(command))


class ResolveTableTest(unittest.TestCase):
    # Direct tests of the lower-level resolve_table used by resolve().

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.remove(self.db_path)

        self.pager = Pager(self.db_path)
        self.catalog = Catalog(self.pager)
        self.binder = Binder(catalog=self.catalog)

        self.catalog.create_table(
            name='products',
            columns=[ColumnDef(name='id', type=ColumnType.INT, size=4)],
            root_page=self.pager.allocate_new_page(),
        )

    def tearDown(self):
        self.pager.close()
        os.remove(self.db_path)

    def test_existing_table_no_columns_requested(self):
        self.assertTrue(self.binder.resolve_table(table_name='products', column_names=[]))

    def test_existing_table_existing_column(self):
        self.assertTrue(self.binder.resolve_table(table_name='products', column_names=['id']))

    def test_existing_table_missing_column(self):
        self.assertFalse(self.binder.resolve_table(table_name='products', column_names=['price']))

    def test_nonexistent_table(self):
        self.assertFalse(self.binder.resolve_table(table_name='ghost', column_names=[]))


if __name__ == '__main__':
    unittest.main()
