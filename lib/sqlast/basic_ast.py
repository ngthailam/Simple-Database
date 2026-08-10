import re

from lib.query.query_type import QueryType, get_query_type
from lib.query.commands import (
    Command,
    SelectCommand,
    InsertCommand,
    InsertAllCommand,
    CreateTableCommand,
    DropTableCommand,
    UpdateCommand,
    DeleteCommand,
)
from lib.data.schema import ColumnDef, ColumnType


def _parse_value(raw: str):
    raw = raw.strip()
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    return int(raw)


def _parse_where(clause: str) -> tuple[str | None, object | None]:
    # clause looks like "id = 1", already stripped of the WHERE keyword
    clause = clause.strip()
    if not clause:
        return None, None

    match = re.match(r'(\w+)\s*=\s*(.+)', clause)
    if not match:
        raise ValueError(f"invalid WHERE clause: '{clause}'")

    column, raw_value = match.groups()
    return column, _parse_value(raw_value)


def _split_where(remainder: str) -> tuple[str, str | None]:
    # splits "... WHERE col = value" into (before, where_clause_or_None)
    match = re.search(r'\bWHERE\b', remainder, flags=re.IGNORECASE)
    if not match:
        return remainder.strip(), None
    return remainder[:match.start()].strip(), remainder[match.end():].strip()


class BasicAst:
    def parse(self, query_type: QueryType, command_str: str) -> Command:
        command_str = command_str.strip().rstrip(';').strip()
        rest = command_str[len(query_type.value):].strip()

        if query_type == QueryType.SELECT:
            return self._parse_select(rest)
        if query_type == QueryType.INSERT:
            return self._parse_insert(rest)
        if query_type == QueryType.CREATE_TABLE:
            return self._parse_create_table(rest)
        if query_type == QueryType.DROP_TABLE:
            return self._parse_drop_table(rest)
        if query_type == QueryType.UPDATE:
            return self._parse_update(rest)
        if query_type == QueryType.DELETE:
            return self._parse_delete(rest)

        raise ValueError(f"no parser implemented for {query_type}")

    def _parse_select(self, rest: str) -> SelectCommand:
        # rest: "* FROM users WHERE id = 1"  or  "id, email FROM users"
        match = re.match(r'(.+?)\s+FROM\s+(\w+)(.*)', rest, flags=re.IGNORECASE)
        if not match:
            raise ValueError(f"invalid SELECT syntax: '{rest}'")

        columns_part, table, remainder = match.groups()
        columns = [c.strip() for c in columns_part.split(',')]

        _, where_clause = _split_where(remainder)
        where_column, where_value = _parse_where(where_clause or '')

        return SelectCommand(
            table=table,
            columns=columns,
            where_column=where_column,
            where_value=where_value,
        )

    def _parse_insert(self, rest: str) -> InsertCommand | InsertAllCommand:
        # rest: "INTO users VALUES (1, 'alice', 'alice@example.com')"
        #   or: "INTO users VALUES (1, 'alice'), (2, 'bob'), (3, 'carol')"
        match = re.match(r'INTO\s+(\w+)\s+VALUES\s*(.+)', rest, flags=re.IGNORECASE)
        if not match:
            raise ValueError(f"invalid INSERT syntax: '{rest}'")

        table, tuples_part = match.groups()

        row_matches = re.findall(r'\(([^()]*)\)', tuples_part)
        if not row_matches:
            raise ValueError(f"invalid INSERT syntax: '{rest}'")

        rows = [
            [_parse_value(v) for v in row.split(',')]
            for row in row_matches
        ]

        if len(rows) == 1:
            return InsertCommand(table=table, values=rows[0])

        return InsertAllCommand(table=table, rows=rows)

    def _parse_create_table(self, rest: str) -> CreateTableCommand:
        # rest: "users (id INT, username TEXT(32), email TEXT(255))"
        match = re.match(r'(\w+)\s*\((.+)\)', rest)
        if not match:
            raise ValueError(f"invalid CREATE TABLE syntax: '{rest}'")

        table, columns_part = match.groups()
        columns = []
        for col_def in columns_part.split(','):
            columns.append(self._parse_column_def(col_def.strip()))

        return CreateTableCommand(table=table, columns=columns)

    def _parse_column_def(self, col_def: str) -> ColumnDef:
        # "username TEXT(32)"  or  "id INT"  or  "id INT PRIMARY KEY"
        match = re.match(
            r'(\w+)\s+(INT|TEXT)(?:\((\d+)\))?(\s+PRIMARY\s+KEY)?',
            col_def,
            flags=re.IGNORECASE,
        )
        if not match:
            raise ValueError(f"invalid column definition: '{col_def}'")

        name, type_str, size_str, primary_key_str = match.groups()
        col_type = ColumnType[type_str.upper()]
        is_primary = primary_key_str is not None

        if col_type == ColumnType.INT:
            size = 4
        else:
            if size_str is None:
                raise ValueError(f"TEXT column '{name}' requires a size, e.g. TEXT(32)")
            size = int(size_str)
            if is_primary:
                raise ValueError(f"PRIMARY KEY column '{name}' must be INT")

        return ColumnDef(name=name, type=col_type, size=size, is_primary=is_primary)

    def _parse_drop_table(self, rest: str) -> DropTableCommand:
        table = rest.strip()
        if not table:
            raise ValueError("DROP TABLE requires a table name")
        return DropTableCommand(table=table)

    def _parse_update(self, rest: str) -> UpdateCommand:
        # rest: "users SET username = 'bob' WHERE id = 1"
        match = re.match(r'(\w+)\s+SET\s+(.+)', rest, flags=re.IGNORECASE)
        if not match:
            raise ValueError(f"invalid UPDATE syntax: '{rest}'")

        table, remainder = match.groups()
        set_part, where_clause = _split_where(remainder)

        set_match = re.match(r'(\w+)\s*=\s*(.+)', set_part.strip())
        if not set_match:
            raise ValueError(f"invalid SET clause: '{set_part}'")

        set_column, raw_value = set_match.groups()
        where_column, where_value = _parse_where(where_clause or '')

        return UpdateCommand(
            table=table,
            set_column=set_column,
            set_value=_parse_value(raw_value),
            where_column=where_column,
            where_value=where_value,
        )

    def _parse_delete(self, rest: str) -> DeleteCommand:
        # rest: "FROM users WHERE id = 1"
        match = re.match(r'FROM\s+(\w+)(.*)', rest, flags=re.IGNORECASE)
        if not match:
            raise ValueError(f"invalid DELETE syntax: '{rest}'")

        table, remainder = match.groups()
        _, where_clause = _split_where(remainder)
        where_column, where_value = _parse_where(where_clause or '')

        return DeleteCommand(
            table=table,
            where_column=where_column,
            where_value=where_value,
        )
