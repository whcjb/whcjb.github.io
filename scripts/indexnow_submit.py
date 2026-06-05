#!/usr/bin/env python3
"""IndexNow 即时索引提交脚本

用法：
  # 1. 单 URL
  python3 scripts/indexnow_submit.py --url https://whcjb.github.io/calvin/harmony-1/1/

  # 2. 批量（最多 10000）
  python3 scripts/indexnow_submit.py --file urls.txt
  python3 scripts/indexnow_submit.py --from-sitemap sitemap-priority.xml

  # 3. 只准备 payload 不真发（dry-run）
  python3 scripts/indexnow_submit.py --from-sitemap sitemap.xml --dry-run

注意：
  - Bing/Yandex 立即响应，Naver/Seznam 也支持
  - Google 不支持 IndexNow
  - 每次提交单 host 单 key，host 必须与提交的 URL host 完全一致
  - HTTP 200 = 成功；202 = 已接受待校验；422 = 校验失败（key 文件取不到）
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = 'f0e1fa1383c454806db07be0e0572d1d'
HOST = 'whcjb.github.io'
KEY_LOCATION = f'https://{HOST}/{KEY}.txt'
ENDPOINT = 'https://api.indexnow.org/IndexNow'   # 统一入口（自动分发给所有支持的引擎）


def submit_urls(urls, dry_run=False):
    if not urls:
        print('No URLs to submit'); return
    if len(urls) > 10000:
        print(f'⚠ 超出 10000 上限，只取前 10000（实有 {len(urls)}）')
        urls = urls[:10000]

    payload = {
        'host': HOST,
        'key': KEY,
        'keyLocation': KEY_LOCATION,
        'urlList': urls,
    }
    print(f'→ 提交 {len(urls)} 个 URL 到 {ENDPOINT}')
    print(f'  host = {HOST}')
    print(f'  key  = {KEY}')
    print(f'  样本: {urls[0]}{" ... " if len(urls) > 1 else ""}')
    if len(urls) > 1:
        print(f'         {urls[-1]}')

    if dry_run:
        print('\n[dry-run] payload (前 500 字符):')
        print(json.dumps(payload)[:500])
        return

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body = resp.read().decode('utf-8', errors='replace')
        print(f'\n响应状态: {status}')
        if status == 200:
            print('✓ 成功提交')
        elif status == 202:
            print('✓ 已接受，待 key 文件校验')
        else:
            print(f'⚠ 异常状态码: {body[:200]}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f'\nHTTP 错误 {e.code}: {body[:300]}')
        codes = {
            400: '请求格式错误',
            403: 'key 文件未找到或内容不匹配',
            422: 'host 与 key 文件 host 不一致；或 URL 中有不属于该 host 的',
            429: '速率超限（每 day 最多 10000 个 URL）',
        }
        if e.code in codes:
            print(f'→ {codes[e.code]}')
    except Exception as e:
        print(f'\n错误: {e}')


def urls_from_sitemap(sitemap_path):
    text = Path(sitemap_path).read_text(encoding='utf-8')
    return re.findall(r'<loc>([^<]+)</loc>', text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--url', help='单个 URL')
    g.add_argument('--file', help='每行一个 URL 的纯文本')
    g.add_argument('--from-sitemap', help='从 sitemap.xml 抽 URL')
    ap.add_argument('--dry-run', action='store_true', help='不真发请求')
    args = ap.parse_args()

    if args.url:
        urls = [args.url]
    elif args.file:
        urls = [ln.strip() for ln in Path(args.file).read_text(encoding='utf-8').splitlines() if ln.strip()]
    else:
        urls = urls_from_sitemap(args.from_sitemap)

    # 过滤：仅本 host 的 URL
    valid = [u for u in urls if u.startswith(f'https://{HOST}/')]
    skipped = len(urls) - len(valid)
    if skipped:
        print(f'⚠ 跳过 {skipped} 个非 {HOST} 的 URL')

    submit_urls(valid, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
