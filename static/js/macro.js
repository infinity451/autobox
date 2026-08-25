// ============================================================
// 宏录制器页面逻辑：录制 → 停止 → 保存 → 列表 → 回放
// ============================================================

// 录制倒计时定时器句柄（用于取消）
let countdownTimer = null;
// 录制状态下自动保存的事件（stop 接口返回）
let recordedEvents = [];

// ---------- 页面加载 ----------
window.addEventListener("DOMContentLoaded", () => {
  loadMacros();
});

// ---------- 录制 ----------

// 开始录制：3 秒倒计时后真正开始（给用户时间准备）
function startRecord() {
  // 隐藏开始按钮，显示停止按钮
  document.getElementById("recBtn").style.display = "none";
  document.getElementById("stopBtn").style.display = "inline-block";
  // 倒计时 3 秒
  let n = 3;
  const cd = document.getElementById("countdown");
  cd.textContent = n;
  // 每秒更新一次倒计时数字
  countdownTimer = setInterval(() => {
    n -= 1;
    if (n <= 0) {
      // 倒计时结束：清空显示，真正开始录制
      clearInterval(countdownTimer);
      cd.textContent = "录制中…";
      // 调后端开始录制
      startMacroRecord()
        .then(() => {
          document.getElementById("recStatus").textContent = "正在录制，做你的操作吧！按「停止录制」结束";
        })
        .catch((err) => alert("开始录制失败：" + err.message));
    } else {
      cd.textContent = n;
    }
  }, 1000);
}

// 停止录制
function stopRecord() {
  // 取消倒计时（如果还在倒计时中）
  if (countdownTimer) clearInterval(countdownTimer);
  // 调后端停止录制，拿到事件列表
  stopMacroRecord()
    .then((result) => {
      // 保存事件，显示保存区
      recordedEvents = result.events || [];
      document.getElementById("recStatus").textContent = "录制结束";
      document.getElementById("countdown").textContent = "";
      document.getElementById("recBtn").style.display = "inline-block";
      document.getElementById("stopBtn").style.display = "none";
      // 显示保存表单
      document.getElementById("saveCard").style.display = "block";
      document.getElementById("eventCount").textContent = result.count || 0;
      // 没录到事件就提示
      if (!result.count) {
        document.getElementById("saveError").textContent = "没有录到任何操作，试试先点「开始录制」再操作鼠标键盘";
      } else {
        document.getElementById("saveError").textContent = "";
      }
    })
    .catch((err) => alert("停止录制失败：" + err.message));
}

// ---------- 保存 ----------

function saveMacro() {
  const name = document.getElementById("macroName").value.trim();
  if (!name) {
    document.getElementById("saveError").textContent = "请填写宏名字";
    return;
  }
  if (!recordedEvents.length) {
    document.getElementById("saveError").textContent = "没有事件可保存";
    return;
  }
  // 调后端保存
  saveMacroApi({ name, events: recordedEvents })
    .then(() => {
      // 清空录制状态
      recordedEvents = [];
      document.getElementById("macroName").value = "";
      document.getElementById("saveCard").style.display = "none";
      // 刷新列表
      loadMacros();
      alert("宏已保存！");
    })
    .catch((err) => {
      document.getElementById("saveError").textContent = "保存失败：" + err.message;
    });
}

// ---------- 宏列表 ----------

function loadMacros() {
  getMacroList()
    .then((data) => {
      const list = data.macros;
      const box = document.getElementById("macroList");
      if (!list.length) {
        box.innerHTML = '<div class="empty-tip">还没有宏，先录一个吧。</div>';
        return;
      }
      // 渲染每个宏：播放（选速度）+ 删除
      box.innerHTML = list
        .map((m) => `
          <div class="rule-item">
            <div>
              <div class="rule-name">${m.name}</div>
              <div class="rule-desc">${m.event_count} 个操作 · ${m.created_at}</div>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
              <select class="play-speed" style="width:80px;">
                <option value="1">1x</option>
                <option value="2">2x</option>
                <option value="4">4x</option>
              </select>
              <button class="btn btn-primary" onclick="playMacroItem('${m.id}', this)">播放</button>
              <button class="btn btn-danger" onclick="deleteMacroItem('${m.id}')">删除</button>
            </div>
          </div>`)
        .join("");
    })
    .catch((err) => {
      document.getElementById("macroList").innerHTML =
        `<div class="empty-tip">加载失败：${err.message}</div>`;
    });
}

// 回放一个宏（播放前强确认，因为会真的动鼠标键盘）
function playMacroItem(id, btn) {
  if (!confirm("⚠️ 回放会真的操作你的鼠标键盘！\n确认要在当前界面下回放吗？\n（回放时按 F8 可紧急停止）")) {
    return;
  }
  // 取这一行选择的速度
  const speed = parseFloat(btn.parentElement.querySelector(".play-speed").value) || 1;
  // 按钮显示"播放中"
  btn.textContent = "播放中…";
  btn.disabled = true;
  // 调后端回放
  playMacro(id, speed)
    .then((result) => {
      btn.textContent = "播放";
      btn.disabled = false;
      // 回放结束提示
      if (result.ok) {
        alert(`回放完成（${result.played} 个操作）`);
      } else {
        alert("回放结束：" + (result.error || ""));
      }
    })
    .catch((err) => {
      btn.textContent = "播放";
      btn.disabled = false;
      alert("回放失败：" + err.message);
    });
}

function deleteMacroItem(id) {
  if (!confirm("确定删除这个宏吗？")) return;
  deleteMacroApi(id).then(() => loadMacros());
}
