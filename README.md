# websh

Lightweight web-based SSH terminal. Three files, zero dependencies.

```
Browser (xterm.js) ── HTTPS ──> api.php ──> server.py ──> ssh
```

## Use cases

- **Shared hosting** — no SSH client on the server? Upload 3 files via FTP, open in browser, done.
- **Corporate networks** — SSH port blocked, but HTTPS is open? websh tunnels SSH through standard HTTPS.
- **Chromebooks & tablets** — no native SSH client available. Any device with a browser becomes a terminal.
- **Customer support / managed servers** — give clients browser-based access to their servers without teaching them PuTTY or terminal.
- **Jump host UI** — put websh on a bastion host, access internal servers through it from any browser.
- **Emergency access** — your laptop died, you're at a friend's computer, you need to restart a service. Open a URL, connect.
- **Teaching & workshops** — provide students with browser-based terminal access, no local setup required.

## Features

- Full terminal emulator in the browser ([xterm.js](https://xtermjs.org/))
- **Split panes** — divide the screen horizontally or vertically, each pane is an independent SSH session
- Draggable resize handles between panes
- Password and SSH key authentication
- Server-side connection config — users click to connect, no passwords on the client
- Restrict mode — limit connections to pre-configured hosts only
- Auto-start — PHP launches the backend automatically, no SSH needed for setup
- Saved connections (browser localStorage)
- **File upload** — click 📎, pick files, they upload via background SSH session (atomic writes, auto-increment on name conflict)
- **File download** — select filename in terminal, click ⬇, file downloads to your browser
- Copy on select, right-click paste
- Search terminal buffer (Ctrl+Shift+F)
- Zoom (Ctrl+/-)
- Dark / light theme toggle (persisted)
- Fullscreen mode (F11)
- Works on shared hosting — no open ports, no WebSocket, no npm
- Python backend uses only the standard library
- Session timeout, auto-cleanup, terminal resize

## Quick start (shared hosting)

**No SSH access required.** Upload three files via FTP, open in browser.

A typical shared hosting directory structure:

```
/home/user/
  example.com/              ← site root
    websh.json              ← config (OUTSIDE www — not accessible via HTTP)
    www/                    ← web root (public)
      console/
        index.html          ← frontend
        api.php             ← PHP proxy
        server.py           ← backend (auto-started by api.php)
```

**Steps:**

1. Create a folder in your web root (e.g. `www/console/`)
2. Upload `index.html`, `api.php`, and `server.py` there
3. Open `https://your-host/console/` in a browser

That's it. `api.php` starts `server.py` automatically on the first request.

> **Path details:** `api.php` looks for `websh.json` two directories up from itself
> (i.e. the site root, above `www/`). This works for most hosting providers.
> If your layout is different, set the `WEBSH_CONFIG` environment variable
> or edit the path in `api.php` line 38.

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

See `websh.json.example` for a full example including SSH key auth.

> **This file contains passwords — keep it outside the web root.**
> It must not be accessible via HTTP. If your hosting layout doesn't match
> the diagram above, set the `WEBSH_CONFIG` environment variable.

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
