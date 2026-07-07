#!/usr/bin/env python3
"""
generate_gallery.py

Scans a folder for images, generates 300x200 thumbnails (center-cropped
to a 3:2 aspect ratio, clipping top/bottom or left/right as needed), and
builds an HTML page that displays the thumbnails in a responsive,
centered table/grid. Clicking a thumbnail opens the original image.
Thumbnails have a glowing shadow effect.

Usage:
    python generate_gallery.py /path/to/folder
    python generate_gallery.py /path/to/folder --output gallery.html --thumb-dir thumbnails

Requires: Pillow  (pip install Pillow --break-system-packages)
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("This script requires Pillow. Install it with:")
    print("    pip install Pillow --break-system-packages")
    sys.exit(1)

THUMB_W, THUMB_H = 300, 200
TARGET_RATIO = THUMB_W / THUMB_H  # 3:2 = 1.5

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


def find_images(folder: Path):
    """Return a sorted list of image files directly inside `folder`."""
    images = []
    for entry in sorted(folder.iterdir()):
        if entry.is_file() and entry.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(entry)
    return images


def make_thumbnail(src_path: Path, dst_path: Path):
    """
    Create a 300x200 thumbnail from src_path, center-cropping the source
    to a 3:2 aspect ratio first (clipping top/bottom if the image is
    relatively taller than 3:2, or left/right if relatively wider),
    then resizing down to exactly 300x200.
    """
    with Image.open(src_path) as im:
        # Respect EXIF orientation (common with phone photos).
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")

        w, h = im.size
        src_ratio = w / h

        if src_ratio > TARGET_RATIO:
            # Image is wider than 3:2 -> clip left/right, keep full height.
            new_w = int(round(h * TARGET_RATIO))
            offset = (w - new_w) // 2
            box = (offset, 0, offset + new_w, h)
        else:
            # Image is taller than (or equal to) 3:2 -> clip top/bottom.
            new_h = int(round(w / TARGET_RATIO))
            offset = (h - new_h) // 2
            box = (0, offset, w, offset + new_h)

        cropped = im.crop(box)
        thumb = cropped.resize((THUMB_W, THUMB_H), Image.LANCZOS)

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        # Always save thumbnails as JPEG for consistent small file size.
        thumb.save(dst_path, "JPEG", quality=85)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
    :root {{
        --thumb-w: 300px;
        --thumb-h: 200px;
        --glow-color: rgba(128, 128, 128, 0.85);
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        padding: 40px 20px;
        min-height: 100vh;
        background: #ffffff;
        color: #222;
        font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        display: flex;
        flex-direction: column;
        align-items: center;
    }}

    h1 {{
        margin-bottom: 30px;
        font-weight: 300;
        letter-spacing: 1px;
        text-align: center;
        color: #222;
    }}

    .gallery {{
        /* Centered, responsive grid: columns auto-adjust to window width,
           but never exceed 6 columns. */
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, var(--thumb-w)));
        gap: 28px;
        justify-content: center;
        max-width: calc(6 * var(--thumb-w) + 5 * 28px);
        width: 100%;
    }}

    .thumb-link {{
        display: block;
        width: 100%;
        aspect-ratio: 3 / 2;
        border-radius: 10px;
        overflow: hidden;
        text-decoration: none;
        cursor: zoom-in;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        box-shadow: 0 0 12px 2px var(--glow-color);
    }}

    .thumb-link:hover,
    .thumb-link:focus {{
        transform: translateY(-4px) scale(1.03);
        box-shadow: 0 0 26px 8px var(--glow-color);
    }}

    .thumb-link img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}

    .caption {{
        margin-top: 8px;
        font-size: 0.85rem;
        color: #666;
        text-align: center;
        word-break: break-word;
    }}

    .empty {{
        text-align: center;
        color: #888;
        margin-top: 60px;
        font-size: 1.1rem;
    }}

    footer {{
        margin-top: 50px;
        color: #999;
        font-size: 0.8rem;
        text-align: center;
    }}

    /* Lightbox overlay: expands the clicked image to fill the screen */
    .lightbox {{
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.9);
        z-index: 1000;
        align-items: center;
        justify-content: center;
        cursor: zoom-out;
        animation: fadeIn 0.2s ease;
    }}

    .lightbox.open {{
        display: flex;
    }}

    .lightbox img {{
        max-width: 92vw;
        max-height: 92vh;
        object-fit: contain;
        border-radius: 6px;
        box-shadow: 0 0 40px 10px rgba(0, 0, 0, 0.6);
    }}

    .lightbox-close {{
        position: fixed;
        top: 18px;
        right: 28px;
        font-size: 2.2rem;
        color: #fff;
        line-height: 1;
        cursor: pointer;
        user-select: none;
        opacity: 0.85;
    }}

    .lightbox-close:hover {{
        opacity: 1;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}
</style>
</head>
<body>
<h1>{title}</h1>
{content}
<footer>Generated by generate_gallery.py &middot; {count} image(s)</footer>

<div class="lightbox" id="lightbox" onclick="closeLightbox()">
    <span class="lightbox-close" onclick="closeLightbox()">&times;</span>
    <img id="lightbox-img" src="" alt="">
</div>

<script>
    function openLightbox(src, alt) {{
        const lb = document.getElementById('lightbox');
        const img = document.getElementById('lightbox-img');
        img.src = src;
        img.alt = alt;
        lb.classList.add('open');
        document.body.style.overflow = 'hidden';
    }}

    function closeLightbox() {{
        const lb = document.getElementById('lightbox');
        lb.classList.remove('open');
        document.body.style.overflow = '';
    }}

    document.addEventListener('keydown', function (e) {{
        if (e.key === 'Escape') {{
            closeLightbox();
        }}
    }});
</script>
</body>
</html>
"""

