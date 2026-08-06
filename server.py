import socket

from engine import Engine

HOST = '127.0.0.1'
PORT = 5432


def handle_client(conn: socket.socket, engine: Engine):
    buffer = b''

    with conn:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break  # client disconnected

            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                command = line.decode('utf-8').strip()

                if not command:
                    continue

                if command == 'quit':
                    conn.sendall(b'bye\n')
                    return

                result = engine.handle_command(command)
                conn.sendall(result.encode('utf-8') + b'\n')


def main():
    engine = Engine()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"listening on {HOST}:{PORT}")

        try:
            while True:
                conn, addr = server_socket.accept()
                print(f"connection from {addr}")
                handle_client(conn, engine)
                print(f"connection closed: {addr}")
        except KeyboardInterrupt:
            pass
        finally:
            engine.flush()


if __name__ == '__main__':
    main()
