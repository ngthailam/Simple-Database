# Binder -> Optimizer

from data.table import *
from validator.query_validator import *

def main():
    table = Table('mydb.db')

    while True:
        line = input('db > ').strip()

        if line == '.exit':
            break

        parts = line.split(' ')
        command = parts[0]

        if command == 'insert':
            try:
                QueryValidator.validateInsert(parts)

                username, email = parts[2], parts[3]
                try:
                    table.insert(int(parts[1]), username, email)
                    print("Executed.")
                except ValueError as e:
                    print(f"Error: {e}")

            except ValueError as e:
                print(f"Validation Error: {e}")

        elif command == 'select':
            for row in table.select_all():
                print(row)

        else:
            print(f"Unrecognized command: '{line}'")

    table.close()

if __name__ == '__main__':
    main()
