-- =====================================================================
-- Rename China-restaurant columns from *_tq to *_cn
--   tq = "Trung Quoc" (Vietnamese for China); change to ISO 3166-1 alpha-2 "CN".
--   vn (Vietnam) stays as-is (already the international standard).
-- Requires DBA privilege (sysadmin / db_owner). The app login erp_readonly
--   has NO ALTER, so run this with a DBA account.
-- Safe to re-run: each step guarded by COL_LENGTH. sp_rename only renames,
--   existing data is preserved.
-- After running, restart the canteen app (the code now reads *_cn columns).
-- =====================================================================

IF COL_LENGTH('dbo.meal_order', 'breakfast_tq') IS NOT NULL
    EXEC sp_rename 'dbo.meal_order.breakfast_tq', 'breakfast_cn', 'COLUMN';
IF COL_LENGTH('dbo.meal_order', 'lunch_tq') IS NOT NULL
    EXEC sp_rename 'dbo.meal_order.lunch_tq', 'lunch_cn', 'COLUMN';
IF COL_LENGTH('dbo.meal_order', 'wucan_tq') IS NOT NULL
    EXEC sp_rename 'dbo.meal_order.wucan_tq', 'wucan_cn', 'COLUMN';
IF COL_LENGTH('dbo.meal_order', 'dinner_tq') IS NOT NULL
    EXEC sp_rename 'dbo.meal_order.dinner_tq', 'dinner_cn', 'COLUMN';
IF COL_LENGTH('dbo.meal_order', 'midnight_tq') IS NOT NULL
    EXEC sp_rename 'dbo.meal_order.midnight_tq', 'midnight_cn', 'COLUMN';

-- Align the stored nationality value: TQ -> CN (VN unchanged)
UPDATE dbo.meal_order SET nationality = 'CN' WHERE nationality = 'TQ';
