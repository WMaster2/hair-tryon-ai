from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import requests, os, traceback
from tempfile import NamedTemporaryFile

app = FastAPI()

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
        # 1) Save user photo
        with NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(await user_photo.read())
            user_path = f.name

        # 2) Download style reference
        style_resp = requests.get(style_url, timeout=30, allow_redirects=True)
        if style_resp.status_code != 200:
            raise Exception(f"Style download failed: {style_resp.status_code} {style_resp.text[:200]}")

        style_path = user_path.replace(".jpg", "_style.jpg")
        with open(style_path, "wb") as f:
            f.write(style_resp.content)

        # 3) OpenAI request (POST, no redirects)
        prompt = (
            "Replace ONLY the hairstyle on the person in the first image to match the hairstyle in the second image. "
            "Keep the face identity, facial features, skin tone, background, lighting, and clothing unchanged. "
            "Photorealistic. Preserve natural hairline. Clean blending at edges. Do not change head shape."
        )

        url = "https://api.openai.com/v1/images/edits"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

        # IMPORTANT: keep file handles open during request
        user_f = open(user_path, "rb")
        style_f = open(style_path, "rb")
        try:
            files = [
                ("image", ("user.jpg", user_f, "image/jpeg")),
                ("image", ("style.jpg", style_f, "image/jpeg")),
            ]
            data = {
                "model": "gpt-image-1.5",
                "prompt": prompt,
                "n": "1",
                "output_format": "png",
            }

            r = requests.request(
                "POST",
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=180,
                allow_redirects=False,  # prevents POST->GET on 302/301
            )

        finally:
            try:
                user_f.close()
            except:
                pass
            try:
                style_f.close()
            except:
                pass

        # 4) Handle response
        print("OpenAI status:", r.status_code)
        if r.status_code != 200:
            # log a bit of body to Render logs
            print("OpenAI response:", (r.text or "")[:2000])
            raise Exception(f"OpenAI error {r.status_code}: {(r.text or '')[:2000]}")

        js = r.json()
        b64 = js["data"][0]["b64_json"]
        return {"image": b64}

    except Exception as e:
        print("TRYON ERROR:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
