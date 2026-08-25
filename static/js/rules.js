// ============================================================
// 规则管家页面逻辑：加载规则、渲染列表、拼装表单、提交保存
// 这是前端里最复杂的一个文件，我们一步一步来
// ============================================================

// 记录当前正在编辑的规则 id（null = 新建模式）
let editingId = null;

// ---------- 页面加载 ----------
// 页面加载完成后：加载规则列表 + 加载日志 + 加一行默认条件/动作
window.addEventListener("DOMContentLoaded", () => {
  loadRules();        // 加载规则列表
  loadLogs();         // 加载运行日志
  addConditionRow();  // 表单里默认有一行条件（不用用户手动加）
  addActionRow();     // 表单里默认有一行动作
  updateTriggerUI();  // 按触发器类型显示/隐藏对应参数框
});

// ---------- 规则列表 ----------

// 从后端取所有规则，渲染到页面上
function loadRules() {
  getRules()
    .then((data) => {
      // 拿到规则列表 data.rules
      const list = data.rules;
      // 列表容器
      const box = document.getElementById("ruleList");
      // 没有规则时显示提示
      if (!list.length) {
        box.innerHTML = '<div class="empty-tip">还没有规则，从下面新建第一条吧。</div>';
        return;
      }
      // 有规则：逐个拼成 HTML 放进容器
      // map() 把每条规则变成一段 HTML 字符串，join("") 把数组拼成一个字符串
      box.innerHTML = list
        .map((r) => {
          // 描述文字：触发器 + 动作的简短说明
          const triggerText = describeTrigger(r.trigger);
          const actionText = r.actions.map((a) => a.type).join("、");
          return `
            <div class="rule-item">
              <div>
                <div class="rule-name">
                  <!-- 启用时显示绿色小圆点 -->
                  <span class="dot-on" style="visibility:${r.enabled ? "visible" : "hidden"}"></span>
                  ${r.name}
                </div>
                <div class="rule-desc">${triggerText} → ${actionText}</div>
              </div>
              <div>
                <!-- 启用/暂停开关按钮 -->
                <button class="btn btn-ghost" onclick="toggleRuleItem('${r.id}')">
                  ${r.enabled ? "暂停" : "启用"}
                </button>
                <!-- 编辑按钮：把这条规则填进表单 -->
                <button class="btn btn-ghost" onclick="editRule('${r.id}')">编辑</button>
                <!-- 删除按钮 -->
                <button class="btn btn-danger" onclick="deleteRuleItem('${r.id}')">删除</button>
              </div>
            </div>`;
        })
        .join("");
    })
    .catch((err) => {
      // 请求失败：显示错误
      document.getElementById("ruleList").innerHTML =
        `<div class="empty-tip">加载失败：${err.message}</div>`;
    });
}

// 把触发器配置转成人能看懂的描述文字
function describeTrigger(t) {
  if (t.type === "schedule") {
    return `定时（${t.cron || "?"}）`;          // 定时触发器显示 cron 表达式
  }
  return `${t.watch_dir || "?"} 有新文件`;      // 文件触发器显示监控目录
}

// 启用/暂停
function toggleRuleItem(id) {
  toggleRule(id).then(() => loadRules());
}

// 删除（先确认，防止误删）
function deleteRuleItem(id) {
  if (!confirm("确定删除这条规则吗？")) return;  // 浏览器弹确认框
  deleteRule(id).then(() => loadRules());
}

// 编辑：把规则数据填进表单
function editRule(id) {
  getRules().then((data) => {
    // 找到要编辑的那条规则
    const rule = data.rules.find((r) => r.id === id);
    if (!rule) return;
    // 进入编辑模式
    editingId = id;
    // 标题改成“编辑规则”，显示取消按钮
    document.getElementById("formTitle").textContent = "编辑规则";
    document.getElementById("cancelBtn").style.display = "inline-block";
    // 填名字
    document.getElementById("ruleName").value = rule.name;
    // 填触发器类型
    document.getElementById("triggerType").value = rule.trigger.type;
    // 填监控目录 / cron
    document.getElementById("watchDir").value = rule.trigger.watch_dir || "";
    document.getElementById("cron").value = rule.trigger.cron || "";
    // 更新触发器界面显示
    updateTriggerUI();
    // 清空条件/动作列表，把规则里的填进去
    document.getElementById("condList").innerHTML = "";
    document.getElementById("actionList").innerHTML = "";
    // 每条条件生成一行表单
    rule.conditions.forEach((c) => addConditionRow(c));
    // 每个动作生成一行表单
    rule.actions.forEach((a) => addActionRow(a));
    // 滚动到表单位置，方便用户看到
    document.getElementById("formTitle").scrollIntoView({ behavior: "smooth" });
  });
}

