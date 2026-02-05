from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import requests, os, base64, traceback
from tempfile import NamedTemporaryFile

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

@app.get("/")
def health():
    return {"ok": True}

@app.post("/tryon")
async def tryon(
    user_photo: UploadFile = File(...),
    style_url: str = Form(...)
):
    try:
        # Save user photo
        with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(await user_photo.read())
            user_path = f.name

        # Download hairstyle reference
        style_resp = requests.get(style_url, timeout=30)
        if style_resp.status_code != 200:
            raise Exception("Failed to download style image")

        style_b64 = base64.b64encode(style_resp.content).decode()
        user_b64 = base64.b64encode(open(user_path, "rb").read()).decode()

        prompt = (
            "Create a photorealistic portrait of the same person from the first image. "
            "Preserve facial identity, skin tone, face shape, age, expression, background and lighting. "
            "Apply ONLY the hairstyle from the second image. "
            "Natural hairline, clean blending, realistic texture. No stylization."
        )

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

        if r.status_code != 200:
            raise Exception(f"OpenAI error {r.status_code}: {r.text}")

        img_b64 = r.json()["data"][0]["b64_json"]
        return {"image": img_b64}

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
