<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('receipt_scan_products', function (Blueprint $table) {
            $table->id();
            $table->string('sku')->unique();
            $table->string('canonical_name');
            $table->boolean('active')->default(true);
            $table->timestamps();
        });

        Schema::create('receipt_product_aliases', function (Blueprint $table) {
            $table->id();
            $table->foreignId('product_id')->constrained('receipt_scan_products')->cascadeOnDelete();
            $table->string('retailer_code')->nullable()->index();
            $table->string('alias');
            $table->boolean('verified')->default(false);
            $table->unsignedInteger('seen_count')->default(0);
            $table->timestamps();
            $table->unique(['product_id', 'retailer_code', 'alias'], 'receipt_alias_unique');
        });

        Schema::create('receipt_scans', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->nullable()->index();
            $table->string('image_path');
            $table->char('image_sha256', 64)->index();
            $table->string('retailer_code')->nullable()->index();
            $table->date('purchase_date')->nullable()->index();
            $table->string('decision')->index();
            $table->unsignedInteger('blast_quantity')->default(0);
            $table->decimal('blast_spend', 10, 2)->nullable();
            $table->decimal('average_blast_unit_price', 10, 2)->nullable();
            $table->decimal('confidence', 6, 5)->nullable();
            $table->json('ocr_payload');
            $table->json('analysis_payload');
            $table->timestamps();
        });

        Schema::create('receipt_scan_items', function (Blueprint $table) {
            $table->id();
            $table->foreignId('receipt_scan_id')->constrained()->cascadeOnDelete();
            $table->foreignId('product_id')->nullable()->constrained('receipt_scan_products')->nullOnDelete();
            $table->boolean('is_blast')->default(false)->index();
            $table->string('raw_name');
            $table->string('normalized_name')->nullable()->index();
            $table->unsignedInteger('quantity')->default(1);
            $table->decimal('unit_price', 10, 2)->nullable();
            $table->decimal('line_total', 10, 2)->nullable();
            $table->decimal('discount_total', 10, 2)->default(0);
            $table->decimal('effective_unit_price', 10, 2)->nullable();
            $table->decimal('confidence', 6, 5)->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('receipt_scan_items');
        Schema::dropIfExists('receipt_scans');
        Schema::dropIfExists('receipt_product_aliases');
        Schema::dropIfExists('receipt_scan_products');
    }
};
