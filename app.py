from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import requests, os, traceback
from tempfile import NamedTemporaryFile

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in Render env vars")

@app.get("/")
def health():
    return {"ok": True}

@app.post("/tryon")
async def tryon(
    user_photo: UploadFile = File(...),
    style_url: str = Form(...)
):
    try:
        # 1) save user photo
        with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(await user_photo.read())
            user_path = f.name

        # 2) download style reference
        style_resp = requests.get(style_url, timeout=30, allow_redirects=True)
        if style_resp.status_code != 200:
            raise Exception(f"Style download failed: HTTP {style_resp.status_code}")

        with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(style_resp.content)
            style_path = f.name

        prompt = (
            "Change ONLY the hairstyle on the person in the FIRST image to match the hairstyle in the SECOND image. "
            "Keep the SAME person: identical face identity, facial features, skin tone, age, expression. "
            "Do NOT change background, lighting, clothes, makeup, jewelry, head shape. "
            "Photorealistic, clean hairline and blending."
        )

        url = "https://api.openai.com/v1/images/edits"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

        # ВАЖНО: multipart/form-data, и два файла под одним именем "image"
        with open(user_path, "rb") as uf, open(style_path, "rb") as sf:
            files = [
                ("image", ("user.jpg", uf, "image/jpeg")),
                ("image", ("style.jpg", sf, "image/jpeg")),
            ]
            data = {
                "model": "gpt-image-1",
                "prompt": prompt,
                "input_fidelity": "high",   # сильнее держит лицо/идентичность
                "output_format": "png",
                "n": "1",
                "size": "1024x1024",
            }

            r = requests.post(url, headers=headers, files=files, data=data, timeout=180)

        print("OpenAI status:", r.status_code)
        if r.status_code != 200:
            print("OpenAI response:", (r.text or "")[:2000])
            raise Exception(f"OpenAI error {r.status_code}: {(r.text or '')[:2000]}")

        b64 = r.json()["data"][0]["b64_json"]
        return {"image": b64}

    except Exception as e:
        print("TRYON ERROR:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
