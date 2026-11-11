-- =====================================================================
-- 02_grant.sql  授权脚本（在 ERPDATANEW 库执行，用 sa/DBA 等有权账号跑）
-- 作用: 给【应用实际连库账号 erp_readonly】开放三张新表的写权限。
--
-- 重要背景（已排查确认）:
--   应用运行时连接身份是 erp_readonly（不是 erpadmin）。
--   erp_readonly 通过 db_datareader 已能读全库（含 meal_*），
--   但默认无写权限，导致点餐/授权管理等写操作报 229 拒绝。
--   本脚本只放开应用自建的三张表，不影响基础 ERP 表的只读属性。
--
-- 若你们实际想让应用改用其他可写账号，把下面的 erp_readonly 改成该账号即可。
-- =====================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_order     TO erp_readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_stat_auth TO erp_readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_config    TO erp_readonly;
GO

-- 验证（可选）：确认 erp_readonly 在三张表上的权限
SELECT
    obj.name             AS table_name,
    perm.permission_name AS permission,
    perm.state_desc      AS state
FROM sys.database_permissions perm
JOIN sys.objects obj ON obj.object_id = perm.major_id
JOIN sys.database_principals pri ON pri.principal_id = perm.grantee_principal_id
WHERE pri.name = 'erp_readonly'
  AND obj.name IN ('meal_order','meal_stat_auth','meal_config')
ORDER BY obj.name, perm.permission_name;
GO
