#!/usr/bin/env python3
"""
昇腾适配模型数据采集器 - GitCode Web API版
使用GitCode Web API获取Ascend模型仓库数据
支持多仓库配置采集
新增：
1. 抓取 GitCode raw README
2. 提取 README 中“安装 / 部署”相关章节完整原文
3. 写入到 ascend_model.json
"""

import json
import os
import re
import requests
import time
import yaml
from datetime import datetime

requests.packages.urllib3.disable_warnings()

# GitCode Web API认证信息（按你的要求，保留硬编码）
BEARER_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI2OGY3MDRiYzdhNGM3NjM4MzFkOTQ5MGEiLCJzdWIiOiJtaW5nLXNoZW4iLCJhdXRob3JpdGllcyI6W10sIm9iamVjdElkIjoiNjk5MDEzY2Y2ODY1NmQwMTEwNGNkN2I2IiwiaWF0IjoxNzcxMDQ5OTM1LCJleHAiOjE3NzI1MDQxMTV9.WzqzdeQ4FavSBigfB5oVNMG0A4-kiBmqwufQ_K2q4EAty1-flwfTXVkzGTMimudOVuLuBjJaRK8NUJWzauMWHQ"

COOKIE = "uuid_tt_dd=10_23424968500-1769827168312-980636; c_gitcode_um=-; gitcode_first_time=2026-01-31%2010:39:28; gitcode_theme=white; _frid=4ff161a6d50e4031a4ef36ab5edba0f6; GITCODE_REFRESH_TOKEN=eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI2OGY3MDRiYzdhNGM3NjM4MzFkOTQ5MGEiLCJzdWIiOiJtaW5nLXNoZW4iLCJhdXRob3JpdGllcyI6W10sIm9iamVjdElkIjoiNjk5MDEzY2Y2ODY1NmQwMTEwNGNkN2I2IiwiaWF0IjoxNzcxMDQ5OTM1LCJleHAiOjE3NzYyMzM5MzV9.FaCera7wC3o0-xDF4Zkr9nD4Oswqb27BodJkN4PvzqZxyWmqhAfCuTC65yForgKqTz2da0cKs5GNonZ_rH5_Xg; GitCodeUserName=ming-shen; HMACCOUNT=5263F4C464578DF0; HWWAFSESTIME=1772417712948; BENSESSCC_TAG=10_23424968500-1769827168312-980636; GITCODE_ACCESS_TOKEN=eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI2OGY3MDRiYzdhNGM3NjM4MzFkOTQ5MGEiLCJzdWIiOiJtaW5nLXNoZW4iLCJhdXRob3JpdGllcyI6W10sIm9iamVjdElkIjoiNjk5MDEzY2Y2ODY1NmQwMTEwNGNkN2I2IiwiaWF0IjoxNzcxMDQ5OTM1LCJleHAiOjE3NzI1MDQxMTV9.WzqzdeQ4FavSBigfB5oVNMG0A4-kiBmqwufQ_K2q4EAty1-flwfTXVkzGTMimudOVuLuBjJaRK8NUJWzauMWHQ; HWWAFSESID=6ba6f136f22d5e09a0a; pageSize={%22global-pager%22:10}; gitcode_lang=zh; _fr_ssid=8cc433596ce048e891f5a2e7b18fa8cd; Hm_lvt_62047c952451105d57bab2c4af9ce85b=1771049716,1772095578,1772417715; c_gitcode_fref=http://localhost:8080/; UnsafeGitCodeUserName=ming-shen; c_gitcode_rid=1772434221353_418077; last-repo-id=8795146; Hm_lpvt_62047c952451105d57bab2c4af9ce85b=1772434479"


