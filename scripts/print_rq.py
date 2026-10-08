import sqlite3
conn = sqlite3.connect('redteam_dev.db')
print(conn.execute("SELECT sql FROM sqlite_master WHERE name='review_queue'").fetchone()[0])
