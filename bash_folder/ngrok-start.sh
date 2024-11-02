#!/bin/bash
# Start ngrok in a detached screen session with HTTP and disable the inspector
screen -dmS ngrok_session bash -c "ngrok http --region ap --inspect=false 5000 > ngrok_output.log 2>&1; exec bash"
sleep 5  # Wait for ngrok to fully start

# Get the public URL from ngrok
PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | cut -d'"' -f4)

# Create or overwrite the ngrok URL text file
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NGROK_URL_FILE="$SCRIPT_DIR/ngrok_url.txt"

echo "$PUBLIC_URL" > "$NGROK_URL_FILE"
echo "Your public URL is: $PUBLIC_URL"
