# -*- coding: utf-8 -*-
"""网页采集器包（第 2 阶段）。

功能：配置式爬虫 —— 填一个网址 + 几个 CSS 选择器，就能把网页上的数据
抓下来存成 CSV/Excel，还支持定时自动采集。

模块分工：
- tasks.py   任务管理：采集任务的增删改查（存数据库）
- fetcher.py 抓取解析：用 requests 抓网页 + BeautifulSoup 按选择器提取数据
- runner.py  执行器：跑一次采集、导出 CSV、定时自动采集
"""

# 包版本
__version__ = "0.2.0"
