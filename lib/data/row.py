import struct

from lib.utils.constants import ROW_FORMAT, ROW_SIZE

def serialize_row(id: int, username: str, email: str) -> bytes:
    username_bytes = username.encode('utf-8')
    email_bytes = email.encode('utf-8')
    if len(username_bytes) > 32:
        raise ValueError("Username too long")
    if len(email_bytes) > 255:
        raise ValueError("Email too long")
    return struct.pack(ROW_FORMAT, id, username_bytes, email_bytes)

def deserialize_row(data: bytes) -> tuple[int, str, str]:
    id_, username_raw, email_raw = struct.unpack(ROW_FORMAT, data)
    username = username_raw.rstrip(b'\x00').decode('utf-8')
    email = email_raw.rstrip(b'\x00').decode('utf-8')
    return id_, username, email

def write_row_to_file(filename: str, offset: int, id: int, username: str, email: str):
    data = serialize_row(id, username, email)
    with open(filename, 'r+b') as f:
        f.seek(offset)
        f.write(data)

def read_row_from_file(filename: str, offset: int) -> tuple[int, str, str]:
    with open(filename, 'rb') as f:
        f.seek(offset)
        data = f.read(ROW_SIZE)
        return deserialize_row(data)