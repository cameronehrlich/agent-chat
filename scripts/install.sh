#!/bin/bash
set -euo pipefail

echo "=== Agent Chat Installer ==="

if ! command -v ergo &>/dev/null; then
    echo "Installing Ergo IRC server..."
    if [[ "$(uname)" != "Darwin" ]]; then
        echo "Error: automated install currently supports macOS only."
        exit 1
    fi
    brew install ergo
fi

if ! command -v tailscale &>/dev/null; then
    echo "Error: Tailscale not installed. Install from https://tailscale.com"
    exit 1
fi

TAILSCALE_IP=$(tailscale ip -4)
echo "Tailscale IP: $TAILSCALE_IP"

sudo mkdir -p /etc/ergo/tls
cat > /tmp/ircd.yaml <<EOFCONF
server:
    name: agent-chat.local
    listeners:
        "${TAILSCALE_IP}:6667": {}
        "${TAILSCALE_IP}:6697":
            tls:
                cert: /etc/ergo/tls/fullchain.pem
                key: /etc/ergo/tls/privkey.pem
network:
    name: AgentNet
accounts:
    registration:
        enabled: true
        allow-before-connect: true
    authentication-enabled: true
    multiclient:
        enabled: true
        allowed-by-default: true
        always-on: opt-in
history:
    enabled: true
    channel-length: 4096
    client-length: 512
    chathistory-maxmessages: 1000
    znc-maxmessages: 2048
    restrictions:
        expire-time: 168h
channels:
    default-modes: +nt
    registration:
        enabled: true
EOFCONF
sudo mv /tmp/ircd.yaml /etc/ergo/ircd.yaml

echo "Generating TLS certificate..."
sudo openssl req -x509 -newkey rsa:4096 \
    -keyout /etc/ergo/tls/privkey.pem \
    -out /etc/ergo/tls/fullchain.pem \
    -days 365 -nodes \
    -subj "/CN=agent-chat.local" 2>/dev/null

echo "Installing ac CLI..."
pip install agent-chat

mkdir -p ~/.agent-chat/hooks
cp hooks/notify.sh ~/.agent-chat/hooks/
cp hooks/tmux-status.sh ~/.agent-chat/hooks/
chmod +x ~/.agent-chat/hooks/notify.sh ~/.agent-chat/hooks/tmux-status.sh

if command -v pm2 &>/dev/null; then
    echo "Setting up PM2..."
    pm2 start server/ecosystem.config.js
    pm2 save
    pm2 startup
else
    echo "PM2 not found. Install with: npm install -g pm2"
fi

echo "=== Setup Complete ==="
echo "Server: ${TAILSCALE_IP}:6667 (plain) / 6697 (TLS)"
echo "CLI: ac send '#general' 'hello world'"
echo "Connect from any device on your Tailscale network!"