ITEM_TEMPLATE = """    <figure style="margin:0;">
        <a class="thumb-link" href="{original_href}" onclick="openLightbox('{js_href}', '{js_alt}'); return false;">
            <img src="{thumb_href}" alt="{alt}" loading="lazy">
        </a>
        <figcaption class="caption">{alt}</figcaption>
    </figure>
"""


def build_html(images_info, folder_name, output_path: Path):
    import html

    if images_info:
        items = "\n".join(
            ITEM_TEMPLATE.format(
                original_href=html.escape(info["original_href"], quote=True),
                thumb_href=html.escape(info["thumb_href"], quote=True),
                alt=html.escape(info["name"], quote=True),
                js_href=info["original_href"].replace("\\", "\\\\").replace("'", "\\'"),
                js_alt=info["name"].replace("\\", "\\\\").replace("'", "\\'"),
            )
            for info in images_info
        )
        content = f'<div class="gallery">\n{items}</div>'
    else:
        content = '<p class="empty">No images found in this folder.</p>'

    html = HTML_TEMPLATE.format(
        title=f"Image Gallery &mdash; {folder_name}",
        content=content,
        count=len(images_info),
    )

    output_path.write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Generate thumbnails and an HTML gallery page for a folder of images."
    )
    parser.add_argument("folder", help="Path to the folder containing images")
    parser.add_argument(
        "--output",
        default="gallery.html",
        help="Name of the HTML file to generate inside the folder (default: gallery.html)",
    )
    parser.add_argument(
        "--thumb-dir",
        default="thumbnails",
        help="Subfolder name (inside the target folder) to store thumbnails (default: thumbnails)",
    )
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Error: '{folder}' is not a valid directory.")
        sys.exit(1)

    thumb_dir = folder / args.thumb_dir
    output_path = folder / args.output

    images = find_images(folder)
    if not images:
        print(f"No images found in {folder}")

    images_info = []
    for img_path in images:
        thumb_name = img_path.stem + "_thumb.jpg"
        thumb_path = thumb_dir / thumb_name
        try:
            make_thumbnail(img_path, thumb_path)
        except Exception as e:
            print(f"Skipping '{img_path.name}': {e}")
            continue

        images_info.append(
            {
                "name": img_path.name,
                # Paths relative to the HTML file (which lives in `folder`)
                "original_href": img_path.name,
                "thumb_href": f"{args.thumb_dir}/{thumb_name}",
            }
        )
        print(f"Thumbnail created: {thumb_path}")

    build_html(images_info, folder.name, output_path)
    print(f"\nGallery created: {output_path}")
    print(f"Open it in a browser to view {len(images_info)} image(s).")


if __name__ == "__main__":
    main()
