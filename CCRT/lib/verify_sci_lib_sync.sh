#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# verify_sci_lib_sync.sh [PAYLOAD_DIR] — fail-closed gate on the shared identity module.
#
# sci-file-index and sci-library-curate each carry an INLINED copy of sci_lib_common.py between
#   # ==== BEGIN GENERATED sci_lib_common vX sha=YYYYYYYY ... ====
#   # ==== END GENERATED sci_lib_common ====
# markers. The two copies MUST be byte-identical (same version + same sha), or the two tools would
# normalize author/title/DOI differently and dedup/rename would silently diverge. This gate proves
# they agree WITHOUT needing the canonical source shipped in the toolkit: it extracts the sha= stamp
# from each script and fails if they differ or are missing.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PAYLOAD="${1:-$SCRIPT_DIR/../payload}"
SFI="$PAYLOAD/skills/sci-file-index/sci_file_index.py"
SLC="$PAYLOAD/skills/sci-library-curate/sci_library_curate.py"

stamp(){  # $1 = script path -> prints "vX sha=YYYYYYYY" or empty
  [ -f "$1" ] || return 0
  grep -oE '# ==== BEGIN GENERATED sci_lib_common v[^ ]+ sha=[0-9a-f]+' "$1" \
    | head -1 | sed -E 's/.*(v[^ ]+) (sha=[0-9a-f]+).*/\1 \2/'
}

# --- self-test: prove a mismatch is caught and a match passes -----------------
if [ "${1:-}" = "--self-test" ]; then
  TD="$(mktemp -d)"; trap 'rm -rf "$TD"' EXIT
  mkdir -p "$TD/payload/skills/sci-file-index" "$TD/payload/skills/sci-library-curate"
  printf '# ==== BEGIN GENERATED sci_lib_common v3 sha=deadbeef -- x ====\n' > "$TD/payload/skills/sci-file-index/sci_file_index.py"
  printf '# ==== BEGIN GENERATED sci_lib_common v3 sha=cafef00d -- x ====\n' > "$TD/payload/skills/sci-library-curate/sci_library_curate.py"
  if bash "$SCRIPT_DIR/verify_sci_lib_sync.sh" "$TD/payload" >/dev/null 2>&1; then
    echo "SELF-TEST FAIL: mismatched shas were NOT caught"; exit 1
  fi
  printf '# ==== BEGIN GENERATED sci_lib_common v3 sha=deadbeef -- x ====\n' > "$TD/payload/skills/sci-library-curate/sci_library_curate.py"
  if bash "$SCRIPT_DIR/verify_sci_lib_sync.sh" "$TD/payload" >/dev/null 2>&1; then
    echo "SELF-TEST OK: matching shas pass, mismatch fails"; exit 0
  else
    echo "SELF-TEST FAIL: matching shas were rejected"; exit 1
  fi
fi

A="$(stamp "$SFI")"; B="$(stamp "$SLC")"
if [ -z "$A" ] || [ -z "$B" ]; then
  echo "FATAL: sci_lib_common GENERATED marker missing (sci-file-index='$A' sci-library-curate='$B')"; exit 1
fi
if [ "$A" != "$B" ]; then
  echo "FATAL: sci_lib_common drift — sci-file-index has [$A] but sci-library-curate has [$B]."
  echo "       Both must inline the SAME module version+sha. Re-run build_sci_lib.py against the canonical module."
  exit 1
fi
echo "sci_lib_common in sync: $A (both skills)"
