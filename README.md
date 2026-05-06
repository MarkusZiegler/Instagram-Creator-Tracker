# Instagram Creator Tracker

Persönlicher Tracker für Instagram Creator. Beim Surfen auf Instagram interessante Creator per Bookmarklet speichern – jeden Morgen automatisch prüfen ob sie neue Posts veröffentlicht haben und eine E-Mail-Zusammenfassung erhalten.

---

## Schnellstart (lokal)

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. Konfiguration erstellen
cp .env.example .env
# .env mit Editor öffnen und ausfüllen (siehe Abschnitt Konfiguration)

# 3. Datenbank anlegen
alembic upgrade head

# 4. App starten
uvicorn app.main:app --reload

# → http://localhost:8000
```

---

## Konfiguration (.env)

```env
# Datenbank (für lokale Entwicklung so lassen)
DATABASE_URL=sqlite:///./data/insta_tracker.db

# Security (zufälligen Wert generieren)
SECRET_KEY=python3 -c "import secrets; print(secrets.token_hex(32))"

# Instagram-Zugangsdaten (EMPFEHLUNG: separaten/leeren Account verwenden!)
INSTAGRAM_USERNAME=dein_instagram_username
INSTAGRAM_PASSWORD=dein_instagram_passwort
INSTAGRAM_SESSION_FILE=./data/ig_session

# E-Mail (Gmail mit App-Passwort)
# Gmail → Sicherheit → 2-Schritt-Verifizierung aktivieren → App-Passwörter
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=dein@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Gmail App-Passwort (nicht das normale Passwort!)
NOTIFY_EMAIL=wohin@senden.com

# Zeitplan
MORNING_CHECK_HOUR=7
MORNING_CHECK_MINUTE=0
TIMEZONE=Europe/Vienna

# Rate-Limiting (Sekunden Pause zwischen Creator-Checks)
DELAY_BETWEEN_CREATORS_MIN=3.0
DELAY_BETWEEN_CREATORS_MAX=8.0
MAX_POSTS_PER_CREATOR_PER_CHECK=12
```

---

## Bookmarklet installieren

1. App starten und `http://localhost:8000` (oder deine Live-URL) öffnen
2. Den gelben **"★ Creator speichern"** Button in die Lesezeichenleiste ziehen
3. Auf jedem Instagram-Profil auf das Lesezeichen klicken → Creator ist sofort gespeichert

---

## Deployment auf Railway.app

Railway ist ein Cloud-Hosting-Dienst der die App 24/7 laufen lässt, sodass der morgendliche Check auch funktioniert wenn der PC aus ist.

**Schritt-für-Schritt:**

