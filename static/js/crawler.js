// ============================================================
// 网页采集器页面逻辑：加载任务、拼装表单、运行采集、显示结果
// 结构上和 rules.js 很像（都是：列表 + 表单 + 操作），可以对照着看
// ============================================================

// 记录当前正在编辑的任务 id（null = 新建模式）
let editingId = null;

// ---------- 页面加载 ----------
window.addEventListener("DOMContentLoaded", () => {
  loadTasks();      // 加载任务列表
  loadRuns();       // 加载采集历史
  addFieldRow();    // 表单默认有一行字段
});

// ---------- 任务列表 ----------

// 从后端取所有采集任务并渲染
function loadTasks() {
  getCrawlTasks()
    .then((data) => {
      const list = data.tasks;
      const box = document.getElementById("taskList");
      // 没有任务时显示提示
      if (!list.length) {
        box.innerHTML = '<div class="empty-tip">还没有采集任务，从下面新建第一条吧。</div>';
        return;
      }
      // 每个任务渲染一行
      box.innerHTML = list
        .map((t) => {
          // 字段简要描述
          const fieldsText = t.fields.map((f) => f.name).join("、");
          // 定时状态文字
          const cronText = t.cron ? ` · 定时:${t.cron}` : "";
          return `
            <div class="rule-item">
              <div>
                <div class="rule-name">
                  <span class="dot-on" style="visibility:${t.enabled ? "visible" : "hidden"}"></span>
                  ${t.name}
                </div>
                <div class="rule-desc">${t.url} · 字段:${fieldsText}${cronText}</div>
              </div>
              <div>
                <!-- 立即运行：调后端执行采集 -->
                <button class="btn btn-primary" onclick="runTaskItem('${t.id}')">运行</button>
                <!-- 启用/暂停 -->
                <button class="btn btn-ghost" onclick="toggleTaskItem('${t.id}')">
                  ${t.enabled ? "暂停" : "启用"}
                </button>
                <!-- 编辑 -->
                <button class="btn btn-ghost" onclick="editTask('${t.id}')">编辑</button>
                <!-- 删除 -->
                <button class="btn btn-danger" onclick="deleteTaskItem('${t.id}')">删除</button>
              </div>
            </div>`;
        })
        .join("");
    })
    .catch((err) => {
      document.getElementById("taskList").innerHTML =
        `<div class="empty-tip">加载失败：${err.message}</div>`;
    });
}

// 立即运行任务
function runTaskItem(id) {
  // 调后端 /api/crawl/tasks/{id}/run 接口
  runCrawlTask(id)
    .then((result) => {
      // 显示结果卡片
      const card = document.getElementById("resultCard");
      card.style.display = "block";
      // 成功：显示条数 + 预览表格 + 下载按钮
      if (result.ok) {
        document.getElementById("resultTitle").textContent = `✅ 采集完成：${result.count} 条`;
        // 生成表格 HTML：表头 = 第一条记录的字段名
        let html = "<table style='width:100%; border-collapse:collapse; font-size:13px;'>";
        if (result.preview && result.preview.length) {
          // 表头行
          html += "<tr>";
          Object.keys(result.preview[0]).forEach((k) => {
            html += `<th style='border:1px solid #eee; padding:6px;'>${k}</th>`;
          });
          html += "</tr>";
          // 数据行（预览前 5 条）
          result.preview.forEach((row) => {
            html += "<tr>";
            Object.values(row).forEach((v) => {
              html += `<td style='border:1px solid #eee; padding:6px;'>${v}</td>`;
            });
            html += "</tr>";
          });
        }
        html += "</table>";
        // 下载按钮：/exports/文件名.csv
        html += `<div class="mt-16"><a class="btn btn-primary" href="/exports/${result.csv}" download>下载 CSV（Excel 可打开）</a></div>`;
        document.getElementById("resultBody").innerHTML = html;
      } else {
        // 失败：显示错误
        document.getElementById("resultTitle").textContent = "❌ 采集失败";
        document.getElementById("resultBody").innerHTML =
          `<div style="color:#e5484d;">${result.error}</div>`;
      }
      // 刷新历史
      loadRuns();
    })
    .catch((err) => {
      alert("运行失败：" + err.message);
    });
}

// 启用/暂停
function toggleTaskItem(id) {
  toggleCrawlTask(id).then(() => loadTasks());
}

// 删除
function deleteTaskItem(id) {
  if (!confirm("确定删除这个采集任务吗？")) return;
  deleteCrawlTask(id).then(() => loadTasks());
}

