import os
from flask import Flask, jsonify
from flask_cors import CORS
import pymysql
import pymysql.cursors

app = Flask(__name__)
CORS(app)

DB_CONFIG = dict(
    host='localhost',
    database='loan_db',
    read_default_file=os.path.expanduser('~/.my.cnf'),
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)

SEGMENT_VIEW = {
    'premium': 'top100_premium',
    'high_risk': 'top100_high_risk',
    'default': 'top100_default',
}


def get_conn():
    return pymysql.connect(**DB_CONFIG)


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/top100/<segment>')
def top100(segment):
    view = SEGMENT_VIEW.get(segment)
    if view is None:
        return jsonify({'error': f'invalid segment: {segment}',
                         'valid': list(SEGMENT_VIEW.keys())}), 400

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {view}")
        rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify(rows)


@app.route('/api/customer/<cust_id>')
def customer_detail(cust_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM customer_score WHERE id=%s", (cust_id,))
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({'error': 'not found'}), 404
    return jsonify(row)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
