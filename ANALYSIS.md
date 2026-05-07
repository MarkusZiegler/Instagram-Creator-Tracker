# Analyse & nächste Schritte

## Was fehlt

`app/services/instagram.py` existiert noch nicht – checker.py importiert sie aber bereits.
Das ist der Grund warum nichts läuft.

## Warum das 429 kommt

instaloader nutzt intern `api/v1/users/web_profile_info/` – dieselbe API wie der Browser.
Der Unterschied:

- **Ohne Login:** Instagram sieht einen anonymen Bot → sofort 429
- **Mit Login (Session-Datei):** Instagram behandelt die Anfragen wie einen eingeloggten Browser → funktioniert

Das 429 ist also kein grundsätzliches Problem mit dem Ansatz, sondern ein fehlendes Login.

---

## Was instagram.py tun muss

```python
# app/services/instagram.py

class ProfileNotFoundError(Exception): pass
class RateLimitedError(Exception): pass

class InstagramService:
    def __init__(self, session_file: str):
        # instaloader.Instaloader() instanziieren
        # Session aus Datei laden (session_file)
        # Falls keine Session-Datei: Login mit USERNAME/PASSWORD aus config,
        #   danach Session speichern
        pass

    def get_new_posts(self, username: str, since_shortcode: str | None, max_posts: int) -> list[PostData]:
        # instaloader.Profile.from_username() aufrufen
        # Posts iterieren bis since_shortcode erreicht (oder max_posts)
        # RateLimitedException → raise RateLimitedError
        # ProfileNotExistsException → raise ProfileNotFoundError
        # PostData ist ein einfaches Dataclass mit den Feldern aus checker.py
        pass
```

### PostData Felder (aus checker.py ableitbar)
```
shortcode, post_url, thumbnail_url, caption,
post_type (photo/video/reel/carousel), like_count, comment_count, posted_at
```

---

## Empfohlene Vorgehensweise

### 1. Session einmalig lokal erzeugen

```bash
python -c "
import instaloader
L = instaloader.Instaloader()
L.interactive_login('DEIN_SCRAPING_ACCOUNT')
L.save_session_to_file('instagram_session')
"
```

Die erzeugte Datei `instagram_session` in `.env` als `INSTAGRAM_SESSION_FILE=instagram_session` eintragen.
**Wichtig:** Datei im `.gitignore` – nie committen.

### 2. instagram.py implementieren (s.o.)

### 3. Lokal testen

```bash
POST /jobs/check-now
```

Mit einem einzigen Creator, der ein öffentlicher Business/Creator-Account ist.

---

## Risiken & Grenzen

| Thema | Details |
|---|---|
| Session läuft ab | Alle paar Wochen neu einloggen nötig. Alternativ: Login-Credentials in `.env` und beim Start automatisch neu einloggen wenn Session abgelaufen |
| Account-Sperre | Separater "Dummy"-Account empfohlen (steht schon im PLAN.md) – nie den Haupt-Account verwenden |
| Nur Business/Creator-Accounts | Private Accounts und reine Privatprofile können nicht abgefragt werden |
| Instagram-API-Änderungen | instaloader-Community pflegt das aktiv, aber es kann vorkommen dass eine Woche lang nichts geht nach einem Instagram-Update |

---

## Delay-Einstellungen (config.py prüfen)

Die 3–8 Sekunden Delay zwischen Creatoren sind gut.
Zusätzlich sinnvoll: nach einem 429 nicht sofort aufhören sondern 60 Sekunden warten und einmal retry versuchen, danach erst abbrechen.

---

## Fazit

Der Plan und die Architektur sind in Ordnung. Einziger fehlender Baustein ist `instagram.py`.
Sobald die existiert und eine gültige Session-Datei vorhanden ist, sollte der Morning-Check funktionieren.
