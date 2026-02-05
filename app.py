from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import requests, os, base64, traceback
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
        # 1) Save user photo to temp file
        with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(await user_photo.read())
            user_path = f.name

        # 2) Download hairstyle reference image
        style_resp = requests.get(style_url, timeout=30, allow_redirects=True)
        if style_resp.status_code != 200:
            raise Exception(f"Style download failed: HTTP {style_resp.status_code}")

        with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(style_resp.content)
            style_path = f.name

        # 3) Convert both images to base64 for OpenAI /v1/images
        user_b64 = base64.b64encode(open(user_path, "rb").read()).decode()
        style_b64 = base64.b64encode(open(style_path, "rb").read()).decode()

        prompt = (
            "Create a photorealistic portrait of the same person from the first image. "
            "Preserve facial identity, skin tone, face shape, age, expression, background and lighting. "
            "Apply ONLY the hairstyle from the second image. "
            "Natural hairline, realistic texture, clean edges. "
            "Do not change clothing, jewelry, makeup, or background."
        )

        payload = {
            "model": "gpt-image-1",
            "prompt": prompt,
            "image": [
                {"type": "input_image", "image_base64": user_b64},
                {"type": "input_image", "image_base64": style_b64},
            ],
            "size": "1024x1024"
        }

        url = "https://api.openai.com/v1/images"
        r = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180,
        )

        print("OpenAI status:", r.status_code)
        if r.status_code != 200:
            print("OpenAI response:", (r.text or "")[:2000])
            raise Exception(f"OpenAI error {r.status_code}: {(r.text or '')[:2000]}")

        js = r.json()
        img_b64 = js["data"][0]["b64_json"]
        return {"image": img_b64}

    except Exception as e:
        print("TRYON ERROR:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