class AscendModelCollector:
    def __init__(self, config_file="config.yaml"):
        self.data_dir = "data"
        self.output_file = os.path.join(self.data_dir, "ascend_model.json")
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

        self.raw_headers = {
            "Accept": "text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": COOKIE,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Referer": "https://gitcode.com/",
        }

        self.modelers_headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://modelers.cn/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        }

    def load_config(self, config_file):
        """加载配置文件"""
        default_config = {
            "gitcode": {"groups": [], "repositories": []},
            "modelers": {"repositories": []},
            "collection": {
                "output_dir": "data",
                "output_file": "ascend_model.json",
                "deduplicate": False,
                "sort_by_stars": True,
                "log_level": "INFO",
                "fetch_readme": True,
                "fetch_readme_for_modelers": False,
            },
        }

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config:
                print(f"⚠️  配置文件 {config_file} 为空，使用默认配置")
                return default_config

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
        """兼容旧入口"""
        return self.search_gitcode_models_by_group("Ascend-SACT", page, per_page)

    def search_gitcode_models_by_group(self, org_id, page=1, per_page=10):
        """GitCode Web API获取指定分组项目"""
        url = f"https://web-api.gitcode.com/api/v2/groups/{org_id}/projects"
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
            modelers_repos = self.config.get("modelers", {}).get("repositories", [])
            if not modelers_repos:
                print("  ⚠️  Modelers配置为空，跳过")
                return [], 0, "unknown"
            owner = modelers_repos[0].get("owner", "Modelers_Park")

        url = f"https://modelers.cn/server/model/{owner}"
        headers = dict(self.modelers_headers)
        headers["Referer"] = f"https://modelers.cn/user/{owner}"

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
        """解析GitCode仓库信息"""
        description = repo.get("description", "") or repo.get("description_cn", "")

        return {
            "id": repo.get("id", ""),
            "name": repo.get("name", ""),
            "full_name": repo.get("path_with_namespace", ""),
            "url": repo.get("web_url", ""),
            "description": description,
            "model_name": self.extract_model_name(repo.get("name", ""), description),
            "model_type": self.classify_model_type(description),
            "adapter_status": self.check_adapter_status(description),
            "stars": repo.get("star_count", 0),
            "forks": repo.get("forks_count", 0),
            "language": repo.get("language", ""),
            "last_updated": repo.get("last_activity_at", ""),
            "created_at": repo.get("created_at", ""),
            "tags": [t.get("name", "") for t in (repo.get("topic_names") or [])],
            "collected_at": datetime.now().isoformat(),
            "source": "gitcode",

            # README章节信息（新增）
            "doc_fetch_status": "not_fetched",
            "doc_readme_length": 0,
            "doc_source": {
                "readme_url": "",
                "fetched_at": "",
            },
            "doc_sections": {
                "install": [],
                "deployment": [],
            },
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

            # 先保留空结构，便于统一
            "doc_fetch_status": "not_fetched",
            "doc_readme_length": 0,
            "doc_source": {
                "readme_url": "",
                "fetched_at": "",
            },
            "doc_sections": {
                "install": [],
                "deployment": [],
            },
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

    def build_raw_readme_urls(self, repo_url):
        """
        将 GitCode 仓库 URL 转成候选 raw README URL 列表
        例：
        https://gitcode.com/vLLM_Ascend/Qwen3.5
        -> https://raw.gitcode.com/vLLM_Ascend/Qwen3.5/raw/main/README.md
        """
        if not repo_url or "gitcode.com/" not in repo_url:
            return []

        try:
            path = repo_url.split("gitcode.com/", 1)[1].strip("/")
            if not path:
                return []

            candidates = [
                f"https://raw.gitcode.com/{path}/raw/main/README.md",
                f"https://raw.gitcode.com/{path}/raw/master/README.md",
                f"https://raw.gitcode.com/{path}/raw/main/readme.md",
                f"https://raw.gitcode.com/{path}/raw/master/readme.md",
                f"https://raw.gitcode.com/{path}/raw/main/README_CN.md",
                f"https://raw.gitcode.com/{path}/raw/master/README_CN.md",
                f"https://raw.gitcode.com/{path}/raw/main/README_zh.md",
                f"https://raw.gitcode.com/{path}/raw/master/README_zh.md",
            ]
            return candidates
        except Exception:
            return []

    def fetch_raw_readme(self, repo_url):
        """获取 raw README 内容，返回 (text, final_url, status)"""
        candidate_urls = self.build_raw_readme_urls(repo_url)
        if not candidate_urls:
            return "", "", "unsupported_url"

        for url in candidate_urls:
            try:
                resp = requests.get(url, headers=self.raw_headers, timeout=30, verify=False)
                if resp.status_code == 200:
                    text = resp.text or ""
                    if text.strip():
                        return text, url, "success"
                elif resp.status_code in (404, 403):
                    continue
            except Exception as e:
                print(f"    README抓取失败: {url}, err={e}")
                continue

        return "", "", "not_found"

    def split_markdown_sections(self, markdown_text):
        """
        按 markdown 标题切分章节
        返回:
        [
          {"title": "...", "level": 2, "content": "..."},
          ...
        ]
        """
        if not markdown_text:
            return []

        lines = markdown_text.splitlines()
        sections = []
        current = None
        heading_re = re.compile(r"^(#{1,6})\s+(.*)$")

        for line in lines:
            m = heading_re.match(line)
            if m:
                if current:
                    current["content"] = "\n".join(current["content"]).strip()
                    sections.append(current)

                current = {
                    "title": m.group(2).strip(),
                    "level": len(m.group(1)),
                    "content": [],
                }
            else:
                if current is None:
                    current = {
                        "title": "__root__",
                        "level": 0,
                        "content": [],
                    }
                current["content"].append(line)

        if current:
            current["content"] = "\n".join(current["content"]).strip()
            sections.append(current)

        return sections

    def extract_doc_sections(self, markdown_text):
        """
        从 README 中提取安装、部署相关章节原文
        """
        sections = self.split_markdown_sections(markdown_text)

        install_keywords = [
            "安装", "环境安装", "环境准备", "安装说明",
            "installation", "install", "setup", "requirements"
        ]
        deployment_keywords = [
            "部署", "单节点部署", "多节点部署", "模型部署", "推理", "运行",
            "deployment", "deploy", "inference", "serving"
        ]

        result = {
            "install": [],
            "deployment": []
        }

        for sec in sections:
            title = (sec.get("title") or "").strip()
            title_lower = title.lower()

            if any(k.lower() in title_lower for k in install_keywords):
                result["install"].append({
                    "title": sec["title"],
                    "level": sec["level"],
                    "content": sec["content"]
                })

            if any(k.lower() in title_lower for k in deployment_keywords):
                result["deployment"].append({
                    "title": sec["title"],
                    "level": sec["level"],
                    "content": sec["content"]
                })

        return result

    def enrich_repo_with_readme_sections(self, item):
        """给 GitCode 仓库补充 README 中的安装/部署章节"""
        repo_url = item.get("url", "")
        readme_text, final_url, status = self.fetch_raw_readme(repo_url)

        item["doc_fetch_status"] = status
        item["doc_source"] = {
            "readme_url": final_url,
            "fetched_at": datetime.now().isoformat() if status == "success" else "",
        }
        item["doc_readme_length"] = len(readme_text) if readme_text else 0

        if readme_text:
            item["doc_sections"] = self.extract_doc_sections(readme_text)
        else:
            item["doc_sections"] = {
                "install": [],
                "deployment": [],
            }

        return item

    def deduplicate(self, repos):
        """
        区分平台的去重逻辑
        允许不同平台（source）存在同名的 full_name
        """
        seen = set()
        unique = []

        for repo in repos:
            name = repo.get("full_name") or repo.get("name")
            source = repo.get("source", "unknown")
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

        collection_config = self.config.get("collection", {})
        fetch_readme = collection_config.get("fetch_readme", True)
        fetch_readme_for_modelers = collection_config.get("fetch_readme_for_modelers", False)

        # 1. 采集 GitCode 数据
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
                    if not repos:
                        break

                    print(f"    第 {page}/{total_pages} 页，抓到 {len(repos)} 个仓库")

                    for repo in repos:
                        item = self.parse_repo(repo)

                        if fetch_readme:
                            item = self.enrich_repo_with_readme_sections(item)
                            print(
                                f"      - {item.get('full_name') or item.get('name')} "
                                f"| README: {item.get('doc_fetch_status')} "
                                f"| install={len(item.get('doc_sections', {}).get('install', []))} "
                                f"| deployment={len(item.get('doc_sections', {}).get('deployment', []))}"
                            )

                        all_repos.append(item)
                        time.sleep(0.2)

                    time.sleep(0.3)

            # 可选：单独配置的 GitCode repositories 入口（当前仅预留）
            # 你现在原代码没真正消费 gitcode.repositories，这里不主动扩展逻辑，避免多做。

        # 2. 采集 Modelers 数据
        modelers_config = self.config.get("modelers", {})
        modelers_repos = modelers_config.get("repositories", [])

        if modelers_repos:
            print("\n🤖 采集 Modelers 数据...")
            seen_owners = set()

            for repo_config in modelers_repos:
                owner = repo_config.get("owner", "")
                if not owner or owner in seen_owners:
                    continue
                seen_owners.add(owner)

                print(f"\n  采集仓库: {owner}")
                models, total, _ = self.fetch_modelers_data(owner)
                if total > 0:
                    modelers_total += total
                    for model in models:
                        item = self.parse_modelers(model)

                        # 当前默认不对 Modelers 抓 README，避免引入额外不确定性
                        if fetch_readme_for_modelers:
                            pass

                        all_repos.append(item)

        # 3. 数据处理
        if collection_config.get("deduplicate", False) or True:
            all_repos = self.deduplicate(all_repos)

        if collection_config.get("sort_by_stars", True):
            all_repos.sort(key=lambda x: x.get("stars", 0), reverse=True)

        # 4. 保存数据
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
        return data


if __name__ == "__main__":
    AscendModelCollector().run()
