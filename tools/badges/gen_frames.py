"""Generate the EMPTY medal frames (OpenAI Images API, transparent background, 1024x1024),
themed for นิดเดียว Badminton Club: black + hot pink, queen-cat crown, shuttlecock feathers, racket strings.
The centre enamel is generated BLACK and re-tinted per quest in code (compose.py), so these 15 frames
(5 shapes x bronze/silver/gold) serve every medal. Mascots are never drawn here.

  python3 -I tools/badges/gen_frames.py circle | all | circle:gold   -> tools/badges/frames/<shape>_<tier>.webp

Costs money (~1 image each). Key from env OPENAI_API_KEY (never printed); model via OPENAI_IMAGE_MODEL.
Token usage is appended to tools/badges/out/usage.jsonl.
"""
import base64, io, json, os, sys, time
import requests
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "frames")
LOG = os.path.join(HERE, "out", "usage.jsonl")
MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare")

COMMON = (
    "A single game achievement medal for a badminton club, front view, centered, isolated on a fully transparent background. "
    "Realistic 3D cast metal, multiple stacked layers, subtle worn edges, light scratches, studio light from the top-left. "
    "Badminton-themed ornament: decorative elements are sculpted from shuttlecock feathers and badminton racket string lattice. "
    "Small accents of glossy hot pink (#EA4CA4) enamel inlay. "
    "The CENTER is a large, completely EMPTY, smooth, flat glossy BLACK enamel field (about 55% of the medal width) with nothing on it. "
    "Absolutely no characters, no animals, no faces, no text, no letters, no numbers, no logos, no symbols in the center. "
    "Premium mobile-game medal aesthetic, crisp edges, high detail."
)

SHAPES = {
    "circle": "Shape: round medal. The outer rim is a ring of metal shuttlecock feathers fanning outward, "
              "each feather tip curling upward like a flickering flame tongue.",
    "shield": "Shape: heraldic shield / hexagon badge with faceted bevels, two crossed metal badminton rackets behind it.",
    "rounded": "Shape: rounded-square badge (squircle); the thick frame is engraved with badminton court lines and a net-mesh band; "
               "small rivets in the corners.",
    "star": "Shape: a royal crown-star medal: 5 sharp star points, each point tipped with a small round ball like a queen's crown, "
            "behind a round central field.",
    "diamond": "Shape: diamond / rhombus badge standing on its point, faceted gem-cut bevels, back plate textured with racket string lattice.",
}

TIERS = {
    "bronze": "Material: weathered BRONZE. Simple: just the back plate and one beveled frame, one tiny hot pink enamel dot at the top. "
              "No wreath, no ribbon, no rays, no banner, no crown.",
    "silver": "Material: brushed SILVER. Back plate, beveled frame, PLUS a wreath made of overlapping silver shuttlecock feathers "
              "curving around the lower half (instead of laurel leaves), with two small hot pink gem inlays. No ribbon, no banner, no crown.",
    "gold":   "Material: rich polished GOLD. Most elaborate: behind the medal a radiating fan of golden shuttlecock feathers like sun rays, "
              "the beveled frame, a golden shuttlecock-feather wreath, a ribbon bow at the top striped in hot pink and black, "
              "a small queen's crown with three ball-tipped points in gold and hot pink above the bow, "
              "and an EMPTY blank gold banner plate across the bottom (banner must be blank, no text).",
}


def prompt(shape, tier):
    return " ".join([COMMON, SHAPES[shape], TIERS[tier]])


def gen(shape, tier):
    key = os.environ["OPENAI_API_KEY"]
    body = {"model": MODEL, "prompt": prompt(shape, tier), "size": "1024x1024",
            "background": "transparent", "output_format": "png", "quality": "high", "n": 1}
    for attempt in range(4):
        r = requests.post("https://api.openai.com/v1/images/generations",
                          headers={"Authorization": f"Bearer {key}"}, json=body, timeout=300)
        if r.status_code == 200:
            break
        print(f"{shape}_{tier}: HTTP {r.status_code} {r.text[:300]}", file=sys.stderr)
        if r.status_code in (429, 500, 502, 503):
            time.sleep(2 ** (attempt + 1)); continue
        sys.exit(1)
    j = r.json()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    im = Image.open(io.BytesIO(base64.b64decode(j["data"][0]["b64_json"])))
    im.save(os.path.join(OUT, f"{shape}_{tier}.webp"), quality=92, alpha_quality=100, method=6)
    with open(LOG, "a") as f:
        f.write(json.dumps({"file": f"{shape}_{tier}", "model": MODEL, "usage": j.get("usage")}) + "\n")
    print("saved", shape, tier, j.get("usage"))


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "circle"
    jobs = []
    for part in arg.split(","):
        if part == "all":
            jobs += [(s, t) for s in SHAPES for t in TIERS]
        elif ":" in part:
            jobs.append(tuple(part.split(":")))
        else:
            jobs += [(part, t) for t in TIERS]
    for s, t in jobs:
        gen(s, t)
