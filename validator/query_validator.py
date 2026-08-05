

class QueryValidator:
    def validateInsert(parts) -> bool:
        if len(parts) != 4:
            raise ValueError("Insert must have 4 parts")
        
        try:
            id_ = int(parts[1])
        except ValueError:
            raise ValueError("Id must be int")

        return True