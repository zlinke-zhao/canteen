-- =====================================================================
-- 03_alter_meal_order_8cols.sql  （在 ERPDATANEW 库执行，用建表的 DBA 账号跑）
-- 变更：点餐模型从「4 餐 + 单国籍(nationality)」升级为「8 个独立勾选位」：
--       中国餐厅 早/中/晚/夜宵 (breakfast_cn, lunch_cn, dinner_cn, midnight_cn)
--       越南餐厅 早/中/晚/夜宵 (breakfast_vn, lunch_vn, dinner_vn, midnight_vn)
-- 兼容：旧列 (nationality, breakfast, lunch, dinner, midnight) 保留不删，
--       旧数据自动迁移到新列；本脚本可重复执行。
-- 权限：表级 GRANT 已覆盖新增列，无需再授权。
-- =====================================================================

-- 1) 新增 8 列（以第一列是否存在为整体判断）
IF COL_LENGTH('dbo.meal_order', 'breakfast_cn') IS NULL
    ALTER TABLE dbo.meal_order ADD
        breakfast_cn INT NOT NULL DEFAULT 0,
        breakfast_vn INT NOT NULL DEFAULT 0,
        lunch_cn     INT NOT NULL DEFAULT 0,
        lunch_vn     INT NOT NULL DEFAULT 0,
        dinner_cn    INT NOT NULL DEFAULT 0,
        dinner_vn    INT NOT NULL DEFAULT 0,
        midnight_cn  INT NOT NULL DEFAULT 0,
        midnight_vn  INT NOT NULL DEFAULT 0;
GO

-- 2) 迁移旧数据：按旧 nationality 把旧 4 餐标志落到对应中/越列。
--    仅处理「新列全为 0 且旧列有勾选」的行，天然幂等（重复执行不重复叠加）。
UPDATE dbo.meal_order SET
    breakfast_cn = CASE WHEN nationality = 'CN' THEN CAST(ISNULL(breakfast, 0) AS INT) ELSE breakfast_cn END,
    breakfast_vn = CASE WHEN nationality = 'VN' THEN CAST(ISNULL(breakfast, 0) AS INT) ELSE breakfast_vn END,
    lunch_cn     = CASE WHEN nationality = 'CN' THEN CAST(ISNULL(lunch, 0)     AS INT) ELSE lunch_cn     END,
    lunch_vn     = CASE WHEN nationality = 'VN' THEN CAST(ISNULL(lunch, 0)     AS INT) ELSE lunch_vn     END,
    dinner_cn    = CASE WHEN nationality = 'CN' THEN CAST(ISNULL(dinner, 0)    AS INT) ELSE dinner_cn    END,
    dinner_vn    = CASE WHEN nationality = 'VN' THEN CAST(ISNULL(dinner, 0)    AS INT) ELSE dinner_vn    END,
    midnight_cn  = CASE WHEN nationality = 'CN' THEN CAST(ISNULL(midnight, 0)  AS INT) ELSE midnight_cn  END,
    midnight_vn  = CASE WHEN nationality = 'VN' THEN CAST(ISNULL(midnight, 0)  AS INT) ELSE midnight_vn  END
WHERE CAST(ISNULL(breakfast, 0) AS INT) + CAST(ISNULL(lunch, 0) AS INT)
    + CAST(ISNULL(dinner, 0) AS INT) + CAST(ISNULL(midnight, 0) AS INT) > 0
  AND breakfast_cn + breakfast_vn + lunch_cn + lunch_vn
    + dinner_cn + dinner_vn + midnight_cn + midnight_vn = 0;
GO

-- 3) 验证（可选）：查看新列结构
SELECT name, system_type_id, max_length FROM sys.columns
WHERE object_id = OBJECT_ID('dbo.meal_order')
ORDER BY column_id;
GO
