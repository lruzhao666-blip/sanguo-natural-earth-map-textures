# 全仓库 AI 阅读版

先读根目录 `AI_INDEX.json` 与 `registration.json`，再按 `catalog.json` 中的 `catalog_parts` 查询源文件。
目录页同样不超过 8192 字节，覆盖所有非生成文件：地图、88 个旧分片、完整海岸线 GeoJSON、剧本、
势力颜色表、史料、说明、校验脚本和图片。JSON / Markdown / 代码均保留原文，不做摘要替代。

每个文本文件有 `first_part` 和 `parts`，对应 `text/NNN/part_001.json` 起的连续编号。
每片是 UTF-8 合法 JSON，实际字节数不超过 8192。依次取 `text` 字段，无分隔符拼接，
即可按目录的 SHA-256 和字节数验证原文件。片内原文可能在 JSON 数组或 Markdown 行中间截断，
不能单独把 `text` 当作完整原文件解析，也不能遗漏后续片。生成目录不索引自身，避免递归。

PNG / WebP 保留原文件，目录记录摘要和元数据路径；文本模型据此读取范围、尺寸、
像素约定和压缩方式。需要视觉判断时仍要加载原图片，元数据不等同图片像素内容。

重建：`python build_ai.py`；只读校验：`python build_ai.py --check`。
脚本仅依赖 Python 标准库和 Git，按固定顺序生成并逐字节重组验证全部文本。
