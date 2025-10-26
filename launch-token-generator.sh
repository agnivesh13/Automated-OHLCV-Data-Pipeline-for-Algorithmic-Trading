#!/bin/bash

echo ""
echo "===================================="
echo "  Fyers Token Generator UI Launcher"
echo "===================================="
echo ""
echo "Opening token generator interface..."
echo ""

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Try to open in browser
if command -v google-chrome &> /dev/null; then
    echo "Using Chrome browser..."
    google-chrome "file://$DIR/token-generator-ui.html" &
elif command -v firefox &> /dev/null; then
    echo "Using Firefox browser..."
    firefox "file://$DIR/token-generator-ui.html" &
elif command -v safari &> /dev/null; then
    echo "Using Safari browser..."
    safari "file://$DIR/token-generator-ui.html" &
else
    echo "Opening with default browser..."
    xdg-open "file://$DIR/token-generator-ui.html" 2>/dev/null || open "file://$DIR/token-generator-ui.html" 2>/dev/null
fi

echo ""
echo "Token Generator UI opened in your browser!"
echo ""
echo "Quick Start:"
echo "1. Enter your Fyers Client ID and App Secret"
echo "2. Click 'Generate Login URL' and open Fyers login"
echo "3. After login, paste the redirect URL to generate tokens"
echo "4. Download AWS CLI commands to update your pipeline"
echo ""
echo "Your credentials will be saved in the browser for next time."
echo ""
