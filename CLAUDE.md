# Instagram Creator Tracker — Projektstatus

## Was ist das?
Persönlicher Instagram-Tracker für Markus Ziegler. Beim Surfen auf Instagram
interessante Creator per Bookmarklet speichern, täglich automatisch auf neue
Posts prüfen, E-Mail-Digest empfangen.

## Aktueller Stand (Mai 2026)
**Lokal läuft alles.** Die App funktioniert auf Markus' Windows-PC.

### Was funktioniert
- Dashboard unter http://localhost:8000
- Bookmarklet: auf Instagram-Profil klicken → Creator wird sofort gespeichert
- Manueller Check ("Jetzt prüfen") findet neue Posts
- E-Mail-Digest wird an instagram.creator.tracker@gmail.com gesendet
  (von dort Weiterleitung zu Markus' persönlicher E-Mail)
- "Als gelesen markieren" (einzeln ✓ oder alle auf einmal)
- Täglicher automatischer Check um 07:00 Uhr (APScheduler)

### Technische Entscheidungen
- **instaloader wird NUR noch für Session-Management verwendet** (Cookie laden)
- **Alle Instagram-API-Aufrufe** gehen über `i.instagram.com/api/v1/` (mobile API)
  - Profile: `GET /api/v1/users/web_profile_info/?username=...`
  - Posts: `GET /api/v1/feed/user/{user_id}/`
- Grund: instaloader's `get_posts()` schlägt mit KeyError 'edges' fehl (Bug in 4.15.1),
  `Profile.from_username()` wird nach dem ersten Aufruf rate-limited (graphql/query 403)
- **Session-Datei**: `data/ig_session` — Cookies von Markus' persönlichem Instagram-Account
  (`zieglermarkus`) via Browser extrahiert (F12 → Application → Cookies)

## Lokales Setup (Windows)
```
# Python 3.12 verwenden (3.14 ist inkompatibel mit SQLAlchemy/pydantic)
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Session erneuern (wenn Instagram-Cookies ablaufen)
```
python make_session.py
```
Werte aus Browser: F12 → Application → Cookies → instagram.com (eingeloggt als zieglermarkus):
- `sessionid`
- `csrftoken`
- `ds_user_id`

## .env Konfiguration
```
DATABASE_URL=sqlite:///./data/insta_tracker.db
INSTAGRAM_SESSION_FILE=./data/ig_session
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=instagram.creator.tracker@gmail.com
SMTP_PASSWORD=<Gmail App-Passwort>
NOTIFY_EMAIL=instagram.creator.tracker@gmail.com
MORNING_CHECK_HOUR=7
TIMEZONE=Europe/Vienna
```

## Offene Punkte / Nächste Schritte

### Sofort
1. **Session erneuern mit `zieglermarkus`-Cookies** (Stand 2026-05-08):
   - Die Session-Cookies sind abgelaufen → "Rate limited after 0 creators" im Log
     bedeutet in Wirklichkeit 401/403 (Session expired), KEIN echtes Rate-Limit
   - Im Browser bei Instagram als `zieglermarkus` einloggen
   - F12 → Application → Cookies → sessionid, csrftoken, ds_user_id kopieren
   - `python make_session.py` ausführen
   - uvicorn neu starten → "Jetzt prüfen"

2. **`insta_creator_tracker` Account NICHT für Session verwenden**:
   - Instagram hat beim Login "We suspect automated behavior" angezeigt
   - Account ist zu neu/unauffällig → höheres Sperr-Risiko
   - Weiterhin `zieglermarkus` verwenden

3. **Creators bereinigen**: `@alphavision.media` und `@sarv.vj` scheinen nicht zu
   existieren oder privat zu sein → im Dashboard entfernen.

### Mittelfristig
4. **Session-Refresh UI** im Dashboard (Option A):
   Eine `/settings` Seite mit Formular für sessionid/csrftoken/ds_user_id,
   damit man nicht mehr das Terminal braucht.

5. **Railway Deployment** für 24/7-Betrieb:
   Derzeit läuft die App nur wenn Markus' PC an ist. Railway würde den
   morgendlichen Check auch ohne PC durchführen.

## Git
- Hauptbranch: `main`
- Feature-Branch: `claude/instagram-creator-tracker-zbu5g`
- Remote: github.com/MarkusZiegler/Instagram-Creator-Tracker

## Schlüsseldateien
- `app/services/instagram.py` — Instagram-API-Wrapper (KEIN direkter instaloader-Aufruf mehr)
- `app/services/checker.py` — Morning-Check-Algorithmus
- `app/services/notifier.py` — E-Mail-Digest
- `app/routers/creators.py` — REST-Endpoints inkl. mark-seen
- `app/templates/dashboard.html` — Haupt-UI
- `make_session.py` — Hilfsskript zum Erstellen der Session-Datei aus Browser-Cookies
- `data/ig_session` — Instagram Session-Cookies (nicht im Git, lokal auf Markus' PC)
