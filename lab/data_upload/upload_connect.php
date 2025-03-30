<?php
header("Access-Control-Allow-Origin: *"); // Erlaubt CORS-Zugriff
header("Content-Type: application/json"); // JSON-Antwort

$upload_dir = __DIR__ . "/uploads/"; // Zielverzeichnis für die Datei
$upload_file = $upload_dir . "tst_point.json"; // Ziel-Dateiname

// Stelle sicher, dass das Verzeichnis existiert
if (!file_exists($upload_dir)) {
    mkdir($upload_dir, 0777, true);
}

// Prüfen, ob eine Datei hochgeladen wurde
if (!isset($_FILES["file"]) || $_FILES["file"]["error"] !== UPLOAD_ERR_OK) {
    echo json_encode(["success" => false, "message" => "Fehler beim Hochladen"]);
    exit;
}

// Datei speichern
if (move_uploaded_file($_FILES["file"]["tmp_name"], $upload_file)) {
    echo json_encode(["success" => true, "message" => "Datei erfolgreich gespeichert"]);
} else {
    echo json_encode(["success" => false, "message" => "Speichern fehlgeschlagen"]);
}
?>
