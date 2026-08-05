from engine import Engine


def main():
    engine = Engine()

    while True:
        command = input('db > ').strip()

        if command == 'quit':
            engine.flush()
            break

        result = engine.handle_command(command)
        
        print(result)


if __name__ == '__main__':
    main()
