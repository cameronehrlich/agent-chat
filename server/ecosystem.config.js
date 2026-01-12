const ERGO_BIN = process.env.ERGO_BIN || '/opt/homebrew/bin/ergo';
const ERGO_CONFIG = process.env.ERGO_CONFIG || '/etc/ergo/ircd.yaml';

module.exports = {
  apps: [
    {
      name: 'agent-chat',
      script: ERGO_BIN,
      args: `run --conf ${ERGO_CONFIG}`,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      kill_timeout: 5000,
      wait_ready: true,
    }
  ]
};
