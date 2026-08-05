from enum import Enum

class QueryType(Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    CREATE_TABLE = "CREATE TABLE"
    DROP_TABLE = "DROP TABLE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


def get_query_type(query_str: str) -> QueryType | None:
    query_str = query_str.upper()
    for query_type in QueryType:
        if query_str.startswith(query_type.value):
            return query_type
    return None