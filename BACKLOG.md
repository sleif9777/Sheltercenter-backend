# Backlog

- **`import_dogs`: report progress while it runs.** The command is silent until it finishes unless debug output is on, so a long run looks the same as a hung one. Print a flushed progress line per page fetched in `_import_all_animals` (e.g. `Page 3/12 — 300/1,180 animals`) and a summary per phase (fetch IDs, import, deactivate, notify).
