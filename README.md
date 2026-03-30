# websh

Lightweight web-based SSH terminal. Three files, zero dependencies.

```
Browser (xterm.js) ── HTTPS ──> api.php ──> server.py ──> ssh
```

## Features

- Full terminal emulator in the browser ([xterm.js](https://xtermjs.org/))
- Password and SSH key authentication
- Server-side connection config — users click to connect, no passwords on the client
- Restrict mode — limit connections to pre-configured hosts only
- Auto-start — PHP launches the backend automatically, no SSH needed for setup
- Saved connections (browser localStorage)
- Works on shared hosting — no open ports, no WebSocket, no npm
- Python backend uses only the standard library
- Session timeout, auto-cleanup, terminal resize

## Quick start (shared hosting)

The simplest setup — **no SSH access required**:

1. Upload `index.html`, `api.php`, and `server.py` to your web directory (e.g. via FTP)
2. Open `https://your-host/console/index.html` in a browser

That's it. The PHP proxy starts the Python backend automatically on first request.

## Server-side connections

You can pre-configure connections in a JSON file so users don't need to enter
credentials. Create `websh.json`:

```json
{
  "restrict_hosts": false,
  "connections": [
    {
      "name": "Production",
      "host": "server.example.com",
      "port": 22,
      "username": "deploy",
      "password": "secret"
    }
  ]
}
```

See `websh.json.example` for a full example including SSH key auth.

> **Security: place this file OUTSIDE your web root.** It contains passwords
> and must not be accessible via HTTP. The default path is two directories up
> from `api.php` (e.g. if websh is in `/www/console/`, the config goes in `/`
> — the site root above `www/`). Set a custom path with the `WEBSH_CONFIG`
> environment variable.

### Restrict mode

Set `"restrict_hosts": true` to only allow connections to hosts defined in
the config. The manual connection form will be hidden, and the backend will
reject any connection attempt to a host not in the list.

This is useful when you want to provide SSH access to specific servers without
letting users connect to arbitrary hosts.

## Configuration

Environment variables for `server.py`:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8765` | Listen port |
| `HOST` | `127.0.0.1` | Bind address |
| `SESSION_TIMEOUT` | `300` | Idle timeout in seconds |
| `MAX_SESSIONS` | `10` | Max concurrent SSH sessions |
| `WEBSH_CONFIG` | *(auto-detected)* | Path to `websh.json` config file |

The PHP proxy reads `WEBSH_PORT` (default `8765`) to find the backend.

## Deployment

### Shared hosting (PHP + Python)

Upload the three files to your web directory. The backend starts automatically.

For manual control (e.g. custom config path):

```bash
WEBSH_CONFIG=/path/to/websh.json nohup python3 server.py &
```

### Docker

```bash
docker build -t websh .
docker run -d -p 8765:8765 websh
```

Serve `index.html` via nginx/Apache and proxy `/api/` to the container.

### systemd

```bash
cp server.py /opt/websh/
cp websh.service /etc/systemd/system/
systemctl enable --now websh
```

## Authentication & security

**websh does not include its own authentication layer by design.**
It is meant to be lightweight — add access control at the web server level:

- **Apache:** `.htaccess` with `AuthType Basic`
- **nginx:** `auth_basic` directive
- **Cloudflare Access**, **Tailscale Funnel**, or similar zero-trust tools
- IP allowlisting via firewall rules

### Saved connections & passwords

Saved connections in the browser are stored in `localStorage` in plaintext,
including passwords. This is a deliberate trade-off for simplicity.

If this is unacceptable for your use case:
- Use server-side connections (`websh.json`) — passwords stay on the server
- Don't save connections in the browser — use SSH keys instead
- Restrict access to the websh URL to trusted networks

### SSH host keys

The backend connects with `StrictHostKeyChecking=no` to avoid interactive
prompts. This means the first connection to a host does not verify its
identity. For most use cases (connecting to your own servers from a
trusted network) this is acceptable.

## Project structure

```
index.html          Frontend — xterm.js terminal + connection UI
api.php             PHP proxy — forwards browser requests to backend
server.py           Python backend — manages SSH sessions via PTY
websh.json.example  Example server-side config
test_server.py      Tests
Dockerfile          Container deployment
websh.service       systemd unit file
```

## Requirements

- **Backend:** Python 3.5+ with `ssh` command available
- **Proxy:** PHP 5.3+ with curl extension (shared hosting) — or any reverse proxy
- **Browser:** Any modern browser (Chrome, Firefox, Safari, Edge)

## License

MIT
