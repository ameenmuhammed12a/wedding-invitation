# Wedding Invitation + RSVP Backend

A responsive wedding invitation website with a built-in RSVP system, built with **Flask** and **SQLite**. Guests open the invitation, enter a short animated welcome, browse the story and gallery, and send their RSVP. The hosts view and export replies from a password-protected admin dashboard.

> **Note:** every name, photo, date and venue in this repository is a **placeholder**. Replace them with your own details before using it for a real event (see [Personalise the template](#personalise-the-template)).

---

## Features

**Invitation page**
- Animated welcome gate with an "Enter the invitation" button
- Hero section, story scenes and couple section
- Event cards (ceremony and reception) with **Get directions** links and **Add to calendar** (`.ics`) downloads
- Live **countdown** to the wedding date, plus a "journey" scene where the two figures walk closer as the date approaches
- Swipeable photo **gallery** with a full-screen lightbox
- Language switcher: English, Malayalam and Arabic (the Arabic view switches to right-to-left)
- Optional background music with a toggle button
- Share buttons: WhatsApp, copy link and native share
- Fully responsive, with reduced-motion support

**RSVP system**
- Attending or not attending
- Number of guests (1 to 4, including the person replying)
- Optional "Whose guest are you?" (bride's side, groom's side, or both)
- Optional message
- Retry protection: a network failure followed by a resubmit does not create duplicate rows

**Admin dashboard (`/admin`)**
- Password login (no username)
- Totals: replies, attending replies, total attending guests, unable to attend
- Filters by attendance and by side
- **CSV export** of all replies

**Security**
- Admin password stored only as a salted hash (PBKDF2-SHA256)
- CSRF protection on forms and the RSVP API
- Rate limits: 30 RSVP submissions per hour and 10 login attempts per 15 minutes, per IP (IP keys are hashed)
- Secure, HTTP-only, SameSite session cookies; admin sessions expire after 8 hours
- Request size limit (16 KB)
- CSV export neutralises spreadsheet formulas (text starting with `=`, `+`, `-` or `@` is prefixed with an apostrophe)
- Database file permissions set to owner-only

---

## Tech stack

| Part | Technology |
| --- | --- |
| Backend | Python 3.10+, Flask 3.1 |
| Database | SQLite (`instance/rsvp.sqlite3`) |
| Frontend | Plain HTML, CSS and JavaScript (no build step) |
| Fonts | Google Fonts (Cormorant Garamond, Jost, Amiri, Noto Sans Malayalam) |
| Hosting | Any WSGI host; PythonAnywhere instructions included below |

---

## Project structure

```
wedding_backend/
├── app.py              # Flask application (routes, database, security)
├── wsgi.py             # Production entry point
├── setup_admin.py      # Create or reset the admin password
├── backup_db.py        # Make a snapshot of the RSVP database
├── test_app.py         # Automated tests
├── requirements.txt
├── templates/
│   ├── index.html      # The invitation page
│   ├── base.html       # Admin layout
│   ├── login.html      # Admin login
│   └── admin.html      # Admin dashboard
├── static/
│   ├── admin.css
│   └── placeholder-*   # Placeholder images (replace with your own)
└── instance/           # Created at runtime: config + database (never commit)
```

---

## Quick start (run locally)

You need Python 3.10 or newer.

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

python setup_admin.py            # choose an admin password (12+ characters)
LOCAL_HTTP=1 python -m flask --app 'app:create_app' run --port 5050
```

On Windows PowerShell, set the variable first: `$env:LOCAL_HTTP=1`.

Then open:
- Invitation: `http://127.0.0.1:5050`
- Admin dashboard: `http://127.0.0.1:5050/admin`

Do not open `index.html` directly in the browser; it must be served by Flask. `LOCAL_HTTP=1` is for local testing only because it allows cookies over plain HTTP.

---

## Personalise the template

Edit `templates/index.html` and search for these placeholders:

| Placeholder | Replace with |
| --- | --- |
| `GROOM`, `BRIDE` | Your names (page title, hero, couple section) |
| `Groom & Bride` (the `COUPLE` variable in the script) | Names used in calendar files and share text |
| `CITY, COUNTRY` | Location shown on the hero section |
| `Nikah Venue Name, City`, `Reception Venue Name, City` | Venue names and addresses |
| `https://www.google.com/maps` | Your Google Maps links |
| `20 June 2027`, `20`, `JUNE<br>2027` | The displayed date |
| `2027-06-20T15:00:00Z` (and the other `2027-06-20...` dates) | Real start and end times in ISO format with your time zone, for example `2027-06-20T15:00:00+05:30` |
| `2026-11-01T00:00:00Z` | Start date of the "journey" animation |

Images live in `static/`. Replace the `placeholder-*` files with your own, keeping the same filenames, or update the paths in `templates/index.html`:

- `placeholder-couple.png` / `.webp`: transparent cut-out of the couple (hero)
- `placeholder-figure-a.*` and `placeholder-figure-b.*`: transparent full-length cut-outs for the journey scene
- `placeholder-portrait-a.jpg`, `placeholder-portrait-b.jpg`: story portraits
- `placeholder-couple-photo.jpg`: photo in the couple section
- `placeholder-gallery-1.jpg` to `placeholder-gallery-9.jpg`: gallery photos
- `music.mp3` (optional, not included): background music. If the file is missing, the page simply plays no music.

The greeting texts in English, Malayalam and Arabic are in the `i18n` object in the script at the bottom of `index.html`. Edit or remove languages as you like.

> **Privacy tip:** if you put real photos and details in the project, keep the repository **private**, or upload the real images directly to your server instead of committing them.

---

## Deploy on PythonAnywhere

1. Sign in to PythonAnywhere and open a **Bash console**.
2. Get the code:

   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git wedding_backend
   cd ~/wedding_backend
   ```

3. Create a virtual environment with a Python version that is also available in the Web tab (3.10 or newer). Example with 3.13:

   ```bash
   mkvirtualenv wedding-env --python=python3.13
   pip install -r requirements.txt
   python setup_admin.py
   ```

4. In **Web → Add a new web app**, choose **Manual configuration** and the **same Python version**.
5. Set **Source code** and **Working directory** to `/home/YOUR_USERNAME/wedding_backend`.
6. Set **Virtualenv** to `/home/YOUR_USERNAME/.virtualenvs/wedding-env`.
7. Open the **WSGI configuration file**, replace its contents with the following, and replace `YOUR_USERNAME`:

   ```python
   import sys

   project = '/home/YOUR_USERNAME/wedding_backend'
   if project not in sys.path:
       sys.path.insert(0, project)

   from app import create_app
   application = create_app()
   ```

8. Under **Static files**, map the URL `/static/` to `/home/YOUR_USERNAME/wedding_backend/static`.
9. Enable **Force HTTPS** and click **Reload**.
10. Open your site, send a test RSVP, then visit `/admin`, sign in and download a CSV. Also try it on your phone before sharing.

Do not use `flask run` or `app.run()` in production; PythonAnywhere runs the WSGI app for you.

Official reference: https://help.pythonanywhere.com/pages/Flask/

### Updating after code changes

```bash
cd ~/wedding_backend
git pull
```

Then click **Reload** in the Web tab. Do not delete or overwrite the `instance/` folder, because it holds your admin configuration and all RSVPs.

### Forgot the admin password?

```bash
workon wedding-env
cd ~/wedding_backend
python setup_admin.py
```

Choose a new password and reload the web app. Your RSVPs are kept and everyone is signed out.

---

## Data and backups

- Replies are stored in `instance/rsvp.sqlite3`, created when the app first starts.
- Private settings (secret key and password hash) are in `instance/config.json`.
- **Never commit `instance/`, `backups/` or any `.sqlite3` file.** The included `.gitignore` already excludes them.
- Export a CSV regularly from `/admin`. For a full snapshot, run `python backup_db.py`; the file is saved in the private `backups/` folder. Keep it private, since it contains guest names and messages.
- CSV notes: guest totals include the person replying, and times are in UTC.
- Names are not unique identifiers. A fresh page load can create a new reply even with the same name.

---

## Tests

```bash
python -m unittest -v test_app.py
```

The tests use temporary databases and never touch your real replies. They cover saving replies, declines, input validation, CSRF, admin access, safe display and export, filters, rate limits and retry protection.

---

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Error on startup: "Run python setup_admin.py first" | Run `python setup_admin.py`, then confirm the virtualenv and the WSGI path |
| Login does not stay signed in | Use the HTTPS address on the hosted site and refresh the form. Use `LOCAL_HTTP=1` only on your own computer |
| Missing pictures | Filenames in `static/` must match the paths in `templates/index.html` exactly, including capitalisation |
| No music | Add your own `static/music.mp3`. Some browsers also block autoplay until the guest taps the enter button |
| "Too many attempts" message | The rate limit was reached. Wait for the window to pass. Guests on the same shared network share a limit |
| Admin page looks unstyled | Check that the `/static/` mapping is set in the Web tab |

Check the **error log** in the PythonAnywhere Web tab for details on any server error.

---

## Limitations

- The rate limits are basic per-IP limits, not a CAPTCHA.
- The app does not send confirmation emails.
- The app is designed for a single event with a single admin password.
- Google Fonts are loaded from Google's servers, so fonts fall back to defaults when offline.

---

## Contributing

Issues and pull requests are welcome. Please keep example content generic and never commit real guest data, photos or private configuration.

## License

No license has been chosen yet. Add a `LICENSE` file (for example MIT) if you want others to reuse the code.
