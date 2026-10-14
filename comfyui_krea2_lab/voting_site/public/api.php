<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function respond(array $data, int $status = 200): never {
    http_response_code($status);
    echo json_encode($data, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
    exit;
}

try {
    $private = dirname(__DIR__) . '/private';
    $config = require $private . '/config.php';
    $secure = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
    $siteId = substr(hash('sha256', $config['secret']), 0, 12);
    session_name('krea_session_' . $siteId);
    ini_set('session.use_strict_mode', '1');
    session_set_cookie_params(['httponly' => true, 'secure' => $secure, 'samesite' => 'Lax', 'path' => '/']);
    session_start();
    $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
    $cookie = 'krea_voter_' . $siteId;
    $token = $_COOKIE[$cookie] ?? '';
    if (!preg_match('/^[a-f0-9]{64}$/D', $token)) {
        $token = bin2hex(random_bytes(32));
        setcookie($cookie, $token, ['expires' => time() + 31536000, 'path' => '/', 'httponly' => true, 'secure' => $secure, 'samesite' => 'Lax']);
    }
    $voter = hash_hmac('sha256', $token, $config['secret']);
    $db = new PDO('sqlite:' . $private . '/voting.sqlite', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    $db->exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;');
    $action = $_GET['action'] ?? 'meta';
    $method = $_SERVER['REQUEST_METHOD'];
    if ($method === 'POST') {
        if (!str_starts_with($_SERVER['CONTENT_TYPE'] ?? '', 'application/json')) respond(['error' => 'Use JSON requests'], 415);
        if (!hash_equals($_SESSION['csrf'], $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '')) respond(['error' => 'Refresh the page and try again'], 403);
        $raw = file_get_contents('php://input', false, null, 0, 8193);
        if (strlen($raw) > 8192) respond(['error' => 'Request too large'], 413);
        $data = json_decode($raw, true, 32, JSON_THROW_ON_ERROR);
        if (!is_array($data)) respond(['error' => 'Invalid request'], 400);
    }
    if ($action === 'meta' && $method === 'GET') {
        $manifest = json_decode($db->query("SELECT value FROM metadata WHERE key='manifest'")->fetchColumn(), true, 32, JSON_THROW_ON_ERROR);
        respond(['manifest' => $manifest, 'csrf' => $_SESSION['csrf'], 'admin' => !empty($_SESSION['admin'])]);
    }
    if ($action === 'trials' && $method === 'GET') {
        $after = max(-1, (int)($_GET['after'] ?? -1));
        $unrated = ($_GET['unrated'] ?? '') === '1';
        $speed = in_array($_GET['sort'] ?? '', ['fast', 'slow'], true);
        $direction = ($_GET['sort'] ?? '') === 'slow' ? 'DESC' : 'ASC';
        $query = 'SELECT t.*, v.score AS my_score FROM trials t LEFT JOIN votes v ON v.trial_id=t.id AND v.voter=:voter WHERE ' . ($speed ? '1=1' : 't.position>:after');
        if ($unrated) $query .= ' AND v.score IS NULL';
        $query .= $speed ? " ORDER BY (json_extract(t.settings,'$.generation_seconds') IS NULL), json_extract(t.settings,'$.generation_seconds') $direction, t.position LIMIT 36 OFFSET :offset" : ' ORDER BY t.position LIMIT 36';
        $statement = $db->prepare($query);
        $statement->bindValue(':voter', $voter);
        $statement->bindValue($speed ? ':offset' : ':after', $speed ? $after + 1 : $after, PDO::PARAM_INT);
        $statement->execute();
        $items = [];
        foreach ($statement->fetchAll(PDO::FETCH_ASSOC) as $row) {
            $items[] = ['id' => $row['id'], 'position' => (int)$row['position'], 'prompt' => $row['prompt'],
                'images' => json_decode($row['images'], true), 'settings' => json_decode($row['settings'], true),
                'my_score' => $row['my_score'] === null ? null : (int)$row['my_score']];
        }
        respond(['trials' => $items, 'next' => $speed ? $after + count($items) : ($items ? end($items)['position'] : $after), 'more' => count($items) === 36]);
    }
    if ($action === 'vote' && $method === 'POST') {
        $id = $data['trial_id'] ?? '';
        $score = $data['score'] ?? null;
        if (!is_string($id) || !preg_match('/^[a-f0-9]{64}$/D', $id) || !is_int($score) || $score < 1 || $score > 5) respond(['error' => 'Use a valid image and score from 1 to 5'], 400);
        $check = $db->prepare('SELECT 1 FROM trials WHERE id=?');
        $check->execute([$id]);
        if (!$check->fetchColumn()) respond(['error' => 'Image not found'], 404);
        $limit = $db->prepare('SELECT COUNT(*) FROM votes WHERE voter=? AND updated_at>?');
        $limit->execute([$voter, time() - 60]);
        if ((int)$limit->fetchColumn() >= 120) respond(['error' => 'Please wait a minute before voting again'], 429);
        $statement = $db->prepare('INSERT INTO votes(trial_id,voter,score,updated_at) VALUES(?,?,?,?) ON CONFLICT(trial_id,voter) DO UPDATE SET score=excluded.score,updated_at=excluded.updated_at');
        $statement->execute([$id, $voter, $score, time()]);
        respond(['ok' => true, 'score' => $score]);
    }
    $summarySql = 'SELECT t.id,t.images,t.settings,COUNT(v.score) AS votes,ROUND(AVG(v.score),3) AS mean FROM trials t JOIN votes v ON v.trial_id=t.id GROUP BY t.id ORDER BY mean DESC,votes DESC';
    $configurationSql = 'SELECT t.config_key,MIN(t.settings) AS settings,COUNT(v.score) AS votes,COUNT(DISTINCT t.id) AS images,ROUND(AVG(v.score),3) AS mean FROM trials t JOIN votes v ON v.trial_id=t.id GROUP BY t.config_key ORDER BY mean DESC,votes DESC';
    if ($action === 'results' && $method === 'GET') {
        respond(['images' => $db->query($summarySql . ' LIMIT 50')->fetchAll(PDO::FETCH_ASSOC),
            'configurations' => $db->query($configurationSql . ' LIMIT 50')->fetchAll(PDO::FETCH_ASSOC),
            'votes' => (int)$db->query('SELECT COUNT(*) FROM votes')->fetchColumn()]);
    }
    if ($action === 'admin-login' && $method === 'POST') {
        $_SESSION['attempts'] ??= [];
        $_SESSION['attempts'] = array_values(array_filter($_SESSION['attempts'], fn($t) => $t > time() - 300));
        if (count($_SESSION['attempts']) >= 8) respond(['error' => 'Too many attempts. Wait five minutes.'], 429);
        $_SESSION['attempts'][] = time();
        if (!is_string($data['key'] ?? null) || !hash_equals($config['admin_key_hash'], hash('sha256', $data['key']))) respond(['error' => 'Incorrect admin key'], 403);
        session_regenerate_id(true);
        $_SESSION['admin'] = true;
        respond(['ok' => true]);
    }
    if ($action === 'admin-logout' && $method === 'POST') {
        unset($_SESSION['admin']);
        respond(['ok' => true]);
    }
    if (in_array($action, ['export-json', 'export-csv'], true) && $method === 'GET') {
        if (empty($_SESSION['admin'])) respond(['error' => 'Admin login required'], 403);
        if ($action === 'export-json') {
            header('Content-Disposition: attachment; filename="voting-backup.json"');
            respond(['metadata' => $db->query('SELECT * FROM metadata')->fetchAll(PDO::FETCH_ASSOC),
                'trials' => $db->query('SELECT * FROM trials')->fetchAll(PDO::FETCH_ASSOC),
                'votes' => $db->query('SELECT * FROM votes')->fetchAll(PDO::FETCH_ASSOC)]);
        }
        header('Content-Type: text/csv; charset=utf-8');
        header('Content-Disposition: attachment; filename="voting-results.csv"');
        $stream = fopen('php://output', 'w');
        fputcsv($stream, ['trial_id','votes','mean','settings'], ',', '"', '');
        foreach ($db->query($summarySql)->fetchAll(PDO::FETCH_ASSOC) as $row) {
            fputcsv($stream, [$row['id'],$row['votes'],$row['mean'],$row['settings']], ',', '"', '');
        }
        exit;
    }
    respond(['error' => 'Unknown action or method'], 404);
} catch (JsonException $error) {
    respond(['error' => 'Invalid JSON'], 400);
} catch (Throwable $error) {
    error_log('Krea2 voting: ' . $error->getMessage());
    respond(['error' => 'Server error. Check PHP logs, PDO_SQLITE and private-directory permissions.'], 500);
}
