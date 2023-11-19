from flask import Flask, request, render_template_string, Response, redirect, url_for
from datetime import datetime, timedelta
import sqlite3
import atexit
import threading
import time

# Admin-Anmeldedaten (Ändern Sie diese für Ihre Umgebung)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# Datenbankinitialisierung
def init_db():
    conn = sqlite3.connect('meeting.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS meetings (name TEXT, call_sign TEXT)')
    conn.commit()
    conn.close()

# Nächstes Treffen berechnen
def next_meeting_date():
    today = datetime.now()
    next_friday = today + timedelta((4-today.weekday()) % 7)
    return next_friday.strftime('%d.%m.%Y')

# Datenbank jede Woche freitags um 21 Uhr leeren
def weekly_db_reset():
    while True:
        now = datetime.now()
        next_friday = next_meeting_date()
        next_friday_date = datetime.strptime(next_friday, '%d.%m.%Y')
        reset_time = next_friday_date.replace(hour=21, minute=0, second=0)
        time_to_wait = (reset_time - now).total_seconds()
        time.sleep(max(time_to_wait, 0))
        init_db()

# Prüfen, ob Eintrag bereits existiert
def entry_exists(name, call_sign):
    conn = sqlite3.connect('meeting.db')
    c = conn.cursor()
    c.execute('SELECT * FROM meetings WHERE name = ? OR call_sign = ?', (name, call_sign))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# Eintrag hinzufügen
def add_entry(name, call_sign):
    conn = sqlite3.connect('meeting.db')
    c = conn.cursor()
    c.execute('INSERT INTO meetings (name, call_sign) VALUES (?, ?)', (name, call_sign))
    conn.commit()
    conn.close()

# Eintrag löschen
def delete_entry(name, call_sign):
    conn = sqlite3.connect('meeting.db')
    c = conn.cursor()
    c.execute('DELETE FROM meetings WHERE name = ? OR call_sign = ?', (name, call_sign))
    conn.commit()
    conn.close()

# Teilnehmeranzahl und -liste abfragen
def get_meeting_info():
    conn = sqlite3.connect('meeting.db')
    c = conn.cursor()
    c.execute('SELECT * FROM meetings')
    participants = c.fetchall()
    count = len(participants)
    conn.close()
    return count, participants

# Authentifizierung für Admin-Bereich
def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response(
    'Bitte Anmeldedaten eingeben', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Flask App
app = Flask(__name__)
init_db()

# Hauptseite
@app.route('/', methods=['GET', 'POST'])
def index():
    meeting_message = ""
    error_message = ""
    if request.method == 'POST':
        name = request.form['name']
        call_sign = request.form['call_sign']
        if not name and not call_sign:
            error_message = "Bitte mindestens ein Feld ausfüllen."
        elif entry_exists(name, call_sign):
            return redirect(url_for('confirm_delete', name=name, call_sign=call_sign))
        else:
            add_entry(name, call_sign)

    participant_count, _ = get_meeting_info()
    if participant_count >= 4:
        meeting_message = f"Das Treffen am {next_meeting_date()} findet statt! Es haben sich {participant_count} Personen angemeldet."
    else:
        meeting_message = f"Das Treffen am {next_meeting_date()} findet wegen zu geringer Beteiligung ({participant_count} Personen) nicht statt. Sollte sich die Anzahl auf 4 erhöhen, findet es statt."

return render_template_string("""
    <html>
    <head>
        <style>
            .message { font-weight: bold; }
            .cancelled { color: red; }
        </style>
    </head>
    <body>
        <h2>Treffen am {{ next_meeting }}</h2>
        <p class="message {{ 'cancelled' if participant_count < 4 else '' }}">{{ meeting_message }}</p>
        <p class="message" style="color:red;">{{ error_message }}</p>
        <form method="post">
            <table>
                <tr>
                    <td>Rufzeichen:</td>
                    <td><input type="text" name="call_sign"></td>
                </tr>
                <tr>
                    <td>Name:</td>
                    <td><input type="text" name="name"></td>
                </tr>
                <tr>
                    <td colspan="2"><input type="submit" value="Zusagen/Absagen"></td>
                </tr>
            </table>
        </form>
    </body>
    </html>
""", next_meeting=next_meeting_date(), meeting_message=meeting_message, error_message=error_message)

# Bestätigung zum Löschen
@app.route('/confirm_delete')
def confirm_delete():
    name = request.args.get('name', '')
    call_sign = request.args.get('call_sign', '')
    return render_template_string("""
        <html>
        <body>
            <h2>Eintrag löschen</h2>
            <p>Möchten Sie den Eintrag für {{ name or call_sign }} löschen?</p>
            <form action="{{ url_for('delete') }}" method="post">
                <input type="hidden" name="name" value="{{ name }}">
                <input type="hidden" name="call_sign" value="{{ call_sign }}">
                <input type="submit" value="Ja, löschen">
            </form>
            <a href="{{ url_for('index') }}">Abbrechen</a>
        </body>
        </html>
    """, name=name, call_sign=call_sign)

# Eintrag löschen
@app.route('/delete', methods=['POST'])
def delete():
    name = request.form.get('name', '')
    call_sign = request.form.get('call_sign', '')
    delete_entry(name, call_sign)
    return redirect(url_for('index'))

# Admin Bereich
@app.route('/admin')
@requires_auth
def admin():
    count, participants = get_meeting_info()
    participants_with_index = enumerate(participants, start=1)
    return render_template_string("""
        <html>
        <body>
            <h2>Teilnehmerliste</h2>
            <table border="1">
                <tr>
                    <th>#</th>
                    <th>Rufzeichen</th>
                    <th>Name</th>
                </tr>
                {% for index, (name, call_sign) in participants_with_index %}
                <tr>
                    <td>{{ index }}</td>
                    <td>{{ call_sign }}</td>
                    <td>{{ name }}</td>
                </tr>
                {% endfor %}
            </table>
        </body>
        </html>
    """, participants_with_index=participants_with_index)

# Server starten
if __name__ == '__main__':
    db_reset_thread = threading.Thread(target=weekly_db_reset)
    db_reset_thread.start()
    atexit.register(lambda: db_reset_thread.join())
    app.run(host='0.0.0.0', port=8083, debug=True)
