"""Create or reset the admin password, preserving all RSVPs."""
import getpass
import json
import os
import secrets
from pathlib import Path
from werkzeug.security import generate_password_hash

if __name__ == '__main__':
    password = getpass.getpass('Choose an admin password (at least 12 characters): ')
    if len(password) < 12:
        raise SystemExit('Password must contain at least 12 characters.')
    if password != getpass.getpass('Confirm password: '):
        raise SystemExit('Passwords do not match. Nothing changed.')
    folder = Path(__file__).resolve().parent / 'instance'
    folder.mkdir(mode=0o700, exist_ok=True)
    # Rotate the signing key on password reset; RSVP records remain untouched.
    config = {'secret_key': secrets.token_hex(32), 'admin_hash': generate_password_hash(password, method='pbkdf2:sha256:1000000')}
    temporary = folder / ('config-' + secrets.token_hex(8) + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(config, f)
    os.replace(temporary, folder / 'config.json')
    print('Admin password saved. Reload your PythonAnywhere web app. Existing RSVPs are preserved.')
