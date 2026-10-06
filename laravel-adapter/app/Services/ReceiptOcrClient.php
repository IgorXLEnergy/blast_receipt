<?php

namespace App\Services;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;

class ReceiptOcrClient
{
    private function client(): PendingRequest
    {
        return Http::baseUrl(rtrim(config('receipt_ocr.url'), '/'))
            ->timeout(config('receipt_ocr.timeout'))
            ->retry(2, 500);
    }

    public function ocr(string $absolutePath, ?string $filename = null): array
    {
        $filename ??= basename($absolutePath);

        return $this->client()
            ->attach('file', fopen($absolutePath, 'r'), $filename)
            ->post('/v1/ocr')
            ->throw()
            ->json();
    }
}
