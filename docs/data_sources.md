# 数据源与采集说明

> 记录时间：2026-11-01｜采集脚本见 `src/crawl/`

## 一、数据源清单

| 来源 | 接口 | 岗位数（原始） | 字段 | 合规说明 |
|---|---|---|---|---|
| 字节跳动招聘 | `POST jobs.bytedance.com/api/v1/search/job/posts` | 10,000 | 标题、职责、要求、岗位大类、城市、发布时间 | 企业官方招聘站公开岗位，仅分页拉取，限速 0.4s/请求 |
| 腾讯招聘 | `GET careers.tencent.com/tencentcareer/api/post/Query` + `ByPostId` | 2,248 | 标题、职责、要求、BG、城市、更新日期 | 同上，限速 0.35s/请求 |
| 网易招聘 | `POST hr.163.com/api/hr163/position/queryPage` | 2,726 | 标题、职责、要求、部门、城市、学历、年限 | 同上，限速 0.3s/请求 |
| Chinese-SkillSpan（学术） | Google Drive（论文 arXiv:2604.23009） | 4,731 句（gold span） | 文本 + LSKT span + 岗位标题/城市 | 仅用于模型训练与评测，不再分发 |

合计原始岗位 **14,974** 条，经岗位族筛选后入池 **4,904** 条 IT/算法岗。

## 二、筛选口径

1. 站点岗位大类命中「产品/设计/市场/销售/运营/人力/职能/游戏策划/游戏艺术」→ 丢弃；
2. 标题含强技术信号（数据分析、算法工程师、后端、前端、测试开发、运维…）→ 例外保留；
3. 正文（职责 + 要求）长度 < 40 字 → 丢弃（抽不出内容）；
4. 按 `content_sha256` 去重；
5. 岗位族归类：标题优先，标题无信号再看正文，正文兜底仅对技术大类放行。

筛选后入池 4,904 条；其中 4,865 条抽到技能进入图谱，各族分布：算法 2,193｜后端 870｜前端客户端 743｜运维安全 414｜数据 405｜测试 215｜MLOps 25。

未入图的 39 条包括：职能岗误入（招聘/HRBP/采购/公关，标题含 Data、AI 触发技术信号例外）、
英文或日文 JD（中文词表命中不了）、模拟电路/光通信等非软件岗。详见报告附录 A。

## 三、字段说明（`data/processed/jobs.jsonl`）

| 字段 | 含义 |
|---|---|
| `doc_id` | `source:source_id`，全局唯一 |
| `title` / `company` / `department` / `category` | 岗位标题、公司、部门、站点大类 |
| `description` / `requirement` | 岗位职责 / 任职要求（抽取输入） |
| `locations` | 城市（已去"市"后缀） |
| `education_level` / `experience_years` | 规则解析的学历/经验要求 |
| `salary` | 解析出的薪酬区间（当前三个源均未公布薪资，字段为空，待接入含薪资的来源） |
| `url` / `crawled_at` / `content_sha256` | 溯源字段 |

## 四、合规边界

- 只抓公开可访问的招聘页面，不登录、不破解接口、不采集个人信息（招聘方 HR 联系人一律不采）。
- 限速 ≥0.3s/请求，失败指数退避，不并发冲击。
- **不对外分发原始 JD 全文**；对外发布的是抽取后的三元组、聚合统计与每族 ≤20 条脱敏样例。
- 数据版权归原发布方，本数据集以 CC BY 4.0 发布衍生结果并注明来源。

## 五、复现

```bash
pip3 install --target=.pkgs requests jieba -i https://pypi.tuna.tsinghua.edu.cn/simple
PYTHONPATH=.pkgs:src python3 src/crawl/bytedance.py
PYTHONPATH=.pkgs:src python3 src/crawl/tencent.py
PYTHONPATH=.pkgs:src python3 src/crawl/netease.py
PYTHONPATH=.pkgs:src python3 src/build/prepare.py
```
