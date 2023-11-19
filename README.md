# Treffen-Verwaltungssystem

Dieses Repository enthält ein Flask-basiertes Webanwendungsskript zur Verwaltung von Amateurfunktreffen. Benutzer können sich für Treffen anmelden oder abmelden, und es gibt einen geschützten Admin-Bereich zur Verwaltung der Teilnehmer.

## Funktionen

- Anmeldung/Absage für Treffen mit Name und/oder Rufzeichen.
- Automatisches Zurücksetzen der Teilnehmerliste jeden Freitag um 21 Uhr.
- Einfache Authentifizierung für den Admin-Bereich.
- Anzeige der Teilnehmerliste und der Gesamtteilnehmerzahl.

## Voraussetzungen

- Python 3.x
- Flask
- SQLite

## Installation

Klonen Sie dieses Repository:

```bash
git clone https://github.com/DO1FFE/Treff-Website
cd Treff-Website
```

Installieren Sie die erforderlichen Pakete:

```bash
pip install -r requirements.txt
```

## Verwendung

Starten Sie die Anwendung:

```bash
python treff.py
```

Die Anwendung ist dann unter `http://localhost:8083` erreichbar.

## Konfiguration

- Ändern Sie bei Bedarf die Admin-Anmeldedaten in `treff.py`.
- Die Datenbank `meeting.db` wird automatisch erstellt und verwaltet.

## Beitrag

Beiträge, Fehlerbehebungen und Feature-Vorschläge sind willkommen. Bitte erstellen Sie ein Issue oder einen Pull-Request.
