from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import requests
import os
import traceback
from tempfile import NamedTemporaryFile

app = FastAPI()

# OpenAI API key must be set in Render → Environment Variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in environment variables")


@app.get("/")
def health():
    return {"ok": True}


@app.post("/tryon")
async def tryon(
    user_photo: UploadFile = File(...),
    style_url: str = Form(...)
):
    try:
        # 1. Save user photo
        with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(await user_photo.read())
            user_path = f.name

        # 2. Download hairstyle reference image
        style_resp = requests.get(style_url, timeout=30, allow_redirects=True)
        if style_resp.status_code != 200:
            raise Exception(f"Style image download failed: HTTP {style_resp.status_code}")

        with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(style_resp.content)
            style_path = f.name

        # 3. Prompt: same person, only hair changes
        prompt = (
            "Change ONLY the hairstyle on the person in the FIRST image to match the hairstyle in the SECOND image. "
            "Keep the SAME person: identical face identity, facial features, skin tone, age and expression. "
            "Do NOT change background, lighting, clothes, makeup, jewelry or head shape. "
            "Photorealistic result with clean hairline and natural blending."
        )

        # 4. OpenAI Images Edits API (multipart/form-data)
        url = "https://api.openai.com/v1/images/edits"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }

        # IMPORTANT:
        # multiple images MUST be sent as image[]
        with open(user_path, "rb") as uf, open(style_path, "rb") as sf:
            files = [
                ("image[]", ("user.jpg", uf, "image/jpeg")),
                ("image[]", ("style.jpg", sf, "image/jpeg")),
            ]

            data = {
                "model": "gpt-image-1",
                "prompt": prompt,
                "input_fidelity": "high",  # keeps face identity stronger
                "size": "1024x1024",
                "n": "1",
                "output_format": "png",
            }

            r = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=180
            )

        print("OpenAI status:", r.status_code)

        if r.status_code != 200:
            print("OpenAI response:", (r.text or "")[:2000])
            raise Exception(f"OpenAI error {r.status_code}: {(r.text or '')[:2000]}")

        # 5. Return base64 image
        result = r.json()
        image_b64 = result["data"][0]["b64_json"]
        return {"image": image_b64}

    except Exception as e:
        print("TRYON ERROR:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
