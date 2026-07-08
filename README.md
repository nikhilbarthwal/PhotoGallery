### Instructions

- **To typecheck code:** `uv run pyright`
- **To run code:** `uv run python src/main.py`

### ToDo:
- Fix typing
- Update config and test albums working
- Create Dataclasses
- create Sidepage with main template
- Create mainpage
- Pass sidepage and create content
- create album

### DataClasses
- content = list(gallery)
- gallery = { name, filename, list(albums) }
- album = { name, list(photo) }
- photo = { filename , description }

### Templates
- main = sidebar, content
- content = list(sections)
- section = almbul with photos
