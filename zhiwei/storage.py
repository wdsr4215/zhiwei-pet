import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def data_dir():
    path = Path(os.environ.get('ZHIWEI_DATA_DIR') or Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ZhiweiPet')
    path.mkdir(parents=True, exist_ok=True)
    return path


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_dir() / 'zhiwei.db'
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                due TEXT NOT NULL, repeat TEXT NOT NULL DEFAULT 'once', status TEXT NOT NULL DEFAULT 'pending');
            CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY, provider TEXT, model TEXT,
                input_tokens INTEGER, output_tokens INTEGER, created TEXT, trace_id TEXT);
        ''')

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value, ensure_ascii=False)))

    def add_note(self, body):
        if not body.strip():
            raise ValueError('请先写下一点内容。')
        with self.db:
            self.db.execute('INSERT INTO notes(body,created) VALUES (?,?)', (body.strip(), datetime.now().isoformat(timespec='seconds')))

    def notes(self, query=''):
        return self.db.execute('SELECT * FROM notes WHERE body LIKE ? ORDER BY id DESC', ('%' + query + '%',)).fetchall()

    def delete_note(self, ident):
        with self.db:
            self.db.execute('DELETE FROM notes WHERE id=?', (ident,))

    def add_reminder(self, title, due, repeat='once', kind='general'):
        if not title.strip() or repeat not in ('once', 'daily', 'weekly'):
            raise ValueError('请填写提醒内容。')
        with self.db:
            cursor = self.db.execute('INSERT INTO reminders(title,due,repeat) VALUES (?,?,?)', (title.strip(), due.isoformat(timespec='seconds'), repeat))
            metadata = self.get('reminder_metadata', {})
            metadata[str(cursor.lastrowid)] = {'anchor': due.isoformat(timespec='seconds'), 'kind': kind}
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('reminder_metadata', json.dumps(metadata, ensure_ascii=False)))

    def reminder_kind(self, ident):
        return self.get('reminder_metadata', {}).get(str(ident), {}).get('kind', 'general')

    def reminders(self):
        return self.db.execute("SELECT * FROM reminders WHERE status != 'done' ORDER BY due").fetchall()

    def due_reminders(self, now=None):
        now = now or datetime.now()
        # Ringing persists until acknowledged, including after an unexpected exit.
        with self.db:
            self.db.execute("UPDATE reminders SET status='ringing' WHERE status='pending' AND due<=?", (now.isoformat(timespec='seconds'),))
        return self.db.execute("SELECT * FROM reminders WHERE status='ringing' ORDER BY due").fetchall()

    def finish_reminder(self, ident, snooze=False, now=None):
        now = now or datetime.now()
        row = self.db.execute('SELECT * FROM reminders WHERE id=?', (ident,)).fetchone()
        if not row or row['status'] == 'done':
            return
        due, state = row['due'], 'done'
        metadata = self.get('reminder_metadata', {})
        meta = metadata.setdefault(str(ident), {'anchor': due, 'kind': 'general'})
        if snooze:
            due, state = (now + timedelta(minutes=5)).isoformat(timespec='seconds'), 'pending'
        elif row['repeat'] != 'once':
            next_due = datetime.fromisoformat(meta['anchor'])
            step = timedelta(days=1 if row['repeat'] == 'daily' else 7)
            while next_due <= now:
                next_due += step
            due, state = next_due.isoformat(timespec='seconds'), 'pending'
        with self.db:
            self.db.execute('UPDATE reminders SET due=?,status=? WHERE id=?', (due, state, ident))
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('reminder_metadata', json.dumps(metadata, ensure_ascii=False)))

    def cancel_reminder(self, ident):
        with self.db:
            self.db.execute("UPDATE reminders SET status='done' WHERE id=?", (ident,))

    def record_usage(self, provider, model, usage, trace_id):
        with self.db:
            self.db.execute('INSERT INTO usage(provider,model,input_tokens,output_tokens,created,trace_id) VALUES (?,?,?,?,?,?)',
                (provider, model, usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0), datetime.now().isoformat(timespec='seconds'), trace_id))

    def usage_summary(self):
        return self.db.execute('SELECT provider,model,COUNT(*) calls,SUM(input_tokens) inputs,SUM(output_tokens) outputs FROM usage GROUP BY provider,model').fetchall()
