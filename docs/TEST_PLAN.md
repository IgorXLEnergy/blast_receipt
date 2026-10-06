# First receipt test plan

Start with 30-50 receipts per high-priority retailer, ideally from different stores, cities and checkout systems.

For each receipt record ground truth:

1. retailer,
2. purchase date,
3. BLAST SKU(s),
4. exact BLAST quantity,
5. displayed unit price,
6. effective unit price after receipt-level/product-level discount,
7. total BLAST spend,
8. whether each non-BLAST OCR line is a real product line.

Track metrics separately:

- retailer accuracy,
- BLAST presence precision / recall,
- exact SKU accuracy,
- exact quantity accuracy,
- unit-price MAE and exact-match rate,
- false automatic acceptance rate,
- OCR failure rate by image-quality class.

For a competition/reward flow, prioritize low false acceptance over raw recall. Uncertain receipts should go to manual review.
