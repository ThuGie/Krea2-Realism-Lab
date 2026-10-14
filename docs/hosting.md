# Hosting a voting website

[← Back to the README](../README.md)

## Export a complete community voting website

Open **Export a standalone voting website**, select a saved run, and click **Build voting website ZIP**. Each export contains:

```text
public/
  index.html, app.js, style.css     Voting gallery and community leaderboards
  api.php                          PHP API for votes, sessions and administration
  admin.html, admin.js              Admin login and CSV/JSON downloads
  images/                          Copies of this run's saved images
private/
  voting.sqlite                    Initialized database; public votes start empty
  config.php                       Unique export secret and hashed admin key
  run.json                         Original run settings and checkpoint snapshot
  disabled_pairs.json              Exclusion snapshot
  failures.jsonl                   Failure log, when present
HOSTING.md                         Deployment instructions and private admin key
manifest.json                      Export summary
```

The export is independent of ComfyUI. Host it with **PHP 8.1+ and PDO_SQLITE**, with **public/** as the web root and **private/** outside it. On shared hosting, copy public/'s contents into public_html/ and place private/ beside public_html/. Give PHP write access to private/ and the database. Keep HOSTING.md private because it contains the admin key. For a local preview, extract the ZIP and run `php -S 127.0.0.1:8080 -t public` from its directory.

Visitors rate images from 1 to 5, can update their ratings, and can compare image/configuration leaderboards. Blind review is enabled initially. Voting identity is a random browser cookie, stored only as a keyed hash; the application does not store IP addresses. This limits accidental duplicate votes, not determined ballot manipulation: clearing cookies or changing browsers creates another identity. CSRF validation, prepared queries and basic rate limiting are included.

The admin key in HOSTING.md opens admin.html, where summaries can be downloaded as CSV and the whole voting dataset as JSON. Back up private/voting.sqlite to preserve public votes. Replacing it with a fresh export resets them.

Exports are **snapshots** of saved images, including partial/running sweeps. Disabled-pair images are omitted unless requested. Local reviews/notes are also excluded unless explicitly included; they never count as community votes. Prompts, images and generation settings are exported. Missing images are counted in manifest.json. Each run has its own dataset; matching saved trials can appear in multiple overlapping run snapshots. ZIP files remain in `krea2_lab/exports/` for download and backup.

