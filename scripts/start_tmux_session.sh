#!/bin/bash

set -uxo pipefail
#cd /home/oli/eInk-weather-display/eInk-weather-display/
#source ./config.env

# Check if the session already exists
tmux has-session -t 'session1'

if [ $? == 0 ]; then
  # Delete the old session if it exists
  tmux kill-session -t 'session1'
fi

tmux new-session -d -s 'session1' ../scripts/run.sh
