# websh

Lightweight web-based SSH terminal. Three files, zero dependencies.

```
Browser (xterm.js) ── HTTPS ──> api.php ──> server.py ──> ssh
```

## Features

- Full terminal emulator in the browser ([xterm.js](https://xtermjs.org/))
- Password and SSH key authentication
- Saved connections (browser localStorage)
- Works on shared hosting — no open ports, no WebSocket, no npm
- Python backend uses only the standard library
- Session timeout, auto-cleanup, terminal resize

## Quick start

**1. Start the backend:**

```bash
python3 server.py
```

Listens on `127.0.0.1:8765` by default.

**2. Serve the frontend:**

Put `index.html` and `api.php` in your web root. The PHP proxy forwards
requests to the Python backend — no ports need to be exposed.

For local development without PHP:

```bash
# server.py is already running on :8765
# open index.html directly and point API to localhost:8765
```

**3. Open** `https://your-host/console/index.html` **in a browser.**

## Configuration

Environment variables for `server.py`:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8765` | Listen port |
| `HOST` | `127.0.0.1` | Bind address |
| `SESSION_TIMEOUT` | `300` | Idle timeout in seconds |
| `MAX_SESSIONS` | `10` | Max concurrent SSH sessions |

The PHP proxy reads `WEBSH_PORT` (default `8765`) to find the backend.

## Deployment

### Shared hosting (PHP + Python)

The original setup. Upload all three files to your web directory.
Start `server.py` in the background (screen, tmux, nohup, or cron `@reboot`).

```bash
nohup python3 server.py &
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

Saved connections are stored in the browser's `localStorage` in plaintext,
including passwords. This is a deliberate trade-off for simplicity.

If this is unacceptable for your use case:
- Don't save connections with passwords — use SSH keys instead
- Restrict access to the websh URL to trusted networks

### SSH host keys

The backend connects with `StrictHostKeyChecking=no` to avoid interactive
prompts. This means the first connection to a host does not verify its
identity. For most use cases (connecting to your own servers from a
trusted network) this is acceptable.

## Project structure

```
index.html      Frontend — xterm.js terminal + connection UI
api.php         PHP proxy — forwards browser requests to backend
server.py       Python backend — manages SSH sessions via PTY
Dockerfile      Container deployment
websh.service   systemd unit file
```

## Requirements

- **Backend:** Python 3.5+ with `ssh` command available
- **Proxy:** PHP 5.3+ with curl extension (shared hosting) — or any reverse proxy
- **Browser:** Any modern browser (Chrome, Firefox, Safari, Edge)

## License

MIT
