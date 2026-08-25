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
