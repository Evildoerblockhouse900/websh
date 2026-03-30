#!/usr/bin/env python3
"""
websh — lightweight SSH terminal backend.

REST API server that manages SSH sessions via PTY.
Designed to run on shared hosting with Python 3.5+, zero dependencies.
Listens on 127.0.0.1 only — meant to be proxied through Apache/nginx via PHP.

Environment variables:
    PORT              — listen port (default: 8765)
    HOST              — bind address (default: 127.0.0.1)
    SESSION_TIMEOUT   — seconds of inactivity before cleanup (default: 300)
    MAX_SESSIONS      — max concurrent SSH sessions (default: 10)
    WEBSH_CONFIG      — path to websh.json config file (optional)

API endpoints:
    POST /api/connect     — start SSH session
    POST /api/input       — send keystrokes
    GET  /api/output      — long-poll for terminal output
    POST /api/resize      — resize terminal
    POST /api/disconnect  — close session
    GET  /api/config      — return server-side config (without secrets)
    GET  /api/ping        — health check
"""

import base64
import fcntl
import json
import os
import pty
import select
import signal
import struct
import sys
import tempfile
import termios
import time
import urllib.parse
import uuid
from collections import OrderedDict
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from threading import Thread, Lock

# ─── Configuration ───────────────────────────────────────────────────

PORT = int(os.environ.get("PORT", "8765"))
HOST = os.environ.get("HOST", "127.0.0.1")
SESSION_TIMEOUT = int(os.environ.get("SESSION_TIMEOUT", "300"))
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "10"))

# Limits
MAX_PORT = 65535
MIN_PORT = 1
MAX_COLS = 500
MAX_ROWS = 200
MIN_COLS = 10
MIN_ROWS = 2

# Timing
CONNECT_SETTLE_TIME = 0.5     # seconds to wait after spawning SSH
POLL_TIMEOUT = 10             # seconds to long-poll for output
POLL_INTERVAL = 0.01          # seconds between buffer checks
PTY_DRAIN_ROUNDS = 50         # max iterations to drain PTY on exit
PTY_DRAIN_INTERVAL = 0.01    # seconds per drain round
PTY_READ_SIZE = 65536         # bytes per read
OUTPUT_BUF_MAX = 1048576      # 1 MB — truncate if exceeded
OUTPUT_BUF_KEEP = 524288      # keep last 512 KB on truncation

# Terminal reset sequence: exit alt screen, show cursor, reset attrs, full reset
TERM_RESET = b"\x1b[?1049l\x1b[?25h\x1b[0m\x1bc"


# ─── Config file ────────────────────────────────────────────────────

_config_cache = None
_config_mtime = 0
_CONFIG_EMPTY = {"connections": [], "restrict_hosts": False}


def load_config():
    """Load websh.json config with mtime-based caching."""
    global _config_cache, _config_mtime
    path = os.environ.get("WEBSH_CONFIG", "")
    if not path or not os.path.isfile(path):
        return _CONFIG_EMPTY
    try:
        mtime = os.path.getmtime(path)
        if _config_cache is not None and mtime == _config_mtime:
            return _config_cache
        with open(path, "r") as f:
            cfg = json.load(f)
        conns = cfg.get("connections", [])
        for c in conns:
            c.setdefault("name", "")
            c.setdefault("host", "")
            c.setdefault("port", 22)
            c.setdefault("username", "")
        result = {
            "connections": conns,
            "restrict_hosts": bool(cfg.get("restrict_hosts", False)),
        }
        _config_cache = result
        _config_mtime = mtime
        return result
    except Exception as e:
        sys.stderr.write("websh: failed to load config: {}\n".format(e))
        return _CONFIG_EMPTY


def config_public():
    """Return config safe for the client (no passwords or keys)."""
    cfg = load_config()
    safe = []
    for c in cfg["connections"]:
        safe.append({
            "name": c.get("name", ""),
            "host": c.get("host", ""),
            "port": c.get("port", 22),
            "username": c.get("username", ""),
        })
    return {"connections": safe, "restrict_hosts": cfg["restrict_hosts"]}


