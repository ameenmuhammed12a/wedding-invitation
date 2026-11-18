# Wedding invitation + RSVP backend (Flask + SQLite)

A wedding invitation page connected to Flask and SQLite. It supports attendance, total guests (1–4 including the respondent), optional bride/groom/both affiliation, and a message. The shared venue does not require separate forms. `/admin` has password login, guest totals, filters, and CSV download. No email service is needed. It does not send email confirmations.

## 1. Personalise the template

This repository ships with **placeholder** names, dates, venues and images so it is safe to publish. Before using it for a real event:

- **Names, venues, date, map links:** edit `templates/index.html` (search for `GROOM`, `BRIDE`, `CITY, COUNTRY`, `Nikah Venue Name`, `Reception Venue Name`, `2027-06-20` and `https://www.google.com/maps`).
- **Images:** replace the `static/placeholder-*` files with your own (keep the same filenames, or update the paths in `templates/index.html`). `placeholder-figure-a/b` and `placeholder-couple` are transparent cut-outs in both `.png` and `.webp`.
- **Music (optional):** add your own `static/music.mp3`. If the file is missing the page simply plays no music.
- **Keep real photos out of a public repo.** Add them to `static/` only on your server, or keep the repository private.

## 2. Run on your Mac first (optional)

Use Python 3.10 or newer. In Terminal, enter the extracted project folder:

```bash
cd ~/Downloads/wedding_backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python setup_admin.py
LOCAL_HTTP=1 python -m flask --app 'app:create_app' run --port 5050
```

Choose your own password when asked. Password typing is hidden. Open `http://127.0.0.1:5050` in your browser, then `http://127.0.0.1:5050/admin` for the dashboard. Do not open index.html directly. Stop the local server with Ctrl+C. LOCAL_HTTP is for local testing only.

## 3. Upload to PythonAnywhere

1. Sign in to PythonAnywhere. In **Files**, upload `wedding_backend.zip` into your home folder. Open a **Bash console**.
2. Extract the ZIP (for a fresh installation):

```bash
unzip wedding_backend.zip
cd ~/wedding_backend
```

3. Create a virtual environment using a Python version available both in the Bash console and in the Web tab's version selector. Example with Python 3.13 (use another available Python 3.10+ version if needed):

```bash
mkvirtualenv wedding-env --python=python3.13
pip install -r requirements.txt
python setup_admin.py
```

4. In **Web → Add a new web app**, choose **Manual configuration**, then the **same Python version** used above.
5. Set **Source code** and **Working directory** to `/home/YOUR_USERNAME/wedding_backend`.
6. Set **Virtualenv** to `/home/YOUR_USERNAME/.virtualenvs/wedding-env`.
7. Open the Web tab's **WSGI configuration file**, replace its example content with this code, and replace YOUR_USERNAME:

```python
import sys

project = '/home/YOUR_USERNAME/wedding_backend'
if project not in sys.path:
    sys.path.insert(0, project)

from app import create_app
application = create_app()
```

8. Under **Static files**, map URL `/static/` to directory `/home/YOUR_USERNAME/wedding_backend/static`.
9. Enable **Force HTTPS**, then click **Reload**. Use the HTTPS address shown in your Web tab. Do not run `flask run` or `app.run()` for production; PythonAnywhere serves the WSGI application.
10. Open your invitation and send a test RSVP. Visit your site's `/admin`, sign in, confirm the name and guest count, and download a CSV. Try the invitation on your phone before sharing it.

Official deployment reference: https://help.pythonanywhere.com/pages/Flask/

## Forgot the admin password?

In a PythonAnywhere Bash console:

```bash
workon wedding-env
cd ~/wedding_backend
python setup_admin.py
```

Choose a new password, then reload the app in the Web tab. This keeps your RSVPs and signs everyone out. No username is required; the admin login uses the password you chose.

## Data and backups

- Replies are stored in `instance/rsvp.sqlite3`, created when the app first starts.
- Private configuration is `instance/config.json`. Never place the instance folder in static or upload it to a public repository.
- Export CSV regularly from `/admin`. For a complete database snapshot, run `python backup_db.py` and download the resulting file from the private `backups/` folder. Keep it private because it contains guest names and messages.
- When updating the application, preserve your existing `instance/` folder. Do not overwrite or delete it. This delivery contains no configured password or live guest database.
- Retry protection prevents duplicate rows from the same in-page submission after a network failure. A fresh page/new submission can create a new reply; names are not unique identifiers.
- Basic per-IP limits allow 30 submissions/hour and 10 login attempts/15 minutes. They are not a CAPTCHA; shared networks may hit the same limit. IP keys are hashed. No forwarded headers are trusted.
- Existing replies stored only in visitors' localStorage by the old HTML are not imported automatically.

## Troubleshooting

- **Error on startup:** run setup_admin.py, verify the virtualenv and WSGI path, then inspect the Web tab error log.
- **Missing pictures:** check that the filenames in `static/` match the paths in `templates/index.html` exactly.
- **Session expired / login does not stick:** use HTTPS on the hosted site; refresh the form. Use LOCAL_HTTP=1 only on your local computer.
- **CSV:** guest totals include the person replying. Times are UTC. Text that could be a spreadsheet formula is prefixed with an apostrophe.

## Tests

```bash
python -m unittest -v test_app.py
```

Tests use temporary databases and do not modify your real replies. They cover persistent saves, declines, invalid input, CSRF, admin access, safe display/export, filters, rate limits and retry protection. Deployment and final visual/media verification must still be performed after upload.
