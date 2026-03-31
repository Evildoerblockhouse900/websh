# websh

Lightweight web-based SSH terminal. Three files, no build step, no server dependencies.

```
Browser (xterm.js) ── HTTPS ──> api.php ──> server.py ──> ssh
```

## How it works

The browser runs a full terminal emulator (xterm.js) and communicates with the backend via HTTP long-polling through a PHP reverse proxy. The backend manages SSH sessions as PTY subprocesses.

**Why not WebSocket?** Most shared hosting PHP environments don't support WebSocket. HTTP long-polling works everywhere — no open ports, no special server configuration. The trade-off is slightly higher latency compared to a native SSH client, but it's negligible for interactive use.

## Requirements

- **Backend:** Python 3.5+ with `ssh` command available
- **Proxy:** PHP 5.3+ with curl extension (shared hosting) — or any reverse proxy (nginx, Apache)
- **Browser:** Any modern browser (Chrome, Firefox, Safari, Edge)
- **Frontend:** Loads [xterm.js](https://xtermjs.org/) from CDN (no npm, no build step)

## Use cases

- **Shared hosting** — no SSH client on the server? Upload 3 files via FTP, open in browser, done.
- **Corporate networks** — SSH port blocked, but HTTPS is open? websh tunnels SSH through standard HTTPS.
- **Chromebooks & tablets** — any device with a browser becomes a terminal.
- **Customer support / managed servers** — give clients browser-based access to their servers without teaching them PuTTY or terminal. Use URL anchors (`#connect=ServerName`) for direct links.
- **Jump host UI** — put websh on a bastion host, access internal servers through it from any browser.
- **Emergency access** — any browser, any computer, just open a URL.
- **Teaching & workshops** — provide students with browser-based terminal access, no local setup required.

## Features

- Full terminal emulator in the browser ([xterm.js](https://xtermjs.org/))
- **Split panes** — divide the screen horizontally or vertically, each pane is an independent SSH session
- Draggable resize handles between panes (mouse and touch)
- **Reconnect on disconnect** — one-click reconnect when a session closes
- **Session persistence** — sessions survive page reload (while the backend keeps them alive)
- **Keyboard pane switching** — Ctrl+Tab / Ctrl+Shift+Tab to cycle between panes
- **Idle timeout warning** — notification 30 seconds before session expires, with a "Keep alive" button
- Password and SSH key authentication
- Server-side connection config — users click to connect, no passwords on the client
- Per-connection SSH options (ProxyJump, StrictHostKeyChecking, etc.)
- Restrict mode — limit connections to pre-configured hosts only
- Auto-start — PHP launches the backend automatically, no SSH needed for setup
- Saved connections (browser localStorage)
- **File upload** — click the upload button, pick files, they upload via background SSH session (atomic writes, auto-increment on name conflict)
- **File download** — select filename in terminal, click download, file saves to your browser
- **Export terminal** — save scrollback buffer as text file
- **URL anchors** — `#connect=ServerName` for direct links to server-side connections
- Copy on select, right-click paste
- Search terminal buffer (Ctrl+Shift+F)
- Zoom (Ctrl+/-)
- Dark / light theme toggle (persisted)
- Fullscreen mode (F11)
- Rate limiting on connection attempts
- Session timeout, auto-cleanup, terminal resize

## Quick start (shared hosting)

**No SSH access required.** Upload three files via FTP, open in browser.

A typical shared hosting directory structure:

```
/home/user/
  example.com/              <- site root
    websh.json              <- config (OUTSIDE www — not accessible via HTTP)
    www/                    <- web root (public)
      console/
        index.html          <- frontend
        api.php             <- PHP proxy
        server.py           <- backend (auto-started by api.php)
```

**Steps:**

1. Create a folder in your web root (e.g. `www/console/`)
2. Upload `index.html`, `api.php`, and `server.py` there
3. Open `https://your-host/console/` in a browser

That's it. `api.php` starts `server.py` automatically on the first request.

> **Path details:** `api.php` looks for `websh.json` two directories up from itself
> (i.e. the site root, above `www/`). This works for most hosting providers.
> If your layout is different, set the `WEBSH_CONFIG` environment variable
> or edit the path in `api.php` line 34.

### Troubleshooting

**"Backend unavailable" or blank page:**
- Check that Python 3 is installed: `python3 --version`
- Check that `ssh` is available: `which ssh`
- Some shared hosts disable `exec()` in PHP — ask your hosting provider or check `phpinfo()`

**Config not loading:**
- Verify `websh.json` path — `api.php` looks two directories up by default
- Set `WEBSH_CONFIG=/full/path/to/websh.json` environment variable if your layout differs
- Check JSON syntax: `python3 -c "import json; json.load(open('websh.json'))"`

**Port already in use:**
- Another instance of `server.py` may be running: `ps aux | grep server.py`
- Change the port: `PORT=8766 python3 server.py`

## Server-side connections (optional)

Pre-configure connections so users just click to connect — no passwords
on the client. Create `websh.json` in your **site root** (not in `www/`):

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

See `websh.json.example` for a full example including SSH key auth and custom SSH options.

> **This file contains passwords — keep it outside the web root.**
> It must not be accessible via HTTP. If your hosting layout doesn't match
> the diagram above, set the `WEBSH_CONFIG` environment variable.

### Per-connection SSH options

Override default SSH behavior for specific connections:

```json
{
  "name": "Strict server",
  "host": "secure.example.com",
  "username": "admin",
  "password": "secret",
  "ssh_options": {
    "StrictHostKeyChecking": "yes",
    "ProxyJump": "bastion.example.com"
  }
}
```

### Restrict mode

Set `"restrict_hosts": true` to only allow connections to hosts defined in
the config. The manual connection form will be hidden, and the backend will
reject any connection attempt to a host not in the list.

### URL anchors

Link directly to a server-side connection:

```
https://your-host/console/#connect=Production
```

This auto-connects on page load — useful for bookmarks and support links.

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

Serve `index.html` via nginx/Apache and proxy `/api/` to the container. Example nginx config:

```nginx
server {
    listen 443 ssl;
    server_name ssh.example.com;

    root /var/www/websh;
    index index.html;

    location /api.php {
        proxy_pass http://127.0.0.1:8765/api;
        proxy_read_timeout 60s;
    }
}
```

### systemd

```bash
# Create a dedicated user
useradd -r -s /bin/false websh

cp server.py /opt/websh/
cp websh.service /etc/systemd/system/
systemctl enable --now websh
```

## Authentication & security

**websh does not include its own authentication layer by design.**
It is meant to be lightweight — add access control at the web server level:

- **Apache:** `.htaccess` with `AuthType Basic` + `AuthUserFile`
- **nginx:** `auth_basic` directive
- **Cloudflare Access**, **Tailscale Funnel**, or similar zero-trust tools
- IP allowlisting via firewall rules

### SSH host keys

The backend connects with `StrictHostKeyChecking=no` by default to avoid
interactive prompts. **This makes the first connection to any host vulnerable
to man-in-the-middle attacks** — the server identity is not verified.

This is acceptable when:
- You are connecting to your own servers on a trusted network
- The connection goes over an encrypted tunnel (VPN, Tailscale, etc.)

To enable host key verification for specific connections, use `ssh_options`
in `websh.json`:

```json
"ssh_options": {"StrictHostKeyChecking": "yes"}
```

### Saved connections & passwords

Saved connections in the browser are stored in `localStorage` **in plaintext**,
including passwords. Any JavaScript running on the same origin (including XSS
vulnerabilities) could read them.

If this is unacceptable for your use case:
- Use server-side connections (`websh.json`) — passwords stay on the server, never reach the browser
- Don't save connections in the browser — use SSH keys instead
- Restrict access to the websh URL to trusted networks

### Input validation

- Host and username values starting with `-` are rejected (prevents SSH flag injection)
- Connection attempts are rate-limited (10 per IP per minute)
- Session IDs are validated as UUID format
- Terminal dimensions are clamped to safe ranges
- `MAX_SESSIONS` prevents resource exhaustion

## Project structure

```
index.html          Frontend — xterm.js terminal + connection UI
api.php             PHP proxy — forwards browser requests to backend
server.py           Python backend — manages SSH sessions via PTY
websh.json.example  Example server-side config
test_server.py      Tests (40 unit + integration tests)
Dockerfile          Container deployment
websh.service       systemd unit file
```

## License

MIT
