# 三国策略地图数据 · AI 直读版

本仓库只整理地图原型所需的数据。无需搜索、克隆或分析完整上游游戏项目。

## 给 AI 的入口

1. 先读本 README 和 [区域索引](province-index.txt)（约 6.5KB）。
2. 使用 [完整地图 JSON](gpkg_all_data.json)（483,426 字节，148 条区域，全部顶点）。优先下载并用程序解析，不要只读网页预览。
3. 仅当单次抓取受 10KB 限制时，按顺序读取 [ai_parts](ai_parts/) 下 part_001.json 至 part_088.json。每份都是合法 JSON，实测最大 7,467 字节。

## 完整数据说明

- 顶层：bounds_wgs84、canvas_size、provinces。
- 画布：2000 × 1600；polygon 是画布 [x,y]，不是 WGS84 经纬度。
- 148 条郡级区域记录、14 个州、42,980 个顶点（含闭合终点）。记录还包含国、尹等，不全部是历史上的郡。
- 字段：id、name、state、faction、capital、center_x、center_y、num_vertices、polygon。
- faction 标签：wei=93、wu=34、shu=21，不等于任意历史年份的准确剧本归属。
- 所有多边形闭合，顶点计数匹配，相邻线段为水平/竖直 2px；跨区域拓扑未核验。历史政区与郡治按三国后期（约 262 年）基准核订；name 是地图显示名，可选用著名郡治或通行城名，不等于正式行政名称，修订记录见 [CHANGELOG.md](CHANGELOG.md)。
- center_x/center_y 可作为标注位置参考，不保证是郡治的精确位置。
- 本仓库 JSON 保留全部区域记录、字段与边界顶点，并采用紧凑序列化；名称、郡治及势力的整理修订见 CHANGELOG.md，不等于未经修订的上游原文。
- 显示名采用“著名城名优先，其余地域名省略郡/国后缀”的规则，参考光荣《三国志》的简洁选名感觉；例如北海国显示为北海、汉中郡显示为汉中，既有许昌、小沛等城名保留。代郡、陈郡、赵国、梁国、鲁郡、吴郡分别显示为代、陈、赵、梁、鲁、吴；抚夷护军等其他名称沿用既有写法。capital 仍保留郡治，不因显示名变化而改变 id、州、势力、标注位置与 polygon。

## 剧本归属参考

- [反董卓联盟（190年1月）](scenarios/anti-dong-zhuo-alliance/README.md)：40个可玩势力、148块区域归属，以及40套HEX/RGB势力色。
- [逐城归属表](scenarios/anti-dong-zhuo-alliance/势力与城池归属.md)和[势力色表](scenarios/anti-dong-zhuo-alliance/势力色表.md)用于审阅；[scenario.json](scenarios/anti-dong-zhuo-alliance/scenario.json)按city_id与地图id关联。
- 剧本包含历史据点、名义辖属和游戏化安排；来源与取舍单独记录，不改写地图的wei/wu/shu标签或边界。

## 10KB 受限工具如何读分片

每份分片有 part_index、total_parts、records。records 中：
- province_index：原 provinces 数组的零起始索引。
- polygon_offset：本段在原 polygon 的零起始顶点偏移。
- province：保留原字段，polygon 为本段；num_vertices 仍是完整顶点数。

按 province_index 分组、polygon_offset 升序拼接 polygon。一条区域可能跨多个文件，分片不是独立区域，单段不一定闭合。完整读取并重组后再绘图。全 88 片已重组并与原文件深度比较一致。

分片解决请求截断，不解决总上下文限制；能执行代码的 AI 应直接下载并解析完整 JSON。

## 可以直接交给 AI 的需求

> 基于完整 gpkg_all_data.json 制作独立的三国策略游戏地图原型。无需搜索上游仓库。完整绘制 provinces 中的148条区域，保留原始 id 和全部 polygon；按 faction 着色，显示区域名称，支持缩放、拖动、悬停高亮及点击查看名称、州、郡治、势力。先完成可运行的地图系统，不添加复杂战争、经济和外交。类似《文明时代2》的视觉与交互参考由我另行提供截图，不复制原游戏素材。缺失的地形、精确城市坐标和历史剧本不能编造为史实。候选邻接关系需根据共享边界计算后核验。

## 目录

- gpkg_all_data.json：完整紧凑数据。
- province-index.txt：148条区域索引，无 polygon。
- [natural-earth/](natural-earth/README.md)：独立的亚洲陆地轮廓与灰度晕渲素材（15°E—180°E、15°S—82°N），含来源、地理配准信息和自检脚本；尚未与三国画布配准。
- ai_parts/：88份不超过8KB的无损分片。
- [scenarios/anti-dong-zhuo-alliance/](scenarios/anti-dong-zhuo-alliance/README.md)：反董卓联盟剧本归属、势力色与校验脚本。
- manifest.json：上游来源、固定提交、原文与紧凑版摘要、坐标范围。
- verification.json：全量数据和分片核验结果。
- CHANGELOG.md：地图数据、素材与剧本修订记录（2026-10-14 至 2026-10-15）。

## 来源和授权状态

来源：https://github.com/liang7833/sanguo-map
原路径：仓库根目录 gpkg_all_data.json
上游固定提交：121ad89a3bd1ab7c925ac875f63c3b7f77462abf（2026-06-22）。整理日期：2026-10-14。

上游原文为2,388,305字节；本仓库的gpkg_all_data.json对应 manifest.json 的 compact_sha256，不是 source_sha256。原文SHA-256：c8acb3e327f8e09fe21aa2e6d17f6d2c2f03a16bc936b7fdd491727d3b860037。

Natural Earth 素材的 public domain 说明仅适用于 `natural-earth/` 中的 Natural Earth 数据，详见该目录的来源记录。

未发现三国地图上游声明的 LICENSE。本整理保留来源，**不为上游地图数据新增开源或商用授权**。后续公开再分发或商业使用前应向权利人确认权限。
