# import requests
# r = requests.post(
#     "https://api.openverse.org/v1/auth_tokens/register/",
#     json={
#         "name": "moto-dataset",
#         "description": "Dataset de motos pour classification d'images",
#         "email": "votremail@exemple.com",
#     },
# )
# print(r.status_code, r.json())

# from PIL import Image, ImageOps

# img = Image.open("000048.png")
# img_resized = ImageOps.pad(img, (16, 16), color=(255, 255, 255))
# img_resized.save("000048_resizedx16.png")