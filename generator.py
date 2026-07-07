#!/usr/bin/env python3
"""
generate_gallery.py

Scans multiple folders for images, generates 300x200 thumbnails
(center-cropped to a 3:2 aspect ratio, clipping top/bottom or left/right
as needed), and builds a SINGLE HTML page that displays every folder's
images in its own responsive, centered grid -- with the folder name as
a heading above each grid. Clicking a thumbnail expands the original
image in place (lightbox); clicking again returns to the gallery.

>>> Edit the FOLDERS list below to point at the folders you want <<<

Requires: Pillow  (pip install Pillow --break-system-packages)
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("This script requires Pillow. Install it with:")
    print("    pip install Pillow --break-system-packages")
    sys.exit(1)

# ---------------------------------------------------------------------------
# CONFIGURATION -- edit these to fit your setup
# ---------------------------------------------------------------------------

# List of folders to scan. Each folder gets its own heading + grid of
# thumbnails on the single generated page.
FOLDERS = [
    "Prague1/",
    "Prague2/",
    "Cyprus/",
]

# Name of the HTML file that will be generated (written to the current
# working directory unless you make this an absolute path).
OUTPUT_FILE = "gallery.html"

# Subfolder name (created inside each of the folders above) where
# generated thumbnails are stored.
THUMB_DIR_NAME = "thumbnails"

# ---------------------------------------------------------------------------

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


PAGE_TEMPLATE = """<!DOCTYPE html>
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
        margin-bottom: 10px;
        font-weight: 300;
        letter-spacing: 1px;
        text-align: center;
        color: #222;
    }}

    section.folder-section {{
        width: 100%;
        max-width: calc(6 * var(--thumb-w) + 5 * 28px);
        margin-top: 50px;
    }}

    section.folder-section:first-of-type {{
        margin-top: 30px;
    }}

    h2.folder-heading {{
        font-weight: 400;
        font-size: 1.4rem;
        text-align: center;
        color: #222;
        border-bottom: 2px solid #eee;
        padding-bottom: 12px;
        margin-bottom: 26px;
    }}

    .gallery {{
        /* Centered, responsive grid: columns auto-adjust to window width,
           but never exceed 6 columns. */
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, var(--thumb-w)));
        gap: 28px;
        justify-content: center;
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
        font-size: 1rem;
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
{sections}
<footer>Generated by generate_gallery.py &middot; {folder_count} folder(s) &middot; {total_count} image(s)</footer>

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

SECTION_TEMPLATE = """<section class="folder-section">
    <h2 class="folder-heading">{folder_name}</h2>
    {content}
</section>
"""

ITEM_TEMPLATE = """    <figure style="margin:0;">
        <a class="thumb-link" href="{original_href}" onclick="openLightbox('{js_href}', '{js_alt}'); return false;">
            <img src="{thumb_href}" alt="{alt}" loading="lazy">
        </a>
        <figcaption class="caption">{alt}</figcaption>
    </figure>
"""


def js_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'")


def process_folder(folder: Path, output_dir: Path):
    """
    Generate thumbnails for every image in `folder` and return a list of
    dicts describing each image, with href paths made relative to
    `output_dir` (where the final HTML file will live).
    """
    thumb_dir = folder / THUMB_DIR_NAME
    images = find_images(folder)

    images_info = []
    for img_path in images:
        thumb_name = img_path.stem + "_thumb.jpg"
        thumb_path = thumb_dir / thumb_name
        try:
            make_thumbnail(img_path, thumb_path)
        except Exception as e:
            print(f"Skipping '{img_path.name}' in '{folder}': {e}")
            continue

        images_info.append(
            {
                "name": img_path.name,
                "original_href": os.path.relpath(img_path, output_dir),
                "thumb_href": os.path.relpath(thumb_path, output_dir),
            }
        )
        print(f"Thumbnail created: {thumb_path}")

    return images_info


def build_section(folder: Path, images_info):
    import html

    if images_info:
        items = "\n".join(
            ITEM_TEMPLATE.format(
                original_href=html.escape(info["original_href"], quote=True),
                thumb_href=html.escape(info["thumb_href"], quote=True),
                alt=html.escape(info["name"], quote=True),
                js_href=js_escape(info["original_href"]),
                js_alt=js_escape(info["name"]),
            )
            for info in images_info
        )
        content = f'<div class="gallery">\n{items}</div>'
    else:
        content = '<p class="empty">No images found in this folder.</p>'

    return SECTION_TEMPLATE.format(folder_name=html.escape(folder.name), content=content)


def main():
    if not FOLDERS:
        print("FOLDERS is empty. Edit the FOLDERS list at the top of this script.")
        sys.exit(1)

    output_path = Path(OUTPUT_FILE).expanduser().resolve()
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    sections_html = []
    total_count = 0

    for folder_str in FOLDERS:
        folder = Path(folder_str).expanduser().resolve()
        if not folder.is_dir():
            print(f"Warning: '{folder}' is not a valid directory. Skipping.")
            sections_html.append(
                SECTION_TEMPLATE.format(
                    folder_name=folder.name,
                    content='<p class="empty">Folder not found.</p>',
                )
            )
            continue

        images_info = process_folder(folder, output_dir)
        total_count += len(images_info)
        sections_html.append(build_section(folder, images_info))

    page = PAGE_TEMPLATE.format(
        title="Image Gallery",
        sections="\n".join(sections_html),
        folder_count=len(FOLDERS),
        total_count=total_count,
    )

    output_path.write_text(page, encoding="utf-8")
    print(f"\nGallery created: {output_path}")
    print(f"Open it in a browser to view {total_count} image(s) across {len(FOLDERS)} folder(s).")


if __name__ == "__main__":
    main()
