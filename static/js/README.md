# static/js/ 脚本文件说明

存放网页的「大脑」——处理用户点击、请求后端数据、更新页面显示。

## 文件清单

| 文件 | 作用 | 谁在用 |
|---|---|---|
| `api.js` | API 工具库：封装所有「请求后端接口」的函数（getRules、createRule、toggleRule、getLogs…） | 所有页面都引用它 |
| `index.js` | 首页脚本：加载引擎状态显示在顶部 | index.html |
| `rules.js` | 规则管家脚本：加载规则列表、拼装表单、保存规则、刷新日志 | rules.html |

## 阅读顺序建议

第一次看代码时按这个顺序读，逻辑最顺：
1. `api.js`（最基础：怎么跟后端要数据）
2. `index.js`（最简单：一个页面怎么用 api.js）
3. `rules.js`（最复杂：完整的功能页面，里面每一步都有注释）

## 小知识

- 这些 JS 都是「原生 JavaScript」（没用任何框架），所以代码直白易懂，适合学习
- 页面里的 JS 在「浏览器」里运行（不是 Python），所以语法是 JavaScript 不是 Python
