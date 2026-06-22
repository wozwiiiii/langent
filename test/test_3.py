#模型下载
import os
# Windows下禁用符号链接，避免重命名问题
os.environ['MODELSCOPE_SYMLINK'] = 'false'

from modelscope import snapshot_download

# 获取脚本所在目录，避免相对路径问题
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(SCRIPT_DIR, 'models')
os.makedirs(models_dir, exist_ok=True)

# 下载模型（使用绝对路径）
model_dir = snapshot_download(
    'Qwen/Qwen3-Embedding-0.6B',
    cache_dir=models_dir
)
print(f"\n模型下载完成，路径：{model_dir}")
print(f"模型文件大小：{os.path.getsize(os.path.join(model_dir, 'model.safetensors')) / 1024**3:.2f} GB")