1. Konto auf [railway.app](https://railway.app) erstellen (kostenloser Start)
2. "New Project → Deploy from GitHub Repo" → `insta-updates` auswählen
3. Ein **Volume** hinzufügen (damit die SQLite-Datenbank nach Deployments erhalten bleibt):
   - Mount Path: `/app/data`
4. Unter "Variables" alle Env-Variablen aus `.env.example` eintragen:
   - `DATABASE_URL=sqlite:////app/data/insta_tracker.db` (**4 Schrägstriche** für absoluten Pfad!)
   - Alle anderen wie in der `.env` (ohne Anführungszeichen)
5. Railway deployt automatisch bei jedem `git push`

**Nach dem Deployment:**
- App-URL von Railway kopieren
- Dashboard öffnen, Bookmarklet neu in Lesezeichenleiste ziehen (mit der richtigen URL)
- `POST /jobs/check-now` im Dashboard testen

---

## Projektstruktur

```
insta-updates/
├── .env.example                  # Vorlage für Konfiguration
├── requirements.txt              # Python-Abhängigkeiten
├── Dockerfile                    # Container-Build
├── railway.toml                  # Railway Deployment-Konfiguration
├── alembic.ini                   # Datenbank-Migrations-Konfiguration
├── alembic/
│   └── versions/
│       └── 001_initial_schema.py # Datenbank-Schema (erste Migration)
└── app/
    ├── main.py                   # FastAPI App + Scheduler-Start
    ├── config.py                 # Alle Einstellungen (liest .env)
    ├── database.py               # SQLAlchemy Engine + Session
    ├── models.py                 # Datenbank-Modelle (Creator, Post, CheckLog)
    ├── schemas.py                # API Request/Response Modelle
    ├── scheduler.py              # APScheduler (täglicher Cron-Job)
    ├── routers/
    │   ├── creators.py           # Creator CRUD + Dashboard
    │   ├── posts.py              # Post-Endpunkte
    │   └── jobs.py               # Manueller Check + Status
    ├── services/
    │   ├── instagram.py          # instaloader Wrapper + Rate-Limit-Schutz
    │   ├── checker.py            # Morning-Check Algorithmus
    │   └── notifier.py           # E-Mail Digest versenden
    └── templates/
        ├── base.html             # Basis-Layout
        ├── dashboard.html        # Hauptseite (Creator-Liste + neue Posts)
        ├── creator_detail.html   # Einzelansicht eines Creators
        └── email/
            └── digest.html       # E-Mail Template
```

---

## Datenbankschema

### `creators` – Gespeicherte Creator
| Feld | Beschreibung |
|---|---|
| `username` | Instagram Username (eindeutig) |
| `display_name` | Anzeigename von Instagram |
| `is_active` | Aktiv/pausiert (false = kein Check) |
| `notes` | Persönliche Notiz |
| `tags` | Komma-getrennte Tags (z.B. "Fotografie,Reisen") |
| `last_checked_at` | Letzter Check-Zeitpunkt |
| `last_post_shortcode` | Letzter bekannter Post (Wasserzeichen für Checks) |

### `posts` – Gefundene Posts
| Feld | Beschreibung |
|---|---|
| `shortcode` | Instagram Post-ID (eindeutig, verhindert Duplikate) |
| `post_url` | Direktlink zum Post |
| `caption` | Bildunterschrift (erste 500 Zeichen) |
| `post_type` | photo / video / reel / carousel |
| `is_new` | `True` bis E-Mail-Digest versendet wurde |

### `check_logs` – Check-Protokoll
| Feld | Beschreibung |
|---|---|
| `status` | success / rate_limited / not_found / error |
| `new_posts_found` | Anzahl neuer Posts in diesem Check |
| `error_message` | Fehlermeldung falls vorhanden |

---

## API Endpunkte

| Method | URL | Beschreibung |
|---|---|---|
| `GET` | `/` | Dashboard (Web-UI) |
| `POST` | `/creators` | Creator hinzufügen (JSON: `{"username": "..."}`) |
| `POST` | `/creators/add-form` | Creator per Web-Formular hinzufügen |
| `GET` | `/creators/{username}` | Creator-Detailseite |
| `PUT` | `/creators/{username}` | Notizen/Tags/Status aktualisieren |
| `DELETE` | `/creators/{username}` | Creator deaktivieren |
| `POST` | `/jobs/check-now` | Alle Creator sofort prüfen |
| `POST` | `/jobs/test-notify` | Test-E-Mail senden |
| `GET` | `/jobs/status` | Letzte Check-Logs anzeigen |
| `GET` | `/health` | Health-Check (für Railway) |
| `GET` | `/docs` | Automatische API-Dokumentation |

---

## Morning-Check Algorithmus

```
07:00 Uhr (täglich, konfigurierbar):

1. Alle aktiven Creator laden, sortiert nach "zuletzt geprüft" (älteste zuerst)
2. Für jeden Creator:
   a. Neue Posts seit letztem bekannten Post holen (instaloader)
   b. Neue Posts in Datenbank speichern (is_new=True)
   c. Check-Log schreiben
   d. 3-8 Sekunden Pause (zufällig) → schützt vor Rate-Limits

   Bei Rate-Limit: STOP (nicht weiter machen, Instagram beruhigen lassen)
   Bei "Profil nicht gefunden": Creator deaktivieren

3. Wenn neue Posts vorhanden: E-Mail-Digest senden
4. Alle gesendeten Posts als "gesehen" markieren (is_new=False)
```

**Wichtig:** Beim ersten Hinzufügen eines Creators wird `last_post_shortcode` auf den aktuell neuesten Post gesetzt – es werden also keine alten Posts rückwirkend angezeigt.

---

## Tech Stack

| Layer | Technologie |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Datenbank | SQLite + SQLAlchemy 2.0 |
| Migrations | Alembic |
| Instagram | instaloader |
| Scheduler | APScheduler (AsyncIOScheduler) |
| E-Mail | smtplib + Gmail SMTP |
| Frontend | Jinja2 Templates + Tailwind CSS (CDN) |
| Deployment | Docker + Railway.app |

---

## Häufige Probleme

**Rate-Limit von Instagram:**
- Einen dedizierten (leeren) Instagram-Account für das Scraping verwenden
- Nicht zu viele Creator auf einmal hinzufügen
- Die Pausen zwischen Checks (`DELAY_BETWEEN_CREATORS_MIN/MAX`) erhöhen

**E-Mails kommen nicht an:**
- Gmail: 2-Faktor-Authentifizierung muss aktiviert sein
- Dann unter "App-Passwörter" ein neues Passwort generieren
- Das generierte Passwort (16 Zeichen) als `SMTP_PASSWORD` eintragen

**Datenbank auf Railway geht nach Deploy verloren:**
- Sicherstellen dass ein Volume mit Mount Path `/app/data` angelegt ist
- `DATABASE_URL` muss 4 Schrägstriche haben: `sqlite:////app/data/...`
