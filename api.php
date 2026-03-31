<?php
/**
 * websh — PHP proxy.
 *
 * Forwards AJAX requests from the browser to the Python REST API
 * running on 127.0.0.1. This allows all traffic to flow through
 * the hosting provider's HTTPS — no exposed ports, no WebSocket.
 *
 * Compatible with PHP 5.3+ and requires only the curl extension.
 */

// HTTPS enforcement via reverse proxy headers.
$proto = isset($_SERVER['HTTP_X_FORWARDED_PROTO']) ? $_SERVER['HTTP_X_FORWARDED_PROTO'] : '';
if ($proto === 'http') {
    header('Location: https://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'], true, 301);
    exit;
}

@set_time_limit(55);

if (!extension_loaded('curl')) {
    header('HTTP/1.1 500 Internal Server Error');
    echo '{"error":"PHP curl extension is required"}';
    exit;
}

header('Content-Type: application/json');
header('Cache-Control: no-cache, no-store, must-revalidate');

$BACKEND = 'http://127.0.0.1:' . (getenv('WEBSH_PORT') ?: '8765');
$action  = isset($_GET['action']) ? $_GET['action'] : '';

// Path to config file (must be OUTSIDE the web root for security).
$WEBSH_CONFIG = getenv('WEBSH_CONFIG') ?: dirname(__FILE__) . '/../../websh.json';

// Auto-start: launch server.py if it's not running.
ensure_backend($BACKEND, $WEBSH_CONFIG);

switch ($action) {
    case 'config':     proxy_get($BACKEND . '/api/config');     break;
    case 'connect':    proxy_post($BACKEND . '/api/connect');    break;
    case 'input':      proxy_post($BACKEND . '/api/input');      break;
    case 'resize':     proxy_post($BACKEND . '/api/resize');     break;
    case 'disconnect': proxy_post($BACKEND . '/api/disconnect'); break;
    case 'output':
        $sid = isset($_GET['session_id']) ? $_GET['session_id'] : '';
        proxy_get($BACKEND . '/api/output?session_id=' . urlencode($sid));
        break;
    case 'ping':
        proxy_get($BACKEND . '/api/ping');
        break;
    default:
        header('HTTP/1.1 404 Not Found');
        echo '{"error":"unknown action"}';
        break;
}

// ── Helpers ──────────────────────────────────────────────────────────

function ping_backend($backend) {
    $ch = curl_init($backend . '/api/ping');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 2);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 1);
    $ok = curl_exec($ch) !== false;
    curl_close($ch);
    return $ok;
}

function proxy_post($url) {
    $body = file_get_contents('php://input');
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    $resp = curl_exec($ch);
    $err  = curl_error($ch);
    curl_close($ch);
    if ($resp === false) {
        header('HTTP/1.1 502 Bad Gateway');
        echo json_encode(array('error' => 'backend unavailable: ' . $err));
        return;
    }
    echo $resp;
}

function proxy_get($url) {
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 50);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    $resp = curl_exec($ch);
    $err  = curl_error($ch);
    curl_close($ch);
    if ($resp === false) {
        header('HTTP/1.1 502 Bad Gateway');
        echo json_encode(array('error' => 'backend unavailable: ' . $err));
        return;
    }
    echo $resp;
}

function ensure_backend($backend, $config_path) {
    if (ping_backend($backend)) return;

    // Lock to prevent double-start.
    $lock = fopen(sys_get_temp_dir() . '/websh_start.lock', 'c');
    if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) {
        if ($lock) fclose($lock);
        usleep(1500000);
        ping_backend($backend);
        return;
    }

    // Re-check after acquiring lock.
    if (ping_backend($backend)) { flock($lock, LOCK_UN); fclose($lock); return; }

    $script = dirname(__FILE__) . '/server.py';
    if (file_exists($script)) {
        $cmd = sprintf(
            'WEBSH_CONFIG=%s nohup python3 %s </dev/null >/dev/null 2>&1 &',
            escapeshellarg($config_path),
            escapeshellarg($script)
        );
        exec($cmd);
        usleep(800000);
    }

    flock($lock, LOCK_UN);
    fclose($lock);
}
