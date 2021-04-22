import httpx


username = "barsikus07@gmail.com"
password = "password"

auth = httpx.post(
    "https://edu.donstu.ru/api/tokenauth",
    content=str({"password": password, "userName": username}).encode(),
    headers={"content-type": "application/json"}
)

header = {"authorization": f'Bearer {auth.json()["data"]["accessToken"]}'}
req = httpx.get("https://edu.donstu.ru/api/RaspManager?course=2", headers=header)

print(req.text)
