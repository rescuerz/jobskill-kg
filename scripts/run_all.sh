#!/bin/bash
# 私有完整数据流程：采集 → 清洗 → 抽取 → 构图 → 站点 → 打包
set -e
cd "$(dirname "$0")/.."

PY=${JOBSKILL_PYTHON:-python3.12}
export PYTHONPATH=.pkgs:src

echo "[0/10] 依赖"
if [ ! -d .pkgs ]; then
  pip3 install --target=.pkgs requests jieba rdflib python-pptx markdown -i https://pypi.tuna.tsinghua.edu.cn/simple
fi

echo "[1/10] 采集（已存在则跳过，脚本内部断点续采）"
$PY src/crawl/bytedance.py || true
$PY src/crawl/tencent.py   || true
$PY src/crawl/netease.py   || true

echo "[2/10] 清洗筛选"
$PY src/build/prepare.py

echo "[3/10] 技能抽取（词典，默认不启用模型）"
PYTHONPATH=.pkgs $PY src/extract/evidence.py

echo "[4/10] 构图"
$PY src/build/build_kg.py

echo "[5/10] 站点"
$PY src/app/build_site.py

echo "[6/10] OpenKG 打包"
$PY src/build/package.py

echo "[7/10] GitHub Pages 站点"
$PY src/app/build_pages.py

echo "完成数据与站点重建。当前报告与讲稿见 docs；不调用含旧分数的历史 PPT/PDF 生成器。"
