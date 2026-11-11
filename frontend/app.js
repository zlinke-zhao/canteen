// 工厂食堂预约系统 - 前端逻辑（原生 JS + fetch），中/越双语
const $ = (id) => document.getElementById(id);
// 二级目录部署：页面在 "/" 时 BASE=""，挂在 "/XXX/" 时 BASE="/XXX"。
// 独立运行与通过统一网关访问都正确，静态资源用相对路径配套。
const BASE = location.pathname.replace(/\/+$/, "");
const state = { token: localStorage.getItem("token"), user: null, orderNat: "cn" };

// ---------- 双语 ----------
const I18N = {
  zh: {
    app_title: "工厂食堂预约系统", ph_username: "工号", ph_password: "密码",
    btn_login: "登录", login_hint: "使用 ERP 工号登录（与 pass_hd 账号一致）",
    brand: "食堂预约", nav_order: "点餐", nav_daily: "日报", nav_monthly: "月报",
    nav_settings: "设定", btn_logout: "登出",
    order_title: "点餐登记", lbl_canteen: "用餐食堂", lbl_date_from: "日期从",
    lbl_date_to: "到", btn_search: "搜索", btn_search2: "搜索",
    chk_guest: "客户用餐登记", lbl_guest_count: "用餐人数", btn_add: "添加",
    chk_mode_self: "个人点餐", lbl_emp_search: "按工号搜索",
    lbl_nat: "点餐对象", opt_nat_cn: "中国员工点餐", opt_nat_vn: "越南员工点餐",
    ph_emp_kw: "输入工号或姓名后回车", chk_mode_dept: "按部门点",
    btn_save_all: "保存全部", btn_saving: "保存中…",
    daily_title: "每日各部门登记 · BIỂU BÁO CƠM HÀNG NGÀY",
    monthly_title: "月度汇总 · THỐNG KÊ THÁNG",
    lbl_date: "日期", lbl_canteen_f: "食堂", lbl_year: "年", lbl_month: "月",
    btn_query: "查询", btn_export: "导出CSV",
    settings_title: "设定", tab_auth: "页签一 · 统计授权", tab_canteen: "页签二 · 点餐食堂", tab_mealtimes: "页签三 · 开餐时间",
    auth_desc: "名单内人员可查看日报 / 月报，也可以在本页为本名单添加或移除人员。",
    ph_auth_kw: "搜索工号/姓名添加授权", btn_auth_add: "添加授权",
    th_emp_no: "工号", th_name: "姓名", th_granted_by: "授权人", th_action: "操作",
    canteen_desc: "食堂对应「部门节点代号」：下属部门代号自动包含上级代号，因此填 1013 即覆盖 1013 及其全部下级部门。特殊食堂（如安阳）可填「规则JSON」按多前缀/名称子集覆盖。",
    ph_ct_code: "部门代号，如 1013", ph_ct_name: "食堂名称，如 A食堂",
    ph_ct_rules: "规则JSON(可选)：留空=按代号前缀；特殊食堂填 [{\"type\":\"prefix\",\"value\":\"101305\"}] 或 [{\"type\":\"prefix_name\",\"prefix\":\"1013\",\"name\":\"安阳\"}]",
    canteen_desc2: "提示：点餐页的「中国/越南员工点餐」决定部门名单范围与写入餐厅；按工号点餐不受限。",
    btn_add_row: "添加一行", btn_save_canteen: "保存食堂设定", btn_save_meal_time: "保存开餐时间",
    btn_remove_auth: "移除", btn_delete: "删除",
    // 点餐网格 / 报表表头
    h_date: "日期", h_emp_no: "工号", h_name: "姓名",
    meal_breakfast: "早餐", meal_lunch: "中餐", meal_wucan: "午餐", meal_dinner: "晚餐", meal_midnight: "夜餐",
    r_no: "序号", r_dept: "部门", r_manager: "负责人", r_subtotal: "小计", r_total: "汇总",
    sub_cn: "中", sub_vn: "越",
    // 提示 / 消息
    hint_base: "个人点餐：设好日期范围后点「搜索」，列出该时段已有登记，未点餐的日期自动补一行；按部门点餐一次只处理一天（到日期自动隐藏），选部门后先列已登记的，再补未登记的人。同一餐不可在两个食堂重复点。各餐标题上有「全选」按钮，点击才将该餐批量勾给本部门全部人员（按班次互斥会自动取消对班）；单格手动勾选只影响本人。只能点开餐时间 2 小时以后的餐，过期/过去的餐次自动禁用。",
    hint_stat: "统计授权人员：可为「当前食堂」代号起头的全部部门点餐（如食堂 1013 → 1013 及其所有下级部门），按部门下拉已放开到整个食堂范围。",
    err_login: "工号或密码错误", err_token: "登录状态已失效，请重新登录",
    err_fill: "请输入工号和密码",
    err_empkw: "请输入工号或姓名",
    err_notfound_kw: "未找到「{kw}」对应的员工",
    msg_added: "已加入 {n} 人到名单", msg_already: "该员工已在名单中",
    msg_dept_loaded: "已载入部门名单 {n} 人（已登记排前，未登记自动补行）",
    msg_dept_truncated: "已载入 {n} 人（已达上限 {l} 人，请改选更细的部门再点）",
    msg_range: "已列出 {a} 至 {b} 的登记情况，红色日期为未点餐（自动补行）",
    err_need_canteen: "请先选择用餐食堂（未配置请到「设定」页）",
    err_need_date: "请选择用餐日期", err_need_meal: "请先勾选餐别",
    err_guest_count: "用餐人数请填 1-99",
    msg_canteen_switched: "已切换食堂，请重新选择部门",
    msg_saved: "已保存", msg_no_change: "无变更",
    msg_skip_head: "（{n} 条跳过：无权限/不存在/异常——", msg_conflict: "；冲突未保存：",
    no_canteen_opt: "（未配置食堂，请在「设定」页添加）",
    dept_placeholder: "（选择部门载入名单）",
    me_suffix: "（本人）", guest_suffix: "(客人{n})",
    confirm_remove: "移除 {emp} 的统计权限？", alert_pick_emp: "请先搜索并选择一名员工",
    msg_canteen_saved: "已保存 {n} 个食堂", canteen_all: "全部食堂",
    report_none: "暂无登记数据",
    rep_shift_day: "白班", rep_shift_night: "夜班", rep_nat_cn: "中国餐厅", rep_nat_vn: "越南餐厅",
    shift_conflict: "白班与夜班餐次互斥（早餐不限）：已自动取消该员工另一班次的已选餐",
    sel_all: "全选", sel_all_hint: "点击将该餐批量勾给全部人员",
    sel_all_done: "已全选 {meal}（按班次互斥已自动取消对班）",
    csv_total: "汇总",
    nav_detail: "明细", detail_title: "明细报表 · BÁO CÁO CHI TIẾT",
    lbl_start: "起始日期", lbl_end: "结束日期",
    detail_hint: "按日期范围查询每人每天的明细登记：可查单日，也可查多日。",
    detail_rows: "记录数", detail_total_meals: "总餐次",
  },
  vi: {
    app_title: "Hệ thống đặt cơm nhà máy", ph_username: "Mã nhân viên", ph_password: "Mật khẩu",
    btn_login: "Đăng nhập", login_hint: "Đăng nhập bằng mã nhân viên ERP (tài khoản pass_hd)",
    brand: "Đặt cơm", nav_order: "Đăng ký cơm", nav_daily: "Báo cáo ngày", nav_monthly: "Báo cáo tháng",
    nav_settings: "Cài đặt", btn_logout: "Đăng xuất",
    order_title: "Đăng ký cơm", lbl_canteen: "Căng tin", lbl_date_from: "Từ ngày",
    lbl_date_to: "Đến ngày", btn_search: "Tìm kiếm", btn_search2: "Tìm kiếm",
    chk_guest: "Đăng ký khách ăn", lbl_guest_count: "Số khách", btn_add: "Thêm",
    chk_mode_self: "Đăng ký cá nhân", lbl_emp_search: "Tìm theo mã NV",
    lbl_nat: "Đối tượng", opt_nat_cn: "Nhân viên CN", opt_nat_vn: "Nhân viên VN",
    ph_emp_kw: "Nhập mã NV hoặc tên rồi Enter", chk_mode_dept: "Theo phòng ban",
    btn_save_all: "Lưu tất cả", btn_saving: "Đang lưu…",
    daily_title: "Đăng ký hằng ngày theo phòng ban · BIỂU BÁO CƠM HÀNG NGÀY",
    monthly_title: "Tổng hợp theo tháng · THỐNG KÊ THÁNG",
    lbl_date: "Ngày", lbl_canteen_f: "Căng tin", lbl_year: "Năm", lbl_month: "Tháng",
    btn_query: "Truy vấn", btn_export: "Xuất CSV",
    settings_title: "Cài đặt", tab_auth: "Tab 1 · Phân quyền thống kê", tab_canteen: "Tab 2 · Căng tin ăn", tab_mealtimes: "Tab 3 · Giờ ăn",
    auth_desc: "Người trong danh sách được xem báo cáo ngày/tháng, và có thể thêm hoặc gỡ người khác khỏi danh sách tại đây.",
    ph_auth_kw: "Tìm mã NV / tên để thêm phân quyền", btn_auth_add: "Thêm phân quyền",
    th_emp_no: "Mã NV", th_name: "Họ tên", th_granted_by: "Người cấp quyền", th_action: "Thao tác",
    canteen_desc: "Căng tin ứng với \"mã phòng ban\": mã phòng ban cấp dưới tự động gồm mã cấp trên, nên điền 1013 là phủ 1013 và toàn bộ phòng ban cấp dưới. Căng tin đặc biệt (như An Dương) có thể điền \"Quy tắc JSON\" để phủ nhiều tiền tố / tập con theo tên.",
    ph_ct_code: "Mã phòng ban, vd 1013", ph_ct_name: "Tên căng tin, vd Căng tin A",
    ph_ct_rules: "Quy tắc JSON (tùy chọn): để trống=theo tiền tố mã; căng tin đặc biệt điền [{\"type\":\"prefix\",\"value\":\"101305\"}] hoặc [{\"type\":\"prefix_name\",\"prefix\":\"1013\",\"name\":\"An Dương\"}]",
    canteen_desc2: "Gợi ý: lựa chọn \"Nhân viên CN/VN\" trên trang đăng ký quyết định phạm vi danh sách và căng tin ghi nhận; tìm theo mã NV không bị giới hạn.",
    btn_add_row: "Thêm dòng", btn_save_canteen: "Lưu cấu hình căng tin", btn_save_meal_time: "Lưu giờ ăn",
    btn_remove_auth: "Gỡ bỏ", btn_delete: "Xóa",
    h_date: "Ngày", h_emp_no: "Mã NV", h_name: "Họ tên",
    meal_breakfast: "Bữa sáng", meal_lunch: "Bữa trưa", meal_wucan: "Cơm trưa 2", meal_dinner: "Bữa tối", meal_midnight: "Cơm đêm",
    r_no: "STT", r_dept: "Phòng ban", r_manager: "Người phụ trách", r_subtotal: "Cộng", r_total: "Tổng cộng",
    sub_cn: "CN", sub_vn: "VN",
    hint_base: "Đăng ký cá nhân: chọn khoảng ngày rồi bấm \"Tìm kiếm\", hệ thống liệt kê đăng ký đã có trong khoảng đó, ngày chưa đăng ký tự thêm dòng; đăng ký theo phòng ban mỗi lần chỉ xử lý một ngày (ô \"Đến ngày\" tự ẩn), chọn phòng ban sẽ liệt kê người đã đăng ký trước rồi bổ sung người chưa đăng ký. Cùng một bữa không thể đăng ký ở hai căng tin. Mỗi tiêu đề bữa có nút \"Chọn tất cả\": nhấn mới tích bữa này cho toàn bộ phòng ban (theo ca loại trừ nhau sẽ tự bỏ ca đối diện); tích thủ công từng ô chỉ ảnh hưởng bản thân. Chỉ được đặt bữa cách giờ ăn ít nhất 2 tiếng, bữa quá hạn/quá khứ tự vô hiệu.",
    hint_stat: "Người được phân quyền thống kê: có thể đăng ký cho mọi phòng ban có mã bắt đầu bằng mã căng tin hiện tại (vd căng tin 1013 → 1013 và tất cả phòng ban cấp dưới), danh sách phòng ban đã mở rộng toàn bộ phạm vi căng tin.",
    err_login: "Mã nhân viên hoặc mật khẩu sai", err_token: "Phiên đăng nhập hết hạn, vui lòng đăng nhập lại",
    err_fill: "Vui lòng nhập mã NV và mật khẩu",
    err_empkw: "Vui lòng nhập mã NV hoặc tên",
    err_notfound_kw: "Không tìm thấy nhân viên \"{kw}\"",
    msg_added: "Đã thêm {n} người vào danh sách", msg_already: "Nhân viên đã có trong danh sách",
    msg_dept_loaded: "Đã tải danh sách phòng ban {n} người (đã đăng ký xếp trước, chưa đăng ký tự thêm dòng)",
    msg_dept_truncated: "Đã tải {n} người (giới hạn {l} người, hãy chọn phòng ban nhỏ hơn)",
    msg_range: "Đã liệt kê tình hình đăng ký từ {a} đến {b}, ngày màu đỏ là chưa đăng ký (tự thêm dòng)",
    err_need_canteen: "Vui lòng chọn căng tin trước (chưa có hãy vào \"Cài đặt\")",
    err_need_date: "Vui lòng chọn ngày ăn", err_need_meal: "Vui lòng tích chọn bữa ăn",
    err_guest_count: "Số khách vui lòng nhập 1-99",
    msg_canteen_switched: "Đã đổi căng tin, vui lòng chọn lại phòng ban",
    msg_saved: "Đã lưu", msg_no_change: "Không có thay đổi",
    msg_skip_head: " ({n} dòng bỏ qua: không có quyền/không tồn tại/lỗi — ", msg_conflict: "；xung đột chưa lưu: ",
    no_canteen_opt: "(Chưa cấu hình căng tin, hãy thêm trong \"Cài đặt\")",
    dept_placeholder: "(Chọn phòng ban để tải danh sách)",
    me_suffix: "(Bản thân)", guest_suffix: "(Khách {n})",
    confirm_remove: "Gỡ quyền thống kê của {emp}?", alert_pick_emp: "Vui lòng tìm và chọn một nhân viên",
    msg_canteen_saved: "Đã lưu {n} căng tin", canteen_all: "Tất cả căng tin",
    report_none: "Chưa có dữ liệu đăng ký",
    rep_shift_day: "Ca ngày", rep_shift_night: "Ca đêm", rep_nat_cn: "Căng tin CN", rep_nat_vn: "Căng tin VN",
    shift_conflict: "Ca ngày và ca đêm loại trừ nhau (bữa sáng không giới hạn): đã bỏ các bữa ca kia của nhân viên này",
    sel_all: "Chọn tất cả", sel_all_hint: "Nhấn để tích bữa này cho tất cả mọi người",
    sel_all_done: "Đã chọn tất cả {meal} (theo ca loại trừ nhau, tự bỏ ca đối diện)",
    csv_total: "Tổng cộng",
    nav_detail: "Chi tiết", detail_title: "Báo cáo chi tiết · BÁO CÁO CHI TIẾT",
    lbl_start: "Từ ngày", lbl_end: "Đến ngày",
    detail_hint: "Truy vấn chi tiết đăng ký từng người từng ngày theo khoảng ngày: có thể một ngày hoặc nhiều ngày.",
    detail_rows: "Số bản ghi", detail_total_meals: "Tổng suất",
  },
};
let LANG = localStorage.getItem("canteen_lang") || "zh";
function t(key, vars) {
  let s = (I18N[LANG] && I18N[LANG][key]) != null ? I18N[LANG][key] : (I18N.zh[key] != null ? I18N.zh[key] : key);
  if (vars) for (const k in vars) s = s.split("{" + k + "}").join(vars[k]);
  return s;
}
function applyLang() {
  document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
  document.title = t("app_title");
  $("lang-btn").textContent = LANG === "zh" ? "Tiếng Việt" : "中文";
  $("order-hint").textContent = (state.user && state.user.can_stat ? t("hint_stat") : "") + t("hint_base");
  document.documentElement.lang = LANG === "vi" ? "vi" : "zh-CN";
}
$("lang-btn").addEventListener("click", () => {
  LANG = LANG === "zh" ? "vi" : "zh";
  localStorage.setItem("canteen_lang", LANG);
  applyLang();
  renderGrid();                      // 表头随语言刷新
});