// 取消编辑：清空表单回到新建模式
function resetForm() {
  editingId = null;
  document.getElementById("formTitle").textContent = "新建规则";
  document.getElementById("cancelBtn").style.display = "none";
  document.getElementById("ruleName").value = "";
  document.getElementById("watchDir").value = "";
  document.getElementById("cron").value = "";
  document.getElementById("condList").innerHTML = "";
  document.getElementById("actionList").innerHTML = "";
  document.getElementById("formError").textContent = "";
  addConditionRow();
  addActionRow();
}

// ---------- 触发器界面切换 ----------

// 触发器类型变化时：文件类显示“监控目录”框，定时类显示“cron”框
// 定时触发时还会禁用"文件类动作"选项（移动/复制/重命名没有具体文件可操作，
// 后端校验也会拦截，这里前端先挡一道，给用户即时反馈）
function updateTriggerUI() {
  const type = document.getElementById("triggerType").value;
  // 定时：显示 cron，隐藏监控目录
  document.getElementById("cronWrap").style.display = type === "schedule" ? "block" : "none";
  document.getElementById("watchDirWrap").style.display = type === "schedule" ? "none" : "block";

  // 处理每一行动作的类型下拉框
  document.querySelectorAll("#actionList .act-type").forEach((sel) => {
    // 遍历所有选项，定时触发时禁用文件类动作
    Array.from(sel.options).forEach((opt) => {
      opt.disabled = type === "schedule" && ["move", "copy", "rename"].includes(opt.value);
    });
    // 如果当前选中的是文件类动作，切回"通知"（定时规则唯一合理的动作）
    if (type === "schedule" && ["move", "copy", "rename"].includes(sel.value)) {
      sel.value = "notify";
      updateActionParams(sel);
    }
  });
}
// 给触发器下拉框绑定变化事件（页面加载时绑定一次）
document.getElementById("triggerType").addEventListener("change", updateTriggerUI);

// ---------- 条件行 ----------

// 添加一行条件表单；editData 是编辑模式下已有的条件值（可选）
function addConditionRow(editData = null) {
  // 容器
  const box = document.getElementById("condList");
  // 新建一个 div 放这一行
  const row = document.createElement("div");
  // 行的样式：横排 + 间距
  row.style.cssText = "display:flex; gap:8px; margin-bottom:8px; align-items:center;";
  // 字段下拉框（看文件的哪个属性）
  row.innerHTML = `
    <select style="width:110px;">
      <option value="name">文件名</option>
      <option value="ext">扩展名</option>
      <option value="size">大小(MB)</option>
      <option value="path">路径</option>
    </select>
    <select style="width:110px;" class="cond-op">
      <option value="contains">包含</option>
      <option value="equals">等于</option>
      <option value="in">属于</option>
      <option value="gt">大于</option>
      <option value="lt">小于</option>
    </select>
    <input placeholder="值（属于/大于等用逗号分隔）" class="cond-val">
    <button class="btn btn-danger" onclick="this.parentElement.remove()">✕</button>`;
  // 如果是编辑模式：把已有值填进这一行
  if (editData) {
    // 设置字段下拉框选中项
    row.querySelector("select").value = editData.field;
    // 设置操作符下拉框选中项
    row.querySelector(".cond-op").value = editData.op;
    // 设置值（列表用逗号拼成字符串显示）
    row.querySelector(".cond-val").value = Array.isArray(editData.value)
      ? editData.value.join(",")
      : String(editData.value);
  }
  // 把这一行加进容器
  box.appendChild(row);
}

// ---------- 动作行 ----------

// 添加一行动作表单；editData 是编辑模式下已有的动作值（可选）
function addActionRow(editData = null) {
  const box = document.getElementById("actionList");
  const row = document.createElement("div");
  row.style.cssText = "display:flex; gap:8px; margin-bottom:8px; align-items:center;";
  // 动作类型下拉框
  row.innerHTML = `
    <select style="width:120px;" class="act-type" onchange="updateActionParams(this)">
      <option value="move">移动文件</option>
      <option value="copy">复制文件</option>
      <option value="rename">重命名</option>
      <option value="notify">通知</option>
    </select>
    <!-- 参数输入框：移动/复制=目标目录，重命名=新文件名，通知=消息 -->
    <input placeholder="参数：目标目录 / 新文件名 / 消息" class="act-param">
    <button class="btn btn-danger" onclick="this.parentElement.remove()">✕</button>`;
  if (editData) {
    row.querySelector(".act-type").value = editData.type;
    // 根据动作类型把已有参数填进对应输入框
    const param = editData.dest_dir || editData.new_name || editData.message || "";
    row.querySelector(".act-param").value = param;
    updateActionParams(row.querySelector(".act-type"));
  }
  // 新加的行也要应用"定时触发禁用文件动作"的限制（如果当前是定时模式）
  box.appendChild(row);
  updateTriggerUI();
}

