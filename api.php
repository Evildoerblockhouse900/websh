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

// HTTPS enforcement: redirect if accessed over plain HTTP.
// Works with reverse proxies that set X-Forwarded-Proto or Port headers.
$proto = isset($_SERVER['HTTP_X_FORWARDED_PROTO']) ? $_SERVER['HTTP_X_FORWARDED_PROTO'] : '';
$port  = isset($_SERVER['HTTP_PORT']) ? $_SERVER['HTTP_PORT'] : '';
if ($proto === 'http' || ($port !== '' && $port !== '443')) {
    header('Location: https://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'], true, 301);
    exit;
}

set_time_limit(55);
while (ob_get_level()) ob_end_clean();

header('Content-Type: application/json');
header('Cache-Control: no-cache, no-store, must-revalidate');

$BACKEND = 'http://127.0.0.1:' . (getenv('WEBSH_PORT') ?: '8765');
$action  = isset($_GET['action']) ? $_GET['action'] : '';

switch ($action) {
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
        http_response_code(404);
        echo '{"error":"unknown action"}';
        break;
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
        http_response_code(502);
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
        http_response_code(502);
        echo json_encode(array('error' => 'backend unavailable: ' . $err));
        return;
    }
    echo $resp;
}