function esc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function todayStr() {
  const d = new Date();
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

// 是否星期天（date 为 YYYY-MM-DD，按本地时区解析，避免 UTC 偏移串日）
function isSunday(dateStr) {
  const p = String(dateStr || "").split("-");
  if (p.length !== 3) return false;
  return new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2])).getDay() === 0;
}

async function api(method, path, body) {
  const opt = { method, headers: { "Content-Type": "application/json" } };
  if (state.token) opt.headers["Authorization"] = "Bearer " + state.token;
  if (body) opt.body = JSON.stringify(body);
  const r = await fetch(BASE + path, opt);
  const data = await r.json().catch(() => ({}));
  if (r.status === 401) {
    if (path === "/api/login") throw new Error(data.detail || t("err_login"));
    logout();
    throw new Error(t("err_token"));
  }
  if (!r.ok) throw new Error(data.detail || ("Error " + r.status));
  return data;
}

function show(el, on) { el.classList.toggle("hidden", !on); }
function setMsg(id, text, ok) {
  const m = $(id); m.textContent = text || "";
  m.className = "msg " + (ok ? "ok" : "err");
}

// ---------- 登录 ----------
async function doLogin() {
  setMsg("login-msg", "");
  const username = $("username").value.trim();
  const password = $("password").value;
  if (!username || !password) return setMsg("login-msg", t("err_fill"), false);
  try {
    const data = await api("POST", "/api/login", { username, password });
    state.token = data.access_token;
    state.user = data.user;
    localStorage.setItem("token", state.token);
    await enterApp();
  } catch (e) { setMsg("login-msg", e.message, false); }
}

