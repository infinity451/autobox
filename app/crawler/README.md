# app/crawler/ 网页采集器包说明

网页采集器（第 2 阶段）：配置式爬虫——填一个网址 + 几个 CSS 选择器，
就能把网页上的数据抓下来存成 CSV 文件（Excel 能打开），还支持定时自动采集。

## 文件清单

| 文件 | 作用 | 一句话解释 |
|---|---|---|
| `__init__.py` | 包的身份证 | 告诉 Python「crawler 是一个包」 |
| `tasks.py` | 任务管理 | 采集任务的增删改查（存数据库 crawler_tasks 表），校验配置是否合法 |
| `fetcher.py` | 抓取解析 | 用 requests 抓网页源码 + BeautifulSoup 按 CSS 选择器提取数据 |
| `runner.py` | 执行器 | 跑一次采集（抓取→解析→写 CSV→记历史），还负责定时自动采集的调度 |

## 一条采集任务长什么样

```json
{
  "id": "e0e92c6b",
  "name": "本地新闻采集",
  "url": "http://127.0.0.1:8000/static/test_page.html",
  "item_selector": "div.news-item",
  "fields": [
    {"name": "标题", "selector": "h2", "attr": "text"},
    {"name": "链接", "selector": "a", "attr": "attr.href"},
    {"name": "日期", "selector": ".date", "attr": "text"}
  ],
  "cron": "",
  "max_items": 50,
  "enabled": true
}
```

## 采集流程（一条任务从配置到出 CSV）

```
网页填表 → tasks.py 校验+存库 → 点「运行」→ runner.py
→ fetcher.fetch_html() 抓网页 → fetcher.parse_items() 按选择器提取
→ 写 CSV 到 data/exports/ → 记 crawl_runs 历史 → 前端显示预览+下载
```

## 关键设计

- **CSS 选择器**（fetcher.py）：`div.news-item` 定位每条记录的容器，字段用 `h2`/`.date`/`a` 在容器内提取。想学更多：搜「CSS 选择器入门」
- **取值方式**（extract_value）：`text`=文本、`html`=源码、`attr.href`=属性。图片地址用 `attr.src`
- **CSV 编码**（runner.py）：用 `utf-8-sig`（带 BOM）——不然 Excel 打开中文会乱码，这是给普通用户的关键细节
- **定时采集**（runner.py）：任务配置 cron 表达式后，复用规则引擎的 APScheduler 定时器，到点自动采集
- **本地测试页**：`static/test_page.html` 是模拟新闻站，采集器测试专用（不依赖外网、不会触发反爬）

## 局限与说明（诚实提醒）

- 只支持**静态网页**（数据直接写在 HTML 里）；需要点击/滚动才加载的**动态网页**（很多现代网站）抓不到，那是进阶课题（Selenium/Playwright）
- 网站改版会导致选择器失效，这是所有爬虫的通病，重新配置即可
- 抓别人网站前请遵守对方 robots.txt 和服务条款，只采集允许的数据