def find_config_connection(name):
    """Find a connection by name in config. Returns full entry with secrets."""
    cfg = load_config()
    for c in cfg["connections"]:
        if c.get("name", "") == name:
            return c
    return None


def is_host_allowed(host, port, username):
    """Check if a host is allowed when restrict_hosts is on."""
    cfg = load_config()
    if not cfg["restrict_hosts"]:
        return True
    for c in cfg["connections"]:
        if (c.get("host", "") == host
                and c.get("port", 22) == port
                and c.get("username", "") == username):
            return True
    return False


# ─── Validation ──────────────────────────────────────────────────────

def clamp(value, lo, hi, default):
    """Parse int and clamp to range. Returns default on failure."""
    try:
        v = int(value)
        return max(lo, min(hi, v))
    except (TypeError, ValueError):
        return default


# ─── Session management ─────────────────────────────────────────────

sessions = OrderedDict()
sessions_lock = Lock()


class SSHSession(object):
    """Manages a single SSH connection via PTY subprocess."""

    def __init__(self, session_id, host, port, username, password, cols, rows,
                 key=None):
        self.id = session_id
        self.master_fd = None
        self.pid = None
        self.output_buf = b""
        self.buf_lock = Lock()
        self.alive = True
        self.last_activity = time.time()
        self._password = password
        self._password_sent = False
        self._key_file = None

        if key:
            self._key_file = self._write_key(key)

        self._spawn(host, port, username, cols, rows)

        self._reader = Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _clear_password(self):
        """Wipe password from memory once it has been sent."""
        self._password = None

    @staticmethod
    def _write_key(key_data):
        """Write SSH private key to a secure temp file. Returns path."""
        fd, path = tempfile.mkstemp(prefix="websh_key_", suffix=".pem")
        try:
            text = key_data.strip() + "\n"
            os.write(fd, text.encode("utf-8"))
        finally:
            os.close(fd)
        os.chmod(path, 0o600)
        return path

    def _spawn(self, host, port, username, cols, rows):
        """Fork a PTY and exec ssh."""
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["LANG"] = "en_US.UTF-8"
        env["LC_ALL"] = "en_US.UTF-8"

        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-p", str(port),
            "-l", username,
        ]

        if self._key_file:
            ssh_cmd.extend(["-i", self._key_file])

        ssh_cmd.append(host)

        pid, fd = pty.fork()
        if pid == 0:
            os.execvpe("ssh", ssh_cmd, env)
            sys.exit(1)

        self.pid = pid
        self.master_fd = fd
        self._set_winsize(cols, rows)

    def _set_winsize(self, cols, rows):
        try:
            fcntl.ioctl(
                self.master_fd, termios.TIOCSWINSZ,
                struct.pack("HHHH", rows, cols, 0, 0),
            )
        except Exception:
            pass

    def _read_loop(self):
        """Background thread: reads PTY output into buffer."""
        try:
            while self.alive:
                try:
                    r, _, _ = select.select([self.master_fd], [], [], 0.05)
                except (ValueError, OSError):
                    break

                if r:
                    try:
                        data = os.read(self.master_fd, PTY_READ_SIZE)
                    except OSError:
                        break
                    if not data:
                        break

                    # Auto-type password on prompt
                    if self._password and not self._password_sent:
                        text = data.decode("latin-1", errors="replace").lower()
                        if "password:" in text or "password for" in text:
                            time.sleep(0.1)
                            try:
                                os.write(self.master_fd,
                                         (self._password + "\n").encode())
                            except OSError:
                                break
                            self._password_sent = True
                            self._clear_password()

                    with self.buf_lock:
                        self.output_buf += data
                        if len(self.output_buf) > OUTPUT_BUF_MAX:
                            self.output_buf = self.output_buf[-OUTPUT_BUF_KEEP:]

                # Check if child exited
                try:
                    pid, _ = os.waitpid(self.pid, os.WNOHANG)
                    if pid != 0:
                        break
                except ChildProcessError:
                    break
        except Exception:
            pass
        finally:
            # Drain remaining PTY data (exit escape sequences, etc.)
            try:
                for _ in range(PTY_DRAIN_ROUNDS):
                    r, _, _ = select.select(
                        [self.master_fd], [], [], PTY_DRAIN_INTERVAL)
                    if r:
                        leftover = os.read(self.master_fd, PTY_READ_SIZE)
                        if leftover:
                            with self.buf_lock:
                                self.output_buf += leftover
                        else:
                            break
                    else:
                        break
            except Exception:
                pass

            # Append terminal reset so the frontend restores normal screen
            with self.buf_lock:
                self.output_buf += TERM_RESET

            self.alive = False

    def read(self):
        """Return and clear buffered output."""
        with self.buf_lock:
            data = self.output_buf
            self.output_buf = b""
        self.last_activity = time.time()
        return data

    def write(self, data):
        """Send input to SSH process."""
        if not self.alive:
            return False
        self.last_activity = time.time()
        try:
            os.write(self.master_fd, data)
            return True
        except OSError:
            self.alive = False
            return False

    def resize(self, cols, rows):
        self.last_activity = time.time()
        self._set_winsize(cols, rows)

    def close(self):
        self.alive = False
        try:
            os.close(self.master_fd)
        except Exception:
            pass
        try:
            os.kill(self.pid, signal.SIGTERM)
        except Exception:
            pass
        try:
            os.waitpid(self.pid, os.WNOHANG)
        except Exception:
            pass
        if self._key_file:
            try:
                os.unlink(self._key_file)
            except Exception:
                pass
            self._key_file = None

    def is_expired(self):
        return time.time() - self.last_activity > SESSION_TIMEOUT


