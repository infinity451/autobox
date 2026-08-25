// ============================================================
// API 工具库：把“请求后端接口”的代码封装成一个个小函数。
// 页面里想拿数据时，直接调用这里的函数，不用重复写 fetch。
// 所有函数都返回 Promise（“未来会有的数据”），用 .then 拿到结果。
// ============================================================

// 定义一个基础请求函数：封装 fetch，自动处理错误和 JSON 解析
// 参数：url 接口地址，method 请求方式（GET/POST/PUT/DELETE），body 要发送的数据（可选）
function request(url, method = "GET", body = null) {
  // fetch 是浏览器自带的“发网络请求”函数
  // 第二个参数（对象）是请求的配置：
  return fetch(url, {
    method: method,                      // 请求方式
    headers: body ? { "Content-Type": "application/json" } : {},  // 发数据时声明格式是 JSON
    body: body ? JSON.stringify(body) : null,  // 把 JS 对象转成 JSON 字符串发送（没有就不发）
  }).then((res) => {
    // 响应不正常（4xx/5xx）时抛出错误
    if (!res.ok) {
      // 尝试从响应里取出后端返回的错误说明
      return res.json().then((data) => {
        // 抛出自定义错误，错误信息是后端写的（如“规则名字不能为空”）
        throw new Error(data.detail || "请求失败");
      });
    }
    // 响应正常：解析 JSON 并返回
    return res.json();
  });
}

// 获取所有规则（GET /api/rules）
function getRules() {
  return request("/api/rules");
}

// 创建规则（POST /api/rules），body 是规则内容对象
function createRule(body) {
  return request("/api/rules", "POST", body);
}

// 更新规则（PUT /api/rules/{id}）
function updateRule(id, body) {
  return request(`/api/rules/${id}`, "PUT", body);
}

// 删除规则（DELETE /api/rules/{id}）
function deleteRule(id) {
  return request(`/api/rules/${id}`, "DELETE");
}

// 切换启用/暂停（POST /api/rules/{id}/toggle）
function toggleRule(id) {
  return request(`/api/rules/${id}/toggle`, "POST");
}

// 获取运行日志（GET /api/logs）
function getLogs() {
  return request("/api/logs");
}

// 获取引擎状态（GET /api/status）
function getStatus() {
  return request("/api/status");
}

// ============ 网页采集器接口 ============

// 获取所有采集任务（GET /api/crawl/tasks）
function getCrawlTasks() {
  return request("/api/crawl/tasks");
}

// 创建采集任务（POST /api/crawl/tasks）
function createCrawlTask(body) {
  return request("/api/crawl/tasks", "POST", body);
}

// 更新采集任务（PUT /api/crawl/tasks/{id}）
function updateCrawlTask(id, body) {
  return request(`/api/crawl/tasks/${id}`, "PUT", body);
}

// 删除采集任务（DELETE /api/crawl/tasks/{id}）
function deleteCrawlTask(id) {
  return request(`/api/crawl/tasks/${id}`, "DELETE");
}

// 切换任务启用/暂停（POST /api/crawl/tasks/{id}/toggle）
function toggleCrawlTask(id) {
  return request(`/api/crawl/tasks/${id}/toggle`, "POST");
}

// 立即运行采集（POST /api/crawl/tasks/{id}/run）
function runCrawlTask(id) {
  return request(`/api/crawl/tasks/${id}/run`, "POST");
}

// 获取采集历史（GET /api/crawl/runs）
function getCrawlRuns() {
  return request("/api/crawl/runs");
}

// ============ 批量文件魔法接口 ============

// 预览重命名（POST /api/batch/rename/preview）
function previewBatchRename(body) {
  return request("/api/batch/rename/preview", "POST", body);
}

// 执行重命名（POST /api/batch/rename/execute）
function executeBatchRename(body) {
  return request("/api/batch/rename/execute", "POST", body);
}

// ============ 定时提醒中心接口 ============

// 获取所有定时任务（GET /api/timer/tasks）
function getTimerTasks() {
  return request("/api/timer/tasks");
}

// 创建定时任务（POST /api/timer/tasks）
function createTimerTask(body) {
  return request("/api/timer/tasks", "POST", body);
}

// 更新定时任务（PUT /api/timer/tasks/{id}）
function updateTimerTask(id, body) {
  return request(`/api/timer/tasks/${id}`, "PUT", body);
}

// 删除定时任务（DELETE /api/timer/tasks/{id}）
function deleteTimerTask(id) {
  return request(`/api/timer/tasks/${id}`, "DELETE");
}

// 切换任务启用/暂停（POST /api/timer/tasks/{id}/toggle）
function toggleTimerTask(id) {
  return request(`/api/timer/tasks/${id}/toggle`, "POST");
}

// 立即执行一次（POST /api/timer/tasks/{id}/run）
function runTimerTask(id) {
  return request(`/api/timer/tasks/${id}/run`, "POST");
}
