import sqlite3
import csv

conn = sqlite3.connect("/home/claude/proj/analytics.db")
cur = conn.cursor()

cur.executescript("""
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS funnel_events;
DROP TABLE IF EXISTS activity_log;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    channel TEXT,
    city_tier TEXT,
    device TEXT,
    ab_group TEXT,
    install_date TEXT
);

CREATE TABLE funnel_events (
    user_id INTEGER,
    step TEXT,
    event_date TEXT
);

CREATE TABLE activity_log (
    user_id INTEGER,
    activity_date TEXT,
    week_number INTEGER
);
""")

def load_csv(path, table, cols):
    with open(path) as f:
        r = csv.DictReader(f)
        rows = [tuple(row[c] for c in cols) for row in r]
    placeholders = ",".join("?" * len(cols))
    cur.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)

load_csv("/home/claude/proj/data/users.csv", "users", ["user_id", "channel", "city_tier", "device", "ab_group", "install_date"])
load_csv("/home/claude/proj/data/funnel_events.csv", "funnel_events", ["user_id", "step", "event_date"])
load_csv("/home/claude/proj/data/activity_log.csv", "activity_log", ["user_id", "activity_date", "week_number"])

conn.commit()
print("Users:", cur.execute("SELECT COUNT(*) FROM users").fetchone()[0])
print("Funnel events:", cur.execute("SELECT COUNT(*) FROM funnel_events").fetchone()[0])
print("Activity rows:", cur.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0])
conn.close()
