# Repository multi-file import — 2026-10-30

- Repository Add Test Case opens a multiple .py file chooser. Capture the selected destination once, then import each file through the existing validated single-file API. Each successful file remains an independent source generation; existing versions and Plan copies are unchanged.
- Show a result dialog with filename, per-file status, errors and total imported/failed counts. Continue after an invalid file; successful imports are retained. No automatic retry of potentially committed network failures. Close/Escape are blocked while processing; leaving/reloading the page prompts while imports are active.
- Keep the shared direct Plan picker single-file. No backend changes or formal database mutation during validation; browser refresh loads this update.
- PASS: JavaScript syntax; repository_multi_import.test.cjs (multiple selection, captured folder, UTF-8, invalid middle file, continued import, summary, refreshed list, busy-close guard, subsequent import). Uses mock APIs only.
