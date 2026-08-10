from lib.data.database import *
from lib.query.query_validator import *
from lib.query.query_type import *
from lib.binder.binder import *
from lib.sqlast.basic_ast import *
from lib.optimizer.optimizer import *
from lib.utils.constants import DB_FILE


def _format_rows(column_names: list[str], rows: list[tuple]) -> str:
    if not rows:
        return "(0 rows)"

    widths = [len(name) for name in column_names]
    for row in rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(str(value)))

    def format_line(values):
        return " | ".join(str(v).ljust(widths[i]) for i, v in enumerate(values))

    header = format_line(column_names)
    separator = "-+-".join("-" * w for w in widths)
    body = "\n".join(format_line(row) for row in rows)

    return f"{header}\n{separator}\n{body}\n({len(rows)} row{'s' if len(rows) != 1 else ''})"


class Engine:
    def __init__(self, filename: str = DB_FILE):
        pager = Pager(filename)
        catalog = Catalog(pager)
        
        self.db = Database(pager=pager, catalog=catalog)
        self.binder = Binder(catalog=catalog)
        self.query_validator = QueryValidator()
        self.ast = BasicAst()
        self.optimizer = Optimizer(catalog=catalog)

    def handle_command(self, command: str) -> str:
        try:
            # Validate query type
            query_type = get_query_type(command)
            if query_type is None:
                return f"Query type not supported"

            # Validate syntax
            validated = self.query_validator.validate(query_type, command)
            if not validated:
                return f"Invalid command"

            # Parse into an AST
            ast_command = self.ast.parse(query_type=query_type, command_str=command)

            # Validate table/columns referenced by the AST exist
            if not self.binder.resolve(ast_command):
                return f"Invalid table names/cols"

            # Optimize the (now-validated) AST
            ast_command = self.optimizer.optimize(ast_command=ast_command)

            # Run actual query
            data = self.exec_db_by_type(ast_command=ast_command)

            if query_type in (QueryType.CREATE_TABLE, QueryType.INSERT, QueryType.DELETE, QueryType.UPDATE, QueryType.DROP_TABLE):
                self.db.flush()

            if query_type == QueryType.SELECT:
                all_columns = [col.name for col in self.db.catalog.get_table(ast_command.table).columns]
                selected_columns = all_columns if ast_command.columns == ['*'] else ast_command.columns
                return _format_rows(selected_columns, data)

            return str(data)
        except Exception as e:
            return f"error handling command '{command}': {e}"
    
    def exec_db_by_type(self, ast_command: Command):
        match ast_command:
            case SelectCommand():
                return self.db.select_all(
                    table_name=ast_command.table,
                    columns=ast_command.columns,
                    where_column=ast_command.where_column,
                    where_value=ast_command.where_value
                )
            case CreateTableCommand():
                return self.db.create_table(
                    name=ast_command.table,
                    columns=ast_command.columns
                )
            case InsertCommand():
                return self.db.insert(
                    table_name=ast_command.table,
                    values=ast_command.values
                )
            case InsertAllCommand():
                return self.db.insert_all(
                    table_name=ast_command.table,
                    rows=ast_command.rows
                )
            case DeleteCommand():
                return self.db.delete(
                    table_name=ast_command.table,
                    where_column=ast_command.where_column,
                    where_value=ast_command.where_value
                )
            case UpdateCommand():
                return self.db.update(
                    table_name=ast_command.table,
                    set_column=ast_command.set_column,
                    set_value=ast_command.set_value,
                    where_column=ast_command.where_column,
                    where_value=ast_command.where_value
                )
            case DropTableCommand():
                return self.db.delete_table(
                    name=ast_command.table
                )


    def flush(self):
        self.db.close()
