<?php

$input = isset($_GET['input']) ? $_GET['input'] : null;
$mode = isset($_POST['mode']) ? $_POST['mode'] : 'default';
$tags = isset($_POST['tags']) ? $_POST['tags'] : null;

if (!$input) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing input text']);
    exit;
}

// Your API Key
$apiKey = 'YOUR_API_KEY_HERE';

$data = [
    'input' => $input,
    'mode' => $mode,
    'tags' => $tags
];

// Use cURL to send a POST request to the Python API
$ch = curl_init('http://localhost:5000/generate');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'X-API-KEY: ' . $apiKey
]);

$response = curl_exec($ch);
curl_close($ch);

header('Content-Type: application/json');
echo $response;
?>
