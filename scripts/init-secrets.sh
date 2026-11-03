#!/usr/bin/env bash
# Generates the database password once. The file is ignored by Git.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p secrets
if [ ! -s secrets/db_password.txt ]; then
  head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n' > secrets/db_password.txt
  echo "Generated secrets/db_password.txt"
fi
