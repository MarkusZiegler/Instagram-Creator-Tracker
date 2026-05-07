import pickle
import requests

sid = input("sessionid: ").strip()
jar = requests.cookies.RequestsCookieJar()
jar.set("sessionid", sid, domain=".instagram.com", path="/")
with open("data/ig_session", "wb") as f:
    pickle.dump(jar, f)
print("Gespeichert!")
