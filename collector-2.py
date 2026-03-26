#!/usr/bin/env python3
"""
昇腾适配模型数据采集器 - GitCode Web API版
使用GitCode Web API获取Ascend-SACT模型仓库数据
支持多仓库配置采集
"""

import json
import os
import requests
import time
import yaml
from datetime import datetime

# GitCode Web API认证信息
BEARER_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI2OGY3MDRiYzdhNGM3NjM4MzFkOTQ5MGEiLCJzdWIiOiJtaW5nLXNoZW4iLCJhdXRob3JpdGllcyI6W10sIm9iamVjdElkIjoiNjk5MDEzY2Y2ODY1NmQwMTEwNGNkN2I2IiwiaWF0IjoxNzcxMDQ5OTM1LCJleHAiOjE3NzI1MDQxMTV9.WzqzdeQ4FavSBigfB5oVNMG0A4-kiBmqwufQ_K2q4EAty1-flwfTXVkzGTMimudOVuLuBjJaRK8NUJWzauMWHQ"

# Cookie信息（完整版，包含更多关键参数）
COOKIE = "uuid_tt_dd=10_23424968500-1769827168312-980636; c_gitcode_um=-; gitcode_first_time=2026-01-31%2010:39:28; gitcode_theme=white; _frid=4ff161a6d50e4031a4ef36ab5edba0f6; GITCODE_REFRESH_TOKEN=eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI2OGY3MDRiYzdhNGM3NjM4MzFkOTQ5MGEiLCJzdWIiOiJtaW5nLXNoZW4iLCJhdXRob3JpdGllcyI6W10sIm9iamVjdElkIjoiNjk5MDEzY2Y2ODY1NmQwMTEwNGNkN2I2IiwiaWF0IjoxNzcxMDQ5OTM1LCJleHAiOjE3NzYyMzM5MzV9.FaCera7wC3o0-xDF4Zkr9nD4Oswqb27BodJkN4PvzqZxyWmqhAfCuTC65yForgKqTz2da0cKs5GNonZ_rH5_Xg; GitCodeUserName=ming-shen; HMACCOUNT=5263F4C464578DF0; HWWAFSESTIME=1772417712948; BENSESSCC_TAG=10_23424968500-1769827168312-980636; GITCODE_ACCESS_TOKEN=eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI2OGY3MDRiYzdhNGM3NjM4MzFkOTQ5MGEiLCJzdWIiOiJtaW5nLXNoZW4iLCJhdXRob3JpdGllcyI6W10sIm9iamVjdElkIjoiNjk5MDEzY2Y2ODY1NmQwMTEwNGNkN2I2IiwiaWF0IjoxNzcxMDQ5OTM1LCJleHAiOjE3NzI1MDQxMTV9.WzqzdeQ4FavSBigfB5oVNMG0A4-kiBmqwufQ_K2q4EAty1-flwfTXVkzGTMimudOVuLuBjJaRK8NUJWzauMWHQ; HWWAFSESID=6ba6f136f22d5e09a0a; pageSize={%22global-pager%22:10}; gitcode_lang=zh; _fr_ssid=8cc433596ce048e891f5a2e7b18fa8cd; Hm_lvt_62047c952451105d57bab2c4af9ce85b=1771049716,1772095578,1772417715; c_gitcode_fref=http://localhost:8080/; UnsafeGitCodeUserName=ming-shen; c_gitcode_rid=1772434221353_418077; last-repo-id=8795146; Hm_lpvt_62047c952451105d57bab2c4af9ce85b=1772434479"

#!/usr/bin/env python3
import json
import re
import time
from urllib.parse import urlparse
import subprocess

ADAPTER_KEYWORDS = [
    ("vllm-ascend", ["vllm-ascend", "vllm_ascend", "vllm ascend"]),
    ("mindspeed-llm", ["mindspeed-llm", "mindspeed_llm", "mindspeed llm"]),
    ("mindspeed-mm", ["mindspeed-mm", "mindspeed_mm", "mindspeed mm"]),
    ("sglang", ["sglang"]),
    ("mindie", ["mindie"]),
    ("omni-infer", ["omni-infer", "omni infer"]),
    ("LLaMa Factory", ["llama factory", "llama-factory", "llamafactory"]),
    ("verl", ["verl"]),
    ("vllm", ["vllm"]),
]

