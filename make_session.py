import pickle

sid = input("sessionid: ").strip()
with open("data/ig_session", "wb") as f:
    pickle.dump({"sessionid": sid}, f)
print("Gespeichert!")
