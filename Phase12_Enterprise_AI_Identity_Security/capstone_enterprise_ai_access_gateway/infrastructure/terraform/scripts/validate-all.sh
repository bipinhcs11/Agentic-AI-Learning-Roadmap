#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MODULE_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

terraform fmt -check -recursive "$MODULE_DIR"
python3 -m unittest discover -s "$MODULE_DIR/tests" -p 'test_*.py' -q

for track in aws azure gcp; do
  terraform -chdir="$MODULE_DIR/$track" init -backend=false -input=false
  terraform -chdir="$MODULE_DIR/$track" validate
  terraform -chdir="$MODULE_DIR/$track" test
done
