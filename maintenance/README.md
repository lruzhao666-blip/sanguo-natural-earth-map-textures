# 维护与来源（按需读取）

默认地图制作只使用根 README 列出的五个运行文件。此页列出的源资料、旧分片和工具用于追溯与重建，不需要逐个送入模型上下文。源文件保留既有路径，避免破坏旧链接和调用方。

## 原始地图与剧本

- `../gpkg_all_data.json`：148 区域、42,980 个边界顶点、原始字段；运行版 `map.json` 仅删除直线冗余点和非绘图字段。每段重新展开为 2px 步进后与原边界逐点相同。
- `../province-index.txt`：原始区域索引。
- `../ai_parts/part_001.json` 至 `part_088.json`：完整地图的备用分片，只供单次读取受限的旧客户端使用；不要与完整地图或运行版重复合并。
- `../scenarios/anti-dong-zhuo-alliance/scenario.json`：完整剧本、史料引用与游戏化取舍。旁边的三份中文 Markdown 包含详细归属、颜色来源及历史说明。
- 运行版 `scenario.json` 将 HEX 色号合并到势力记录；保留开局、势力 ID/名称/起始区域及全部归属。省略的史料、推定标签、联盟细节仍在原文件，未重新考订历史。
- `../manifest.json`、`../verification.json`：旧数据摘要与校验记录；`../CHANGELOG.md` 为修订记录。

## 原始底图与配准

- `../natural-earth/`：完整亚洲陆地轮廓、17 MB 灰度 PNG、世界文件、来源、版本与授权说明。
- `../natural-earth/derived/`：范围较大的全/半尺寸 WebP；用于扩大视野或更高细节的开发，不是默认加载资源。
- `../registration.json`：声明范围的详细数学换算及验证记录。
- `original_relief.json`：2026-10-16 重新下载并验证的官方全球原图记录，含 21600×10800 TIFF、44 MB 原始 ZIP、世界文件、版本差异与摘要；亚洲 PNG 与其对应裁剪区域逐像素一致。全球 ZIP/TIFF 不进入运行包。
- `runtime_manifest.json`：轻量包输入/输出 SHA-256、字节数、边界点数、实测轮廓误差和晕渲浮点裁剪框。

轻量 `land.geojson` 完整覆盖画布，并在上下各扩展 100 个逻辑像素、左右补成 16:9 背景后，在画布坐标中使用保拓扑简化；最终轮廓误差检查不超过 0.5px 加坐标舍入容差。保留岛屿和孔洞，不修改游戏区域边界。

轻量晕渲完整保留原地图，向上下和左右取更宽的经纬度背景，再用 LANCZOS 缩至 2880×1620，WebP quality 30 / method 6，要求低于 320,000 字节；不使用整数裁剪框导致地理位置偏移，也不二次压缩旧有损 WebP。

初始相机按包含上下余量的 1800 逻辑像素高度适配：1080p 上下各留 60px，1440p 上下各留 80px。1920×1080 和 2560×1440 视口均检查所有区域顶点可见。原区域 `bounds_wgs84` 与 2000×1600 画布不变，宽屏背景通过负 x、y 的 `draw_canvas_rect` 定位，不使用 cover 截断上下。

## 重建和校验

只使用运行数据不需要安装这些依赖。重建要求 Python 3.11+，依赖见 `requirements.txt`：

```sh
python -m pip install -r maintenance/requirements.txt
python maintenance/build_runtime.py
python maintenance/build_runtime.py --check
node verify_registration.cjs
node scenarios/anti-dong-zhuo-alliance/verify.cjs
python natural-earth/verify.py
```

`--check` 重新计算并检查输出，不写文件。校验边界精确还原、区域/势力覆盖、起始位置和颜色、地理有效性、陆地范围与简化误差、PNG 世界文件、裁剪框和 WebP 尺寸/体积。

图像编码器或几何库版本变化可能改变生成字节；升级依赖时重新生成、审阅预览和摘要。
