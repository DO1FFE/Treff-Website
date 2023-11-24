# Treffen-Verwaltungssystem

## Überblick
Diese Flask-Anwendung dient zur Organisation von Treffen. Benutzer können ihre Teilnahme an einem Treffen mit Namen und Rufzeichen bestätigen oder absagen. Die Anwendung bietet auch eine Administrationsseite zur Teilnehmerverwaltung.

## Funktionen
- Teilnehmer können ihre Teilnahme an einem Treffen bestätigen oder absagen.
- Administratoren können Teilnehmerlisten einsehen und verwalten.
- Automatisches Zurücksetzen der Teilnehmerliste jede Woche.
- Einfache Authentifizierung für den Administrationsbereich.

## Voraussetzungen
Stellen Sie sicher, dass Python 3 und pip auf Ihrem System installiert sind.

## Installation
1. Klone dieses Repository:
   ```
   git clone https://github.com/DO1FFE/Treff-Website
   ```
2. Installieren Sie die erforderlichen Pakete:
   ```
   pip install -r requirements.txt
   ```

## Ausführung
Starten Sie die Anwendung mit dem folgenden Befehl:
```
python treff.py
```

Die Anwendung läuft dann auf `http://localhost:8083/`.

## Konfiguration
- Admin-Anmeldedaten: Speichern Sie Ihre Anmeldedaten in einer `.pwd`-Datei im Format:
  ```
  ADMIN_USERNAME=IhrBenutzername
  ADMIN_PASSWORD=IhrPasswort
  ```
- Datenbank: Die Anwendung verwendet eine SQLite-Datenbank zur Speicherung der Teilnehmerdaten.

## Beitrag
Beiträge sind willkommen. Bitte erstellen Sie einen Pull Request oder ein Issue, wenn Sie Änderungen oder Verbesserungen vorschlagen möchten.
