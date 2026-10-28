"""IA 的 *_jp2.zip 支持 HTTP Range：按成员只取那一个 jp2，不下整包、不走 IA 现场转码（page/nN.jpg 一页 40 秒）。

    from ia_rangezip import RangeZip
    z = RangeZip(item, f'{item}_jp2.zip'); im = z.image(leaf)   # PIL Image（原生分辨率）
"""
import io
import re
import urllib.request
import zipfile

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'


class _HTTPFile(io.RawIOBase):
    def __init__(self, url):
        self.url = url
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            self.url = r.geturl()
            self.size = int(r.headers['Content-Length'])
        self.pos = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b''
        end = min(self.size, self.pos + n) - 1
        req = urllib.request.Request(self.url, headers={'User-Agent': UA, 'Range': f'bytes={self.pos}-{end}'})
        for k in range(4):
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    b = r.read()
                break
            except Exception:      # noqa: BLE001
                if k == 3:
                    raise
        self.pos += len(b)
        return b

    def readinto(self, buf):
        b = self.read(len(buf))
        buf[:len(b)] = b
        return len(b)


class RangeZip:
    def __init__(self, item, name):
        self.f = io.BufferedReader(_HTTPFile(f'https://archive.org/download/{item}/{name}'), buffer_size=1 << 16)
        self.z = zipfile.ZipFile(self.f)
        self.members = sorted(n for n in self.z.namelist() if n.endswith('.jp2'))
        self.by_leaf = {int(re.search(r'_(\d+)\.jp2$', n).group(1)): n for n in self.members}

    def raw(self, leaf):
        return self.z.read(self.by_leaf[leaf])

    def image(self, leaf):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        return Image.open(io.BytesIO(self.raw(leaf)))
