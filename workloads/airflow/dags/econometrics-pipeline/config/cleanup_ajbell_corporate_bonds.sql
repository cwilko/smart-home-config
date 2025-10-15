-- Clean up AJ Bell corporate bond data from the mixed table
-- This removes today's data so AJ Bell can be collected into the new dedicated table

-- Check what we're about to delete (run this first to verify)
SELECT 
    COUNT(*) as records_to_delete,
    MIN(created_at) as earliest_created,
    MAX(created_at) as latest_created,
    DATE(scraped_date) as scraped_date
FROM corporate_bond_prices 
WHERE DATE(created_at) = CURRENT_DATE
GROUP BY DATE(scraped_date);

-- Uncomment the following line to actually delete today's data
DELETE FROM corporate_bond_prices WHERE DATE(created_at) = CURRENT_DATE;

-- Alternative: Delete by scraped_date if you want to be more specific
-- DELETE FROM corporate_bond_prices WHERE scraped_date = '2025-10-15';

-- Check remaining data after deletion
SELECT COUNT(*) as remaining_records FROM corporate_bond_prices;