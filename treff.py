from flask import Flask, request, render_template_string, Response, redirect, url_for
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import sqlite3
import atexit
import threading
import time
import pytz
import re

# Admin-Anmeldedaten einlesen aus .pwd Datei
def load_credentials():
    with open('.pwd', 'r') as file:
        lines = file.readlines()
        credentials = {}
        for line in lines:
            key, value = line.strip().split('=')
            credentials[key] = value
        return credentials

credentials = load_credentials()
ADMIN_USERNAME = credentials['ADMIN_USERNAME']
ADMIN_PASSWORD = credentials['ADMIN_PASSWORD']

# Standardmäßige Reset-Zeit (Freitag um 21 Uhr)
RESET_WEEKDAY = 4  # Freitag (Montag=0, Dienstag=1, ..., Sonntag=6)
RESET_HOUR = 22
RESET_MINUTE = 50


# Logger konfigurieren
def setup_logger():
    logger = logging.getLogger('TreffenLogger')
    logger.setLevel(logging.INFO)  # oder DEBUG, WARNING, etc.

    # Log-Rotation einrichten, um zu verhindern, dass die Log-Datei zu groß wird
    handler = RotatingFileHandler('treff.log', maxBytes=10000, backupCount=5)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger

# Logger-Instanz erstellen
logger = setup_logger()

