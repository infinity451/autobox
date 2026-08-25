// ============================================================
// 批量文件魔法页面逻辑：预览 → 确认 → 执行
// ============================================================

// 保存最后一次预览结果（执行时要用同一份对照表）
let lastPreview = null;

// ---------- 模式参数显示切换 ----------

// 根据选中的模式，显示对应的参数输入框
function updateModeUI() {
  const mode = document.getElementById("batchMode").value;
  // 四个参数区，只有当前模式对应的显示出来
  document.getElementById("paramPrefix").style.display = mode === "prefix" ? "block" : "none";
  document.getElementById("paramSuffix").style.display = mode === "suffix" ? "block" : "none";
  document.getElementById("paramReplace").style.display = mode === "replace" ? "block" : "none";
  document.getElementById("paramSequence").style.display = mode === "sequence" ? "block" : "none";
}

// 收集表单配置（预览和执行共用）
function collectConfig() {
  const mode = document.getElementById("batchMode").value;
  const directory = document.getElementById("batchDir").value.trim();
  // 按模式收集参数
  let params = {};
  if (mode === "prefix") params = { prefix: document.getElementById("prefixText").value };
  if (mode === "suffix") params = { suffix: document.getElementById("suffixText").value };
  if (mode === "replace") params = {
    find: document.getElementById("findText").value,
    replace: document.getElementById("replaceText").value,
  };
  if (mode === "sequence") params = { position: document.getElementById("seqPosition").value };
  return { directory, mode, params };
}

// ---------- ① 预览 ----------

function doPreview() {
  const cfg = collectConfig();
  // 目录没填就提示
  if (!cfg.directory) {
    document.getElementById("batchError").textContent = "请先填写目标文件夹";
    return;
  }
  document.getElementById("batchError").textContent = "";

  // 调后端预览接口
  previewBatchRename(cfg)
    .then((result) => {
      // 失败：显示错误
      if (!result.ok) {
        document.getElementById("batchError").textContent = result.error || "预览失败";
        return;
      }
      // 成功：保存预览结果，渲染对照表
      lastPreview = result;
      document.getElementById("previewCard").style.display = "block";
      // 标题：显示总数和冲突数
      document.getElementById("previewTitle").textContent =
        `预览：共 ${result.total} 个文件，${result.conflicts} 个冲突（冲突项不会执行）`;
      // 渲染列表：旧名 → 新名，冲突标红
      document.getElementById("previewList").innerHTML = result.files
        .map((f) => {
          // 冲突标红提示
          const style = f.conflict ? "color:#e5484d;" : "";
          const tag = f.conflict ? " ⚠️冲突" : "";
          return `<div class="log-item">
            <span style="color:#8a9099;">${f.old}</span>
            → <span style="${style}">${f.new}${tag}</span>
          </div>`;
        })
        .join("");
      // 有可执行项才启用"确认执行"按钮
      const executable = result.files.filter((f) => f.old !== f.new && !f.conflict).length;
      document.getElementById("execBtn").disabled = executable === 0;
    })
    .catch((err) => {
      document.getElementById("batchError").textContent = "预览失败：" + err.message;
    });
}

// ---------- ② 确认执行 ----------

function doExecute() {
  // 必须预览过才能执行（安全原则：先看再改）
  if (!lastPreview) {
    alert("请先点「预览」确认要改哪些文件");
    return;
  }
  // 二次确认
  if (!confirm(`确认对 ${lastPreview.total} 个文件执行重命名吗？`)) return;

  const cfg = collectConfig();
  // 调后端执行接口
  executeBatchRename(cfg)
    .then((result) => {
      // 显示执行结果
      document.getElementById("resultCard").style.display = "block";
      document.getElementById("resultBody").innerHTML = `
        <div style="font-size:15px;">
          ✅ 成功改名 <b>${result.renamed}</b> 个，
          跳过 <b>${result.skipped}</b> 个（没变化/冲突），
          ${result.failed.length ? `失败 <b style="color:#e5484d;">${result.failed.length}</b> 个` : "无失败"}
        </div>
        ${result.failed.length ? `<div class="mt-8" style="color:#e5484d; font-size:13px;">${result.failed.map((f) => f.name + ": " + f.error).join("；")}</div>` : ""}
      `;
      // 执行完清除预览，防止重复执行
      lastPreview = null;
      document.getElementById("execBtn").disabled = true;
    })
    .catch((err) => {
      document.getElementById("batchError").textContent = "执行失败：" + err.message;
    });
}
