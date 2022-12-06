#!/usr/bin/env bash

IRC_PASSWORD=YourActualPassword
CONFIG_PATH="/workspaces/irc-bots/libera/feed-bot/config.yaml"

python -m ircrssfeedbot --config-path "${CONFIG_PATH}"
