from PIL import Image, ImageDraw

SIZES = [16, 32, 48, 64, 128, 256]

# Nord palette
BG = (46, 52, 64)
SCREEN_BG = (30, 34, 45)
GREEN = (163, 190, 140)
BRACKET = (136, 192, 208)
PROMPT = (216, 222, 233)
BEZEL = (59, 66, 82)
HIGHLIGHT = (94, 129, 172)


def draw_terminal(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    cx = cy = size // 2
    r = size // 2 - max(1, size // 32)

    d.rounded_rectangle(
        [cx - r, cy - r, cx + r, cy + r],
        radius=max(2, r // 6),
        fill=BG,
        outline=BEZEL,
        width=max(1, size // 48),
    )

    m = max(3, r // 4)
    sr = r - m
    d.rounded_rectangle(
        [cx - sr, cy - sr, cx + sr, cy + sr],
        radius=max(1, sr // 8),
        fill=SCREEN_BG,
    )

    pw = max(1, size // 64)
    fs = max(4, sr // 2)

    bracket_y = cy - sr // 4
    d.text(
        (cx - sr // 3, bracket_y),
        "[",
        fill=BRACKET,
        font_size=fs,
    )

    d.text(
        (cx + sr // 3 - fs * 0.3, bracket_y),
        "]",
        fill=BRACKET,
        font_size=fs,
    )

    gt_x = cx - sr // 6
    gt_y = cy + sr // 8
    gt_size = max(2, fs // 2)
    d.text(
        (gt_x, gt_y),
        ">_",
        fill=GREEN,
        font_size=gt_size,
    )

    dot_r = max(1, size // 64)
    dot_y = cy - sr + sr // 3
    for i, color in enumerate([(235, 203, 139), GREEN, (191, 97, 106)]):
        x = cx + sr - sr // 3 + i * dot_r * 3
        d.ellipse(
            [x - dot_r, dot_y - dot_r, x + dot_r, dot_y + dot_r],
            fill=color,
        )

    return im


def main():
    pngs = {}
    for s in SIZES:
        pngs[s] = draw_terminal(s)

    pngs[256].save("icon.png")

    pngs[256].save("icon.ico", format="ICO", sizes=[(s, s) for s in SIZES])

    print("icon.png and icon.ico generated")

    for s in [16, 32, 48, 64, 128]:
        pngs[s].save(f"icon_{s}.png")


if __name__ == "__main__":
    main()
