from lib.query.commands import Command


class Optimizer:
    def __init__(self, catalog):
        self.catalog = catalog

    # Optimize the parsed command, e.g. by reordering WHERE/SELECT clauses,
    # or other optimization techniques
    def optimize(self, ast_command: Command) -> Command:
        return ast_command