def cleanup():
    """Remove timed-out sessions."""
    with sessions_lock:
        expired = [sid for sid, s in sessions.items() if s.is_expired()]
        for sid in expired:
            sys.stderr.write("websh: session {} expired, cleaning up\n".format(sid))
            sessions[sid].close()
            del sessions[sid]


def _cleanup_loop():
    """Background thread: periodically removes expired sessions."""
    while True:
        time.sleep(30)
        try:
            cleanup()
        except Exception:
            pass


# ─── HTTP handler ────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n) if n else b""

    def _path(self):
        return self.path.split("?")[0].rstrip("/")

    # ── Routes ──

    def do_POST(self):
        cleanup()
        p = self._path()
        if p == "/api/connect":
            self._connect()
        elif p == "/api/input":
            self._input()
        elif p == "/api/resize":
            self._resize()
        elif p == "/api/disconnect":
            self._disconnect()
        else:
            self._json({"error": "not found"}, 404)

    def do_GET(self):
        cleanup()
        p = self._path()
        if p == "/api/output":
            self._output()
        elif p == "/api/config":
            self._json(config_public())
        elif p == "/api/ping":
            self._json({"ok": True})
        else:
            self._json({"error": "not found"}, 404)

    # ── Handlers ──

    def _connect(self):
        try:
            body = json.loads(self._body().decode("utf-8"))
        except Exception:
            self._json({"error": "invalid json"}, 400)
            return

        cols = clamp(body.get("cols"), MIN_COLS, MAX_COLS, 80)
        rows = clamp(body.get("rows"), MIN_ROWS, MAX_ROWS, 24)

        # Resolve credentials: by config connection name, or from request body
        conn_name = body.get("connection", "").strip()
        if conn_name:
            entry = find_config_connection(conn_name)
            if not entry:
                self._json({"error": "connection not found"}, 404)
                return
            host = entry.get("host", "")
            port = clamp(entry.get("port"), MIN_PORT, MAX_PORT, 22)
            username = entry.get("username", "")
            password = entry.get("password", "")
            key = entry.get("key", "")
        else:
            host = body.get("host", "").strip()
            username = body.get("username", "").strip()
            port = clamp(body.get("port"), MIN_PORT, MAX_PORT, 22)
            password = body.get("password", "")
            key = body.get("key", "")

        if not host or not username:
            self._json({"error": "host and username are required"}, 400)
            return

        # Enforce restrict_hosts
        if not conn_name and not is_host_allowed(host, port, username):
            self._json({"error": "connections to this host are not allowed"}, 403)
            return

        # Check session limit
        with sessions_lock:
            if len(sessions) >= MAX_SESSIONS:
                self._json({"error": "too many active sessions"}, 429)
                return

        sid = str(uuid.uuid4())[:12]
        session = None
        try:
            session = SSHSession(
                session_id=sid,
                host=host,
                port=port,
                username=username,
                password=password,
                cols=cols,
                rows=rows,
                key=key,
            )
            with sessions_lock:
                sessions[sid] = session

            time.sleep(CONNECT_SETTLE_TIME)
            sys.stderr.write("websh: new session {} for {}@{}:{}\n".format(
                sid, username, host, port))
            self._json({
                "session_id": sid,
                "status": "connecting",
                "alive": session.alive,
            })
        except Exception as e:
            if session:
                session.close()
            self._json({"error": str(e)}, 500)

    def _input(self):
        try:
            body = json.loads(self._body().decode("utf-8"))
        except Exception:
            self._json({"error": "invalid json"}, 400)
            return

        with sessions_lock:
            session = sessions.get(body.get("session_id", ""))
        if not session:
            self._json({"error": "session not found"}, 404)
            return

        ok = session.write(body.get("data", "").encode("utf-8"))
        self._json({"ok": ok, "alive": session.alive})

    def _output(self):
        params = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query)
        sid = params.get("session_id", [""])[0]

        with sessions_lock:
            session = sessions.get(sid)
        if not session:
            self._json({"error": "session not found"}, 404)
            return

        # Long-poll: wait up to POLL_TIMEOUT seconds for data
        deadline = time.time() + POLL_TIMEOUT
        while time.time() < deadline:
            data = session.read()
            if data:
                self._json({
                    "data": base64.b64encode(data).decode("ascii"),
                    "alive": session.alive,
                })
                return
            if not session.alive:
                self._json({"data": "", "alive": False})
                return
            time.sleep(POLL_INTERVAL)

        self._json({"data": "", "alive": session.alive})

    def _resize(self):
        try:
            body = json.loads(self._body().decode("utf-8"))
        except Exception:
            self._json({"error": "invalid json"}, 400)
            return

        with sessions_lock:
            session = sessions.get(body.get("session_id", ""))
        if not session:
            self._json({"error": "session not found"}, 404)
            return

        cols = clamp(body.get("cols"), MIN_COLS, MAX_COLS, 80)
        rows = clamp(body.get("rows"), MIN_ROWS, MAX_ROWS, 24)
        session.resize(cols, rows)
        self._json({"ok": True})

    def _disconnect(self):
        try:
            body = json.loads(self._body().decode("utf-8"))
        except Exception:
            self._json({"error": "invalid json"}, 400)
            return

        with sessions_lock:
            session = sessions.pop(body.get("session_id", ""), None)
        if session:
            session.close()
        self._json({"ok": True})


class Server(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    # Start background cleanup thread
    t = Thread(target=_cleanup_loop, daemon=True)
    t.start()

    server = Server((HOST, PORT), Handler)

    def shutdown(signum, frame):
        with sessions_lock:
            for s in sessions.values():
                s.close()
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    sys.stdout.write("websh server listening on http://{}:{}\n".format(
        HOST, PORT))
    sys.stdout.flush()
    server.serve_forever()


if __name__ == "__main__":
    main()
