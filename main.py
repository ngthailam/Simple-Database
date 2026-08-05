import os
from data.database import Database
from data.schema import ColumnDef, ColumnType

DB_FILE = 'test_e2e.db'

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)  # start clean each run

# --- first session: create tables, insert rows ---
db = Database(DB_FILE)

db.create_table('users', [
    ColumnDef('id', ColumnType.INT, 4),
    ColumnDef('username', ColumnType.TEXT, 32),
    ColumnDef('email', ColumnType.TEXT, 255),
])

db.create_table('posts', [
    ColumnDef('id', ColumnType.INT, 4),
    ColumnDef('title', ColumnType.TEXT, 64),
])

db.insert('users', [1, 'alice', 'alice@example.com'])
db.insert('users', [2, 'bob', 'bob@example.com'])
db.insert('posts', [1, 'hello world'])

print("users (before close):", db.select_all('users'))
print("posts (before close):", db.select_all('posts'))

db.close()

# --- second session: reopen, confirm persistence, insert more ---
db2 = Database(DB_FILE)

print("users (after reopen):", db2.select_all('users'))
print("posts (after reopen):", db2.select_all('posts'))

db2.insert('users', [3, 'carol', 'carol@example.com'])
print("users (after new insert):", db2.select_all('users'))

# --- sanity checks on catalog behavior ---
try:
    db2.create_table('users', [ColumnDef('id', ColumnType.INT, 4)])
    print("ERROR: expected duplicate table creation to raise")
except ValueError as e:
    print("OK, duplicate rejected:", e)

try:
    db2.select_all('does_not_exist')
    print("ERROR: expected missing table to raise")
except ValueError as e:
    print("OK, missing table rejected:", e)

db2.close()