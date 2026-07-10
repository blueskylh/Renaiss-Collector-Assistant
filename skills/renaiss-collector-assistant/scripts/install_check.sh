#!/usr/bin/env bash
set -euo pipefail
printf 'Checking Node.js...\n'
node --version
npm --version
NODE_MAJOR=$(node --version | sed 's/v//' | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 22 ]; then
  echo "Node.js >=22 is required for Renaiss CLI." >&2
  exit 1
fi
printf 'Checking Renaiss CLI via npx...\n'
npx --yes renaiss --help >/tmp/renaiss_help.txt
head -40 /tmp/renaiss_help.txt
printf '\nOK: Renaiss CLI is reachable.\n'