TRAINING_FRAMEWORKS = ["mindspeed-llm", "mindspeed-mm", "LLaMa Factory", "verl"]
INFERENCE_FRAMEWORKS = ["vllm-ascend", "sglang", "mindie", "omni-infer"]

HARDWARE_KEYWORDS = [
    ("A2", ["910b", "Atlas 800T A2", "Atlas 800I A2", " A2"]),
    ("A3", ["910c", "Atlas 800T A3", "Atlas 800I A3", " A3"]),
    ("310", ["310"]),
]

def get_raw_readme_url(url):
    """从gitcode仓库URL获取raw README URL"""
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) >= 2:
        owner, repo = path_parts[0], path_parts[1]
        return f"https://raw.gitcode.com/{owner}/{repo}/raw/main/README.md"
    return None

def fetch_readme_content(url):
    """使用curl获取README内容"""
    raw_url = get_raw_readme_url(url)
    if not raw_url:
        return None
    
    try:
        result = subprocess.run(
            ['curl', '-sL', raw_url],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout:
            content = result.stdout
            if len(content) > 100:
                return content
    except:
        pass
    return None

def detect_adapter_framework(content):
    """检测适配框架"""
    if not content:
        return None, None
    
    content_lower = content.lower()
    
    for framework, keywords in ADAPTER_KEYWORDS:
        for keyword in keywords:
            keyword_escaped = re.escape(keyword)
            pattern_with_boundary = re.compile(r'\b' + keyword_escaped + r'\b', re.IGNORECASE)
            pattern_without_boundary = re.compile(keyword_escaped, re.IGNORECASE)
            
            if pattern_with_boundary.search(content_lower):
                if framework == "vllm":
                    framework = "vllm-ascend"
                training_or_inference = "训练" if framework in TRAINING_FRAMEWORKS else "推理"
                return framework, training_or_inference
            
            if pattern_without_boundary.search(content_lower):
                if framework == "vllm":
                    framework = "vllm-ascend"
                training_or_inference = "训练" if framework in TRAINING_FRAMEWORKS else "推理"
                return framework, training_or_inference
    
    return None, None

def check_adapter_framework(model):
    """检查模型的适配框架
    
    按顺序检查：
    1. name字段
    2. full_name字段  
    3. description字段
    4. README文档（必须获取）
    """
    name = model.get("name", "")
    full_name = model.get("full_name", "")
    description = model.get("description", "") or ""
    url = model.get("url", "")
    
    search_sources = [name, full_name, description]
    
    adapter_framework = None
    training_or_inference = None
    
    for source in search_sources:
        if source:
            fw, toi = detect_adapter_framework(source)
            if fw:
                adapter_framework = fw
                training_or_inference = toi
                return adapter_framework, training_or_inference
    
    readme_content = fetch_readme_content(url)
    if readme_content:
        adapter_framework, training_or_inference = detect_adapter_framework(readme_content)
    
    return adapter_framework, training_or_inference


def detect_adapter_hardware(content):
    """检测适配硬件"""
    if not content:
        return None
    
    content_lower = content.lower()
    
    for hardware, keywords in HARDWARE_KEYWORDS:
        for keyword in keywords:
            keyword_escaped = re.escape(keyword)
            pattern_with_boundary = re.compile(r'\b' + keyword_escaped + r'\b', re.IGNORECASE)
            pattern_without_boundary = re.compile(keyword_escaped, re.IGNORECASE)
            
            if pattern_with_boundary.search(content_lower):
                return hardware
            
            if pattern_without_boundary.search(content_lower):
                return hardware
    
    return None


def check_adapter_hardware(model):
    """检查模型的适配硬件
    
    按顺序检查：
    1. name字段
    2. full_name字段  
    3. description字段
    4. README文档（必须获取）
    """
    name = model.get("name", "")
    full_name = model.get("full_name", "")
    description = model.get("description", "") or ""
    url = model.get("url", "")
    
    search_sources = [name, full_name, description]
    
    adapter_hardware = None
    
    for source in search_sources:
        if source:
            hw = detect_adapter_hardware(source)
            if hw:
                adapter_hardware = hw
                return adapter_hardware
    
    readme_content = fetch_readme_content(url)
    if readme_content:
        adapter_hardware = detect_adapter_hardware(readme_content)
    
    return adapter_hardware

def update_framework_hardware():
    input_file = "./data/ascend_model.json"
    output_file = "./data/ascend_model_with_adapter.json"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    models = data.get("models", [])
    gitcode_models = [m for m in models if m.get("source") == "gitcode"]
    
    print(f"Gitcode models: {len(gitcode_models)}")
    
    for idx, model in enumerate(gitcode_models):
        adapter_framework, training_or_inference = check_adapter_framework(model)
        model["adapter_framework"] = adapter_framework or ""
        model["training_or_inference"] = training_or_inference or ""
        
        adapter_hardware = check_adapter_hardware(model)
        model["adapter_hardware"] = adapter_hardware or ""
        
        series_vendor = check_model_series_vendor(model)
        model["model_series"] = series_vendor.get("series", "")
        model["model_vendor"] = series_vendor.get("vendor", "")
        
        print(f"[{idx+1}/{len(gitcode_models)}] {model.get('name')} -> framework: {adapter_framework}, hardware: {adapter_hardware}, series: {series_vendor.get('series')}, vendor: {series_vendor.get('vendor')}")
        
        time.sleep(0.3)
        
        if (idx + 1) % 50 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Checkpoint saved at {idx+1}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    frameworks = {}
    hardware_counts = {}
    training_count = 0
    inference_count = 0
    series_counts = {}
    vendor_counts = {}
    for m in gitcode_models:
        fw = m.get('adapter_framework', '')
        hw = m.get('adapter_hardware', '')
        toi = m.get('training_or_inference', '')
        series = m.get('model_series', '')
        vendor = m.get('model_vendor', '')
        if fw:
            frameworks[fw] = frameworks.get(fw, 0) + 1
        if hw:
            hardware_counts[hw] = hardware_counts.get(hw, 0) + 1
        if toi == '训练':
            training_count += 1
        elif toi == '推理':
            inference_count += 1
        if series:
            series_counts[series] = series_counts.get(series, 0) + 1
        if vendor:
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
    
    print(f"\n=== Results ===")
    print(f"Total gitcode models: {len(gitcode_models)}")
    print(f"Adapter frameworks: {frameworks}")
    print(f"Adapter hardware: {hardware_counts}")
    print(f"Training: {training_count}, Inference: {inference_count}")
    print(f"Model series: {series_counts}")
    print(f"Model vendors: {vendor_counts}")
    print(f"Output saved to: {output_file}")



class AscendModelCollector:
    def __init__(self, config_file="config.yaml"):
        self.data_dir = "data"
        # 仅修改此处：文件名改为 ascend_model.json
        self.output_file = os.path.join(self.data_dir, "ascend_model.json")

        # 加载配置
        self.config = self.load_config(config_file)

        os.makedirs(self.data_dir, exist_ok=True)

        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "Cookie": COOKIE,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Referer": "https://gitcode.com/",
            "Origin": "https://gitcode.com",
            "X-App-Channel": "gitcode-fe",
            "X-App-Version": "0",
            "X-Device-ID": "unknown",
            "X-Device-Type": "MacOS",
            "X-Network-Type": "4g",
            "X-OS-Version": "Unknown",
            "X-Platform": "web",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
        }

    def load_config(self, config_file):
        """加载配置文件"""
        # 默认配置 - 仅修改文件名
        default_config = {
            "gitcode": {"groups": [], "repositories": []},
            "modelers": {"repositories": []},
            "collection": {
                "output_dir": "data",
                "output_file": "ascend_model.json",
                "deduplicate": False,
                "sort_by_stars": True,
                "log_level": "INFO",
            },
        }

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config:
                print(f"⚠️  配置文件 {config_file} 为空，使用默认配置")
                return default_config

            # 合并配置
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
                elif isinstance(default_config[key], dict):
                    for subkey in default_config[key]:
                        if subkey not in config[key]:
                            config[key][subkey] = default_config[key][subkey]

            return config
        except FileNotFoundError:
            print(f"⚠️  配置文件 {config_file} 不存在，使用默认配置")
            return default_config
        except yaml.YAMLError as e:
            print(f"⚠️  配置文件格式错误: {e}，使用默认配置")
            return default_config
        except Exception as e:
            print(f"⚠️  加载配置文件失败: {e}，使用默认配置")
            return default_config

    def search_gitcode_models(self, page=1, per_page=10):
        """GitCode Web API获取Ascend-SACT分组项目（兼容旧版本）"""
        return self.search_gitcode_models_by_group("Ascend-SACT", page, per_page)

    def search_gitcode_models_by_group(self, org_id, page=1, per_page=10):
        """GitCode Web API获取指定分组项目"""
        url = "https://web-api.gitcode.com/api/v2/groups/{}/projects".format(org_id)
        params = {
            "orgId": org_id,
            "page": page,
            "per_page": per_page,
            "simple": "false",
            "include_subgroups": "true",
            "search": "",
            "with_programming_language": "",
            "order_by": "last_activity_at",
            "sort": "desc",
            "tag": "",
            "archived": "false",
            "repo_type": "1",
        }

        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=30, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("content", []), data.get("total", 0)
            else:
                print(f"  API错误: {resp.status_code}")
                return [], 0
        except Exception as e:
            print(f"  请求失败: {e}")
            return [], 0
    
    def fetch_modelers_data(self, owner=None):
        """获取Modelers社区模型数据"""
        if owner is None:
            # 如果没有指定owner，使用配置中的第一个仓库
            modelers_repos = self.config.get("modelers", {}).get("repositories", [])
            if not modelers_repos:
                print("  ⚠️  Modelers配置为空，跳过")
                return [], 0, "unknown"
            owner = modelers_repos[0].get("owner", "Modelers_Park")

        url = f"https://modelers.cn/server/model/{owner}"
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": f"https://modelers.cn/user/{owner}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        }

        try:
            all_models = []
            total = 0
            page = 1
            seen = set()

            while True:
                params = {"count": "true", "page": page, "pageSize": 50}
                resp = requests.get(url, params=params, headers=headers, timeout=30, verify=False)
                if resp.status_code != 200:
                    print(f"  API错误: {resp.status_code}")
                    break

                data = resp.json()
                payload = data.get("data", {})
                models = payload.get("models", []) or []
                total = payload.get("total", total or len(models))

                new_count = 0
                for m in models:
                    key = str(m.get("id") or "") + "|" + str(m.get("name") or "")
                    if key in seen:
                        continue
                    seen.add(key)
                    all_models.append(m)
                    new_count += 1

                if not models or new_count == 0:
                    break
                if total and len(all_models) >= total:
                    break
                page += 1

            return all_models, total or len(all_models), owner
        except Exception as e:
            print(f"  请求失败: {e}")
            return [], 0, owner

    def parse_repo(self, repo):
        """解析仓库信息"""
        return {
            "id": repo.get("id", ""),
            "name": repo.get("name", ""),
            "full_name": repo.get("path_with_namespace", ""),
            "url": repo.get("web_url", ""),
            "description": repo.get("description", "")
            or repo.get("description_cn", ""),
            "model_name": self.extract_model_name(
                repo.get("name", ""), repo.get("description", "")
            ),
            "model_type": self.classify_model_type(repo.get("description", "")),
            "adapter_status": self.check_adapter_status(repo.get("description", "")),
            "stars": repo.get("star_count", 0),
            "forks": repo.get("forks_count", 0),
            "language": repo.get("language", ""),
            "last_updated": repo.get("last_activity_at", ""),
            "created_at": repo.get("created_at", ""),
            "tags": [t.get("name", "") for t in (repo.get("topic_names") or [])],
            "collected_at": datetime.now().isoformat(),
            "source": "gitcode",
        }

    def parse_modelers(self, model):
        """解析Modelers模型信息"""
        owner = model.get("owner", "")
        name = model.get("name", "")
        full_name = f"{owner}/{name}" if owner and name else name

        return {
            "id": model.get("id", ""),
            "name": name,
            "full_name": full_name,
            "url": f"https://modelers.cn/models/{owner}/{name}",
            "description": model.get("desc", ""),
            "model_name": full_name,
            "model_type": self.classify_model_type(model.get("desc", "")),
            "adapter_status": self.check_adapter_status(model.get("desc", "")),
            "stars": model.get("praise_count", 0),
            "forks": model.get("download_count", 0),
            "language": "",
            "last_updated": model.get("updated_at", ""),
            "created_at": model.get("created_at", ""),
            "tags": model.get("tags", []) or [],
            "collected_at": datetime.now().isoformat(),
            "source": "modelers",
        }

    def extract_model_name(self, name, description):
        """提取模型名"""
        combined = f"{name} {description}".lower()

        models = [
            "resnet", "yolo", "bert", "gpt", "vit", "efficientnet", "llama", "chatglm", "qwen", "baichuan",
            "stable diffusion", "diffusion", "transformer", "lstm", "cnn", "gan", "mask rcnn", "faster rcnn",
            "ssd", "retinanet", "vgg", "alexnet", "mobilenet", "swintransformer", "clip", "sam", "segment anything",
            "whisper", "pangu", "pangu2", "openpangu", "qwen2", "qwen3", "llama2", "llama3", "llama3.1", "llama3.5",
            "asr", "tts", "speech", "audio", "bert4rec", "mae", "dino", "llava", "mixtral",
        ]

        for m in models:
            if m in combined:
                return m.upper()

        return name if name else "未知"

    def classify_model_type(self, description):
        """分类模型类型"""
        desc = (description or "").lower()

        if any(kw in desc for kw in ["class", "classification", "分类", "cv"]):
            return "图像分类"
        elif any(kw in desc for kw in ["detect", "detection", "检测", "yolo"]):
            return "目标检测"
        elif any(kw in desc for kw in ["segment", "分割", "mask"]):
            return "图像分割"
        elif any(kw in desc for kw in ["gan", "diffusion", "生成", "stable", "文生图", "文生文"]):
            return "生成模型"
        elif any(kw in desc for kw in ["nlp", "自然语言", "文本", "llm", "language", "chat", "大模型", "sft", "rl", "微调", "对话", "pangu", "qwen", "llama", "chatglm"]):
            return "NLP模型"
        elif any(kw in desc for kw in ["recommend", "推荐", "recsys"]):
            return "推荐模型"
        elif any(kw in desc for kw in ["speech", "audio", "语音", "asr", "tts", "whisper"]):
            return "语音模型"
        elif any(kw in desc for kw in ["benchmark", "评测", "评估"]):
            return "评测框架"
        elif any(kw in desc for kw in ["train", "训练", "sft"]):
            return "训练框架"
        elif any(kw in desc for kw in ["infer", "推理", "部署"]):
            return "推理框架"
        elif any(kw in desc for kw in ["docker", "容器", "镜像"]):
            return "容器镜像"
        elif any(kw in desc for kw in ["test", "测试"]):
            return "测试工具"
        else:
            return "其他"

    def check_adapter_status(self, description):
        """检查适配状态"""
        desc = (description or "").lower()

        if any(kw in desc for kw in ["昇腾", "ascend", "npu", "适配", "adapter", "cann", "torch_npu"]):
            return "已适配"
        elif any(kw in desc for kw in ["移植", "porting", "迁移"]):
            return "移植中"
        else:
            return "待验证"

    def deduplicate(self, repos):
            """
            方案 A：区分平台的去重逻辑
            允许不同平台（Source）存在同名的 full_name。
            """
            seen = set()
            unique = []
            for repo in repos:
                # 1. 获取模型名称
                name = repo.get("full_name") or repo.get("name")
                # 2. 获取来源平台（gitcode 或 modelers）
                source = repo.get("source", "unknown")
                
                # 3. 将【平台 + 名称】组合成唯一的 Key
                # 例如: "gitcode|Ascend/resnet50" 与 "modelers|Ascend/resnet50" 将被视为不同项
                key = f"{source}|{name}"
                
                if name and key not in seen:
                    seen.add(key)
                    unique.append(repo)
            
            return unique

    def run(self):
        """运行采集"""
        print("=" * 60)
        print("开始采集昇腾适配模型数据...")
        print(f"配置文件: {self.config.get('collection', {}).get('config_file', '默认配置')}")
        print("=" * 60)

        all_repos = []
        gitcode_total = 0
        modelers_total = 0

        # 1. 采集GitCode数据
        gitcode_config = self.config.get("gitcode", {})
        gitcode_groups = gitcode_config.get("groups", [])
        gitcode_repos = gitcode_config.get("repositories", [])

        if gitcode_groups or gitcode_repos:
            print("\n📦 采集 GitCode 数据...")
            for group in gitcode_groups:
                group_name = group.get("name", "未知分组")
                org_id = group.get("org_id", group_name)
                print(f"\n  采集分组: {group_name} (org_id: {org_id})")

                repos, total = self.search_gitcode_models_by_group(org_id, page=1, per_page=10)
                if total == 0:
                    continue

                print(f"    总数: {total} 个仓库")
                gitcode_total += total

                per_page = 20
                total_pages = (total + per_page - 1) // per_page
                for page in range(1, total_pages + 1):
                    repos, _ = self.search_gitcode_models_by_group(org_id, page=page, per_page=per_page)
                    if not repos: break
                    for repo in repos:
                        all_repos.append(self.parse_repo(repo))
                    time.sleep(0.3)

        # 2. 采集Modelers数据
        modelers_config = self.config.get("modelers", {})
        modelers_repos = modelers_config.get("repositories", [])

        if modelers_repos:
            print("\n🤖 采集 Modelers 数据...")
            seen_owners = set()
            for repo_config in modelers_repos:
                owner = repo_config.get("owner", "")
                if not owner or owner in seen_owners: continue
                seen_owners.add(owner)
                print(f"\n  采集仓库: {owner}")
                models, total, _ = self.fetch_modelers_data(owner)
                if total > 0:
                    modelers_total += total
                    for model in models:
                        all_repos.append(self.parse_modelers(model))

        # 3. 数据处理 (保留你原版的去重和排序)
        collection_config = self.config.get("collection", {})
        if collection_config.get("deduplicate", False) or True: # 原版逻辑强制了去重
            all_repos = self.deduplicate(all_repos)

        if collection_config.get("sort_by_stars", True):
            all_repos.sort(key=lambda x: x.get("stars", 0), reverse=True)

        # 4. 保存数据 - 仅修改文件名
        output_dir = collection_config.get("output_dir", "data")
        output_file = "ascend_model.json"
        self.output_file = os.path.join(output_dir, output_file)
        os.makedirs(output_dir, exist_ok=True)

        data = {
            "collected_at": datetime.now().isoformat(),
            "total_count": len(all_repos),
            "gitcode_total": gitcode_total,
            "modelers_total": modelers_total,
            "config_source": "repositories.yaml",
            "models": all_repos,
        }

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print(f"🎉 采集完成! 💾 数据已保存至: {self.output_file}")
        print("=" * 60)
        update_framework_hardware()
        return data

if __name__ == "__main__":
    AscendModelCollector().run()
