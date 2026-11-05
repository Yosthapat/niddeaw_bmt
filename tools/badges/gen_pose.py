"""Re-pose a REAL mascot, passing the original as a reference image so the face/design stays the same.
Never draw a mascot from scratch (faces drift); always start from frontend/public/tiers/*.webp.

  python3 -I tools/badges/gen_pose.py gemini frontend/public/tiers/beer.webp tools/badges/poses/beer_x.webp "<pose>" [green|magenta]

Gemini (gemini-3-pro-image) kept the likeness best. It can't output transparency, so it draws on a chroma
background that chroma.py keys out (use magenta for green mascots like Soju). The raw image and token
usage go to tools/badges/out/. Costs money. Keys from env (never printed).
"""
import base64, io, os, sys, requests
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
prov, src, out, pose = sys.argv[1:5]
KEY = sys.argv[5] if len(sys.argv) > 5 else "green"
KEYTXT = {"green": "pure chroma-key green #00FF00", "magenta": "pure chroma-key magenta #FF00FF"}[KEY]
P = ("Redraw EXACTLY this same character from the reference image: identical face (same eyes, same smile), "
     "same body/container shape and proportions, same cap/topping/headwear, same label text layout and colors, same short white arms and legs, same sticker-style white outline, same cartoon "
     f"rendering style. Only change the pose: {pose}. Full body, centered, front-facing, no added text, "
     "no extra props unless stated (a stated badminton racket or shuttlecock is fine), no background scenery.")
ref = io.BytesIO(); Image.open(src).convert("RGBA").resize((1024, 1024), Image.LANCZOS).save(ref, "PNG")
if prov == "openai":
    r = requests.post("https://api.openai.com/v1/images/edits",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        files={"image[]": ("ref.png", ref.getvalue(), "image/png")},
        data={"model": os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare"), "prompt": P + " Transparent background.",
              "size": "1024x1024", "background": "transparent", "quality": "high"}, timeout=300)
    if r.status_code != 200: sys.exit(f"HTTP {r.status_code} {r.text[:400]}")
    Image.open(io.BytesIO(base64.b64decode(r.json()["data"][0]["b64_json"]))).save(out)
else:
    from chroma import key_out
    body = {"contents": [{"parts": [
        {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(ref.getvalue()).decode()}},
        {"text": P + " Background: perfectly flat uniform " + KEYTXT + ", no shadow."}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}}}
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, json=body, timeout=300)
    if r.status_code != 200: sys.exit(f"HTTP {r.status_code} {r.text[:400]}")
    d = next(p["inlineData"]["data"] for p in r.json()["candidates"][0]["content"]["parts"] if "inlineData" in p)
    im = Image.open(io.BytesIO(base64.b64decode(d))).convert("RGB").resize((1024, 1024), Image.LANCZOS)
    OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(OUTD, exist_ok=True)
    im.save(os.path.join(OUTD, os.path.splitext(os.path.basename(out))[0] + "_raw.png"))
    key_out(im, KEY, despill_all=False).save(out, quality=92, alpha_quality=100, method=6)
    import json
    open(os.path.join(OUTD, "usage.jsonl"), "a").write(json.dumps({"file": out, "usage": r.json().get("usageMetadata")}) + "\n")
print("saved", out)
