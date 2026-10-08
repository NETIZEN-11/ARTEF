import sqlite3

conn = sqlite3.connect('redteam_dev.db')
for table in ['guardrails', 'guardrail_findings', 'guardrail_configs', 'review_queue', 'feature_flags', 'audit_logs']:
    cols = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    print(f"--- {table} ---")
    for c in cols:
        print(f"  {c[1]} ({c[2]})")
