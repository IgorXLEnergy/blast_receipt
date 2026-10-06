<?php

return [
    'url' => env('RECEIPT_OCR_URL', 'http://127.0.0.1:8010'),
    'timeout' => (int) env('RECEIPT_OCR_TIMEOUT', 60),
    'auto_threshold' => (float) env('RECEIPT_BLAST_AUTO_THRESHOLD', 0.94),
    'review_threshold' => (float) env('RECEIPT_BLAST_REVIEW_THRESHOLD', 0.72),
];
