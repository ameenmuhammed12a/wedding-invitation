import sqlite3
from pathlib import Path
from datetime import datetime, timezone
root=Path(__file__).resolve().parent
source=root/'instance/rsvp.sqlite3'
if not source.exists(): raise SystemExit('No RSVP database yet. Start the app first.')
folder=root/'backups'
folder.mkdir(mode=0o700, exist_ok=True)
output=folder/('rsvp-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
with sqlite3.connect(source) as src, sqlite3.connect(output) as dst: src.backup(dst)
output.chmod(0o600)
print('Backup saved:',output)
