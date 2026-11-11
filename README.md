# 工厂食堂预约吃饭系统

全栈项目：员工登录 → 为自己 / 本部门同事预约某天用餐（早餐 / 中餐 / 晚餐 / 夜宵，每餐分 **中国 TQ / 越南 VN**）→ 授权人员查看 **日报 / 月报**（部门 × 餐别中越 交叉汇总，样式参照 BIỂU BÁO CƠM HÀNG NGÀY）。

## 技术栈
- 后端：Python + **FastAPI** + **pymssql**（复用现有 MSSQL 连接约定）
- 前端：原生 HTML/CSS/JS 单页应用，由 FastAPI 静态托管（**零构建**）
- 数据库：MSSQL（现有 `pass_hd` / `sys_emp_fourlevel` / `sys_dept` 只读；新建 `meal_*` 三张表）

## 底层数据关系（已探查确认）
- 登录账号：`pass_hd.user_name` = 工号(`EmpNo`)，密码 `pass_hd.pwd`
- **密码校验（本地，无需 ERP 接口）**：直接校验 `pass_hd.pwd`，兼容三套历史格式——
  `bcrypt`（`$2a$11$...`，60 位）、`MD5`（32 位 hex）、`Base64(SHA1)`（28 字符）。员工用**自己的真实 ERP 密码**登录即可。
  如需改走 ERP 统一登录接口，填 `ERP_LOGIN_URL` 即可（优先级最高）。
- 姓名：`pass_hd.name_desc`（`sys_emp_fourlevel.EmpName` 多数为空，不使用）
- 部门名 / 负责人：`sys_emp_fourlevel.deptno` → `sys_dept.dept` → `deptdesc` / `deptmanager`
- 在职过滤：`ISNULL(IsDelete,0)=0`（`EmpState` 字段为空，不可用）

## 一、数据库建表（你来执行）
1. 在 `erpdatanew`（或目标库）执行 `sql/01_create_tables.sql`。
1b. **已建过表的库**再执行 `sql/03_alter_meal_order_8cols.sql`——点餐模型已升级为
   「中国餐厅 早/中/晚/夜宵 + 越南餐厅 早/中/晚/夜宵」8 个独立勾选位（新增 8 列并自动迁移旧数据，可重复执行）。
2. 给**应用实际连库的账号**对三张新表开 `SELECT/INSERT/UPDATE/DELETE`。
   > 已实测：本机应用连库身份是 **`erp_readonly`**（不是 erpadmin），只读角色能读全库但写新表会被拒（错误 229）。故须显式授权，脚本见 `sql/02_grant.sql`：
   ```sql
   GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_order     TO erp_readonly;
   GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_stat_auth TO erp_readonly;
   GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.meal_config    TO erp_readonly;
   ```
3. `meal_config.admin_emp_nos` 默认空；管理员可在 `.env` 的 `APP_ADMIN_EMP_NOS` 先填好（逗号分隔工号），首次启动会自动注入；也可后续在库里直接改。

> 表已用 `IF OBJECT_ID(...) IS NULL` 保护，重复执行安全。

## 二、后端运行
```bash
cd canteen/backend
pip install -r ../requirements.txt
cp ../.env.example .env     # 然后编辑 .env：填 JWT_SECRET、APP_ADMIN_EMP_NOS 等
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
**推荐：统一入口** —— 双击 ERP 根目录的 `start.bat`，一次启动所有子系统：食堂 `http://127.0.0.1:8000/`，IT 资产管理 `http://127.0.0.1:8000/ITAM/`；应用清单在 `gateway/apps.json`，以后新增系统只加一行，不必再写新的 start.bat。
仅单独调试本系统时才双击 `canteen/start.bat`（它同样占用 8000，不要与统一入口同时开）。

### 关键配置（.env）
| 项 | 说明 |
|---|---|
| `ERP_LOGIN_URL` | **可选**。留空时用 `pass_hd.pwd` 本地校验真实密码（支持 bcrypt / MD5 / Base64-SHA1）。若要改走 ERP 统一登录接口，填此地址；默认契约 `POST {username,password}` → HTTP 200 且 `success` 为真 / `code=0` / 含 `token`；格式不同则改 `backend/auth.py` 的 `_verify_via_erp`。 |
| `JWT_SECRET` | 改成一段随机长字符串（≥32 字节）。**换掉它会让所有已登录令牌失效**（需重新登录）。 |
| `APP_DEV_FALLBACK` | 本地联调开关。`1` 时可用统一口令 `APP_DEV_PWD` 登录**任意有效员工**账号。生产务必 `0`。 |
| `APP_DEV_PWD` | 开发兜底口令 |
| `APP_ADMIN_EMP_NOS` | 管理员工号（逗号分隔），可看全部统计、管理授权名单 |
| `MSSQL_*` | 默认读机器级注册表；可用环境变量覆盖 |

