"""Build an AI text view of every repository source; standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
LIMIT = 8192


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def build(check=False):
    files = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT
    ).decode('utf-8').split('\0')
    files = sorted({p for p in files if p and not p.startswith('ai/')})
    outputs = {}
    catalog = []
    for number, name in enumerate(files, 1):
        raw = (ROOT / name).read_bytes()
        entry = {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if name.endswith(('.png', '.webp')):
            entry.update(kind='image', text_conversion='metadata_only_original_image_retained',
                         metadata=('natural-earth/derived/SR_sanguo.json' if name.endswith('.webp')
                                   else 'natural-earth/metadata.json'))
        else:
            text = raw.decode('utf-8')
            if name.endswith(('.json', '.geojson')):
                json.loads(text)
            entry.update(kind='utf8_text', content_type=Path(name).suffix or 'text')
            pieces = []
            position = 0
            while position < len(text) or not pieces:
                end = min(position + 6000, len(text))
                while len(json_bytes({'source': name, 'part': len(pieces) + 1,
                                      'parts': 999999, 'text': text[position:end]})) > LIMIT:
                    end = position + (end - position) // 2
                assert end > position or not text
                pieces.append(text[position:end])
                position = end
            entry.update(first_part=f'ai/text/{number:03d}/part_001.json', parts=len(pieces))
            reconstructed = []
            for i, piece in enumerate(pieces, 1):
                payload = json_bytes({'source': name, 'part': i, 'parts': len(pieces), 'text': piece})
                assert len(payload) <= LIMIT
                outputs[f'ai/text/{number:03d}/part_{i:03d}.json'] = payload
                reconstructed.append(json.loads(payload)['text'])
            assert ''.join(reconstructed).encode('utf-8') == raw, name
        catalog.append(entry)
    catalog_pages = []
    page = []
    for entry in catalog:
        if page and len(json_bytes({'files': page + [entry]})) > LIMIT:
            catalog_pages.append(page)
            page = []
        page.append(entry)
    if page:
        catalog_pages.append(page)
    catalog_paths = []
    for i, page in enumerate(catalog_pages, 1):
        name = f'ai/catalog_{i:03d}.json'
        outputs[name] = json_bytes({'files': page})
        assert len(outputs[name]) <= LIMIT
        catalog_paths.append(name)
    text_parts = sum(e.get('parts', 0) for e in catalog)
    outputs['ai/catalog.json'] = json_bytes({
        'format_version': 1,
        'scope': 'every repository source except the generated ai/ directory',
        'encoding': 'UTF-8', 'part_max_bytes': LIMIT,
        'reconstruction': 'Read parts numerically and concatenate text exactly, without separators. '
                          'A part is valid JSON, but its text may split the original JSON or Markdown. '
                          'Verify the reconstructed UTF-8 bytes and SHA-256 against this catalog.',
        'binary_policy': 'Images retain their original bytes. Metadata describes coordinates and '
                         'processing; text is not a replacement for image pixels.',
        'source_count': len(catalog), 'catalog_parts': catalog_paths,
    })
    outputs['ai/README.md'] = '''# 全仓库 AI 阅读版

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
''' .encode('utf-8')
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'ai').rglob('*') if p.is_file()}
    expected = set(outputs)
    if check:
        assert actual == expected, f'AI file inventory differs: {actual ^ expected}'
        for name, payload in outputs.items():
            assert (ROOT / name).read_bytes() == payload, f'Stale AI output: {name}'
    else:
        for name in actual - expected:
            (ROOT / name).unlink()
        for name, payload in outputs.items():
            destination = ROOT / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
    text_files = sum(e['kind'] == 'utf8_text' for e in catalog)
    print(f'PASS: {len(catalog)} sources ({text_files} text, {len(catalog)-text_files} images); '
          f'{text_parts} valid JSON text parts <= {LIMIT} bytes; exact text reconstruction.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check committed outputs without writing')
    build(parser.parse_args().check)
