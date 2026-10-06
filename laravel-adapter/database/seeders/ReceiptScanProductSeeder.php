<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;

class ReceiptScanProductSeeder extends Seeder
{
    public function run(): void
    {
        $products = [
            ['sku' => 'BLAST-ENERGY-KAKTUS', 'canonical_name' => 'BLAST Energy Drink Very Nice Kaktus'],
            ['sku' => 'BLAST-ENERGY-MANGO-ANANAS', 'canonical_name' => 'BLAST Energy Drink Very Nice Mango-Ananas'],
            ['sku' => 'BLAST-ENERGY-KLASYK', 'canonical_name' => 'BLAST Energy Drink Very Nice Klasyk'],
            ['sku' => 'BLAST-ENERGY-ARBUZ', 'canonical_name' => 'BLAST Energy Drink Very Nice Arbuz'],
            ['sku' => 'BLAST-BOOST-TRIPLE-BERRY', 'canonical_name' => 'BLAST Boost Triple Berry'],
            ['sku' => 'BLAST-BOOST-CLEMENTINE', 'canonical_name' => 'BLAST Boost Clementine'],
            ['sku' => 'BLAST-BOOST-KIWI', 'canonical_name' => 'BLAST Boost Kiwi'],
        ];
        foreach ($products as $product) {
            DB::table('receipt_scan_products')->updateOrInsert(['sku' => $product['sku']], $product + ['active' => true, 'updated_at' => now(), 'created_at' => now()]);
        }
    }
}
