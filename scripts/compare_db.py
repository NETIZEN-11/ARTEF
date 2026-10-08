import sqlite3

c1 = sqlite3.connect('redteam_dev.db')
c2 = sqlite3.connect('backend/redteam_dev.db')
tables = [r[0] for r in c1.execute("SELECT name FROM sqlite_master WHERE type='table'")]
for t in tables:
    if not t.startswith('sqlite'):
        n1 = c1.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        n2 = c2.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        if n1 > 0 or n2 > 0:
            print(f"{t}: root={n1}, backend={n2}")
