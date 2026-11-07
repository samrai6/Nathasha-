#!/usr/bin/env bash
set -Eeuo pipefail

# Fail early with a clear message when a required Koyeb secret is missing.
required_vars=(BOT_TOKEN OWNER_ID TELEGRAM_API TELEGRAM_HASH)
missing=()
for name in "${required_vars[@]}"; do
    if [[ -z "${!name:-}" ]]; then
        missing+=("$name")
    fi
done

if (( ${#missing[@]} > 0 )); then
    printf 'ERROR: Missing required environment variable(s): %s\n' "${missing[*]}" >&2
    exit 1
fi

echo "Starting WZML-X setup..."
python3 update.py

echo "Starting Telegram bot..."
exec python3 -m bot
