#!/bin/sh
# Signs commit if 3+ voices match
if [ "$(grok-ssh verify -n 3)" = "APPROVED" ]; then
  git commit -S --amend -m "🔐 All hands in"
fi
