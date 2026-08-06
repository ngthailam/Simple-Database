from abc import ABC, abstractmethod


class TableInterface(ABC):
    @abstractmethod
    def insert(self, values: list):
        ...

    @abstractmethod
    def delete(self, where_column: str | None, where_value: object | None) -> int:
        ...

    @abstractmethod
    def update(
        self,
        set_column: str,
        set_value: object,
        where_column: str | None,
        where_value: object | None,
    ) -> int:
        ...

    @abstractmethod
    def select_all(
        self,
        columns: list[str],
        where_column: str | None,
        where_value: object | None,
    ) -> list[tuple]:
        ...

    @abstractmethod
    def flush_header(self):
        ...
