#!/usr/bin/env python3
"""
ローカルのSQLite (final-project/local.sqlite) を検査する簡易スクリプト
"""
import os
import sqlite3
from pathlib import Path


def main():
    db_path = Path(__file__).parent / 'local.sqlite'
    print('DB path:', db_path)
    if not db_path.exists():
        print('DB not found')
        return
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    print('Tables:', tables)
    for t in tables:
        print('\n==', t)
        cur.execute(f'PRAGMA table_info({t});')
        for col in cur.fetchall():
            print(col)
        cur.execute(f'SELECT COUNT(*) FROM {t};')
        print('Count:', cur.fetchone()[0])
    conn.close()


if __name__ == '__main__':
    main()