function logout() {
  state.token = null; state.user = null;
  localStorage.removeItem("token");
  show($("login-page"), true); show($("app-page"), false);
}

async function enterApp() {
  try { const me = await api("GET", "/api/me"); state.user = me; }
  catch (e) { return; }
  show($("login-page"), false); show($("app-page"), true);
  $("who").textContent = (state.user.name || state.user.emp_no) + " · " + (state.user.dept_name || "");
  // 设定页签：管理员或统计名单内人员可见；食堂页签仅管理员
  show(document.querySelector(".settings-only"), state.user.is_admin || state.user.can_stat);
  show($("tab-canteen-btn"), state.user.is_admin);
  show($("tab-mealtimes-btn"), state.user.is_admin);
  applyLang();
  await loadMealTimes();              // 拉取开餐时间（用于禁用过期/过去餐次）
  switchView("order");
  initOrder();
}

// ---------- 导航 ----------
function switchView(v) {
  document.querySelectorAll(".nav-btn[data-view]").forEach(b => b.classList.toggle("active", b.dataset.view === v));
  ["order", "daily", "monthly", "detail", "settings"].forEach(n => show($("view-" + n), n === v));
  if (v === "order") initOrder();
  if (v === "daily") initDaily();
  if (v === "monthly") initMonthly();
  if (v === "detail") initDetail();
  if (v === "settings") loadSettings();
}

// ---------- 点餐 ----------
// 5 个基础餐别（中国/越南餐厅由后端按员工国籍写入对应 *_cn/*_vn）
const MEAL_KEYS = ["breakfast", "lunch", "wucan", "dinner", "midnight"];
// 班次分组（早餐共用 | 白班:中餐+午餐 | 夜班:晚餐+夜餐），用于点餐表头与报表
const SHIFT_GROUPS = [
  { nameKey: "meal_breakfast", bg: "#fff2cc", meals: ["breakfast"] },
  { nameKey: "rep_shift_day", bg: "#fce4d6", meals: ["lunch", "wucan"] },
  { nameKey: "rep_shift_night", bg: "#ddebf7", meals: ["dinner", "midnight"] },
];
// 每个餐别所属班次：早餐=共用(不限) | 中餐/午餐=白班 | 晚餐/夜餐=夜班
const SHIFT_OF = { breakfast: "common", lunch: "day", wucan: "day", dinner: "night", midnight: "night" };
// 班次互斥：除早餐外，白班(中餐+午餐)与夜班(晚餐+夜餐)不可同选。
// winShift 为刚勾选的一侧，另一侧已勾选的餐自动取消（该员工只能归属一个班次）。
function enforceShift(key, winShift) {
  if (winShift === "common") return false;
  const f = getFlags(key);
  const clear = winShift === "day" ? ["dinner", "midnight"] : ["lunch", "wucan"];
  let changed = false;
  clear.forEach(k => { if (f[k] === true) { f[k] = false; changed = true; } });
  return changed;
}
// 保存兜底：若既有数据（含历史已存）同时勾选了白班与夜班，保留勾选更多的一侧（平局保留白班），清除另一侧
function resolveShiftConflict(f) {
  const day = ["lunch", "wucan"], night = ["dinner", "midnight"];
  const dc = day.filter(k => f[k] === true).length;
  const nc = night.filter(k => f[k] === true).length;
  if (dc > 0 && nc > 0) (dc >= nc ? night : day).forEach(k => f[k] = false);
}
// 将网格内所有勾选框同步回 draft 状态（互斥自动取消后刷新界面）
function syncAllCheckboxes() {
  document.querySelectorAll('#order-grid input[type="checkbox"]').forEach(el => {
    const key = el.dataset.emp + "|" + el.dataset.date;
    const k = el.dataset.k;
    if (el.disabled) { el.checked = false; return; }   // 过期/过去餐次恒显示未勾
    const v = draft[key] ? draft[key][k] : null;
    el.checked = (v === true);
  });
}

