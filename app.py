from fastapi import FastAPI, UploadFile, File, Form
import requests, base64, os
from tempfile import NamedTemporaryFile

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.post("/tryon")
async def tryon(
    user_photo: UploadFile = File(...),
    style_url: str = Form(...)
):
    with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
        f.write(await user_photo.read())
        user_path = f.name

    style_resp = requests.get(style_url, timeout=30)
    style_path = user_path.replace(".jpg", "_style.jpg")
    with open(style_path, "wb") as f:
        f.write(style_resp.content)

    prompt = (
        "Replace ONLY the hairstyle on the person in the first image "
        "to match the hairstyle in the second image. "
        "Keep face identity, skin tone, background unchanged. "
        "Photorealistic, clean blending."
    )

    url = "https://api.openai.com/v1/images/edits"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    files = [
        ("image", ("user.jpg", open(user_path, "rb"), "image/jpeg")),
        ("image", ("style.jpg", open(style_path, "rb"), "image/jpeg")),
    ]

    data = {
        "model": "gpt-image-1.5",
        "prompt": prompt,
        "n": 1,
        "output_format": "png",
    }

    r = requests.post(url, headers=headers, files=files, data=data, timeout=180)
    r.raise_for_status()

    b64 = r.json()["data"][0]["b64_json"]
    return {"image": b64}
