# Documentation screenshots

These are browser captures of the real interface, using synthetic records and original SVG illustrations. They contain no user images, reviews, local installation paths or private runs. The illustrations demonstrate layout, not Krea2 output quality.

To refresh them:

1. Run `python tools/screenshot_demo.py` from the repository root.
2. Open `http://127.0.0.1:8198/krea2-lab` in a browser at a 1600 × 1050 viewport.
3. Choose **LoRAs + strengths only**, name the experiment **Natural light study**, and set strengths to `0.5, 0.75, 1`.
4. Use the mountain-lake prompt from the demo records. Capture the workspace at the top of the page.
5. Select three gallery images, open comparison and choose three columns. Capture the comparison dialog.
6. Open **Display & accessibility**. Choose OpenDyslexic, light appearance, green accents, large text and extra reading space. Capture the header and settings panel.

The demo server is read-only, binds only to localhost, and never connects to ComfyUI. Stop it with Ctrl+C when finished.