// 编辑：把任务数据填进表单
function editTask(id) {
  getCrawlTasks().then((data) => {
    const task = data.tasks.find((t) => t.id === id);
    if (!task) return;
    editingId = id;
    // 切换标题和按钮显示
    document.getElementById("formTitle").textContent = "编辑采集任务";
    document.getElementById("cancelBtn").style.display = "inline-block";
    // 填基础信息
    document.getElementById("taskName").value = task.name;
    document.getElementById("taskUrl").value = task.url;
    document.getElementById("itemSelector").value = task.item_selector;
    document.getElementById("taskCron").value = task.cron;
    document.getElementById("maxItems").value = task.max_items;
    // 清空字段行，把任务里的字段填进去
    document.getElementById("fieldList").innerHTML = "";
    task.fields.forEach((f) => addFieldRow(f));
    // 滚动到表单
    document.getElementById("formTitle").scrollIntoView({ behavior: "smooth" });
  });
}

// 取消编辑
function resetForm() {
  editingId = null;
  document.getElementById("formTitle").textContent = "新建采集任务";
  document.getElementById("cancelBtn").style.display = "none";
  ["taskName", "taskUrl", "itemSelector", "taskCron"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  document.getElementById("maxItems").value = 50;
  document.getElementById("fieldList").innerHTML = "";
  document.getElementById("formError").textContent = "";
  addFieldRow();
}

// ---------- 字段行 ----------

// 添加一行字段表单；editData 是编辑模式下的已有字段（可选）
function addFieldRow(editData = null) {
  const box = document.getElementById("fieldList");
  const row = document.createElement("div");
  row.style.cssText = "display:flex; gap:8px; margin-bottom:8px; align-items:center;";
  // 三个输入：字段名、选择器、取值方式
  row.innerHTML = `
    <input placeholder="字段名（CSV 列名）" class="f-name" style="width:150px;">
    <input placeholder="CSS 选择器，如 h2 或 .date" class="f-selector">
    <select class="f-attr" style="width:120px;">
      <option value="text">文本</option>
      <option value="attr.href">链接(href)</option>
      <option value="attr.src">图片(src)</option>
      <option value="html">HTML源码</option>
    </select>
    <button class="btn btn-danger" onclick="this.parentElement.remove()">✕</button>`;
  // 编辑模式：填已有值
  if (editData) {
    row.querySelector(".f-name").value = editData.name;
    row.querySelector(".f-selector").value = editData.selector;
    row.querySelector(".f-attr").value = editData.attr || "text";
  }
  box.appendChild(row);
}

// ---------- 保存任务 ----------

function saveTask() {
  // 收集表单数据
  const name = document.getElementById("taskName").value.trim();
  const url = document.getElementById("taskUrl").value.trim();
  const itemSelector = document.getElementById("itemSelector").value.trim();
  const cron = document.getElementById("taskCron").value.trim();
  const maxItems = parseInt(document.getElementById("maxItems").value) || 50;

  // 收集字段：遍历每个字段行
  const fields = [];
  document.querySelectorAll("#fieldList > div").forEach((row) => {
    const fname = row.querySelector(".f-name").value.trim();
    const fsel = row.querySelector(".f-selector").value.trim();
    const fattr = row.querySelector(".f-attr").value;
    // 字段名和选择器都填了才收（不完整的行跳过）
    if (fname && fsel) {
      fields.push({ name: fname, selector: fsel, attr: fattr });
    }
  });

  // 组装提交数据
  const body = { name, url, item_selector: itemSelector, fields, cron, max_items: maxItems, enabled: true };

  // 编辑模式调更新接口，否则调创建接口
  const promise = editingId ? updateCrawlTask(editingId, body) : createCrawlTask(body);
  promise
    .then(() => {
      resetForm();
      loadTasks();
      alert("任务已保存！点任务上的「运行」按钮试试采集。");
    })
    .catch((err) => {
      document.getElementById("formError").textContent = "保存失败：" + err.message;
    });
}

// ---------- 运行历史 ----------

function loadRuns() {
  getCrawlRuns().then((data) => {
    const box = document.getElementById("runHistory");
    if (!data.runs.length) {
      box.innerHTML = '<div class="empty-tip">暂无采集历史。</div>';
      return;
    }
    // 每条历史渲染一行
    box.innerHTML = data.runs
      .map((r) => {
        // 成功绿色/失败红色
        const color = r.status === "success" ? "#16a34a" : "#e5484d";
        // 有 CSV 文件就显示下载链接
        const download = r.csv_file
          ? ` <a href="/exports/${r.csv_file}" style="color:#4f6ef7;">下载</a>`
          : "";
        return `<div class="log-item">
          <span class="log-time">${r.created_at}</span>
          <span style="color:${color};">[${r.status}] ${r.message}${download}</span>
        </div>`;
      })
      .join("");
  });
}
