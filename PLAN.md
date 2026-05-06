# Plan: Instagram Creator Tracker

## Context

Markus möchte einen persönlichen Instagram-Creator-Tracker bauen:
- Beim Surfen auf Instagram interessante Creator mit einem Klick (Bookmarklet) in eine Datenbank speichern
- Jeden Morgen automatisch prüfen, ob diese Creator neue Posts veröffentlicht haben
- Eine Benachrichtigung erhalten (E-Mail-Digest + Web-Dashboard)
- Das System soll von überall erreichbar sein

Das Repo ist komplett leer. Wir bauen alles von Grund auf.

---

## Hosting-Entscheidung (wichtig!)

**IONOS Shared Hosting (normales Webspace-Paket):** ❌ Nicht geeignet für Python-Apps.  
**IONOS VPS/Cloud Server:** ✅ Funktioniert, aber manuelle Serverkonfiguration nötig.  
**Empfehlung: Railway.app** (kostenloser Start, automatisches Deployment per Git-Push, kein Serverbetrieb).

→ **Plan verwendet Railway.** Falls Markus einen IONOS VPS hat, ist das auch möglich - kurze Rückfrage nötig vor dem Deployment-Schritt.

---

## Tech Stack

| Layer | Technologie | Begründung |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async, gut für Scraping, automatische API-Docs |
| Datenbank | SQLite + SQLAlchemy 2.0 | Kein eigener DB-Server nötig, einfaches Backup |
| Migrations | Alembic | Schema-Versionierung |
| Instagram | `instaloader` | Beste Python-Bibliothek für Instagram-Daten |
| Scheduler | APScheduler | Cron-Job im gleichen Prozess, kein Redis/Celery |
| E-Mail | smtplib + Gmail SMTP App Password | Kostenlos, zuverlässig |
| Frontend | Jinja2 + Tailwind CSS (CDN) | Kein Build-Step nötig |
| Deployment | Railway.app + Volume für SQLite | Persistent, kostenlos für kleine Projekte |

---

## Projektstruktur

```
insta-updates/
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
├── railway.toml
├── alembic.ini
├── alembic/versions/001_initial_schema.py
└── app/
    ├── main.py              # FastAPI App + Lifespan (Scheduler start/stop)
    ├── config.py            # Settings via pydantic-settings (.env)
    ├── database.py          # SQLAlchemy Engine + Session + WAL mode
    ├── models.py            # ORM: Creator, Post, CheckLog
    ├── schemas.py           # Pydantic Request/Response Modelle
    ├── scheduler.py         # APScheduler Jobs
    ├── routers/
    │   ├── creators.py      # CRUD Endpoints für Creator
    │   ├── posts.py         # Post-Browser Endpoints
    │   └── jobs.py          # Manual Trigger + Status
    ├── services/
    │   ├── instagram.py     # instaloader Wrapper + Rate-Limit-Handling
    │   ├── checker.py       # Morning-Check Algorithmus
    │   └── notifier.py      # E-Mail Digest senden
    └── templates/
        ├── base.html
        ├── dashboard.html
        ├── creator_detail.html
        └── email/digest.html
```

---

## Datenbankschema (3 Tabellen)

### `creators`
```
id, username (unique), display_name, profile_pic_url, bio,
follower_count, is_active, notes, tags (comma-separated),
added_at, last_checked_at, last_post_shortcode
```
- `last_post_shortcode` = Wasserzeichen: beim Check gehen wir nur bis zu diesem Post zurück

### `posts`
```
id, creator_id (FK), shortcode (unique), post_url,
thumbnail_url, caption, post_type (photo/video/reel/carousel),
like_count, comment_count, posted_at, discovered_at, is_new (bool)
```
- `shortcode` = Instagram Post-ID (der Teil nach `/p/` in der URL) - verhindert Duplikate
- `is_new = True` bis der Digest versendet wurde

