module.exports = {
  apps: [
    {
      name: 'agent-chat',
      script: process.env.ERGO_BIN || '/opt/homebrew/bin/ergo',
      args: 'run --config /etc/ergo/ircd.yaml',
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      kill_timeout: 5000,
      wait_ready: true,
    }
  ]
};
