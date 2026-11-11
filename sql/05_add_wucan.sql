-- =====================================================================
-- 05_add_wucan.sql  在 ERPDATANEW 库执行（用 sa/DBA 等有权账号跑）
-- 变更：点餐模型新增第 5 个餐别「午餐」(wucan)，中/越各一列：
--       wucan_tq（中国餐厅午餐）、wucan_vn（越南餐厅午餐）
-- 背景：报表在「过滤越南员工」时改为班次布局（早餐 | 白班(中餐,午餐) | 夜班(晚餐,夜餐)），
--       为与截图 5 列严格对应，系统新增一个「午餐」餐别。
-- 权限：meal_order 的 GRANT 在 02_grant.sql 已是表级（SELECT/INSERT/UPDATE/DELETE），
--       新增列自动继承，无需再授权；下方 GRANT 幂等补一遍更稳妥。
-- 可重复执行（以列是否存在为判断）。
-- =====================================================================

IF COL_LENGTH('dbo.meal_order', 'wucan_tq') IS NULL
    ALTER TABLE dbo.meal_order ADD
        wucan_tq INT NOT NULL DEFAULT 0,
        wucan_vn INT NOT NULL DEFAULT 0;
GO

GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_order TO erp_readonly;
GO

-- 验证（可选）：确认已新增两列
SELECT name FROM sys.columns
WHERE object_id = OBJECT_ID('dbo.meal_order')
  AND name IN ('wucan_tq', 'wucan_vn')
ORDER BY name;
GO