// ---------- 开餐时间 / 2 小时提前量 ----------
// 开餐时间由管理员在「开餐时间」设定页维护；前端据此禁用过期/过去餐次。
let mealTimes = { breakfast: "07:00", lunch: "11:30", wucan: "17:00", dinner: "19:00", midnight: "23:30" };
let savedFlags = {};   // "emp|date" -> 载入时已从 DB 存在的餐别勾选（过期餐次保留历史用）
async function loadMealTimes() {
  try { const d = await api("GET", "/api/meal-times"); if (d && d.meal_times) mealTimes = d.meal_times; } catch (e) {}
}
function mealName(k) { return t("meal_" + k); }
// 是否不早于今天（过去日期不可点）
function dateOrderable(dateStr) { return !!dateStr && dateStr >= todayStr(); }
// 该餐次是否可点：过去日期不可；未来日期全部可点；今天须 开餐时间 >= 当前时间 + 2 小时
function mealOrderable(dateStr, k) {
  if (!dateOrderable(dateStr)) return false;
  const today = todayStr();
  if (dateStr > today) return true;
  const mt = mealTimes[k];
  if (!mt) return true;
  const p = String(mt).split(":");
  const hh = parseInt(p[0], 10), mm = parseInt(p[1], 10);
  if (isNaN(hh) || isNaN(mm)) return true;
  const now = new Date();
  const mealDt = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hh, mm, 0);
  return mealDt >= new Date(now.getTime() + 2 * 3600 * 1000);
}
let canteens = [];
let persons = [];             // [{emp_no, name, type: self|search|guest}] 名单上的人（去重）
let rows = [];                // [{emp_no, name, date, type}] 一人一天一行
let draft = {};               // "emp|date" -> 8 勾选位
let existingKeys = new Set(); // "emp|date"（当前食堂+日期范围内已有登记）
let orderMode = "self";       // self=个人点餐 | dept=按部门点

// 勾选三态：null=未表态（尚未登记的空白格）| true=Y 打勾 | false=N 已明确取消
// 按部门点餐时勾选一格，只把同列 null 自动置 Y；N 永不被自动覆盖。
function emptyFlags() {
  const o = {};
  MEAL_KEYS.forEach(k => o[k] = null);
  return o;
}
function getFlags(key) {
  if (!draft[key]) draft[key] = emptyFlags();
  return draft[key];
}
// 批量勾选已移除：单格勾选只影响本人；整部门批量改由餐别标题「全选」按钮显式触发。

function addPerson(p) {
  if (persons.some(x => x.emp_no === p.emp_no)) return false;
  persons.push(p);
  return true;
}

function activeDates() {
  return orderMode === "dept" ? [$("date-from").value].filter(Boolean) : rangeDates();
}

function rebuildRows() {
  const dates = activeDates();
  const out = [];
  persons.forEach(p => dates.forEach(dt =>
    out.push({ emp_no: p.emp_no, name: p.name, date: dt, type: p.type })));
  rows = out;
}

