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

# Cookie信息
COOKIE = "uuid_tt_dd=10_23424968500-1769827168312-980636; c_gitcode_um=-; gitcode_first_time=2026-01-31%2010:39:28; gitcode_theme=white; _frid=4ff161a6d50e4031a4ef36ab5edba0f6; GITCODE_REFRESH_TOKEN=eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI2OGY3MDRiYzdhNGM3NjM4MzFkOTQ5MGEiLCJzdWIiOiJtaW5nLXNoZW4iLCJhdXRob3JpdGllcyI6W10sIm9iamVjdElkIjoiNjk5MDEzY2Y2ODY1NmQwMTEwNGNkN2I2IiwiaWF0IjoxNzcxMDQ5OTM1LCJleHAiOjE3NzYyMzM5MzV9.FaCera7wC3o0-xDF4Zkr9nD4Oswqb27BodJkN4PvzqZxyWmqhAfCuTC65yForgKqTz2da0cKs5GNonZ_rH5_Xg; GitCodeUserName=ming-shen; HMACCOUNT=5263F4C464578DF0; HWWAFSESTIME=1772417712948; BENSESSCC_TAG=10_23424968500-1769827168312-980636; GITCODE_ACCESS_TOKEN=eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI2OGY3MDRiYzdhNGM3NjM4MzFkOTQ5MGEiLCJzdWIiOiJtaW5nLXNoZW4iLCJhdXRob3JpdGllcyI6W10sIm9iamVjdElkIjoiNjk5MDEzY2Y2ODY1NmQwMTEwNGNkN2I2IiwiaWF0IjoxNzcxMDQ5OTM1LCJleHAiOjE3NzI1MDQxMTV9.WzqzdeQ4FavSBigfB5oVNMG0A4-kiBmqwufQ_K2q4EAty1-flwfTXVkzGTMimudOVuLuBjJaRK8NUJWzauMWHQ; HWWAFSESID=6ba6f136f22d5e09a0a; pageSize={%22global-pager%22:10}; gitcode_lang=zh; _fr_ssid=8cc433596ce048e891f5a2e7b18fa8cd; Hm_lvt_62047c952451105d57bab2c4af9ce85b=1771049716,1772095578,1772417715; c_gitcode_fref=http://localhost:8080/; UnsafeGitCodeUserName=ming-shen; c_gitcode_rid=1772434221353_418077; last-repo-id=8795146; Hm_lpvt_62047c952451105d57bab2c4af9ce85b=1772434479"