### `check_logs`
```
id, creator_id (FK), checked_at, new_posts_found,
status (success/rate_limited/not_found/error), error_message
```

---

## Morning-Check Algorithmus

```
1. Lade alle aktiven Creator, sortiert nach last_checked_at ASC
   (ältester Check kommt zuerst - fairness bei Rate-Limits)

2. FÜR JEDEN Creator:
   a. instaloader.get_new_posts(username, since=last_post_shortcode)
   b. Neue Posts in DB speichern (is_new=True), creator.last_post_shortcode aktualisieren
   c. CheckLog schreiben (status=success)
   d. Warte 3-8 Sekunden (zufällig) → Rate-Limit-Schutz

   BEI RateLimitError: CheckLog(status=rate_limited), STOP (nicht weiter machen)
   BEI ProfileNotFound: creator.is_active=False (Account gelöscht/privat)

3. send_digest_if_needed():
   - Alle Posts WHERE is_new=True abfragen
   - Wenn >0: E-Mail senden, dann alle is_new=False setzen
```

**Wichtig:** Beim ersten Hinzufügen eines Creators wird `last_post_shortcode` auf den aktuell neuesten Post gesetzt - es werden also keine alten Posts nachgefüllt.

---

## Creator hinzufügen (2 Wege)

### 1. Web-Formular auf dem Dashboard
Ein Textfeld für Instagram-URL oder Username. JavaScript extrahiert den Username aus der URL.

### 2. Browser-Bookmarklet (Hauptfeature!)
Ein Link auf dem Dashboard, den man in die Lesezeichenleiste zieht:

```javascript
javascript:(function(){
  var m=location.href.match(/instagram\.com\/([^\/\?#]+)/);
  if(m)fetch('https://DEINE-APP.railway.app/creators',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({username:m[1]})
  }).then(r=>r.json()).then(d=>alert('✓ Gespeichert: '+d.username));
  else alert('Keine Instagram-Profil-Seite!');
})();
```

Die App rendert das Bookmarklet dynamisch mit der eigenen URL - keine manuelle Konfiguration nötig.

---

## E-Mail Digest Format

**Betreff:** `Instagram Updates – 8 neue Posts von 3 Creatoren`

```
[Name @username] – 3 neue Posts
  [Vorschau] Caption-Ausschnitt... → Auf Instagram ansehen
  ...

[Name @username] – 2 neue Posts
  ...

→ Alle auf dem Dashboard: https://deine-app.railway.app
```

Transport: Gmail SMTP mit App-Passwort (Gmail-Account + 2FA + App-Passwort generieren).
Falls kein SMTP konfiguriert: Digest wird ins Log geschrieben (dev-freundlich).

---

## Umgebungsvariablen (.env)

```
DATABASE_URL=sqlite:////app/data/insta_tracker.db
SECRET_KEY=<zufälliger hex string>
INSTAGRAM_USERNAME=<Instagram-Account für Scraping>
INSTAGRAM_PASSWORD=<Passwort>
SMTP_USERNAME=dein@gmail.com
SMTP_PASSWORD=<Gmail App-Passwort>
NOTIFY_EMAIL=dein@email.de
MORNING_CHECK_HOUR=7
TIMEZONE=Europe/Vienna
```

**Empfehlung:** Einen separaten, "leeren" Instagram-Account für das Scraping verwenden - nicht den Haupt-Account.

---

## Implementierungsreihenfolge

### Phase 1 – Foundation
1. `.gitignore`, `.env.example`, `requirements.txt`
2. `app/config.py` (Settings), `app/database.py` (Engine + WAL), `app/models.py`
3. Alembic Setup + erste Migration
4. **Test:** `alembic upgrade head` → DB-Schema prüfen

### Phase 2 – Instagram Service
5. `app/services/instagram.py` – `InstagramService` Klasse
6. **Test:** Interaktiv gegen echten öffentlichen Account testen