> 连接账号需对 `meal_*` 有读写权限（见上）。`pass_hd` 等已有表只读即可。
> 登录失败提示：密码/工号错误显示「工号或密码错误」；令牌真正失效（如换了 `JWT_SECRET` 或超 12 小时）显示「登录状态已失效，请重新登录」。

## 三、功能与权限
- **双语界面**：右上角「Tiếng Việt / 中文」一键切换，选择存 localStorage；登录页、点餐、日报/月报、设定页全部翻译，报表导出 CSV 表头同步翻译。
- **姓名中越同显**：`sys_emp_fourlevel.EmpName`（中文名）+ `e_name`（越南名）合并显示为「武文雄(Vũ Văn Hùng)」；一方缺失只显示另一方；`e_name` 被填了中文备注的脏数据（不含越南语变音字符）不会误拼。
- **点餐**：本人下单；勾选「代本部门同事点」可搜索同部门同事代点。每人**每天每食堂一条记录**（`UNIQUE(emp_no, meal_date, canteen_code)`），重复保存即更新。同一餐不可在两个食堂重复点。
- **统计授权人员跨部门代点**：在 `meal_stat_auth` 名单内的人，可为「当前所选食堂」代号起头的**任意部门**点餐 —— 如食堂 1013（越南旺盈），则 1013 及其所有下级部门的员工均可代点；按部门点餐的下拉也会放开到整个食堂范围。切换食堂后范围随之变化（1013 ↔ 1020 各管各的）。跨部门已登记记录在点餐页预填同样可见，避免误覆盖。
- **按部门批量勾选（三态 NULL / Y / N）**：选择部门会自动切换到「按部门点」，并取消「个人点餐 / 客户用餐登记」。勾选任一餐次时，系统把**同一天、同一餐次列**中所有「尚未登记的空白格（NULL）」自动打勾（Y），用户再逐个取消不吃的同事（N）。之后无论反复勾选 → 取消 → 再勾选，**N 永远不会被自动勾回**；已登记为 0 的格子同样视为 N，保存后刷新也不会退化。保存时前端把三态归一化成 0/1 提交，**数据库表结构无需改动**。
- **日报 / 月报**：需 `can_stat` 权限（管理员 或 被加入 `meal_stat_auth` 名单）。按部门汇总各餐中/越人数 + 小计 + 红色合计行。可导出 CSV。
- **管理**：仅管理员可见。维护 `meal_stat_auth` 授权名单（搜索工号/姓名添加、移除）。

## 三·一、中文/越南文编码（重要）
- 数据库 varchar 列（`pass_hd.name_desc`、`sys_dept.deptdesc` 等）按 **GBK** 存字节；nvarchar 列（`EmpName`、`e_name`）是真 Unicode（含越南文 ễ/ơ，GBK 编不了）。
- 连接字符集用 **UTF-8**（`MSSQL_CHARSET=UTF-8`）：写入中文/越南文全部正确落库；nvarchar 读取无损。
- varchar 列直接读会乱 → 统一 `CONVERT(VARBINARY(n), col)` 取原始字节，客户端 `db.dec_gbk()` 按 GBK 解码（hex 技巧）。
- 历史乱码（GBK 字节被按 Latin-1 码点写入 nvarchar，SSMS 里显示「Îä´º³¤」）已由 `backend/_fix_mojibake.py` 一次性修复（meal_order / meal_stat_auth / meal_config）；若再出现可重跑。

## 四、API 速查
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/login` | 登录，返回 JWT |
| GET | `/api/me` | 当前用户 + 权限标志 |
| GET | `/api/colleagues?keyword=` | 同部门同事 |
| GET/POST/DELETE | `/api/order` | 点餐查询 / 保存(upsert) / 取消 |
| GET | `/api/report/daily?date=` | 日报 |
| GET | `/api/report/monthly?year=&month=` | 月报 |
| GET/POST/DELETE | `/api/admin/stat-auth` | 授权名单管理（管理员） |
| GET | `/api/admin/employees/search?keyword=` | 全厂员工搜索（管理员） |

## 说明 / 已知限制
- 国籍为**订单级**（一人一天选一次中或越），用于报表中越分列；不做按餐别分别选国籍。
- 日报仅列出**当日有登记**的部门；如需固定部门清单/顺序或更高层级汇总，可在 `backend/routers/report.py` 调整分组口径。
- 管理员名单通过环境变量 / `meal_config` 维护，UI 暂不直接新增管理员（避免权限失控）。
