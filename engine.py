from data.database import *
from query.query_validator import *
from query.query_type import *
from binder.binder import *
from sqlast.basic_ast import *

DB_FILE = 'test_e2e.db'


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
            
            # Validate if table/col exists
            table_name = "s"
            col_names = []
            binder_resolved = self.binder.resolve_table(table_name=table_name, column_names=col_names)
            if not binder_resolved:
                return f"Invalid table names/cols"
            
            # TODO: Optimizer to optimize
            
            # Run actual query
            data = self.exec_db_by_type(query_type=query_type, command=command)

            if query_type in (QueryType.CREATE_TABLE, QueryType.INSERT, QueryType.DELETE):
                self.db.flush()

            return str(data)
        except Exception as e:
            return f"error handling command '{command}': {e}"
    
    def exec_db_by_type(self, query_type: QueryType, command: str):
        ast_command = self.ast.parse(query_type=query_type, command_str=command)
        match ast_command:
            case SelectCommand():
                return self.db.select_all(
                    table_name=ast_command.table
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
            case DeleteCommand():
                return self.db.delete_table(
                    name=ast_command.table
                ) 
            

    def flush(self):
        self.db.close()
