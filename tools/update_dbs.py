import pickle

import httpx

auds = httpx.get("https://edu.donstu.ru/api/raspAudlist?year=2020-2021").json()

with open("../auds.pickle", "wb") as file:
    pickle.dump(auds, file)

# students = httpx.get("https://edu.donstu.ru/api/raspAudlist?year=2020-2021").json()