### Phase 3 – Web API + Dashboard
7. `app/schemas.py`, `app/routers/creators.py`, `app/routers/posts.py`
8. `app/main.py` – FastAPI App verdrahten
9. Templates: `base.html`, `dashboard.html`, `creator_detail.html`
10. Bookmarklet-Generierung im Dashboard
11. **Test:** `uvicorn app.main:app --reload`, Creator via Formular hinzufügen

### Phase 4 – Checker + Scheduler
12. `app/services/checker.py` – `run_morning_check()` + `send_digest_if_needed()`
13. `app/routers/jobs.py` – manueller Trigger
14. `app/scheduler.py` + in `main.py` einbinden
15. **Test:** `POST /jobs/check-now` → Posts erscheinen in DB

### Phase 5 – Benachrichtigungen
16. `app/services/notifier.py` – SMTP-Versand
17. `app/templates/email/digest.html`
18. **Test:** `POST /jobs/test-notify` → Test-E-Mail ankommt

### Phase 6 – Deployment
19. `Dockerfile` + `railway.toml`
20. Railway-Projekt erstellen, Volume mounten, Env-Vars setzen
21. Git push → Auto-Deploy
22. Bookmarklet in Lesezeichenleiste ziehen, ersten Creator auf Instagram hinzufügen
23. `POST /jobs/check-now` manuell testen, E-Mail empfangen

---

## Kritische Dateien

- `app/services/instagram.py` – Herzstück; Rate-Limit-Handling und Session-Management
- `app/models.py` – Das `shortcode`-Wasserzeichen und `is_new`-Flag sind zentrale Design-Entscheidungen
- `app/services/checker.py` – Der Morning-Check-Algorithmus mit Hard-Stop bei Rate-Limit
- `app/config.py` – Alle konfigurierbaren Parameter

---

## Verifizierung (End-to-End Test)

1. App lokal starten: `uvicorn app.main:app --reload`
2. Dashboard öffnen, Creator über Formular hinzufügen (z.B. `natgeo`)
3. `POST /jobs/check-now` → Neue Posts erscheinen im Dashboard
4. `POST /jobs/test-notify` → Test-E-Mail prüfen
5. Auf Railway deployen, Bookmarklet installieren
6. Auf Instagram surfen, Profil öffnen, Bookmarklet klicken → Alert "Gespeichert"
7. Am nächsten Morgen (07:00 Uhr) E-Mail-Digest empfangen

---

## Geplante Erweiterungen

### Multi-User Support (Stufe 2)

Ziel: Die App an Freunde weitergeben – jeder hat seine eigene Creator-Liste und bekommt seinen eigenen Digest.

**Was sich ändert:**
- Neue Tabelle `users` (id, email, password_hash, created_at, notify_hour, timezone)
- `creators`-Tabelle bekommt eine `user_id`-Spalte (FK auf `users`)
- Login/Registrierung per E-Mail + Passwort (z.B. mit `passlib` für Passwort-Hashing)
- Sessions oder JWT-Token für eingeloggte Benutzer
- Morning-Check läuft pro User und sendet jedem seinen eigenen Digest
- Dashboard zeigt nur die eigenen Creator

**Was gleich bleibt:**
- Gesamte App-Logik (Bookmarklet, Check-Algorithmus, E-Mail-Digest)
- Datenbankstruktur von `posts` und `check_logs` (erben `user_id` über `creator`)

**Datenbankänderung:**
```
# Neue Tabelle
users: id, email, password_hash, display_name, notify_hour, timezone, created_at

# Geänderte Tabelle (eine Spalte dazu)
creators: ... + user_id (FK → users.id)
```

**Hinweis für die Umsetzung:** Das Fundament (Phase 1–6) ist so gebaut, dass `user_id` per Alembic-Migration sauber nachträglich hinzugefügt werden kann, ohne bestehende Daten zu verlieren.
