#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SKILL_DIR"

printf 'Checking Node.js...\n'
node --version
npm --version
NODE_MAJOR=$(node --version | sed 's/v//' | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 22 ]; then
  echo "Node.js >=22 is required for Renaiss CLI." >&2
  exit 1
fi

printf '\nChecking Python...\n'
python3 --version
python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit('Python >=3.11 is required for Renaiss Collector Assistant scripts.')
PY
python3 -m py_compile scripts/*.py

printf '\nChecking .env loading behavior...\n'
python3 - <<'PY'
from pathlib import Path
import tempfile, os, sys
sys.path.insert(0, str(Path('scripts').resolve()))
from common_env import load_dotenv_files
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / '.env'
    p.write_text('RENAISS_ENV_LOAD_TEST=ok\n')
    load_dotenv_files([p], override=True)
    assert os.getenv('RENAISS_ENV_LOAD_TEST') == 'ok'
print('OK: .env loader works')
PY

printf '\nChecking optional Alchemy configuration...\n'
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path('scripts').resolve()))
import bsc_wallet_analyzer as wallet
if wallet.is_alchemy_configured():
    print('OK: Alchemy BNB Mainnet RPC is configured (value hidden)')
else:
    print('INFO: ALCHEMY_API_KEY / ALCHEMY_BNB_RPC_URL not set; wallet-report will ask for an Alchemy key or use another available history source.')
PY

printf '\nChecking Renaiss CLI via npx...\n'
TMP_HELP=$(mktemp)
npx --yes renaiss --help >"$TMP_HELP"
head -40 "$TMP_HELP"
rm -f "$TMP_HELP"
printf '\nOK: Renaiss CLI is reachable and Python scripts compile.\n'
