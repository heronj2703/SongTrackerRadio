from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)

DB_PATH = "songs.db"


# Ensure DB exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            artist TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


# --- Logging function ---
def log_to_db(title, artist):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    now = datetime.now()
    five_min_ago = now - timedelta(minutes=5)

    # Check for duplicate in last 5 minutes
    c.execute("""
        SELECT timestamp FROM songs
        WHERE title = ? AND artist = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (title, artist))

    row = c.fetchone()
    if row:
        last_play = datetime.strptime(row[0], "%d-%m-%Y %H:%M:%S")
        if last_play >= five_min_ago:
            print(f"⏩ Skipped (recently logged): {title}")
            conn.close()
            return

    timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
    c.execute("INSERT INTO songs (title, artist, timestamp) VALUES (?, ?, ?)", (title, artist, timestamp))
    conn.commit()
    conn.close()
    print(f"✅ Logged: {title} at {timestamp}")


# --- Routes ---

@app.route("/")
def home():
    return redirect(url_for('songs'))


@app.route("/songs")
def songs():
    search = request.args.get("search", "").lower()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if search:
        c.execute("""
            SELECT title, artist, COUNT(*) FROM songs
            WHERE lower(title) LIKE ?
            GROUP BY title, artist
            ORDER BY COUNT(*) DESC
        """, (f"%{search}%",))
    else:
        c.execute("""
            SELECT title, artist, COUNT(*) FROM songs
            GROUP BY title, artist
            ORDER BY COUNT(*) DESC
        """)

    results = c.fetchall()
    conn.close()
    return render_template("songs.html", songs=results)


@app.route("/song/<title>")
def song_detail(title):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT timestamp FROM songs WHERE title = ?", (title,))
    rows = c.fetchall()
    conn.close()

    import collections
    day_counts = collections.Counter()
    times_by_day = {day: [] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}

    for (timestamp,) in rows:
        try:
            dt = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S")
            day = dt.strftime("%A")
            time = dt.strftime("%H:%M:%S")
            day_counts[day] += 1
            times_by_day[day].append(time)
        except:
            continue

    # Sort weekdays
    ordered_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    sorted_day_counts = {d: day_counts.get(d, 0) for d in ordered_days}
    sorted_times_by_day = {d: times_by_day.get(d, []) for d in ordered_days}

    return render_template("song_detail.html", title=title,
                           play_counts=sorted_day_counts,
                           times_by_day=sorted_times_by_day)


# Optional: Endpoint to simulate logging a play (useful for testing)
@app.route("/log/<title>/<artist>")
def manual_log(title, artist):
    log_to_db(title, artist)
    return f"Logged: {title} by {artist}"


if __name__ == "__main__":
    app.run(debug=True)
