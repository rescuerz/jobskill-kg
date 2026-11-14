"""按标注规范人工（AI 辅助）复核 100 句，写回 eval/domain_review.jsonl。

标注原则（见 docs/annotation_guideline.md）：
- 只标 L/S/K/T 四类能力片段，不标岗位词（服务端/客户端）、泛化动词（开发/设计）
- 最小且语义充分；同句可多段但不重叠
- 岗位/职责描述里没有具体技能时留空

用法：python3 src/extract/annotate_domain.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "eval", "domain_review.jsonl")

# id -> [(原文片段, 标签)]
ANN: dict[int, list[tuple[str, str]]] = {
    1: [("数据处理", "S"), ("智能应用开发", "S")],
    2: [("功能、性能、功耗及物理层级的全面验证", "S")],
    3: [("性能指标验证", "S"), ("性能瓶颈", "K")],
    4: [("大模型", "K"), ("LLM", "K"), ("风控", "K")],
    5: [("Zabbix", "K"), ("Prometheus", "K"), ("Grafana", "K"), ("监控工具", "K")],
    6: [("推荐", "S"), ("CV", "K"), ("NLP", "K"), ("RL", "K"), ("大模型", "K")],
    7: [("GPU", "K"), ("渲染架构", "K")],
    8: [("沟通", "T")],
    9: [("高可用", "S")],
    10: [],
    11: [("自动化测试", "S")],
    12: [("测试开发", "S"), ("质量体系建设", "S"), ("跨团队协作", "T")],
    13: [("SSD固件架构", "K")],
    14: [],
    15: [("故障分析", "S"), ("根因分析", "S")],
    16: [("测试环境", "K"), ("测试用例", "S")],
    17: [("效能度量体系", "S")],
    18: [("系统分析", "S"), ("抽象设计", "S")],
    19: [("系统性能分析", "S")],
    20: [("客户端", "S")],
    21: [],
    22: [("数据结构", "K"), ("C#", "K"), ("lua", "K"), ("C/C++", "K")],
    23: [("主人翁意识", "T"), ("责任心", "T"), ("团队协作", "T"), ("承压能力", "T")],
    24: [("沟通能力", "T"), ("团队协作", "T")],
    25: [("大数据", "K"), ("Hive", "K"), ("Spark", "K")],
    26: [("运维", "S")],
    27: [("信息检索", "K"), ("分布式信息检索系统", "K"), ("ElasticSearch", "K"), ("Vespa", "K")],
    28: [("齿轮传动设计", "S"), ("齿形优化", "S")],
    29: [("Python", "K"), ("Go", "K"), ("Java", "K")],
    30: [],
    31: [("任务细分", "S"), ("体验优化", "S")],
    32: [("communication", "T"), ("cross-team collaboration", "T"), ("self-drive", "T")],
    33: [("实名认证", "K")],
    34: [("大模型", "K"), ("内容安全", "K")],
    35: [("编程语言", "K")],
    36: [("Profiling", "S"), ("性能基线建设", "S"), ("算子平台化", "S"), ("稳定性治理", "S")],
    37: [("React", "K"), ("TypeScript", "K"), ("设计模式", "K")],
    38: [("质量保障", "S"), ("模型部署", "S")],
    39: [("数据模型", "K"), ("ETL", "K"), ("性能优化", "S")],
    40: [("Python", "K"), ("异步编程", "K"), ("并发处理", "K")],
    41: [("高质量的代码", "S")],
    42: [("大模型", "K")],
    43: [],
    44: [("模型部署", "S"), ("推理加速", "S"), ("vLLM", "K"), ("SGLang", "K")],
    45: [],
    46: [("质量管理", "S")],
    47: [("架构评审", "S"), ("技术规划", "S"), ("Agent", "K")],
    48: [("Agent Workflow", "K"), ("Agent Runtime", "K"), ("多Agent协作", "S")],
    49: [("需求评审", "S"), ("体验优化", "S")],
    50: [("技术文档", "S")],
    51: [],
    52: [("Nccl", "K"), ("Nvshmem", "K"), ("RDMA", "K"), ("NVLINK", "K")],
    53: [("Linux", "K"), ("问题排查", "S")],
    54: [],
    55: [],
    56: [("分析问题和解决问题的能力", "T")],
    57: [("大模型", "K")],
    58: [("高并发", "S")],
    59: [("LLM", "K"), ("稳定性保障", "S"), ("性能优化", "S")],
    60: [("开发语言", "K")],
    61: [("系统设计", "S"), ("性能优化", "S")],
    62: [("指标体系", "S")],
    63: [("合规", "K")],
    64: [("业务建模", "S"), ("跨团队沟通", "T")],
    65: [("多模态", "S"), ("内容理解", "S")],
    66: [("AI", "K")],
    67: [("架构设计", "S"), ("GPU", "K"), ("系统架构", "S"), ("计算机体系结构", "K"), ("CPU", "K")],
    68: [("数据驱动", "T"), ("因果推断", "S"), ("量化分析", "S")],
    69: [("数据分析", "S")],
    70: [("功能测试", "S")],
    71: [("云架构", "K")],
    72: [("云计算", "S"), ("操作系统", "K"), ("CKA", "K")],
    73: [],
    74: [("问题分析与解决能力", "T")],
    75: [("分析问题和解决问题的能力", "T"), ("沟通表达能力", "T"), ("团队精神", "T")],
    76: [("SOX", "K")],
    77: [("JVM 调优", "S")],
    78: [],
    79: [("学习能力", "T"), ("业务理解", "T"), ("数据分析", "S")],
    80: [("TCP/IP", "K"), ("路由交换", "K"), ("网络拓扑", "K")],
    81: [("推理服务", "S")],
    82: [("沟通能力", "T"), ("客户服务", "T")],
    83: [("数据挖掘", "S"), ("预测建模", "S")],
    84: [("PyTorch", "K"), ("TensorFlow", "K"), ("性能优化", "S")],
    85: [("PagedAttention", "K"), ("vLLM", "K"), ("TensorRT-LLM", "K"), ("架构设计", "S")],
    86: [("质量保障", "S")],
    87: [("问题解决", "T")],
    88: [("团队合作", "T")],
    89: [("Agent", "K"), ("Multi-Agent", "K"), ("ReAct", "K")],
    90: [("容器技术", "K"), ("D-compose", "K"), ("Linux", "K")],
    91: [],
    92: [("项目管理", "S")],
    93: [("Agent", "K")],
    94: [("固件开发", "S"), ("DDR", "K"), ("SerDes", "K")],
    95: [("Java", "K"), ("Kotlin", "K"), ("Android", "K"), ("Swift", "K"), ("Objective-C", "K"), ("iOS", "K")],
    96: [("技术方案设计", "S"), ("代码质量", "S")],
    97: [("任务调度", "S"), ("离线推理", "S"), ("弹性伸缩", "S")],
    98: [("LLM", "K"), ("Agent", "K"), ("Tool Calling", "K")],
    99: [],
    100: [("数据中心网络", "K"), ("BGP", "K")],
}



def main() -> None:
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    missing = []
    for r in rows:
        if r["id"] not in ANN:
            continue
        text = r["text"]
        spans, used = [], []
        for frag, label in ANN[r["id"]]:
            start = text.find(frag)
            if start < 0:
                missing.append((r["id"], frag))
                continue
            end = start + len(frag)
            if any(start < u[1] and u[0] < end for u in used):
                missing.append((r["id"], f"overlap:{frag}"))
                continue
            used.append((start, end))
            spans.append({"start": start, "end": end, "text": frag, "label": label})
        r["spans"] = sorted(spans, key=lambda x: x["start"])
        r["status"] = "reviewed"
        r["annotator"] = "llm-assisted"

    with open(DATA, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"已复核 {sum(1 for r in rows if r['status'] == 'reviewed')}/{len(rows)} 条")
    if missing:
        print("未匹配/冲突的片段：")
        for m in missing[:20]:
            print("  ", m)


if __name__ == "__main__":
    main()
