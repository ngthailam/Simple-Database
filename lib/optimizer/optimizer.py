
class Optimizer:
    def __init__(self, catalog):
        self.catalog = catalog

    # Optimize command by change order of WHERE clause and SELECT clause, or other optimization techniques
    def optimize(self, command) -> str:
        return command