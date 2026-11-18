"""Wedding RSVP application. Production entry point: wsgi.py."""
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, request, session, render_template, jsonify, redirect, url_for, Response, g
from werkzeug.security import check_password_hash

ROOT = Path(__file__).resolve().parent
SCHEMA = '''
CREATE TABLE IF NOT EXISTS rsvps (
 id INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, payload_hash TEXT NOT NULL,
 name TEXT NOT NULL, side TEXT, attending INTEGER NOT NULL, guests INTEGER NOT NULL,
 message TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS limits (key TEXT PRIMARY KEY, start REAL NOT NULL, count INTEGER NOT NULL);
'''

def create_app(test_config=None):
    app = Flask(__name__)
    config_path = ROOT / 'instance' / 'config.json'
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    app.config.update(SECRET_KEY=config.get('secret_key'), ADMIN_HASH=config.get('admin_hash'),
        DATABASE=str(ROOT / 'instance' / 'rsvp.sqlite3'), MAX_CONTENT_LENGTH=16384,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('LOCAL_HTTP') != '1',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    if test_config:
        app.config.update(test_config)
    if not app.config['SECRET_KEY'] or not app.config['ADMIN_HASH']:
        raise RuntimeError('Run python setup_admin.py first to create your private configuration.')
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.executescript(SCHEMA)
    os.chmod(app.config['DATABASE'], 0o600)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'], timeout=15)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(error):
        connection = g.pop('db', None)
        if connection:
            connection.close()

    def csrf_token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    app.jinja_env.globals['csrf_token'] = csrf_token

    @app.before_request
    def csrf_check():
        if request.method == 'POST':
            provided = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
            if not session.get('csrf') or not hmac.compare_digest(provided.encode(), session['csrf'].encode()):
                if request.path.startswith('/api/'):
                    return jsonify(error='Your session expired. Refresh this page and try again.'), 403
                return 'Your session expired. Refresh the page and try again.', 403

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    def limited(category, maximum, window):
        identity = request.remote_addr or 'unknown'
        key = hmac.new(app.secret_key.encode(), (category + identity).encode(), hashlib.sha256).hexdigest()
        now = time.time()
        connection = db()
        connection.execute('BEGIN IMMEDIATE')
        row = connection.execute('SELECT * FROM limits WHERE key=?', (key,)).fetchone()
        if row and now - row['start'] < window:
            count = row['count'] + 1
            connection.execute('UPDATE limits SET count=? WHERE key=?', (count, key))
        else:
            count = 1
            connection.execute('INSERT OR REPLACE INTO limits VALUES (?,?,?)', (key, now, count))
        connection.execute('DELETE FROM limits WHERE start < ?', (now - 86400,))
        connection.commit()
        return count > maximum

    def admin_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            fingerprint = hashlib.sha256(app.config['ADMIN_HASH'].encode()).hexdigest()
            if session.get('admin') != fingerprint:
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return wrapped

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.post('/api/rsvp')
    def rsvp():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error='Send a valid RSVP.'), 400
        name, message = data.get('name'), data.get('message', '')
        side, attending, guests = data.get('guestSide'), data.get('attending'), data.get('guests')
        request_id = data.get('requestId')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            return jsonify(error='Please enter a name of 1–120 characters.'), 400
        if not isinstance(message, str) or len(message) > 2000:
            return jsonify(error='Please keep your message within 2,000 characters.'), 400
        if side not in (None, '', 'bride', 'groom', 'both') or type(attending) is not bool:
            return jsonify(error='Please choose whether you are attending.'), 400
        if type(guests) is not int or (attending and not 1 <= guests <= 4) or (not attending and guests != 0):
            return jsonify(error='Guest count must be 1–4 when attending, or 0 when declining.'), 400
        if not isinstance(request_id, str) or not 20 <= len(request_id) <= 100 or not all(c.isalnum() or c in '-_' for c in request_id):
            return jsonify(error='Invalid submission identifier. Refresh and retry.'), 400
        values = [name.strip(), side or None, attending, guests, message.strip()]
        digest = hashlib.sha256(json.dumps(values).encode()).hexdigest()
        scoped_id = hashlib.sha256((csrf_token() + request_id).encode()).hexdigest()
        prior = db().execute('SELECT payload_hash FROM rsvps WHERE request_id=?', (scoped_id,)).fetchone()
        if prior:
            if prior['payload_hash'] == digest:
                return jsonify(ok=True)
            return jsonify(error='This reply was already received. Refresh to send a new response.'), 409
        if limited('rsvp', 30, 3600):
            return jsonify(error='Too many replies. Please try again later.'), 429
        try:
            db().execute('INSERT INTO rsvps (request_id,payload_hash,name,side,attending,guests,message,created_at) VALUES (?,?,?,?,?,?,?,?)',
                (scoped_id, digest, *values, datetime.now(timezone.utc).isoformat(timespec='seconds')))
            db().commit()
        except sqlite3.IntegrityError:
            db().rollback()
            prior = db().execute('SELECT payload_hash FROM rsvps WHERE request_id=?', (scoped_id,)).fetchone()
            if not prior or prior['payload_hash'] != digest:
                return jsonify(error='Submission conflict. Refresh and try again.'), 409
        return jsonify(ok=True), 201

    @app.route('/admin/login', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            if limited('login', 10, 900):
                return render_template('login.html', error='Too many attempts. Try again in 15 minutes.'), 429
            if check_password_hash(app.config['ADMIN_HASH'], request.form.get('password', '')):
                session.clear()
                session.permanent = True
                session['admin'] = hashlib.sha256(app.config['ADMIN_HASH'].encode()).hexdigest()
                return redirect(url_for('admin'))
            error = 'Incorrect password.'
        return render_template('login.html', error=error)

    @app.post('/admin/logout')
    @admin_required
    def logout():
        session.clear()
        return redirect(url_for('login'))

    def filtered_rows():
        status, side = request.args.get('status', ''), request.args.get('side', '')
        clauses, params = [], []
        if status in ('yes', 'no'):
            clauses.append('attending=?'); params.append(int(status == 'yes'))
        if side in ('bride', 'groom', 'both'):
            clauses.append('side=?'); params.append(side)
        sql = 'SELECT * FROM rsvps' + (' WHERE ' + ' AND '.join(clauses) if clauses else '')
        return db().execute(sql + ' ORDER BY id DESC', params).fetchall()

    @app.get('/admin')
    @admin_required
    def admin():
        rows = filtered_rows()
        return render_template('admin.html', rows=rows, people=sum(r['guests'] for r in rows),
            yes=sum(r['attending'] for r in rows))

    @app.get('/admin/export.csv')
    @admin_required
    def export():
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(['Name', 'Side', 'Attending', 'Guests (including respondent)', 'Message', 'Submitted (UTC)'])
        def safe(value):
            value = str(value or '')
            return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')) else value
        for r in filtered_rows():
            writer.writerow([safe(r['name']), r['side'] or '', 'Yes' if r['attending'] else 'No', r['guests'], safe(r['message']), r['created_at']])
        return Response('\ufeff' + stream.getvalue(), mimetype='text/csv', headers={'Content-Disposition':'attachment; filename=wedding-rsvps.csv'})

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error='Your submission is too large.'), 413

    @app.errorhandler(500)
    def server_error(error):
        if request.path.startswith('/api/'):
            return jsonify(error='We could not save your reply. Please try again.'), 500
        return 'Something went wrong. Please try again later.', 500

    return app
