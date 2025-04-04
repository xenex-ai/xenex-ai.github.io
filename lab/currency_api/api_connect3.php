<?php
// api_connect.php
// Diese Datei muss im Verzeichnis SERVER-URL/xenexai/connect/ abgelegt werden.

header('Content-Type: application/json');

// Nur POST-Anfragen zulassen
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(["status" => "error", "message" => "Method not allowed."]);
    exit;
}

// Prüfen, ob eine Datei mit dem Schlüssel "file" gesendet wurde
if (!isset($_FILES['file'])) {
    http_response_code(400);
    echo json_encode(["status" => "error", "message" => "No file uploaded."]);
    exit;
}

$uploadDir = __DIR__ . '/uploads/';

// Zielordner erstellen, falls nicht vorhanden
if (!file_exists($uploadDir) && !mkdir($uploadDir, 0755, true)) {
    http_response_code(500);
    echo json_encode(["status" => "error", "message" => "Failed to create upload directory."]);
    exit;
}

// Dateinamen und Pfad festlegen
$uploadedFile = $_FILES['file'];
$targetFile = $uploadDir . basename($uploadedFile['name']);

// Datei in den Zielordner verschieben
if (move_uploaded_file($uploadedFile['tmp_name'], $targetFile)) {
    http_response_code(200);
    echo json_encode(["status" => "success", "message" => "File successfully uploaded."]);
} else {
    http_response_code(500);
    echo json_encode(["status" => "error", "message" => "File upload failed."]);
}
?>
