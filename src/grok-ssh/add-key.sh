#!/bin/sh
# Adds voice-gated SSH key — no passphrase
echo "Add key: $(cat /dev/urandom | head -c 32 | blake3 | cut -c1-64)"
grok-ssh register --key "$1" --voice-gate "FORTRESS ON"