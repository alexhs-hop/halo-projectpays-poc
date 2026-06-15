#!/usr/bin/env bash
# Do NOT use `set -e` — we must run past a failing pytest to write reward=0.
set -uo pipefail

cd /tests
pytest --ctrf /logs/verifier/ctrf.json test_ktrans.py -v -rA
rc=$?

mkdir -p /logs/verifier
if [ $rc -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $rc
