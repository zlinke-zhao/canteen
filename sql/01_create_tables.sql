-- =====================================================================
-- 工厂食堂预约吃饭 - 数据表建表脚本 (MSSQL / SQL Server)
-- 数据库: erpdatanew  (按你们实际库名调整)
-- 说明:
--   1. 本脚本只建「点餐系统」自己的 3 张表，不动 pass_hd / sys_emp_fourlevel。
--   2. 员工/部门只读这两张已有表，不需要权限变更。
--   3. 建表后请对应用连接账号 (如 erpadmin) 开 meal_* 三张表的 SELECT/INSERT/UPDATE/DELETE。
--   4. 表名带 dbo. 前缀，可按你们命名规范改 schema。
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) meal_order  点餐主表（每人每天一条记录，不可重复）
--    餐别: 早餐 breakfast / 中餐 lunch / 晚餐 dinner / 夜宵 midnight
--    每餐分 中国 CN / 越南 VN 两列统计 —— 由就餐人下单时「自己选择」国籍，
--    记录级 nationality 决定该人当天所有餐归入 CN 还是 VN 列。
-- ---------------------------------------------------------------------
IF OBJECT_ID('dbo.meal_order', 'U') IS NULL
CREATE TABLE dbo.meal_order (
    id          BIGINT         IDENTITY(1,1) PRIMARY KEY,
    emp_no      NVARCHAR(20)   NOT NULL,                 -- 工号 = sys_emp_fourlevel.EmpNo = pass_hd.user_name
    emp_name    NVARCHAR(100)  NULL,                     -- 姓名（冗余，便于报表/历史）
    deptno      NVARCHAR(40)   NULL,                     -- 部门码 = sys_emp_fourlevel.deptno
    dept_name   NVARCHAR(200)  NULL,                     -- 部门名（冗余，取自 V_deptfourlevel.deptnodesc）
    companyid   NVARCHAR(10)   NULL,                     -- 公司（冗余，便于多公司隔离）
    meal_date   DATE           NOT NULL,                 -- 用餐日期
    nationality CHAR(2)        NOT NULL,                 -- 'CN' 中国 / 'VN' 越南（本人自选）
    breakfast   BIT            NOT NULL DEFAULT 0,       -- 早餐
    lunch       BIT            NOT NULL DEFAULT 0,       -- 中餐
    dinner      BIT            NOT NULL DEFAULT 0,       -- 晚餐
    midnight    BIT            NOT NULL DEFAULT 0,       -- 夜宵
    orderer_no  NVARCHAR(20)   NULL,                     -- 代点人/本人 工号（谁操作的）
    remark      NVARCHAR(200)  NULL,                     -- 备注
    created_at  DATETIME       NOT NULL DEFAULT GETDATE(),
    updated_at  DATETIME       NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_meal_order_emp_date UNIQUE (emp_no, meal_date)  -- 每人每天唯一
);
-- 报表常用索引
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_meal_order_date' AND object_id=OBJECT_ID('dbo.meal_order'))
CREATE INDEX IX_meal_order_date ON dbo.meal_order (meal_date);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_meal_order_dept' AND object_id=OBJECT_ID('dbo.meal_order'))
CREATE INDEX IX_meal_order_dept ON dbo.meal_order (deptno, meal_date);
GO

-- ---------------------------------------------------------------------
-- 2) meal_stat_auth  汇总统计授权名单
--    记录哪些工号可以查看「日报 / 月报」汇总统计。
-- ---------------------------------------------------------------------
IF OBJECT_ID('dbo.meal_stat_auth', 'U') IS NULL
CREATE TABLE dbo.meal_stat_auth (
    emp_no      NVARCHAR(20)   NOT NULL PRIMARY KEY,      -- 被授权工号
    emp_name    NVARCHAR(100)  NULL,
    granted_by  NVARCHAR(20)   NULL,                     -- 授权人（管理员工号）
    granted_at  DATETIME       NOT NULL DEFAULT GETDATE()
);
GO

-- ---------------------------------------------------------------------
-- 3) meal_config  应用配置（键值对）
--    用途: 存管理员工号列表等。初始 key=admin_emp_nos，value=逗号分隔工号。
--    管理员可以: 管理 meal_stat_auth 名单、看全部统计。
-- ---------------------------------------------------------------------
IF OBJECT_ID('dbo.meal_config', 'U') IS NULL
CREATE TABLE dbo.meal_config (
    cfg_key     NVARCHAR(50)   NOT NULL PRIMARY KEY,
    cfg_value   NVARCHAR(MAX)  NULL,
    updated_at  DATETIME       NOT NULL DEFAULT GETDATE()
);
-- 初始插入管理员占位（请改成你们实际管理员工号；也可留空，由 APP_ADMIN_EMP_NOS 环境变量首次启动注入）
IF NOT EXISTS (SELECT 1 FROM dbo.meal_config WHERE cfg_key='admin_emp_nos')
INSERT INTO dbo.meal_config (cfg_key, cfg_value) VALUES ('admin_emp_nos', '');
GO

-- =====================================================================
-- 权限授予（示例，按你们账号调整）
--   将下方 <APP_DB_USER> 替换为应用实际使用的数据库登录名（如 erpadmin）。
--   如果只是用现有可写账号连库，连表都属于同一登录，通常无需额外授权；
--   若用只读账号 erp_readonly 读已有表、另建写账号写新表，则给写账号如下权限：
-- =====================================================================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_order     TO <APP_DB_USER>;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_stat_auth TO <APP_DB_USER>;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_config    TO <APP_DB_USER>;
-- GO
