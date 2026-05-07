import pickle

print("Alle Werte aus Browser-Cookies: F12 -> Application -> Cookies -> instagram.com")
print()
sid = input("sessionid:  ").strip()
csrf = input("csrftoken:  ").strip()
dsid = input("ds_user_id: ").strip()

with open("data/ig_session", "wb") as f:
    pickle.dump({"sessionid": sid, "csrftoken": csrf, "ds_user_id": dsid}, f)
print("Gespeichert!")
