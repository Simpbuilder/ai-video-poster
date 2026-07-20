#!/bin/bash
cd "$(dirname "$0")"
python3 app.py
status=$?
if [ "$status" -ne 0 ]; then
    echo
    echo "InfoBuilder Studio closed with an error."
    read -r -p "Press Enter to close..."
fi
