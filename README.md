Now update `process_folder` to copy originals into the output folder and generate thumbnails there, using a unique per-folder subfolder name.Now update `main()` to set up the OUTPUT folder, allocate unique subfolder names per source folder, and write `index.html` inside it.Now let's update the module docstring to reflect the new behavior, then test.Now let's test the full flow.All originals and thumbnails are self-contained in `gallery_output/` with `index.html`. Let's verify the paths inside the HTML resolve correctly.Everything resolves correctly relative to `index.html`. Cleaning up and finalizing.Added the **`OUTPUT`** variable — the whole gallery is now self-contained in one folder:

```python
OUTPUT = "gallery_output"
```

When you run the script it now creates:
```
gallery_output/
├── index.html
├── test_a/                  (named after your source folder, deduped if names clash)
│   ├── a0.jpg                (original, copied)
│   ├── a1.jpg
│   └── thumbnails/
│       ├── a0_thumb.jpg
│       └── a1_thumb.jpg
└── test_b/
    ├── b0.jpg
    └── thumbnails/
        └── b0_thumb.jpg
```

Key points:
- Originals are **copied** (not just referenced) into `OUTPUT/<folder_name>/`, so the whole thing is portable — you can zip up `gallery_output` and it'll work anywhere.
- Thumbnails go into `OUTPUT/<folder_name>/thumbnails/`.
- The generated page is always named **`index.html`**, written directly inside `OUTPUT`.
- If two folders in `FOLDERS` happen to share the same name, the script automatically appends `_2`, `_3`, etc. to avoid overwriting.
- All arrow-navigation, lightbox, headings, grid layout, etc. from before still work exactly the same.