class DatabaseManager:
    def __init__(self, db_name='meeting.db'):
        self.db_name = db_name
        self.conn = None
        self.init_db()

    def get_connection(self):
        if not self.conn:
            self.conn = sqlite3.connect(self.db_name)
        return self.conn

    def close_connection(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_db(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS meetings (name TEXT, call_sign TEXT)')
        conn.commit()

    def reset_db(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM meetings')
        conn.commit()
        logger.info('********* Datenbank zurückgesetzt! *********')

    def add_entry(self, name, call_sign):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('INSERT INTO meetings (name, call_sign) VALUES (?, ?)', (name, call_sign))
        conn.commit()
        logger.info(f'Eintrag hinzugefügt: Rufzeichen: {call_sign}, Name: {name}')

    def delete_entry(self, name, call_sign):
        conn = self.get_connection()
        c = conn.cursor()
        if name and call_sign:
            # Lösche den Eintrag mit dem genauen Namen UND Rufzeichen
            c.execute('DELETE FROM meetings WHERE name = ? AND call_sign = ?', (name, call_sign))
        elif name:
            # Lösche nur auf Basis des Namens, wenn kein Rufzeichen angegeben ist
            c.execute('DELETE FROM meetings WHERE name = ?', (name,))
        elif call_sign:
            # Lösche nur auf Basis des Rufzeichens, wenn kein Name angegeben ist
            c.execute('DELETE FROM meetings WHERE call_sign = ?', (call_sign,))
        conn.commit()
        logger.info(f'Eintrag gelöscht: Rufzeichen: {call_sign}, Name: {name}')

    def entry_exists(self, name, call_sign):
        conn = self.get_connection()
        c = conn.cursor()
        if name and call_sign:
            # Überprüfe, ob ein Eintrag mit genau dem gleichen Namen UND Rufzeichen existiert
            c.execute('SELECT * FROM meetings WHERE name = ? AND call_sign = ?', (name, call_sign))
        elif name:
            # Überprüfe nur den Namen, wenn kein Rufzeichen angegeben ist
            c.execute('SELECT * FROM meetings WHERE name = ?', (name,))
        elif call_sign:
            # Überprüfe nur das Rufzeichen, wenn kein Name angegeben ist
            c.execute('SELECT * FROM meetings WHERE call_sign = ?', (call_sign,))
        else:
            # Keine gültige Eingabe
            return False
            
        return c.fetchone() is not None

    def get_meeting_info(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM meetings')
        participants = c.fetchall()
        return len(participants), participants

db_manager = DatabaseManager()

def get_local_time():
    local_timezone = pytz.timezone('Europe/Berlin')  # Setzen Sie hier Ihre lokale Zeitzone
    return datetime.now(local_timezone)

def next_meeting_date():
    now = get_local_time()
    next_friday = now + timedelta((4 - now.weekday()) % 7)
    if now.weekday() == 4 and now.hour >= 21:  # Wenn heute Freitag nach 21 Uhr ist
        next_friday += timedelta(days=7)  # Nächster Freitag ist in einer Woche
    return next_friday.strftime('%d.%m.%Y')

def validate_input(text):
    # Erlaubt leere Eingaben, da entweder Name oder Rufzeichen ausgefüllt sein können
    if text is None or text.strip() == "":
        return True

    if not re.match(r'^[A-Za-z0-9äöüÄÖÜß\s\-]+$', text):
        return False

    return True

def authenticate():
    return Response(
    'Bitte Anmeldedaten eingeben', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == ADMIN_USERNAME and auth.password == ADMIN_PASSWORD):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def weekly_db_reset():
    logger.info("Reset-Thread gestartet.")
    while True:
        now = get_local_time()
        days_until_reset = (RESET_WEEKDAY - now.weekday()) % 7
        next_reset = now + timedelta(days=days_until_reset)
        next_reset = next_reset.replace(hour=RESET_HOUR, minute=RESET_MINUTE, second=0)

        time_to_wait = (next_reset - now).total_seconds()
        
        logger.info(f"Nächstes Datenbank-Reset geplant für: {next_reset}")

        time.sleep(max(time_to_wait, 0))  # Warte bis zum Reset-Zeitpunkt
        db_manager.reset_db()
        logger.info("Datenbank wurde zurückgesetzt")

def wrap_text(text, line_length=45):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= line_length:
            current_line += (word + " ")
        else:
            lines.append(current_line)
            current_line = word + " "

    lines.append(current_line)  # Füge den letzten Textzeile hinzu
    return "<br>".join(lines).strip()

def is_submission_allowed():
    local_time = get_local_time()
    if local_time.weekday() < 3 or (local_time.weekday() == 3 and local_time.hour < 15):
        return True
    elif local_time.weekday() == 4 and local_time.hour >= 21:  # Freitag nach 21 Uhr
        return True
    return False

treff = Flask(__name__)

@treff.route('/', methods=['GET', 'POST'])
def index():
    meeting_message = ""
    error_message = ""
    participant_count = 0

    if request.method == 'POST':
        name = request.form['name']
        call_sign = request.form['call_sign']

        if not validate_input(name) or not validate_input(call_sign):
            error_message = "Ungültige Eingabe. Bitte nur Buchstaben, Zahlen und Bindestriche verwenden."
        elif not name and not call_sign:
            error_message = "Bitte mindestens ein Feld ausfüllen."
        elif db_manager.entry_exists(name, call_sign):
            return redirect(url_for('confirm_delete', name=name, call_sign=call_sign))
        else:
            db_manager.add_entry(name, call_sign)

    participant_count, _ = db_manager.get_meeting_info()
    if participant_count >= 4:
        meeting_message = f"Das Treffen am {next_meeting_date()} findet statt! Es haben sich {participant_count} Personen angemeldet."
    else:
        meeting_message = f"Das Treffen am {next_meeting_date()} findet wegen zu geringer Beteiligung ({participant_count} Personen) nicht statt. Sollte sich die Anzahl auf 4 erhöhen, findet es statt."
    
    wrapped_meeting_message = wrap_text(meeting_message)
    submission_allowed = is_submission_allowed()
    
    return render_template_string("""
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .cancelled { color: red; }
                @media only screen and (max-width: 600px) {
                    body { font-size: 20px; } /* Größere Schrift für mobile Geräte */
                    .message { white-space: normal; }
                }
            </style>
        </head>
        <body>
            <h2>Das nächste L11 Clubtreffen ist am Freitag, {{ next_meeting }}</h2>
            <h3>Hier kannst du dich dafür bis Donnerstag um 15Uhr anmelden.</h3>
            <h4>Bitte Freitags nachschauen, ob es stattfindet!!!</h4>
            <p class="message {{ 'cancelled' if participant_count < 4 else '' }}">{{ meeting_message|safe }}</p>
            <p class="message" style="color:red;">{{ error_message }}</p>
            <form method="post">
                <table>
                    <tr>
                        <td>Rufzeichen:</td>
                        <td><input type="text" name="call_sign" {{ 'disabled' if not submission_allowed }}></td>
                    </tr>
                    <tr>
                        <td>Name:</td>
                        <td><input type="text" name="name" {{ 'disabled' if not submission_allowed }}></td>
                    </tr>
                    <tr>
                    <td colspan="2">&nbsp</td>
                    </tr>
                    <tr>
                        <td colspan="2"><input type="submit" value="Zusagen/Absagen" {{ 'disabled' if not submission_allowed }}></td>
                    </tr>
                </table>
            </form>
        </body>
        </html>
    """, submission_allowed=submission_allowed, next_meeting=next_meeting_date(), meeting_message=wrapped_meeting_message, error_message=error_message, participant_count=participant_count)

@treff.route('/confirm_delete')
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

@treff.route('/delete', methods=['POST'])
def delete():
    name = request.form.get('name', '')
    call_sign = request.form.get('call_sign', '')
    db_manager.delete_entry(name, call_sign)
    return redirect(url_for('index'))

@treff.route('/admin')
@requires_auth
def admin():
    count, participants = db_manager.get_meeting_info()
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
            <br><br>
            <a href="{{ url_for('index') }}">Hauptseite</a>
        </body>
        </html>
    """, participants_with_index=participants_with_index)

if __name__ == '__main__':
    logger.info("Hauptprogramm gestartet, starte den Reset-Thread.")
    db_reset_thread = threading.Thread(target=weekly_db_reset)
    db_reset_thread.start()
    atexit.register(lambda: db_reset_thread.join())
    treff.run(host='0.0.0.0', port=8083, debug=True)
