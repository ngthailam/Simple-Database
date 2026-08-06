import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lib.query.query_type import QueryType, get_query_type


class QueryTypeEnumTest(unittest.TestCase):
    def test_values(self):
        self.assertEqual(QueryType.SELECT.value, "SELECT")
        self.assertEqual(QueryType.INSERT.value, "INSERT")
        self.assertEqual(QueryType.CREATE_TABLE.value, "CREATE TABLE")
        self.assertEqual(QueryType.DROP_TABLE.value, "DROP TABLE")
        self.assertEqual(QueryType.UPDATE.value, "UPDATE")
        self.assertEqual(QueryType.DELETE.value, "DELETE")

    def test_member_count(self):
        # Guards against someone adding a new QueryType without adding a
        # matching get_query_type test case below.
        self.assertEqual(len(QueryType), 6)


class GetQueryTypeTest(unittest.TestCase):
    def test_select(self):
        self.assertEqual(get_query_type("SELECT * FROM users"), QueryType.SELECT)

    def test_insert(self):
        self.assertEqual(get_query_type("INSERT INTO users VALUES (1, 'a')"), QueryType.INSERT)

    def test_create_table(self):
        self.assertEqual(get_query_type("CREATE TABLE users (id INT)"), QueryType.CREATE_TABLE)

    def test_drop_table(self):
        self.assertEqual(get_query_type("DROP TABLE users"), QueryType.DROP_TABLE)

    def test_update(self):
        self.assertEqual(get_query_type("UPDATE users SET age = 1"), QueryType.UPDATE)

    def test_delete(self):
        self.assertEqual(get_query_type("DELETE FROM users WHERE id = 1"), QueryType.DELETE)

    def test_case_insensitive_lowercase(self):
        self.assertEqual(get_query_type("select * from users"), QueryType.SELECT)

    def test_case_insensitive_mixed_case(self):
        self.assertEqual(get_query_type("SeLeCt * from users"), QueryType.SELECT)

    def test_case_insensitive_multiword(self):
        self.assertEqual(get_query_type("create table users (id int)"), QueryType.CREATE_TABLE)

    def test_leading_whitespace_not_stripped(self):
        # get_query_type only uppercases; it does not strip leading whitespace,
        # so a leading space means no prefix matches.
        self.assertIsNone(get_query_type("  SELECT * FROM users"))

    def test_unrecognized_command_returns_none(self):
        self.assertIsNone(get_query_type("EXPLAIN SELECT * FROM users"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(get_query_type(""))

    def test_prefix_ambiguity_create_before_create_table(self):
        # "CREATE" alone isn't a QueryType, but since CREATE_TABLE's value
        # is "CREATE TABLE", a bare "CREATE" prefix must not falsely match.
        self.assertIsNone(get_query_type("CREATE"))

    def test_drop_table_not_confused_with_drop(self):
        # There's no standalone DROP QueryType, only DROP_TABLE ("DROP TABLE").
        self.assertIsNone(get_query_type("DROP INDEX foo"))


if __name__ == '__main__':
    unittest.main()
