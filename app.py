from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
import psycopg2
import csv
from io import StringIO
from collections import defaultdict

# -------------------- CONFIG --------------------
# Production (Render) DB
DATABASE_URL = os.environ.get("DATABASE_URL")

# Fallback for local development
if DATABASE_URL is None:
    DATABASE_URL = "postgresql://postgres:resume123@localhost:5432/hostel_feedback"

app = Flask(__name__, static_folder='static', template_folder='templates')

# -------------------- DB CONNECTION --------------------
def get_db():
    return psycopg2.connect(DATABASE_URL)

# -------------------- DATABASE INIT --------------------
def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    day_of_week TEXT NOT NULL,
                    food_item TEXT NOT NULL,
                    feedback TEXT NOT NULL,
                    comments TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()

# Run table creation on startup
init_db()

# -------------------- ROUTES --------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO feedback
                (name, email, day_of_week, food_item, feedback, comments)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                request.form['name'],
                request.form['email'],
                request.form['day'],
                request.form['food'],
                request.form['feedback'],
                request.form.get('comments')
            ))
        conn.commit()
    return redirect(url_for('thankyou'))

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# -------------------- APIs --------------------
@app.route('/api/summary')
def api_summary():
    conn = get_db()
    cur = conn.cursor()

    # Food-wise summary
    cur.execute("""
        SELECT food_item, feedback, COUNT(*)
        FROM feedback
        GROUP BY food_item, feedback
    """)
    rows = cur.fetchall()

    likes = defaultdict(int)
    dislikes = defaultdict(int)

    for food, fb, count in rows:
        if fb.lower() in ['like', 'good']:
            likes[food] += count
        else:
            dislikes[food] += count

    # Day-wise summary
    cur.execute("""
        SELECT day_of_week, feedback, COUNT(*)
        FROM feedback
        GROUP BY day_of_week, feedback
    """)
    rows = cur.fetchall()

    by_day = defaultdict(lambda: {'Like': 0, 'Dislike': 0})

    for day, fb, count in rows:
        if fb.lower() in ['like', 'good']:
            by_day[day]['Like'] += count
        else:
            by_day[day]['Dislike'] += count

    cur.close()
    conn.close()

    return jsonify({
        'likes': likes,
        'dislikes': dislikes,
        'by_day': by_day
    })

@app.route('/api/records')
def api_records():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, email, day_of_week, food_item, feedback, comments, timestamp
        FROM feedback
        ORDER BY timestamp DESC
    """)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([
        {
            'id': r[0],
            'name': r[1],
            'email': r[2],
            'day_of_week': r[3],
            'food_item': r[4],
            'feedback': r[5],
            'comments': r[6],
            'timestamp': r[7]
        }
        for r in rows
    ])

# -------------------- DELETE RECORD --------------------
@app.route('/api/delete/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback WHERE id = %s", (record_id,))
        conn.commit()
    return jsonify({'status': 'success'})

# -------------------- EXPORT CSV --------------------
@app.route('/export')
def export_csv():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM feedback ORDER BY timestamp DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow([
        'id','name','email','day_of_week',
        'food_item','feedback','comments','timestamp'
    ])
    writer.writerows(rows)

    return send_file(
        StringIO(si.getvalue()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='feedback_export.csv'
    )

# -------------------- RUN --------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
