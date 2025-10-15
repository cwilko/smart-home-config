-- Migration script to separate AJ Bell corporate bond data into its own table
-- Run this AFTER creating the ajbell_corporate_bond_prices table

-- First, create the new table (should already exist from create_tables.sql)
-- CREATE TABLE IF NOT EXISTS ajbell_corporate_bond_prices (...);

-- Insert existing AJ Bell data from the mixed table into the new dedicated table
-- Since we can't reliably identify AJ Bell vs HL data, we'll start fresh
-- The next DAG run will populate the new table correctly

-- Optional: Clean up any mixed data if you want to start completely fresh
-- DELETE FROM corporate_bond_prices WHERE created_at >= '2025-10-15';

-- The AJ Bell collector will now populate ajbell_corporate_bond_prices on the next run
SELECT 'Migration setup complete - AJ Bell corporate bonds will be collected into separate table on next DAG run' as status;