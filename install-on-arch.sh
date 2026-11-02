#!/usr/bin/env bash
# Back-compat wrapper — use setup.sh.
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/setup.sh" "$@"
