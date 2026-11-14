"""构建知识图谱：技能归一 → 分类 → 三元组 → CSV / JSON-LD / 统计。

输入：data/processed/jobs.jsonl, data/processed/job_skills.jsonl, data/lexicon/tech_skills.txt
输出：data/kg/
    nodes.csv / edges.csv        Neo4j 导入用（含 SkillCategory 节点）
    job_skills_norm.jsonl        归一后的 岗位→技能
    sample.jsonld / full.jsonld  JSON-LD
    stats.json / skills_by_family.json / skills_by_category.json

用法：
    python3 src/build/build_kg.py
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JOBS = os.path.join(ROOT, "data", "processed", "jobs.jsonl")
SKILLS = os.path.join(ROOT, "data", "processed", "job_skills.jsonl")
LEXICON = os.path.join(ROOT, "data", "lexicon", "tech_skills.txt")
OUT = os.path.join(ROOT, "data", "kg")

PUNCT = re.compile(r"[\s\u3000（）()【】\[\]「」\"'·•\-—_/\\|]+")

# 别名词表：key → 规范名（规范名必须是词表里的写法，保证大小写一致）
ALIAS = {
    "nlp": "自然语言处理", "nlu": "自然语言处理", "自然语言处理技术": "自然语言处理",
    "cv": "计算机视觉", "计算机视觉技术": "计算机视觉", "机器视觉": "计算机视觉",
    "ml": "机器学习", "机器学习算法": "机器学习",
    "dl": "深度学习", "deeplearning": "深度学习",
    "llm": "大语言模型", "大模型": "大语言模型", "大语言模型技术": "大语言模型",
    "k8s": "Kubernetes", "js": "JavaScript", "golang": "Go", "go语言": "Go",
    "cpp": "C++", "c++语言": "C++", "c语言": "C语言",
    "pytorch框架": "PyTorch", "tensorflow框架": "TensorFlow",
    "mysql数据库": "MySQL", "redis缓存": "Redis", "sql语言": "SQL",
    "推荐系统": "推荐算法", "搜索算法": "搜索", "强化学习算法": "强化学习",
    "提示工程": "Prompt", "promptengineering": "Prompt", "prompt工程": "Prompt",
    "代码review": "代码评审", "代码走查": "代码评审",
    "docker容器": "Docker",
}

# ---- 技能分类（按顺序匹配，先命中先归类）----
CATEGORY_RULES: list[tuple[str, set[str]]] = [
    ("编程语言", {
        "Python", "Java", "Go", "C++", "C语言", "C#", "JavaScript", "TypeScript", "PHP", "Ruby",
        "Rust", "Scala", "Kotlin", "Swift", "Objective-C", "SQL", "Shell", "MATLAB", "Lua",
        "Dart", "Perl", "Verilog", "VHDL", "HTML", "CSS",
    }),
    ("框架与库", {
        "Spring", "Spring Boot", "Spring Cloud", "Django", "Flask", "FastAPI", "React", "Vue",
        "Angular", "Node.js", "jQuery", "MyBatis", "Hibernate", ".NET", "PyTorch", "TensorFlow",
        "Keras", "PaddlePaddle", "MXNet", "scikit-learn", "XGBoost", "LightGBM", "React Native",
        "Flutter", "小程序", "Webpack", "Vite", "WebGL", "Canvas", "OpenGL", "Selenium",
        "Appium", "JMeter", "pytest", "vLLM", "SGLang", "PagedAttention", "TensorRT-LLM",
        "D-compose", "Vespa", "RDS", "Zabbix", "中间件", "数据面DPDK",
    }),
    ("数据库与存储", {
        "MySQL", "PostgreSQL", "Oracle", "MongoDB", "HBase", "ClickHouse", "TiDB", "SQL Server",
        "Redis", "RocksDB", "LevelDB", "OceanBase", "Elasticsearch", "向量数据库", "数据库",
        "数据库原理", "数据库优化", "倒排索引", "列式存储", "对象存储", "分布式存储", "缓存",
        "缓存一致性",
    }),
    ("大数据与流计算", {
        "Hadoop", "Spark", "Flink", "Hive", "Kafka", "YARN", "Kylin", "Doris", "StarRocks",
        "Iceberg", "Hudi", "Paimon", "Flink SQL", "MapReduce", "实时计算", "离线计算",
        "实时数仓", "离线数仓", "数据湖", "湖仓一体", "ETL", "OLAP", "数据仓库",
    }),
    ("云原生与运维", {
        "Docker", "Kubernetes", "Helm", "Istio", "Envoy", "Prometheus", "Grafana", "Jenkins",
        "GitLab CI", "Ansible", "Terraform", "AWS", "Azure", "阿里云", "腾讯云", "华为云",
        "Serverless", "函数计算", "容器编排", "容器化", "服务网格", "Service Mesh", "微服务",
        "微服务架构", "网关", "配置中心", "注册中心", "任务调度", "监控告警", "监控系统",
        "日志系统", "日志分析", "链路追踪", "APM", "可观测性", "灰度发布", "蓝绿发布", "限流",
        "熔断", "降级", "容灾", "高可用", "稳定性保障", "容量规划", "混沌工程", "全链路压测",
        "故障排查", "备份恢复", "虚拟化", "云计算", "DevOps", "CI/CD", "SRE", "服务治理",
        "负载均衡", "幂等", "分布式事务", "一致性协议", "Raft", "Paxos", "分布式系统",
        "高并发", "并发编程", "多线程", "协程", "内存管理", "JVM调优", "性能调优", "性能优化",
        "消息队列", "消息中间件", "RocketMQ", "RabbitMQ", "Nginx", "Tomcat",
    }),
    ("算法与模型", {
        "机器学习", "深度学习", "自然语言处理", "计算机视觉", "推荐算法", "搜索", "搜索推荐",
        "强化学习", "大语言模型", "多模态", "语音识别", "语音合成", "图像处理", "知识图谱",
        "图神经网络", "迁移学习", "联邦学习", "模型压缩", "模型量化", "知识蒸馏", "特征工程",
        "模型训练", "模型部署", "模型优化", "模型评估", "模型微调", "推理加速", "分布式训练",
        "排序算法", "召回策略", "粗排", "精排", "CTR预估", "广告算法", "用户增长", "因果推断",
        "时间序列", "OCR", "人脸识别", "机器翻译", "知识抽取", "关系抽取", "命名实体识别",
        "实体链接", "问答系统", "对话系统", "多智能体", "工具调用", "Agent", "RAG", "检索增强",
        "Transformer", "BERT", "GPT", "Diffusion", "CUDA", "GPU", "算法工程", "算法设计",
        "数据结构", "概率论", "线性代数", "Prompt", "AIGC", "AIGC生成", "SFT", "RLHF",
        "向量检索", "图算法", "NCCL", "NVSHMEM", "ReAct", "Multi-Agent", "Tool Calling",
        "Agent Workflow", "Agent Runtime", "Profiling", "信息检索", "AI", "搜索引擎",
    }),
    ("数据与统计", {
        "数据分析", "数据挖掘", "数据治理", "数据建模", "数据质量", "指标体系", "用户画像",
        "A/B测试", "埋点", "数据可视化", "数据驱动", "实验平台", "特征平台", "数据链路",
        "数据同步", "统计学", "数据模型", "大数据", "知识库",
    }),
    ("工程与架构", {
        "系统设计", "架构设计", "系统架构", "设计模式", "工程化", "组件化", "状态管理", "微前端",
        "低代码", "SSR", "跨端开发", "音视频", "WebRTC", "计算机图形学", "编译原理", "操作系统",
        "计算机网络", "网络协议", "TCP", "TCP/IP", "HTTP", "Linux", "Unix", "嵌入式", "驱动开发",
        "芯片设计", "FPGA", "数字电路", "代码质量", "代码评审", "技术方案设计", "需求分析",
        "技术文档", "文档撰写", "方案输出", "项目管理", "技术分享", "带团队", "鸿蒙", "Android",
        "iOS", "客户端", "服务端", "Linux内核", "RDMA", "NVLink", "SerDes", "DDR", "CPU",
        "计算机体系结构", "异步编程", "路由交换", "网络拓扑", "数据中心网络", "开发语言", "BGP",
        "SSD固件", "云架构", "ARM", "SOC", "存算一体芯片", "人工智能芯片", "交换芯片", "网卡芯片",
    }),
    ("测试与质量", {
        "自动化测试", "单元测试", "接口测试", "性能测试", "测试用例", "测试覆盖率", "接口自动化",
        "UI自动化", "流量回放",
    }),
    ("安全与隐私", {
        "网络安全", "渗透测试", "漏洞挖掘", "加密算法", "身份认证", "等保", "风控", "数据安全",
        "隐私计算", "同态加密", "差分隐私", "内容安全", "合规", "实名认证", "SOX", "CKA",
    }),
]

CATEGORY_ORDER = [c for c, _ in CATEGORY_RULES] + ["通用能力", "语言能力", "其他"]


def load_lexicon() -> dict[str, tuple[str, str]]:
    """key(小写去标点) → (规范写法, 类型)。"""
    lex = {}
    for line in open(LEXICON, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        surface = cols[0].strip()
        typ = cols[1].strip() if len(cols) > 1 else "S"
        lex[PUNCT.sub("", surface.lower())] = (surface, typ)
    return lex


LEX = load_lexicon()


def canon(s: str) -> str:
    key = PUNCT.sub("", (s or "").strip().lower())
    if key in ALIAS:
        return ALIAS[key]
    if key in LEX:
        return LEX[key][0]
    return (s or "").strip()


def skill_type(name: str) -> str:
    key = PUNCT.sub("", name.lower())
    return LEX.get(key, ("", "S"))[1]


def category_of(name: str, typ: str) -> str:
    for cat, members in CATEGORY_RULES:
        if name in members:
            return cat
    if typ == "T":
        return "通用能力"
    if typ == "L":
        return "语言能力"
    return "其他"


def main():
    from export_graph import build
    build(ROOT, canon, skill_type, category_of)

if __name__ == "__main__":
    main()
