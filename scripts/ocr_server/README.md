# PDF OCR Server (Qwen3-VL-8B)

基于 Qwen3-VL-8B 的PDF中文OCR识别服务。部署在多卡4090D上。

## 部署步骤

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动OCR服务
python server.py --port 8765

# 3. 在本地运行客户端处理PDF
python client.py --pdf /path/to/calvin_john.pdf --output /path/to/output/
```

## 文件说明
- `server.py` - OCR服务端（部署在4090D机器上）
- `client.py` - 客户端（在本地Mac上运行，发送PDF页面到服务端识别）
- `requirements.txt` - Python依赖
- `batch_ocr.py` - 批量处理PDF并生成网站md文件
