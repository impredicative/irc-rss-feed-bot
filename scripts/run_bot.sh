#!/usr/bin/env bash

# Run the bot.
#
# This script is intended for developer testing purposes. Actual use is advised via Docker as documented in the readme.
#
# Usage:
# Customize the values of the variables below, but do not check-in IRC_PASSWORD into version control.
# Run: ./scripts/run_bot.sh

export IRC_PASSWORD=YourActualPassword
CONFIG_PATH="/workspaces/irc-bots/libera/feed-bot/config.yaml"

# Run bot in dev mode
export IRCRSSFEEDBOT_ENV='dev'
python -m ircrssfeedbot --config-path "${CONFIG_PATH}"
