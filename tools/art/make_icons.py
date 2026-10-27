"""Every icon the app ships, cut from the one club logo.

    python tools/art/make_icons.py

tools/art/logo-source.jpg is the round crowned-cat emblem on black,
1254px square. The black is part of the icon (it is the club's colour), so
nothing here makes it transparent.

The maskable icon is the one Android crops to a circle, a squircle or a
teardrop depending on the phone. Only the middle 80% is guaranteed to
survive, so the emblem is shrunk into that and the rest is the same black.
"""
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
PUBLIC = HERE.parent.parent / 'frontend' / 'public'
ICONS = PUBLIC / 'pwa-icons'


def main() -> None:
    logo = Image.open(HERE / 'logo-source.jpg').convert('RGB')
    ICONS.mkdir(parents=True, exist_ok=True)

    for size, name in ((64, 'pwa-64x64.png'), (192, 'pwa-192x192.png'), (512, 'pwa-512x512.png'), (180, 'apple-touch-icon-180x180.png')):
        logo.resize((size, size), Image.LANCZOS).save(ICONS / name, optimize=True)

    safe = Image.new('RGB', (512, 512), (0, 0, 0))
    inner = round(512 * 0.8)
    safe.paste(logo.resize((inner, inner), Image.LANCZOS), ((512 - inner) // 2, (512 - inner) // 2))
    safe.save(ICONS / 'maskable-icon-512x512.png', optimize=True)

    logo.save(PUBLIC / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])

    for f in sorted(ICONS.iterdir()) + [PUBLIC / 'favicon.ico']:
        print(f.relative_to(PUBLIC), Image.open(f).size)


if __name__ == '__main__':
    main()
