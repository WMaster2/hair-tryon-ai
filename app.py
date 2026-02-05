from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import requests
import os
import base64
import traceback
from tempfile import NamedTemporaryFile

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in Render Environment Variables")


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

        # 2. Download hairstyle image
        style_resp = requests.get(style_url, timeout=30)
        if style_resp.status_code != 200:
            raise Exception(f"Style image download failed: {style_resp.status_code}")

        with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(style_resp.content)
            style_path = f.name

        # 3. Convert both images to base64
        with open(user_path, "rb") as f:
            user_b64 = base64.b64encode(f.read()).decode()

        with open(style_path, "rb") as f:
            style_b64 = base64.b64encode(f.read()).decode()

        # 4. Prompt
        prompt = (
            "Create a photorealistic portrait of the SAME person from the first image. "
            "Preserve face identity, skin tone, age, expression, lighting and background. "
            "Apply ONLY the hairstyle from the second image. "
            "Natural hairline, realistic texture, clean blending. "
            "Do NOT change clothing, makeup, jewelry, or head shape."
        )

        # 5. OpenAI Images API
        payload = {
            "model": "gpt-image-1",
            "prompt": prompt,
            "image": [
                {"type": "input_image", "image_base64": user_b64},
                {"type": "input_image", "image_base64": style_b64}
            ],
            "size": "1024x1024"
        }

        r = requests.post(
            "https://api.openai.com/v1/images",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=180
        )

        print("OpenAI status:", r.status_code)

        if r.status_code != 200:
            print("OpenAI response:", r.text[:2000])
            raise Exception(f"OpenAI error {r.status_code}: {r.text[:2000]}")

        result = r.json()
        image_b64 = result["data"][0]["b64_json"]

        return {"image": image_b64}

    except Exception as e:
        print("TRYON ERROR:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
