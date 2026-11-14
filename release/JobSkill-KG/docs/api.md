# 查询 API v0.2

运行 `python3 src/app/serve_api.py --port 8765`，监听 127.0.0.1。

- `/evidence`：交互式带证据查询页面。
- `/api/evidence?city=杭州&family=算法&skills=Python,PyTorch&optional_skill=LLM`：全部技能 AND 查询＋加分条件，别名归一，返回三项匹配与证据。
- `/api/stats`：图谱统计，edges 是关系边，rdf_triples 是 RDF 三元组。
- `/api/jobs?skills=Python&city=杭州`：岗位检索。
- `/api/skills?family=算法`：技能频次。
- `/api/gap?family=算法&have=Python`：样本中尚未勾选的技能提及，不表示必备条件。
- `/api/job/<doc_id>`：单岗位详情。

证据字段包含 field/start/end/url/crawled_at；原文私有版本含 quote/surface，公开版仅在三条示例岗位保留少量 quote。浏览器为缺少 quote 的结果提示回源核对。

接口是本地演示服务，未部署公开 API。不要把 localhost 写作公开数据访问地址。

新版 /evidence 页面自动查询默认条件，支持快捷示例、中文逗号、岗位选择、证据折叠和高亮、定位展开、逐批显示更多以及窄屏布局。数据概览直接读取 /api/stats。
