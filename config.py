#!/usr/bin/env python3
"""
generate_gallery.py

Scans multiple folders for images, copies the originals and generates
300x200 thumbnails (center-cropped to a 3:2 aspect ratio, clipping
top/bottom or left/right as needed) into a single OUTPUT folder, and
builds an index.html page (inside that OUTPUT folder) that displays
every source folder's images in its own responsive, centered grid --
with the folder name as a heading above each grid. Clicking a thumbnail
expands the original image in place (lightbox) with left/right arrows
to move to the previous/next image (hidden at the start/end of that
folder's images); clicking again returns to the gallery.

>>> Edit the FOLDERS list and OUTPUT folder name below <<<

Requires: Pillow  (pip install Pillow --break-system-packages)
"""

import os
import shutil
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
FOLDERS = ["Berlin1/", "Berlin2/", "Berlin3/", "Berlin4/", "Berlin5/"]

# Folder where everything gets written: the generated HTML file
# (as index.html), copies of all original images, and their thumbnails.
# Created automatically if it doesn't already exist.
OUTPUT = "/home/nikhil/Workspace/Homepage/photos/"

# Subfolder name (created inside OUTPUT, under each source folder's own
# subfolder) where generated thumbnails are stored.
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

    .lightbox-content {{
        display: flex;
        flex-direction: column;
        align-items: center;
        max-width: 92vw;
        max-height: 92vh;
        cursor: default;
    }}

    .lightbox-content img {{
        max-width: 92vw;
        max-height: 82vh;
        object-fit: contain;
        border-radius: 6px;
        box-shadow: 0 0 40px 10px rgba(0, 0, 0, 0.6);
        display: block;
    }}

    .lightbox-caption {{
        margin-top: 16px;
        color: #fff;
        font-size: 1rem;
        text-align: center;
        max-width: 92vw;
        word-break: break-word;
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

    .lightbox-arrow {{
        position: fixed;
        top: 50%;
        transform: translateY(-50%);
        font-size: 3rem;
        color: #fff;
        cursor: pointer;
        user-select: none;
        opacity: 0.7;
        padding: 10px 18px;
        line-height: 1;
        z-index: 1001;
    }}

    .lightbox-arrow:hover {{
        opacity: 1;
    }}

    .lightbox-arrow.left {{
        left: 10px;
    }}

    .lightbox-arrow.right {{
        right: 10px;
    }}

    .lightbox-arrow.hidden {{
        display: none;
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
    <span class="lightbox-arrow left" id="lightbox-prev" onclick="prevImage(event)">&#10094;</span>
    <div class="lightbox-content" onclick="event.stopPropagation()">
        <img id="lightbox-img" src="" alt="">
        <div class="lightbox-caption" id="lightbox-caption"></div>
    </div>
    <span class="lightbox-arrow right" id="lightbox-next" onclick="nextImage(event)">&#10095;</span>
</div>

<script>
    const GALLERIES = {galleries_json};
    let curSection = -1;
    let curIndex = -1;

    function showImage() {{
        const list = GALLERIES[curSection];
        const item = list[curIndex];
        const img = document.getElementById('lightbox-img');
        const caption = document.getElementById('lightbox-caption');
        img.src = item.src;
        img.alt = item.alt;
        caption.textContent = item.alt;

        const prevBtn = document.getElementById('lightbox-prev');
        const nextBtn = document.getElementById('lightbox-next');
        prevBtn.classList.toggle('hidden', curIndex <= 0);
        nextBtn.classList.toggle('hidden', curIndex >= list.length - 1);
    }}

    function openLightbox(section, index) {{
        curSection = section;
        curIndex = index;
        const lb = document.getElementById('lightbox');
        showImage();
        lb.classList.add('open');
        document.body.style.overflow = 'hidden';
    }}

    function closeLightbox() {{
        const lb = document.getElementById('lightbox');
        lb.classList.remove('open');
        document.body.style.overflow = '';
    }}

    function prevImage(event) {{
        event.stopPropagation();
        if (curIndex > 0) {{
            curIndex -= 1;
            showImage();
        }}
    }}

    function nextImage(event) {{
        event.stopPropagation();
        const list = GALLERIES[curSection];
        if (curIndex < list.length - 1) {{
            curIndex += 1;
            showImage();
        }}
    }}

    document.addEventListener('keydown', function (e) {{
        const lb = document.getElementById('lightbox');
        if (!lb.classList.contains('open')) return;
        if (e.key === 'Escape') {{
            closeLightbox();
        }} else if (e.key === 'ArrowLeft') {{
            prevImage(e);
        }} else if (e.key === 'ArrowRight') {{
            nextImage(e);
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
        <a class="thumb-link" href="{original_href}" onclick="openLightbox({section_idx}, {item_idx}); return false;">
            <img src="{thumb_href}" alt="{alt}" loading="lazy">
        </a>
        <figcaption class="caption">{alt}</figcaption>
    </figure>
"""


def process_folder(folder: Path, dest_dir: Path):
    """
    Copy every image in `folder` into `dest_dir`, generate a thumbnail for
    each (stored under dest_dir/THUMB_DIR_NAME), and return a list of dicts
    describing each image with hrefs relative to the OUTPUT folder (i.e.
    relative to where index.html lives).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir = dest_dir / THUMB_DIR_NAME

    images = find_images(folder)

    images_info = []
    for img_path in images:
        dest_img_path = dest_dir / img_path.name
        try:
            shutil.copy2(img_path, dest_img_path)
        except Exception as e:
            print(f"Skipping '{img_path.name}' in '{folder}': could not copy ({e})")
            continue

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
                "original_href": os.path.relpath(dest_img_path, dest_dir.parent),
                "thumb_href": os.path.relpath(thumb_path, dest_dir.parent),
            }
        )
        print(f"Copied original + thumbnail: {img_path.name}")

    return images_info


def unique_subfolder_name(base_name: str, used_names: set) -> str:
    """Return `base_name`, or `base_name_2`, `base_name_3`, ... if taken."""
    name = base_name
    counter = 2
    while name in used_names:
        name = f"{base_name}_{counter}"
        counter += 1
    used_names.add(name)
    return name


def build_section(folder: Path, images_info, section_idx: int):
    import html

    if images_info:
        items = "\n".join(
            ITEM_TEMPLATE.format(
                original_href=html.escape(info["original_href"], quote=True),
                thumb_href=html.escape(info["thumb_href"], quote=True),
                alt=html.escape(info["name"], quote=True),
                section_idx=section_idx,
                item_idx=item_idx,
            )
            for item_idx, info in enumerate(images_info)
        )
        content = f'<div class="gallery">\n{items}</div>'
    else:
        content = '<p class="empty">No images found in this folder.</p>'

    return SECTION_TEMPLATE.format(folder_name=html.escape(folder.name), content=content)


def main():
    if not FOLDERS:
        print("FOLDERS is empty. Edit the FOLDERS list at the top of this script.")
        sys.exit(1)

    import json

    output_dir = Path(OUTPUT).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"

    sections_html = []
    galleries_data = []  # list of lists of {"src":..., "alt":...} -> one list per folder/section
    total_count = 0
    used_names = set()

    for section_idx, folder_str in enumerate(FOLDERS):
        folder = Path(folder_str).expanduser().resolve()
        if not folder.is_dir():
            print(f"Warning: '{folder}' is not a valid directory. Skipping.")
            sections_html.append(
                SECTION_TEMPLATE.format(
                    folder_name=folder.name,
                    content='<p class="empty">Folder not found.</p>',
                )
            )
            galleries_data.append([])
            continue

        subfolder_name = unique_subfolder_name(folder.name, used_names)
        dest_dir = output_dir / subfolder_name

        images_info = process_folder(folder, dest_dir)
        total_count += len(images_info)
        sections_html.append(build_section(folder, images_info, section_idx))
        galleries_data.append(
            [{"src": info["original_href"], "alt": info["name"]} for info in images_info]
        )

    # Embed the per-section image lists as JSON for the lightbox's prev/next
    # navigation. Escape "</" so a filename can never prematurely close the
    # surrounding <script> tag.
    galleries_json = json.dumps(galleries_data).replace("</", "<\\/")

    page = PAGE_TEMPLATE.format(
        title="Image Gallery",
        sections="\n".join(sections_html),
        folder_count=len(FOLDERS),
        total_count=total_count,
        galleries_json=galleries_json,
    )

    output_path.write_text(page, encoding="utf-8")
    print(f"\nGallery created: {output_path}")
    print(f"Open it in a browser to view {total_count} image(s) across {len(FOLDERS)} folder(s).")


if __name__ == "__main__":
    main()
