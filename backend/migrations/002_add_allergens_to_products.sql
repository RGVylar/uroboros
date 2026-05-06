-- Add allergens JSON column to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS allergens JSON;
