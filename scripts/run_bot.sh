#!/usr/bin/env bash

# Run the bot.
#
# This script is intended for developer testing purposes. Actual use is advised via Docker as documented in the readme.
#
# Usage:
# Customize IRC_PASSWORD below, but do not checkin the password into version control.
# Run: ./scripts/run_bot.sh

IRC_PASSWORD=YourActualPassword
CONFIG_PATH="/workspaces/irc-bots/libera/feed-bot/config.yaml"

python -m ircrssfeedbot --config-path "${CONFIG_PATH}"
