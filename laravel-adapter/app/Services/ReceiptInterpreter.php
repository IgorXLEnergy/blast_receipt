<?php

namespace App\Services;

use Illuminate\Support\Str;

/**
 * Starter interpreter. In production replace $products/$retailers with DB-backed
 * Product, ProductAlias and RetailerProfile models.
 */
class ReceiptInterpreter
{
    public function interpret(array $ocr, array $products, array $retailers): array
    {
        $rows = collect($ocr['lines'] ?? [])->values();
        $lines = $rows->pluck('text')->map(fn ($v) => (string) $v)->all();
        $retailer = $this->detectRetailer($lines, $retailers);
        $items = [];

        foreach ($lines as $index => $raw) {
            $match = $this->matchProduct($raw, $products);
            if (!$match) {
                continue;
            }
            $price = $this->quantityAndPrice($lines, $index);
            $ocrConfidence = (float) ($rows[$index]['confidence'] ?? 0.80);
            $items[] = array_merge($price, [
                'sku' => $match['sku'],
                'canonical_name' => $match['canonical_name'],
                'match_score' => $match['score'],
                'ocr_confidence' => $ocrConfidence,
                'confidence' => min($match['score'], $ocrConfidence),
                'source_line' => $raw,
            ]);
        }

        $quantity = array_sum(array_column($items, 'quantity'));
        $spendValues = array_values(array_filter(array_column($items, 'effective_total'), fn ($v) => $v !== null));
        $spend = count($spendValues) ? round(array_sum($spendValues), 2) : null;
        $minConfidence = count($items) ? min(array_column($items, 'confidence')) : 0.0;

        $decision = 'reject_no_blast';
        if ($quantity > 0) {
            $decision = $minConfidence >= config('receipt_ocr.auto_threshold') ? 'accepted' : 'manual_review';
        }

        return [
            'decision' => $decision,
            'retailer' => $retailer,
            'blast' => [
                'found' => $quantity > 0,
                'quantity' => $quantity,
                'spend' => $spend,
                'average_effective_unit_price' => $spend !== null && $quantity > 0 ? round($spend / $quantity, 2) : null,
                'products' => $items,
            ],
            'ocr' => $ocr,
        ];
    }

    private function quantityAndPrice(array $lines, int $index): array
    {
        $context = [];
        foreach ([$index, $index + 1, $index - 1, $index + 2] as $i) {
            if (isset($lines[$i])) {
                $context[] = $this->normalize($lines[$i]);
            }
        }
        $joined = implode(' | ', $context);
        $quantity = 1;
        $unitPrice = null;

        if (preg_match('/(?:^|\s)(\d{1,3})\s*[X*]\s*(\d{1,4}[,.]\d{2})/', $joined, $m)) {
            $quantity = max(1, min(200, (int) $m[1]));
            $unitPrice = $this->money($m[2]);
        } elseif (preg_match('/(?:^|\s)(\d{1,3})\s*SZT\.?\b/', $joined, $m)) {
            $quantity = max(1, min(200, (int) $m[1]));
        }

        preg_match_all('/(?<!\d)(-?\d{1,4}[,.]\d{2})(?!\d)/', $this->normalize($lines[$index]), $amounts);
        $current = array_map(fn ($v) => $this->money($v), $amounts[1] ?? []);
        $lineTotal = null;

        if ($quantity > 1 && $unitPrice !== null) {
            $lineTotal = round($quantity * $unitPrice, 2);
        } elseif (count($current)) {
            $lineTotal = end($current);
            $unitPrice = $lineTotal;
        }

        if ($quantity > 1 && $unitPrice === null && $lineTotal !== null) {
            $unitPrice = round($lineTotal / $quantity, 2);
        }

        return [
            'quantity' => $quantity,
            'unit_price' => $unitPrice,
            'line_total' => $lineTotal,
            'discount_total' => 0.0,
            'effective_unit_price' => $unitPrice,
            'effective_total' => $lineTotal,
        ];
    }

    private function matchProduct(string $line, array $products): ?array
    {
        $line = $this->normalize($line);
        if (!Str::contains($line, ['BLAST', 'BLST', 'BLA5T'])) {
            return null;
        }

        $best = null;
        $bestScore = 0.0;
        foreach ($products as $product) {
            foreach ($product['aliases'] ?? [] as $alias) {
                $score = $this->similarity($line, $this->normalize($alias));
                if ($score > $bestScore) {
                    $best = $product;
                    $bestScore = $score;
                }
            }
        }
        if (!$best || $bestScore < 0.55) {
            return null;
        }
        return ['sku' => $best['sku'], 'canonical_name' => $best['canonical_name'], 'score' => round($bestScore, 4)];
    }

    private function detectRetailer(array $lines, array $retailers): ?array
    {
        $head = $this->normalize(implode(' ', array_slice($lines, 0, 20)));
        foreach ($retailers as $retailer) {
            foreach ($retailer['markers'] ?? [] as $marker) {
                if (Str::contains($head, $this->normalize($marker))) {
                    return ['code' => $retailer['code'], 'name' => $retailer['name'], 'confidence' => 0.99];
                }
            }
        }
        return null;
    }

    private function normalize(string $value): string
    {
        $value = Str::upper(Str::ascii($value));
        $value = preg_replace('/[^A-Z0-9.,%+*X -]/', ' ', $value);
        return trim(preg_replace('/\s+/', ' ', $value));
    }

    private function similarity(string $a, string $b): float
    {
        if ($a === '' || $b === '') return 0.0;
        similar_text($a, $b, $pct);
        return $pct / 100;
    }

    private function money(string $value): float
    {
        return round((float) str_replace(',', '.', $value), 2);
    }
}
