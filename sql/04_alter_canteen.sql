-- =====================================================================
-- 04_alter_canteen.sql  （在 ERPDATANEW 库执行，用 DBA 账号跑；可重复执行）
-- 变更：
--   1) meal_order 增加 canteen_code（点餐食堂，对应部门节点代号，如 1013/1020）
--   2) 唯一约束从 (emp_no, meal_date) 改为 (emp_no, meal_date, canteen_code)
--      —— 同一人同一天可分食堂点不同餐（中餐 A 食堂、晚餐 B 食堂）；
--         同一食堂内每人每天仍只有一条记录。
--   3) meal_config 预置两个食堂（可在系统「设定」页修改）
-- 权限：canteen_code 为 meal_order 新列，表级 GRANT 自动覆盖，无需再授权。
-- =====================================================================

-- 1) 新增食堂列
IF COL_LENGTH('dbo.meal_order', 'canteen_code') IS NULL
    ALTER TABLE dbo.meal_order ADD canteen_code NVARCHAR(20) NOT NULL DEFAULT N'';
GO

-- 2) 删除旧唯一约束（每人每天一条 → 改为 每人每天每食堂一条）
IF EXISTS (SELECT 1 FROM sys.key_constraints
           WHERE name = 'UQ_meal_order_emp_date'
             AND parent_object_id = OBJECT_ID('dbo.meal_order'))
    ALTER TABLE dbo.meal_order DROP CONSTRAINT UQ_meal_order_emp_date;
GO

-- 3) 新唯一约束
IF NOT EXISTS (SELECT 1 FROM sys.key_constraints
               WHERE name = 'UQ_meal_order_emp_date_canteen'
                 AND parent_object_id = OBJECT_ID('dbo.meal_order'))
    ALTER TABLE dbo.meal_order
        ADD CONSTRAINT UQ_meal_order_emp_date_canteen
        UNIQUE (emp_no, meal_date, canteen_code);
GO

-- 4) 食堂配置种子（JSON；后续在系统「设定」页维护）
IF NOT EXISTS (SELECT 1 FROM dbo.meal_config WHERE cfg_key = N'canteens')
    INSERT INTO dbo.meal_config (cfg_key, cfg_value)
    VALUES (N'canteens',
            N'[{"code":"1013","name":"越南旺盈食堂"},{"code":"1020","name":"越南至美食堂"}]');
GO

-- 5) 验证
SELECT name FROM sys.key_constraints
WHERE parent_object_id = OBJECT_ID('dbo.meal_order');
GO
