# Standalone voting site

This package is a snapshot of one Krea2 experiment. It includes PHP, HTML, CSS, JavaScript, saved images and an initialized SQLite database. No ComfyUI, Python, Node.js, external API or model installation is required on the host.

## Hosting

Use PHP 8.1+ with PDO_SQLITE and PHP sessions enabled. Set your site's document root to the exported **public/** directory. Keep **private/** outside the document root. PHP needs write access to private/ and private/voting.sqlite for votes and SQLite journals.

On shared hosting, place the *contents* of public/ in public_html/, and place private/ beside public_html/ under the same parent. Do not upload private/ or this HOSTING.md inside public_html/. The private/.htaccess file is additional Apache protection, not a substitute for this layout.

For a local preview only, from the package directory run:

```text
php -S 127.0.0.1:8080 -t public
```

Then open http://127.0.0.1:8080/. Use your hosting provider's normal HTTPS configuration for public hosting; PHP's built-in server is for local testing.

## Voting

Visitors rate realism from 1 to 5. Model and generation labels are hidden by default, with an optional reveal checkbox. Scores can be changed; each browser receives one vote per image. The leaderboard reports vote count and average for images and generation configurations.

Identity uses a random browser cookie, stored in SQLite only as a keyed hash. No IP addresses are recorded by this application. Cookies, CSRF checks and a basic per-voter rate limit reduce accidental duplicates and simple abuse, but this is anonymous community voting, not verified one-person-one-vote: clearing cookies or switching browsers permits another identity. Your web host may maintain its own access logs.

## Administration and backups

Open admin.html and enter the admin access key below. You can download vote summaries as CSV or a full JSON backup containing votes, trials and run metadata. Keep the key private; it is never embedded in the public HTML/JavaScript. New exports generate new keys and fresh databases. Back up private/voting.sqlite on the host to retain votes. Replacing that database with a new export resets public votes.

Public vote totals start empty. Optional local reviews are stored separately and never counted as public votes. Prompts, generated images and generation labels are part of the published dataset; review them before hosting. This snapshot does not update automatically as the ComfyUI sweep generates more images.