// 动作类型变化时：更新参数输入框的提示文字（方便用户知道填什么）
function updateActionParams(select) {
  // 找到这一行的参数输入框（select 的父元素里找 .act-param）
  const paramInput = select.parentElement.querySelector(".act-param");
  // 按类型换 placeholder（提示文字）
  const tips = {
    move: "目标目录，如 D:/视频",
    copy: "目标目录，如 D:/备份",
    rename: "新文件名，支持 {{file.name}}，如 备份_{{file.name}}",
    notify: "通知内容，如 {{file.name}} 已处理",
  };
  paramInput.placeholder = tips[select.value] || "";
}

// ---------- 保存规则 ----------

// 从表单收集所有输入，组装成规则对象提交给后端
function saveRule() {
  // 收集名字
  const name = document.getElementById("ruleName").value.trim();
  // 收集触发器
  const trigger = {
    type: document.getElementById("triggerType").value,
    watch_dir: document.getElementById("watchDir").value.trim(),
    cron: document.getElementById("cron").value.trim(),
  };
  // 收集条件：遍历每个条件行
  const conditions = [];
  document.querySelectorAll("#condList > div").forEach((row) => {
    // 取三个输入的值
    const field = row.querySelector("select").value;          // 字段
    const op = row.querySelector(".cond-op").value;           // 操作符
    const raw = row.querySelector(".cond-val").value.trim();  // 值（原始文本）
    if (!raw) return;  // 值空的行跳过
    // “属于”操作符：值按逗号拆成数组；其他操作符：保留字符串
    // 大小字段转数字（gt/lt 需要数字比较）
    let value = op === "in" ? raw.split(",").map((s) => s.trim()) : raw;
    if (field === "size") value = parseFloat(raw);
    // 加进条件数组
    conditions.push({ field, op, value });
  });
  // 收集动作：遍历每个动作行
  const actions = [];
  document.querySelectorAll("#actionList > div").forEach((row) => {
    // 取类型和参数
    const type = row.querySelector(".act-type").value;
    const param = row.querySelector(".act-param").value.trim();
    if (!param) return;  // 参数空的行跳过
    // 按类型把参数放对位置
    const action = { type };
    if (type === "move" || type === "copy") action.dest_dir = param;
    if (type === "rename") action.new_name = param;
    if (type === "notify") action.message = param;
    // 加进动作数组
    actions.push(action);
  });

  // 组装最终提交的数据
  const body = { name, trigger, conditions, actions, enabled: true };

  // 编辑模式调用更新接口，新建模式调用创建接口
  const promise = editingId ? updateRule(editingId, body) : createRule(body);
  promise
    .then(() => {
      // 成功：清空表单回到新建模式 + 刷新列表 + 提示
      resetForm();
      loadRules();
      alert("规则已保存！");  // 简单提示（正式产品会用更友好的提示框）
    })
    .catch((err) => {
      // 失败：把后端返回的错误显示在表单下方
      document.getElementById("formError").textContent = "保存失败：" + err.message;
    });
}

// ---------- 运行日志 ----------

// 加载最近日志显示在页面底部
function loadLogs() {
  getLogs().then((data) => {
    const box = document.getElementById("logList");
    // 没有日志时显示提示
    if (!data.logs.length) {
      box.innerHTML = '<div class="empty-tip">暂无日志。规则被触发后这里会出现记录。</div>';
      return;
    }
    // 把每条日志渲染成一行；级别决定颜色（success/error/info）
    box.innerHTML = data.logs
      .map((l) => {
        // 级别对应 CSS 类名（log-success/log-error/log-info），控制颜色
        const cls = l.level === "success" ? "log-success" : l.level === "error" ? "log-error" : "log-info";
        return `<div class="log-item">
          <span class="log-time">${l.time}</span>
          <span class="${cls}">[${l.rule}] ${l.message}</span>
        </div>`;
      })
      .join("");
  });
}

// 定时刷新日志：每 3 秒自动刷新一次（这样网页开着就能看到最新日志）
setInterval(loadLogs, 3000);