class AscendModelCollector:
    def __init__(self, config_file="config.yaml"):
        self.data_dir = "data"
        # 修正：将文件名改为 ascend_model.json 以符合你的预想
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
        default_config = {
            "gitcode": {"groups": [], "repositories": []},
            "modelers": {"repositories": []},
            "collection": {
                "output_dir": "data",
                "output_file": "ascend_model.json", # 修正点
                "deduplicate": False,
                "sort_by_stars": True,
                "log_level": "INFO",
            },
        }
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if not config: return default_config
            # 合并配置
            for key in default_config:
                if key not in config: config[key] = default_config[key]
                elif isinstance(default_config[key], dict):
                    for subkey in default_config[key]:
                        if subkey not in config[key]:
                            config[key][subkey] = default_config[key][subkey]
            return config
        except:
            return default_config

    def search_gitcode_models_by_group(self, org_id, page=1, per_page=10):
        url = "https://web-api.gitcode.com/api/v2/groups/{}/projects".format(org_id)
        params = {
            "orgId": org_id, "page": page, "per_page": per_page, "simple": "false",
            "include_subgroups": "true", "order_by": "last_activity_at", "sort": "desc",
            "archived": "false", "repo_type": "1",
        }
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("content", []), data.get("total", 0)
            return [], 0
        except:
            return [], 0

    def fetch_modelers_data(self, owner=None):
        if owner is None:
            modelers_repos = self.config.get("modelers", {}).get("repositories", [])
            if not modelers_repos: return [], 0, "unknown"
            owner = modelers_repos[0].get("owner", "Modelers_Park")
        url = f"https://modelers.cn/server/model/{owner}"
        headers = {"Accept": "*/*", "User-Agent": "Mozilla/5.0"}
        try:
            all_models = []; total = 0; page = 1; seen = set()
            while True:
                params = {"count": "true", "page": page, "pageSize": 50}
                resp = requests.get(url, params=params, headers=headers, timeout=30)
                if resp.status_code != 200: break
                payload = resp.json().get("data", {})
                models = payload.get("models", []) or []
                total = payload.get("total", total or len(models))
                new_count = 0
                for m in models:
                    key = str(m.get("id") or "") + "|" + str(m.get("name") or "")
                    if key not in seen:
                        seen.add(key); all_models.append(m); new_count += 1
                if not models or new_count == 0 or len(all_models) >= total: break
                page += 1
            return all_models, total or len(all_models), owner
        except:
            return [], 0, owner

    def parse_repo(self, repo):
        return {
            "id": repo.get("id", ""), "name": repo.get("name", ""),
            "full_name": repo.get("path_with_namespace", ""),
            "url": repo.get("web_url", ""), "description": repo.get("description", "") or repo.get("description_cn", ""),
            "model_name": self.extract_model_name(repo.get("name", ""), repo.get("description", "")),
            "model_type": self.classify_model_type(repo.get("description", "")),
            "adapter_status": self.check_adapter_status(repo.get("description", "")),
            "stars": repo.get("star_count", 0), "forks": repo.get("forks_count", 0),
            "language": repo.get("language", ""), "last_updated": repo.get("last_activity_at", ""),
            "created_at": repo.get("created_at", ""), "tags": [t.get("name", "") for t in (repo.get("topic_names") or [])],
            "collected_at": datetime.now().isoformat(), "source": "gitcode",
        }

    def parse_modelers(self, model):
        owner = model.get("owner", ""); name = model.get("name", "")
        full_name = f"{owner}/{name}" if owner and name else name
        return {
            "id": model.get("id", ""), "name": name, "full_name": full_name,
            "url": f"https://modelers.cn/models/{owner}/{name}", "description": model.get("desc", ""),
            "model_name": full_name, "model_type": self.classify_model_type(model.get("desc", "")),
            "adapter_status": self.check_adapter_status(model.get("desc", "")),
            "stars": model.get("praise_count", 0), "forks": model.get("download_count", 0),
            "last_updated": model.get("updated_at", ""), "created_at": model.get("created_at", ""),
            "tags": model.get("tags", []) or [], "collected_at": datetime.now().isoformat(), "source": "modelers",
        }

    def extract_model_name(self, name, description):
        combined = f"{name} {description}".lower()
        models = ["resnet", "yolo", "bert", "gpt", "vit", "llama", "chatglm", "qwen", "baichuan", "stable diffusion"]
        for m in models:
            if m in combined: return m.upper()
        return name if name else "未知"

    def classify_model_type(self, description):
        desc = (description or "").lower()
        if any(kw in desc for kw in ["class", "分类"]): return "图像分类"
        if any(kw in desc for kw in ["detect", "检测", "yolo"]): return "目标检测"
        if any(kw in desc for kw in ["nlp", "语言", "llm", "chat"]): return "NLP模型"
        if any(kw in desc for kw in ["gan", "diffusion", "生成"]): return "生成模型"
        return "其他"

    def check_adapter_status(self, description):
        desc = (description or "").lower()
        if any(kw in desc for kw in ["昇腾", "ascend", "npu", "适配"]): return "已适配"
        return "待验证"

    def deduplicate(self, repos):
        seen = set(); unique = []
        for repo in repos:
            key = repo.get("full_name") or repo.get("name")
            if key and key not in seen:
                seen.add(key); unique.append(repo)
        return unique

    def run(self):
        print("开始采集昇腾适配模型数据...")
        all_repos = []; gitcode_total = 0; modelers_total = 0
        
        # GitCode 采集
        gitcode_groups = self.config.get("gitcode", {}).get("groups", [])
        for group in gitcode_groups:
            org_id = group.get("org_id", group.get("name"))
            repos, total = self.search_gitcode_models_by_group(org_id)
            gitcode_total += total
            for repo in repos: all_repos.append(self.parse_repo(repo))
            
        # Modelers 采集
        modelers_repos = self.config.get("modelers", {}).get("repositories", [])
        for repo_config in modelers_repos:
            owner = repo_config.get("owner")
            if owner:
                models, total, _ = self.fetch_modelers_data(owner)
                modelers_total += total
                for model in models: all_repos.append(self.parse_modelers(model))

        # 处理并保存
        all_repos = self.deduplicate(all_repos)
        if self.config.get("collection", {}).get("sort_by_stars", True):
            all_repos.sort(key=lambda x: x.get("stars", 0), reverse=True)

        data = {
            "collected_at": datetime.now().isoformat(),
            "total_count": len(all_repos),
            "models": all_repos,
        }
        
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"采集完成！总数: {len(all_repos)}，已保存至 {self.output_file}")
        return data

if __name__ == "__main__":
    collector = AscendModelCollector()
    collector.run()
