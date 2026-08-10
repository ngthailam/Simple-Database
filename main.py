import time

from engine import Engine


def main():
    engine = Engine()

    while True:
        command = input('db > ').strip()

        if command == 'quit':
            engine.flush()
            break

        start = time.perf_counter()
        result = engine.handle_command(command)
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(result)
        print(f"({elapsed_ms:.2f} ms)")


if __name__ == '__main__':
    main()
