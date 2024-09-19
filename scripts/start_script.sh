#!/bin/bash

# Log file path
LOGFILE="/home/raspi/myscript.log"

# Wait until the network is up by pinging a reliable host
until ping -c1 8.8.8.8 &>/dev/null; do
    echo "$(date) - Waiting for network..." >> "$LOGFILE"
    sleep 5
done

echo "$(date) - Network is up. Proceeding..." >> "$LOGFILE"

# Change to the desired directory
cd /home/raspi/eInk-weather-display/eInk-weather-display || {
    echo "$(date) - Failed to change directory to /home/raspi/eInk-weather-display/eInk-weather-display" >> "$LOGFILE"
    exit 1
}

# Activate the virtual environment
source /home/raspi/weather/bin/activate

# Run the Python script
python weather-display.py
