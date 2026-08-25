// ============================================================
// 首页脚本：负责把引擎状态（运行中？几条规则？）显示到页面上
// ============================================================

// 页面加载完成后执行：浏览器读完 HTML 后自动调用
window.addEventListener("DOMContentLoaded", () => {
  // 调用 api.js 里封装好的 getStatus() 函数，请求后端的 /api/status 接口
  getStatus()
    .then((data) => {
      // 请求成功：把状态文字填到页面顶部的 <span id="statusText"> 里
      // 模板字符串 `${}` 里可以直接插变量，非常方便
      document.getElementById("statusText").textContent =
        `引擎运行中 · ${data.rules_enabled} 条规则启用 · v${data.version}`;
    })
    .catch(() => {
      // 请求失败（比如后端没启动）：显示提示
      document.getElementById("statusText").textContent = "引擎未连接";
    });
});
