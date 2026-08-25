// ============================================================
// 定时提醒中心页面逻辑：任务列表 + 新建/编辑 + 立即测试
// ============================================================

// 记录当前编辑的任务 id（null = 新建）
let editingId = null;

// ---------- 页面加载 ----------
window.addEventListener("DOMContentLoaded", () => {
  loadTasks();
});

// ---------- 任务列表 ----------

function loadTasks() {
  getTimerTasks()
    .then((data) => {
      const list = data.tasks;
      const box = document.getElementById("taskList");
      if (!list.length) {
        box.innerHTML = '<div class="empty-tip">还没有定时任务，从下面新建第一条吧。</div>';
        return;
      }
      // 动作类型的中文名（显示友好）
      const actionNames = {
        notify: "提醒", shutdown: "关机", restart: "重启",
        sleep: "休眠", open: "打开程序",
      };
      box.innerHTML = list
        .map((t) => `
          <div class="rule-item">
            <div>
              <div class="rule-name">
                <span class="dot-on" style="visibility:${t.enabled ? "visible" : "hidden"}"></span>
                ${t.name}
              </div>
              <div class="rule-desc">${actionNames[t.action] || t.action} · ${t.cron}${t.message ? " · " + t.message : ""}</div>
            </div>
            <div>
              <!-- 立即执行一次（测试弹窗用） -->
              <button class="btn btn-primary" onclick="runTimerItem('${t.id}')">测试</button>
              <button class="btn btn-ghost" onclick="toggleTaskItem('${t.id}')">${t.enabled ? "暂停" : "启用"}</button>
              <button class="btn btn-ghost" onclick="editTask('${t.id}')">编辑</button>
              <button class="btn btn-danger" onclick="deleteTaskItem('${t.id}')">删除</button>
            </div>
          </div>`)
        .join("");
    })
    .catch((err) => {
      box.innerHTML = `<div class="empty-tip">加载失败：${err.message}</div>`;
    });
}

// 立即执行一次（点「测试」弹窗验证）
function runTimerItem(id) {
  runTimerTask(id)
    .then((result) => {
      if (!result.ok) alert("执行失败：" + result.error);
    })
    .catch((err) => alert("执行失败：" + err.message));
}

function toggleTaskItem(id) {
  toggleTimerTask(id).then(() => loadTasks());
}

function deleteTaskItem(id) {
  if (!confirm("确定删除这个定时任务吗？")) return;
  deleteTimerTask(id).then(() => loadTasks());
}

// ---------- 编辑 ----------

function editTask(id) {
  getTimerTasks().then((data) => {
    const task = data.tasks.find((t) => t.id === id);
    if (!task) return;
    editingId = id;
    document.getElementById("formTitle").textContent = "编辑定时任务";
    document.getElementById("cancelBtn").style.display = "inline-block";
    document.getElementById("taskName").value = task.name;
    document.getElementById("taskAction").value = task.action;
    document.getElementById("taskCron").value = task.cron;
    document.getElementById("taskMessage").value = task.message;
    document.getElementById("taskProgram").value = task.program;
    updateActionUI();
  });
}

function resetForm() {
  editingId = null;
  document.getElementById("formTitle").textContent = "新建定时任务";
  document.getElementById("cancelBtn").style.display = "none";
  ["taskName", "taskCron", "taskMessage", "taskProgram"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  document.getElementById("taskAction").value = "notify";
  document.getElementById("formError").textContent = "";
  updateActionUI();
}

// 动作类型切换：open 显示程序路径框，其他显示提醒内容框
function updateActionUI() {
  const action = document.getElementById("taskAction").value;
  document.getElementById("wrapProgram").style.display = action === "open" ? "block" : "none";
  document.getElementById("wrapMessage").style.display = action === "open" ? "none" : "block";
}

// ---------- 保存 ----------

function saveTask() {
  const body = {
    name: document.getElementById("taskName").value.trim(),
    action: document.getElementById("taskAction").value,
    cron: document.getElementById("taskCron").value.trim(),
    message: document.getElementById("taskMessage").value.trim(),
    program: document.getElementById("taskProgram").value.trim(),
    enabled: true,
  };
  // 编辑模式调更新接口，否则调创建
  const promise = editingId ? updateTimerTask(editingId, body) : createTimerTask(body);
  promise
    .then(() => {
      resetForm();
      loadTasks();
      alert("任务已保存！可以点「测试」试试效果。");
    })
    .catch((err) => {
      document.getElementById("formError").textContent = "保存失败：" + err.message;
    });
}
