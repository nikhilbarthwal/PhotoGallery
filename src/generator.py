#!/usr/bin/env python3
"""
generate_gallery.py

Scans multiple config.folders for images, copies the originals and generates
300x200 thumbnails (center-cropped to a 3:2 aspect ratio, clipping
top/bottom or left/right as needed) into a single OUTPUT folder, and
builds an index.html page (inside that OUTPUT folder) that displays
every source folder's images in its own responsive, centered grid --
with the folder name as a heading above each grid. Clicking a thumbnail
expands the original image in place (lightbox) with left/right arrows
to move to the previous/next image (hidden at the start/end of that
folder's images); clicking again returns to the gallery.


Requires: Pillow  (pip install Pillow --break-system-packages)
"""

import os
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageOps
import template
import config
from typing import List, Dict
import json


ratio = config.thumbs_width / config.thumbs_height

def find_images(folder: Path) -> List[Path]:
    """Return a sorted list of image files directly inside `folder`."""
    images: List[Path] = []
    for entry in sorted(folder.iterdir()):
        if entry.is_file() and entry.suffix.lower() in config.extensions:
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

        if src_ratio > ratio:
            # Image is wider than 3:2 -> clip left/right, keep full height.
            new_w = int(round(h * ratio))
            offset = (w - new_w) // 2
            box = (offset, 0, offset + new_w, h)
        else:
            # Image is taller than (or equal to) 3:2 -> clip top/bottom.
            new_h = int(round(w / ratio))
            offset = (h - new_h) // 2
            box = (0, offset, w, offset + new_h)

        cropped = im.crop(box)
        thumb = cropped.resize((config.thumbs_width, config.thumbs_height),
                               Image.LANCZOS)

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        # Always save thumbnails as JPEG for consistent small file size.
        thumb.save(dst_path, "JPEG", quality=85)


def process_folder(folder: Path, dest_dir: Path) -> List[Dict[str, str]]:
    """
    Copy every image in `folder` into `dest_dir`, generate a thumbnail for each (
    stored under dest_dir/thumb_dir), and return a list of dicts describing each
    image with hrefs relative to the OUTPUT folder (i.e. relative to where
    index.html lives).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir = dest_dir / config.thumbs_dir

    images: List[Path] = find_images(folder)

    images_info: List[Dict[str, str]] = []
    for img_path in images:
        dest_img_path: Path = dest_dir / img_path.name
        try:
            shutil.copy2(img_path, dest_img_path)
        except Exception as e:
            print(f"Skipping '{img_path.name}' in '{folder}': could not copy ({e})")
            continue

        thumb_name: str = img_path.stem + "_thumb.jpg"
        thumb_path: Path = thumb_dir / thumb_name
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


def unique_subfolder_name(base_name: str, used_names: set[str]) -> str:
    """Return `base_name`, or `base_name_2`, `base_name_3`, ... if taken."""
    name: str = base_name
    counter: int = 2
    while name in used_names:
        name: str = f"{base_name}_{counter}"
        counter += 1
    used_names.add(name)
    return name


def build_section(folder: Path, images_info: List[Dict[str, str]], section_idx: int) -> str:
    import html

    if images_info:
        items = "\n".join(
            template.item.format(
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

    return template.section.format(folder_name=html.escape(folder.name),
                                   content=content)


def main():
    if not config.folders:
        print("config.folders is empty. Edit the config.folders list.")
        sys.exit(1)

    output_dir = Path(config.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"

    # list of lists of {"src":..., "alt":...} -> one list per folder/section
    galleries_data: List[List[Dict[str, str]]] = []
    sections_html: List[str] = []
    total_count: int = 0
    used_names: set[str] = set()

    for section_idx, folder_str in enumerate(config.folders):
        folder = Path(folder_str).expanduser().resolve()
        if not folder.is_dir():
            print(f"Warning: '{folder}' is not a valid directory. Skipping.")
            sections_html.append(
                template.section.format(
                    folder_name=folder.name,
                    content='<p class="empty">Folder not found.</p>',
                )
            )
            galleries_data.append([])
            continue

        subfolder_name: str = unique_subfolder_name(folder.name, used_names)
        dest_dir: Path = output_dir / subfolder_name

        images_info: List[Dict[str, str]] = process_folder(folder, dest_dir)
        total_count += len(images_info)
        sections_html.append(build_section(folder, images_info, section_idx))
        galleries_data.append(
            [{"src": info["original_href"], "alt": info["name"]}
             for info in images_info]
        )

    # Embed the per-section image lists as JSON for the lightbox's prev/next
    # navigation. Escape "</" so a filename can never prematurely close the
    # surrounding <script> tag.
    galleries_json = json.dumps(galleries_data).replace("</", "<\\/")

    page = template.page.format(
        title="Image Gallery",
        sections="\n".join(sections_html),
        folder_count=len(config.folders),
        total_count=total_count,
        galleries_json=galleries_json,
    )

    output_path.write_text(page, encoding="utf-8")
    print(f"\nGallery created: {output_path}")


if __name__ == "__main__":
    main()
