#!/bin/sh



#set -euxo pipefail

#
#source ./config.env
cd /home/oli/eInk-weather-display/eInk-weather-display/

sudo /home/oli/venv/eink/bin/python weather-display.py; exec ${SHELL}  # Leaves the tmux session running so we can see errors

# Bleson version - not yet production ready
# sudo RUUVI_BLE_ADAPTER="Bleson" ${VENV_DIRECTORY}/bin/python ${APP_DIRECTORY}/weather-display.py; exec $SHELL  # Leaves the tmux session running so we can see errors
