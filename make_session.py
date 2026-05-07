import pickle

sid = input("sessionid: ").strip()
csrf = input("csrftoken: ").strip()
with open("data/ig_session", "wb") as f:
    pickle.dump({"sessionid": sid, "csrftoken": csrf}, f)
print("Gespeichert!")
