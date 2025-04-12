<?php
// transactions_api.php

header("Content-Type: application/json; charset=UTF-8");

// Pfad zur Datei, in der die Transaktionen gespeichert werden
$data_file = __DIR__ . "/transactions.json";

// Stelle sicher, dass die Datei existiert – falls nicht, erstelle eine leere JSON-Liste
if (!file_exists($data_file)) {
    file_put_contents($data_file, json_encode([]));
}

// Lese die gespeicherten Transaktionen
function readTransactions($data_file) {
    $data = file_get_contents($data_file);
    $transactions = json_decode($data, true);
    if (!is_array($transactions)) {
        $transactions = [];
    }
    return $transactions;
}

// Schreibe die aktualisierte Transaktionsliste
function writeTransactions($data_file, $transactions) {
    return file_put_contents($data_file, json_encode($transactions, JSON_PRETTY_PRINT));
}

// Hole die HTTP-Methode und gegebenenfalls den "action"-Parameter
$method = $_SERVER['REQUEST_METHOD'];
$action = isset($_REQUEST['action']) ? $_REQUEST['action'] : "";

if ($method === 'GET' && empty($action)) {
    // GET-Anfrage ohne Aktion: Liefere alle Transaktionen
    $transactions = readTransactions($data_file);
    echo json_encode($transactions);
    exit;
} elseif (($method === 'POST' || $method === 'DELETE') && $action === 'delete') {
    // Entweder POST oder DELETE mit action=delete: Lösche einen Eintrag anhand der ID
    // Hole die ID (z.B. per POST oder als URL-Parameter)
    $entry_id = isset($_REQUEST['id']) ? $_REQUEST['id'] : "";
    if (empty($entry_id)) {
        http_response_code(400);
        echo json_encode(["success" => false, "error" => "Keine ID angegeben."]);
        exit;
    }
    $transactions = readTransactions($data_file);
    $found = false;
    // Durchsuche und entferne den Eintrag mit passender ID
    foreach ($transactions as $index => $transaction) {
        if (isset($transaction['id']) && $transaction['id'] === $entry_id) {
            unset($transactions[$index]);
            $found = true;
            break;
        }
    }
    if (!$found) {
        http_response_code(404);
        echo json_encode(["success" => false, "error" => "Eintrag nicht gefunden."]);
        exit;
    }
    // Reindexiere das Array, falls notwendig, und speichere es
    $transactions = array_values($transactions);
    if (writeTransactions($data_file, $transactions) === false) {
        http_response_code(500);
        echo json_encode(["success" => false, "error" => "Fehler beim Speichern."]);
        exit;
    }
    echo json_encode(["success" => true]);
    exit;
} else {
    http_response_code(405);
    echo json_encode(["success" => false, "error" => "Ungültige Anfragemethode oder Aktion."]);
    exit;
}
?>
