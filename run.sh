#!/bin/bash
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/../.venv/bin/python" ]; then
    PYTHON="$(cd "$SCRIPT_DIR/.." && pwd)/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON="$(cd "$SCRIPT_DIR" && pwd)/.venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
else
    echo "Python3 is not installed. Please install it first."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "Creating .env file based on .env.example..."
    cp .env.example .env

    echo "Please enter your Telegram API credentials:"
    read -p "API_ID: " api_id
    read -p "API_HASH: " api_hash
    read -p "HANDLER (default .saveit): " handler
    handler=${handler:-.saveit}

    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/API_ID=.*/API_ID=$api_id/" .env
        sed -i '' "s/API_HASH=.*/API_HASH=$api_hash/" .env
        sed -i '' "s/HANDLER=.*/HANDLER=$handler/" .env
    else
        sed -i "s/API_ID=.*/API_ID=$api_id/" .env
        sed -i "s/API_HASH=.*/API_HASH=$api_hash/" .env
        sed -i "s/HANDLER=.*/HANDLER=$handler/" .env
    fi
fi

echo "Running Saveit.py..."
"$PYTHON" Saveit.py

echo "Done."
