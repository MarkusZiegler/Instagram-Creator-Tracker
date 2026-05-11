"""Quick test: Ruft Instagram API direkt auf ohne App-Overhead."""
import pickle
import requests

SESSION_FILE = "data/ig_session"
TEST_USER = "american_cinematographer"

with open(SESSION_FILE, "rb") as f:
    data = pickle.load(f)

print(f"Session-Datei Typ: {type(data)}")
print(f"Enthaltene Keys: {list(data.keys()) if isinstance(data, dict) else 'kein dict'}")

session = requests.Session()
if isinstance(data, dict):
    for key, value in data.items():
        session.cookies.set(key, value, domain=".instagram.com")
        print(f"  Cookie gesetzt: {key} = {value[:12]}...")
else:
    session.cookies = data

headers = {
    "X-IG-App-ID": "936619743392459",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.91 Mobile Safari/537.36"
    ),
}

print(f"\nRufe API auf für @{TEST_USER}...")
resp = session.get(
    "https://i.instagram.com/api/v1/users/web_profile_info/",
    headers=headers,
    params={"username": TEST_USER},
    timeout=15,
)
print(f"HTTP Status: {resp.status_code}")
if resp.status_code == 200:
    user = resp.json().get("data", {}).get("user", {})
    print(f"OK! Username: {user.get('username')}, Follower: {user.get('edge_followed_by', {}).get('count')}")
elif resp.status_code == 429:
    print("Rate Limited (429) - IP oder Session gesperrt")
elif resp.status_code in (401, 403):
    print(f"Auth-Fehler ({resp.status_code}) - Cookies ungültig oder abgelaufen")
else:
    print(f"Antwort: {resp.text[:300]}")
