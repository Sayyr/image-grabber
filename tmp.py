import requests
r = requests.post(
    "https://api.openverse.org/v1/auth_tokens/register/",
    json={
        "name": "moto-dataset",
        "description": "Dataset de motos pour classification d'images",
        "email": "votremail@exemple.com",
    },
)
print(r.status_code, r.json())