function rangeDates() {
  const from = $("date-from").value, to = $("date-to").value || from;
  if (!from) return [];
  const out = [];
  const d = new Date(from + "T00:00:00");
  const end = new Date(to + "T00:00:00");
  if (end < d) return [from];
  while (d <= end && out.length < 31) {
    out.push(d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"));
    d.setDate(d.getDate() + 1);
  }
  return out;
}

async function initOrder() {
  $("date-from").value = todayStr();
  $("date-to").value = todayStr();
  $("emp-kw").value = "";
  $("guest-mode").checked = false;
  show($("guest-box"), false);
  $("mode-self").checked = true;
  $("mode-dept").checked = false;
  $("nat-cn").checked = true;
  $("nat-vn").checked = false;
  state.orderNat = "cn";
  orderMode = "self";
  show($("date-to-label"), true);
  $("dept-sel").value = "";
  persons = [{ emp_no: state.user.emp_no, name: (state.user.name || "") + t("me_suffix"), type: "self" }];
  await loadCanteenOptions();
  await loadDepts();
  await refreshOrders();
}

async function loadCanteenOptions() {
  try { canteens = (await api("GET", "/api/canteens")).list; } catch (e) { canteens = []; }
  const sel = $("canteen-sel");
  sel.innerHTML = "";
  if (!canteens.length) {
    sel.innerHTML = '<option value="">' + esc(t("no_canteen_opt")) + "</option>";
    return;
  }
  canteens.forEach(c => {
    const o = document.createElement("option");
    o.value = c.code; o.textContent = c.name + "（" + c.code + "）";
    sel.appendChild(o);
  });
}

async function loadDepts() {
  const sel = $("dept-sel");
  sel.innerHTML = '<option value="">' + esc(t("dept_placeholder")) + "</option>";
  const canteen = $("canteen-sel").value || "";
  try {
    // 统计授权名单内人员：返回当前食堂代号起头的全部部门（含各下级部门）
    const d = await api("GET", "/api/depts?canteen=" + encodeURIComponent(canteen));
    (d.list || []).forEach(x => {
      const o = document.createElement("option");
      o.value = x.deptno; o.textContent = x.name + "（" + x.deptno + "）";
      sel.appendChild(o);
    });
  } catch (e) {}
}

// 核心刷新：重建行（人×日期）→ 拉取已有登记预填 → 部门模式把已登记排前面 → 渲染
async function refreshOrders() {
  rebuildRows();
  await loadDraft();
  if (orderMode === "dept") {
    rows.sort((a, b) =>
      (existingKeys.has(b.emp_no + "|" + b.date) ? 1 : 0) -
      (existingKeys.has(a.emp_no + "|" + a.date) ? 1 : 0));
  }
  renderGrid();
}

async function loadDraft() {
  draft = {}; existingKeys = new Set(); savedFlags = {};
  const from = $("date-from").value, to = orderMode === "dept" ? from : ($("date-to").value || from);
  const canteen = $("canteen-sel").value;
  if (!from) return;
  try {
    const d = await api("GET", `/api/orders?date_from=${from}&date_to=${to}&canteen=${encodeURIComponent(canteen || "")}`);
    (d.orders || []).forEach(o => {
      const key = o.emp_no + "|" + o.meal_date;
      const f = emptyFlags();
      MEAL_KEYS.forEach(k => f[k] = !!(o[k + "_cn"] || o[k + "_vn"]));
      draft[key] = f;
      savedFlags[key] = Object.assign({}, f);   // 记录已存在状态，过期餐次保留历史
      existingKeys.add(key);
      // 自己登记过的客人行自动恢复显示
      const mePre = state.user.emp_no + "_";
      if (o.emp_no.startsWith(mePre) && !persons.some(p => p.emp_no === o.emp_no)) {
        addPerson({ emp_no: o.emp_no, name: o.emp_name || o.emp_no, type: "guest" });
        rebuildRows();
      }
    });
  } catch (e) { setMsg("order-msg", e.message, false); }
}

function renderGrid() {
  // 班次布局：早餐(共用) | 白班(中餐,午餐) | 夜班(晚餐,夜餐)，单一组 5 餐别
  const mealLabels = { breakfast: t("meal_breakfast"), lunch: t("meal_lunch"),
                       wucan: t("meal_wucan"), dinner: t("meal_dinner"), midnight: t("meal_midnight") };
  let html = '<table class="grid order-grid"><thead>';
  html += `<tr class="h1"><th rowspan="2">${t("h_date")}</th><th rowspan="2">${t("h_emp_no")}</th><th rowspan="2">${t("h_name")}</th>`;
  SHIFT_GROUPS.forEach(g => { html += `<th colspan="${g.meals.length}" style="background:${g.bg};color:#333">${t(g.nameKey)}</th>`; });
  html += "</tr>";
  html += '<tr class="h2">';
  SHIFT_GROUPS.forEach(g => { g.meals.forEach(m => html += `<th style="background:${g.bg};color:#333">${mealLabels[m]}<br><button type="button" class="selall" data-k="${m}" title="${t("sel_all_hint")}">${t("sel_all")}</button></th>`); });
  html += "</tr></thead><tbody>";
  rows.forEach(r => {
    const key = r.emp_no + "|" + r.date;
    const trCls = [];
    if (r.type === "guest") trCls.push("guest-row");
    if (isSunday(r.date)) trCls.push("sun-row");   // 星期天整行浅黄
    const cls = trCls.length ? ` class="${trCls.join(" ")}"` : "";
    const f = draft[key] || emptyFlags();
    const dateCls = existingKeys.has(key) ? "" : ' class="date-new"';
    html += `<tr${cls}><td${dateCls}>${esc(r.date.replace(/-/g, "/"))}</td>` +
            `<td class="nm">${esc(r.emp_no)}</td><td class="nm">${esc(r.name)}</td>`;
    MEAL_KEYS.forEach(k => {
      const ok = mealOrderable(r.date, k);
      const checked = ok && f[k] === true;
      html += `<td class="chk"><input type="checkbox" data-emp="${esc(r.emp_no)}" data-date="${r.date}" data-k="${k}"${checked ? " checked" : ""}${ok ? "" : " disabled"} /></td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table>";
  $("order-grid").innerHTML = html;
}

$("order-grid").addEventListener("change", (e) => {
  const box = e.target;
  if (box.type !== "checkbox" || box.disabled) return;
  const emp = box.dataset.emp, date = box.dataset.date, k = box.dataset.k;
  const key = emp + "|" + date;
  getFlags(key)[k] = box.checked;   // 勾选=Y / 取消=N（仅影响本人，不再整列/整部门级联）
  // 班次互斥（仅本人）：除早餐外，白班与夜班不可同选；勾选一侧自动取消该员工另一侧的已选餐
  const sf = SHIFT_OF[k];
  if (box.checked && sf !== "common" && enforceShift(key, sf)) {
    setMsg("order-msg", t("shift_conflict"), true);
  }
  syncAllCheckboxes();
});

// 餐别标题上的「全选」按钮：点击才将该餐批量勾给本部门/名单全部人员（按班次互斥自动取消对班）
$("order-grid").addEventListener("click", (e) => {
  const btn = e.target.closest(".selall");
  if (!btn) return;
  applySelectAll(btn.dataset.k);
});

function applySelectAll(k) {
  const sf = SHIFT_OF[k];
  const seen = new Set();
  rows.forEach(r => {
    const rk = r.emp_no + "|" + r.date;
    if (seen.has(rk)) return;
    seen.add(rk);
    if (!mealOrderable(r.date, k)) return;   // 过期/过去餐次不可点，跳过
    const f = getFlags(rk);
    f[k] = true;
    if (sf !== "common") enforceShift(rk, sf);   // 班次互斥：自动取消该员工另一班次
  });
  syncAllCheckboxes();
  setMsg("order-msg", t("sel_all_done", { meal: mealName(k) }), true);
}

// 模式切换：个人点餐 / 按部门点 互斥
// 选了部门就自动切到「按部门点」，并清掉其他勾选（个人点餐 / 客户用餐登记）
async function switchToDeptMode() {
  if (orderMode === "dept") return;
  $("mode-dept").checked = true;
  $("mode-self").checked = false;
  $("guest-mode").checked = false;
  show($("guest-box"), false);
  orderMode = "dept";
  show($("date-to-label"), false);   // 按部门点一次只处理一天
  $("date-to").value = $("date-from").value;
}
$("mode-self").addEventListener("change", async (e) => {
  if (!e.target.checked) { e.target.checked = true; return; }  // 个人点餐不可取消，只能切到部门
  $("mode-dept").checked = false;
  orderMode = "self";
  show($("date-to-label"), true);
  $("dept-sel").value = "";
  persons = persons.filter(p => p.type !== "dept");
  if (!persons.some(p => p.type === "self")) {
    persons.unshift({ emp_no: state.user.emp_no, name: (state.user.name || "") + t("me_suffix"), type: "self" });
  }
  await refreshOrders();
});
$("mode-dept").addEventListener("change", async (e) => {
  if (!e.target.checked) { e.target.checked = true; return; }  // 部门模式不可取消，只能切回个人
  await switchToDeptMode();
  if ($("dept-sel").value) await loadDeptRows($("dept-sel").value);
  else { persons = []; rows = []; renderGrid(); }
});

// 中国/越南员工点餐：决定部门名单范围（按工号点餐不受限）；切换即按当前模式重载名单
function onNatChange() {
  state.orderNat = $("nat-vn").checked ? "vn" : "cn";
  if (orderMode === "dept" && $("dept-sel").value) loadDeptRows($("dept-sel").value);
}
$("nat-cn").addEventListener("change", onNatChange);
$("nat-vn").addEventListener("change", onNatChange);

// 按工号搜索（回车或按钮）：加入名单并载入其时段内记录
async function doEmpSearch() {
  const kw = $("emp-kw").value.trim();
  if (!kw) return setMsg("order-msg", t("err_empkw"), false);
  try {
    const d = await api("GET", "/api/emp/search?keyword=" + encodeURIComponent(kw));
    if (!d.list.length) return setMsg("order-msg", t("err_notfound_kw", { kw }), false);
    let added = 0;
    d.list.forEach(p => {
      if (addPerson({ emp_no: p.emp_no, name: p.name + "（" + (p.dept_name || "") + "）", type: "search" })) added++;
    });
    setMsg("order-msg", added ? t("msg_added", { n: added }) : t("msg_already"), true);
    await refreshOrders();
  } catch (e) { setMsg("order-msg", e.message, false); }
}
$("emp-search").addEventListener("click", doEmpSearch);
$("emp-kw").addEventListener("keydown", (e) => { if (e.key === "Enter") doEmpSearch(); });

// 按部门载入（本部门及下属部门，单日）：先列已有登记，再补未登记的人
// 统计授权名单内人员：可选当前食堂代号起头的任意部门
async function loadDeptRows(deptno) {
  if (!deptno) { persons = []; return refreshOrders(); }
  try {
    const canteen = $("canteen-sel").value || "";
    const d = await api("GET", "/api/dept/employees?deptno=" + encodeURIComponent(deptno) +
      "&canteen=" + encodeURIComponent(canteen) + "&nat=" + encodeURIComponent(state.orderNat));
    persons = (d.list || []).map(p => ({
      emp_no: p.emp_no,
      name: p.emp_no === state.user.emp_no ? (p.name || "") + t("me_suffix") : p.name + "（" + (p.dept_name || "") + "）",
      type: "dept",
    }));
    await refreshOrders();
    const n = persons.length;
    setMsg("order-msg", d.truncated
      ? t("msg_dept_truncated", { n, l: d.limit })
      : t("msg_dept_loaded", { n }), !d.truncated);
  } catch (e) { setMsg("order-msg", e.message, false); }
}
$("dept-sel").addEventListener("change", async (e) => {
  const deptno = e.target.value;
  if (deptno) await switchToDeptMode();   // 选部门但未勾「按部门点」→ 自动切过去
  await loadDeptRows(deptno);
});

// 客户用餐登记
$("guest-mode").addEventListener("change", (e) => show($("guest-box"), e.target.checked));
$("guest-add").addEventListener("click", async () => {
  const n = parseInt($("guest-count").value, 10);
  if (!n || n < 1 || n > 99) return setMsg("order-msg", t("err_guest_count"), false);
  const base = state.user.emp_no;
  const myName = state.user.name || base;
  const re = new RegExp("^" + base.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&") + "_(\\d+)$");
  let seq = 0;
  persons.forEach(p => { const m = p.emp_no.match(re); if (m) seq = Math.max(seq, parseInt(m[1], 10)); });
  for (let i = 0; i < n; i++) {
    seq++;
    addPerson({ emp_no: base + "_" + seq, name: myName + t("guest_suffix", { n: seq }), type: "guest" });
  }
  await refreshOrders();
});

// 日期范围搜索按钮（第一个搜索）：列出该时段登记情况，未点的自动补行
$("range-search").addEventListener("click", async () => {
  if (orderMode === "dept" && $("dept-sel").value) return loadDeptRows($("dept-sel").value);
  await refreshOrders();
  const dates = activeDates();
  setMsg("order-msg", t("msg_range", { a: dates[0] || "", b: dates.slice(-1)[0] || "" }), true);
});

// 日期/食堂变化 → 重新载入（食堂变了，可点部门范围也随之变化）
["date-from", "date-to"].forEach(id =>
  $(id).addEventListener("change", async () => {
    if (orderMode === "dept") $("date-to").value = $("date-from").value;
    if (orderMode === "dept" && $("dept-sel").value) return loadDeptRows($("dept-sel").value);
    await refreshOrders();
  }));
$("canteen-sel").addEventListener("change", async () => {
  // 食堂决定可点范围：重置部门选择并重载下拉
  $("dept-sel").value = "";
  await loadDepts();
  if (orderMode === "dept") {
    persons = []; rows = []; renderGrid();
    setMsg("order-msg", t("msg_canteen_switched"), true);
  }
  await refreshOrders();
});

// 保存（防重复提交）：一行 = 一人一天，逐行携带日期
let saving = false;
$("save-order").addEventListener("click", async () => {
  if (saving) return;
  const canteen = $("canteen-sel").value;
  if (!canteen) return setMsg("order-msg", t("err_need_canteen"), false);
  const dates = activeDates();
  if (!dates.length) return setMsg("order-msg", t("err_need_date"), false);
  const items = [];
  const seen = new Set();
  rows.forEach(r => {
    const key = r.emp_no + "|" + r.date;
    if (seen.has(key)) return;
    seen.add(key);
    const f = draft[key] || emptyFlags();
    resolveShiftConflict(f);                 // 兜底：白班/夜班互斥，避免历史数据同时勾选两侧
    const flags = {};                        // 三态归一化为 0/1 再提交（null 未表态 = 不点）
    MEAL_KEYS.forEach(k => {
      let v = f[k] === true;
      // 过期/不足 2 小时的餐次：新建不允许；已保存的历史记录保留（不发送删除）
      if (v && !mealOrderable(r.date, k) && !(savedFlags[key] && savedFlags[key][k] === true)) v = false;
      flags[k] = v;
    });
    const any = MEAL_KEYS.some(k => flags[k]);
    const existed = existingKeys.has(key);
    if (any || existed) items.push(Object.assign({ emp_no: r.emp_no, meal_date: r.date }, flags));
  });
  if (!items.length) return setMsg("order-msg", t("err_need_meal"), false);
  saving = true;
  $("save-order").disabled = true;
  $("save-order").textContent = t("btn_saving");
  try {
    const d = await api("POST", "/api/orders/batch", { canteen_code: canteen, dates, items, order_nat: state.orderNat });
    setMsg("order-msg", d.msg || t("msg_saved"), true);
    await refreshOrders();
  } catch (e) { setMsg("order-msg", e.message, false); }
  saving = false;
  $("save-order").disabled = false;
  $("save-order").textContent = t("btn_save_all");
});

// ---------- 报表渲染 ----------
// 报表布局：中国 / 越南 分为左右两大块，每块 5 餐（早餐 | 白班中餐 | 白班午餐 | 夜班晚餐 | 夜班夜宵）
const REPORT_BLOCKS = [
  { nat: "cn", nameKey: "rep_nat_cn", bg: "#fce4d6" },
  { nat: "vn", nameKey: "rep_nat_vn", bg: "#ddebf7" },
];
const REPORT_MEALS = ["breakfast", "lunch", "wucan", "dinner", "midnight"];
// 餐别列标题：早餐共用，中/午餐带「白班」前缀，晚/夜餐带「夜班」前缀
function reportMealLabel(k) {
  if (k === "breakfast") return t("meal_breakfast");
  if (k === "lunch") return t("rep_shift_day") + t("meal_lunch");
  if (k === "wucan") return t("rep_shift_day") + t("meal_wucan");
  if (k === "dinner") return t("rep_shift_night") + t("meal_dinner");
  if (k === "midnight") return t("rep_shift_night") + t("meal_midnight");
  return t("meal_" + k);
}
async function fillCanteenFilter(selId) {
  const sel = $(selId);
  sel.innerHTML = '<option value=""></option>';
  const all = document.createElement("option");
  all.value = ""; all.textContent = t("canteen_all");
  sel.appendChild(all);
  canteens.forEach(c => {
    const o = document.createElement("option");
    o.value = c.code; o.textContent = c.name;
    sel.appendChild(o);
  });
}

function renderReport(containerId, data) {
  const el = $(containerId);
  if (!data.departments.length) { el.innerHTML = '<p class="muted">' + esc(t("report_none")) + "</p>"; return; }
  // 表头：序号 | 部门 | 负责人 | 中国餐厅(5餐) | 越南餐厅(5餐) | 小计
  let head = `<thead><tr class="h1">`
    + `<th rowspan="2">${t("r_no")}</th><th rowspan="2">${t("r_dept")}</th><th rowspan="2">${t("r_manager")}</th>`;
  REPORT_BLOCKS.forEach(b => head += `<th colspan="${REPORT_MEALS.length}" class="${b.nat === "vn" ? "blk-sep" : ""}" style="background:${b.bg};color:#333">${t(b.nameKey)}</th>`);
  head += `<th rowspan="2">${t("r_subtotal")}</th></tr>`;
  head += `<tr class="h2">`;
  REPORT_BLOCKS.forEach(b => REPORT_MEALS.forEach((m, mi) => {
    const sep = (b.nat === "vn" && mi === 0) ? ' class="blk-sep"' : "";
    head += `<th${sep} style="background:${b.bg};color:#333">${reportMealLabel(m)}</th>`;
  }));
  head += `</tr></thead>`;
  let body = "<tbody>";
  data.departments.forEach((d, i) => {
    let sub = 0;
    body += `<tr><td>${i + 1}</td><td class="dept">${esc(d.dept_name)}</td><td>${esc(d.manager || "")}</td>`;
    REPORT_BLOCKS.forEach(b => REPORT_MEALS.forEach((m, mi) => {
      const v = d[m + "_" + b.nat] || 0; sub += v;
      const sep = (b.nat === "vn" && mi === 0) ? ' class="blk-sep"' : "";
      body += `<td${sep}>${v}</td>`;
    }));
    body += `<td class="sub">${sub}</td></tr>`;
  });
  body += "</tbody>";
  const total = data.total;
  let tt = 0;
  let foot = `<tfoot><tr class="total"><td></td><td class="dept">${t("r_total")}</td><td></td>`;
  REPORT_BLOCKS.forEach(b => REPORT_MEALS.forEach(m => { const v = total[m + "_" + b.nat] || 0; tt += v; foot += `<td>${v}</td>`; }));
  foot += `<td>${tt}</td></tr></tfoot>`;
  el.innerHTML = `<table class="report-table">${head}${body}${foot}</table>`;
  el.dataset.json = JSON.stringify(data);
}

function buildCsv(data) {
  const header = [t("r_no"), t("r_dept"), t("r_manager")];
  REPORT_BLOCKS.forEach(b => REPORT_MEALS.forEach(m => header.push(t(b.nameKey) + "-" + reportMealLabel(m))));
  header.push(t("r_subtotal"));
  const rows2 = [];
  data.departments.forEach((d, i) => {
    let sub = 0;
    const r = [i + 1, d.dept_name, d.manager || ""];
    REPORT_BLOCKS.forEach(b => REPORT_MEALS.forEach(m => { const v = d[m + "_" + b.nat] || 0; sub += v; r.push(v); }));
    r.push(sub);
    rows2.push(r);
  });
  const total = data.total;
  let tt = 0;
  const totalRow = ["", t("csv_total"), ""];
  REPORT_BLOCKS.forEach(b => REPORT_MEALS.forEach(m => { const v = total[m + "_" + b.nat] || 0; tt += v; totalRow.push(v); }));
  totalRow.push(tt);
  rows2.push(totalRow);
  return [header, ...rows2].map(r => r.map(c => `"${c}"`).join(",")).join("\r\n");
}
function exportCsv(containerId, filename) {
  const el = $(containerId);
  if (!el.dataset.json) return;
  const csv = "﻿" + buildCsv(JSON.parse(el.dataset.json));
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = filename; a.click();
}

// 日报
async function initDaily() {
  $("daily-date").value = todayStr();
  await fillCanteenFilter("daily-canteen");
}
$("daily-query").addEventListener("click", async () => {
  const date = $("daily-date").value;
  if (!date) return;
  try {
    const d = await api("GET", `/api/report/daily?date=${date}&canteen=${encodeURIComponent($("daily-canteen").value || "")}`);
    renderReport("daily-table", d);
  } catch (e) { $("daily-table").innerHTML = `<p class="msg err">${esc(e.message)}</p>`; }
});
$("daily-export").addEventListener("click", () => exportCsv("daily-table", "食堂日报_" + $("daily-date").value + ".csv"));

// 月报
async function initMonthly() {
  const d = new Date();
  $("rep-year").value = d.getFullYear(); $("rep-month").value = d.getMonth() + 1;
  await fillCanteenFilter("monthly-canteen");
}
$("monthly-query").addEventListener("click", async () => {
  const y = $("rep-year").value, m = $("rep-month").value;
  if (!y || !m) return;
  try {
    const d = await api("GET", `/api/report/monthly?year=${y}&month=${m}&canteen=${encodeURIComponent($("monthly-canteen").value || "")}`);
    renderReport("monthly-table", d);
  } catch (e) { $("monthly-table").innerHTML = `<p class="msg err">${esc(e.message)}</p>`; }
});
$("monthly-export").addEventListener("click", () => exportCsv("monthly-table", `食堂月报_${$("rep-year").value}-${$("rep-month").value}.csv`));

// 明细报表（按日期范围，单日/多日）
async function initDetail() {
  const d = todayStr();
  $("detail-start").value = d; $("detail-end").value = d;
  $("detail-hint").textContent = t("detail_hint");
  await fillCanteenFilter("detail-canteen");
}
// 带鉴权地取原始文本（用于 CSV 下载，避免无 token 的 <a> 直链）
async function apiText(path) {
  const opt = { method: "GET", headers: {} };
  if (state.token) opt.headers["Authorization"] = "Bearer " + state.token;
  const r = await fetch(BASE + path, opt);
  if (r.status === 401) { logout(); throw new Error(t("err_token")); }
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || ("Error " + r.status)); }
  return r.text();
}
function renderDetail(data) {
  const el = $("detail-table");
  if (!data.rows.length) { el.innerHTML = '<p class="muted">' + esc(t("report_none")) + "</p>"; el.dataset.json = ""; return; }
  const cols = data.columns;
  let head = "<thead><tr>";
  cols.forEach(c => head += `<th>${esc(c.label)}</th>`);
  head += "</tr></thead>";
  let body = "<tbody>";
  data.rows.forEach(r => {
    body += "<tr>";
    cols.forEach(c => body += `<td>${esc(r[c.key])}</td>`);
    body += "</tr>";
  });
  body += "</tbody>";
  const tt = data.total, grand = data.grand;
  let foot = `<tfoot><tr class="total">`;
  cols.forEach((c, i) => {
    let v = (tt[c.key] !== undefined) ? tt[c.key] : "";
    if (i === 2) v = t("csv_total");
    if (c.key === "created_at") v = t("detail_total_meals") + " " + grand;
    foot += `<td>${esc(v)}</td>`;
  });
  foot += "</tr></tfoot>";
  el.innerHTML = `<table class="report-table detail-table">${head}${body}${foot}</table>`;
  el.dataset.json = JSON.stringify(data);
}
$("detail-query").addEventListener("click", async () => {
  const s = $("detail-start").value, e = $("detail-end").value;
  if (!s || !e) return;
  try {
    const d = await api("GET", `/api/report/detail?start=${s}&end=${e}&canteen=${encodeURIComponent($("detail-canteen").value || "")}`);
    renderDetail(d);
    $("detail-hint").textContent = t("detail_hint") + " " + t("detail_rows") + "：" + d.count;
  } catch (err) { $("detail-table").innerHTML = `<p class="msg err">${esc(err.message)}</p>`; }
});
$("detail-export").addEventListener("click", async () => {
  const s = $("detail-start").value, e = $("detail-end").value;
  if (!s || !e) return;
  try {
    const csv = await apiText(`/api/report/detail?start=${s}&end=${e}&canteen=${encodeURIComponent($("detail-canteen").value || "")}&format=csv`);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `食堂明细_${s}_${e}.csv`;
    a.click();
  } catch (err) { $("detail-table").innerHTML = `<p class="msg err">${esc(err.message)}</p>`; }
});

// ---------- 设定页 ----------
function loadSettings() {
  loadAuth();
  if (state.user.is_admin) { loadCanteenAdmin(); loadMealTimesSettings(); }
}

function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
  show($("tab-auth"), tab === "auth");
  show($("tab-canteen"), tab === "canteen");
  show($("tab-mealtimes"), tab === "mealtimes");
}
document.querySelectorAll(".tab-btn").forEach(b => b.addEventListener("click", () => switchTab(b.dataset.tab)));

// 页签一：统计授权
async function loadAuth() {
  try {
    const d = await api("GET", "/api/admin/stat-auth");
    const tb = $("auth-table").querySelector("tbody");
    tb.innerHTML = "";
    d.list.forEach(a => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${esc(a.emp_no)}</td><td>${esc(a.emp_name || "")}</td><td>${esc(a.granted_by || "")}</td>
        <td><button data-emp="${esc(a.emp_no)}" class="danger">${esc(t("btn_remove_auth"))}</button></td>`;
      tb.appendChild(tr);
    });
    tb.querySelectorAll("button[data-emp]").forEach(b =>
      b.addEventListener("click", () => removeAuth(b.dataset.emp)));
  } catch (e) { setMsg("order-msg", e.message, false); }
}
$("auth-kw").addEventListener("input", async (e) => {
  const kw = e.target.value;
  try {
    const d = await api("GET", "/api/admin/employees/search?keyword=" + encodeURIComponent(kw));
    const sel = $("auth-sel"); sel.innerHTML = "";
    d.list.forEach(c => {
      const o = document.createElement("option");
      o.value = c.emp_no; o.textContent = c.emp_no + "  " + c.name + "  (" + (c.dept_name || "") + ")";
      sel.appendChild(o);
    });
  } catch (e) {}
});
$("auth-add").addEventListener("click", async () => {
  const o = $("auth-sel").selectedOptions[0];
  if (!o) return alert(t("alert_pick_emp"));
  try { await api("POST", "/api/admin/stat-auth", { emp_no: o.value }); loadAuth(); }
  catch (e) { alert(e.message); }
});
async function removeAuth(empNo) {
  if (!confirm(t("confirm_remove", { emp: empNo }))) return;
  try { await api("DELETE", "/api/admin/stat-auth/" + empNo); loadAuth(); }
  catch (e) { alert(e.message); }
}

// 页签二：点餐食堂
function canteenRowEl(c) {
  const div = document.createElement("div");
  div.className = "row canteen-row";
  const rulesVal = (c.rules && c.rules.length) ? JSON.stringify(c.rules) : "";
  div.innerHTML = `<input type="text" class="ct-code" placeholder="${esc(t("ph_ct_code"))}" style="width:140px" value="${esc(c.code)}" />
    <input type="text" class="ct-name" placeholder="${esc(t("ph_ct_name"))}" style="width:240px" value="${esc(c.name)}" />
    <input type="text" class="ct-rules" placeholder="${esc(t("ph_ct_rules"))}" style="width:420px" value="${esc(rulesVal)}" />
    <button class="danger ct-del">${esc(t("btn_delete"))}</button>`;
  div.querySelector(".ct-del").addEventListener("click", () => div.remove());
  return div;
}
async function loadCanteenAdmin() {
  try {
    const d = await api("GET", "/api/admin/canteens");
    const box = $("canteen-rows");
    box.innerHTML = "";
    (d.list.length ? d.list : [{ code: "", name: "" }]).forEach(c => box.appendChild(canteenRowEl(c)));
  } catch (e) { setMsg("canteen-msg", e.message, false); }
}

$("canteen-add-row").addEventListener("click", () => $("canteen-rows").appendChild(canteenRowEl({ code: "", name: "" })));
$("canteen-save").addEventListener("click", async () => {
  const list = [];
  document.querySelectorAll("#canteen-rows .canteen-row").forEach(row => {
    const code = row.querySelector(".ct-code").value.trim();
    const name = row.querySelector(".ct-name").value.trim();
    if (!code) return;
    const item = { code, name };
    const rulesRaw = row.querySelector(".ct-rules").value.trim();
    if (rulesRaw) {
      try {
        const rules = JSON.parse(rulesRaw);
        if (Array.isArray(rules)) item.rules = rules;
      } catch (e) {
        setMsg("canteen-msg", "规则JSON 解析失败：" + e.message, false);
        throw e;
      }
    }
    list.push(item);
  });
  try {
    const d = await api("PUT", "/api/admin/canteens", { list });
    setMsg("canteen-msg", d.msg || t("msg_canteen_saved", { n: list.length }), true);
    await loadCanteenAdmin();
    await loadCanteenOptions();
  } catch (e) { /* 已在上方提示 */ }
});

// 页签三：开餐时间（管理员）
async function loadMealTimesSettings() {
  try {
    const d = await api("GET", "/api/meal-times");
    const times = (d && d.meal_times) || mealTimes;
    const box = $("meal-time-rows");
    box.innerHTML = "";
    MEAL_KEYS.forEach(k => {
      const row = document.createElement("div");
      row.className = "row";
      row.style.margin = "6px 0";
      row.innerHTML = `<label style="display:inline-flex;align-items:center;gap:8px;min-width:220px">`
        + `<span style="min-width:64px;text-align:right">${esc(mealName(k))}</span>`
        + `<input type="time" class="mt-time" data-k="${k}" value="${esc(times[k] || mealTimes[k])}" style="width:130px" /></label>`;
      box.appendChild(row);
    });
  } catch (e) { setMsg("meal-time-msg", e.message, false); }
}
$("meal-time-save").addEventListener("click", async () => {
  const times = {};
  document.querySelectorAll("#meal-time-rows .mt-time").forEach(inp => { times[inp.dataset.k] = inp.value; });
  try {
    const d = await api("PUT", "/api/admin/meal-times", { meal_times: times });
    if (d.meal_times) mealTimes = d.meal_times;
    setMsg("meal-time-msg", d.msg || t("msg_saved"), true);
  } catch (e) { setMsg("meal-time-msg", e.message, false); }
});

// ---------- 启动 ----------
$("login-btn").addEventListener("click", doLogin);
$("password").addEventListener("keydown", (e) => { if (e.key === "Enter") doLogin(); });
$("logout-btn").addEventListener("click", logout);
document.querySelectorAll(".nav-btn[data-view]").forEach(b => b.addEventListener("click", () => switchView(b.dataset.view)));

applyLang();
if (state.token) enterApp();
