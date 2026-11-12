#!/usr/bin/env bash
# Run every Java sample in content/ and compare its output with the .expected file next to it.
# A post may only quote output that this script has reproduced.
set -euo pipefail
status=0
while IFS= read -r -d '' src; do
  expected="${src%.java}.expected"
  if [[ ! -f "$expected" ]]; then echo "MISSING $expected"; status=1; continue; fi
  if diff <(cd "$(dirname "$src")" && java "$(basename "$src")") "$expected" > /dev/null; then
    echo "ok   $src"
  else
    echo "FAIL $src: output differs from $(basename "$expected")"; status=1
  fi
done < <(find content -name '*.java' -print0)
exit $status
