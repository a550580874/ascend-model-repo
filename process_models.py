#!/usr/bin/env python3
import json
import re
import time
from urllib.parse import urlparse
import subprocess
import random

from model_series_vendor_detector import check_model_series_vendor

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
    """最原始的 raw url 拼接方式（已被证实有效）"""
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) >= 2:
        owner, repo = path_parts[0], path_parts[1]
        return f"https://raw.gitcode.com/{owner}/{repo}/raw/main/README.md"
    return None

def fetch_readme_content(url, max_retries=3):
    """回归 curl 方案，加入极致的 Debug 打印信息"""
    raw_url = get_raw_readme_url(url)
    if not raw_url:
        return None
    
    for attempt in range(max_retries):
        try:
            # -sL: 静默并跟随重定向
            # -k: 忽略 SSL 证书校验
            # --max-time: 防止网络卡死
            cmd = ['curl', '-sL', '-k', '--max-time', '15', raw_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            
            if result.returncode == 0:
                content = result.stdout
                # === 核心调试打印 ===
                # 把回车换行去掉，截取前 150 个字符预览
                preview = content[:150].replace('\n', ' ').strip()
                print(f"      [Debug] curl 成功 (0). 拿到 {len(content)} 字节. 预览: {preview}")
                
                if len(content) > 100:
                    # 如果抓到了 HTML 标签，说明是被防火墙拦截了，并非真实的 Markdown
                    if "<html" in content.lower() or "<!doctype" in content.lower():
                        print(f"      [警告] 抓到的疑似网页/防火墙拦截页，不是 README！")
                    return content
                else:
                    print(f"      [警告] 内容过短，可能被拦截或文件为空。")
            else:
                # 打印出标准错误流里的信息
                err_msg = result.stderr.strip()[:100] if result.stderr else "无错误日志"
                print(f"      [curl错误] 第 {attempt+1} 次失败，退出码: {result.returncode}, 日志: {err_msg}")
                
        except subprocess.TimeoutExpired:
            print(f"      [超时] 第 {attempt+1} 次执行 curl 卡死")
        except Exception as e:
            print(f"      [异常] 第 {attempt+1} 次执行出错: {e}")
            
        # 失败后随机休眠再重试
        if attempt < max_retries - 1:
            sleep_time = random.uniform(2.0, 4.0)
            print(f"      -> 等待 {sleep_time:.1f} 秒后重试...")
            time.sleep(sleep_time)
            
    return None

def detect_adapter_framework(content):
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
    name = model.get("name", "")
    full_name = model.get("full_name", "")
    description = model.get("description", "") or ""
    url = model.get("url", "")
    
    search_sources = [name, full_name, description]
    
    for source in search_sources:
        if source:
            fw, toi = detect_adapter_framework(source)
            if fw:
                return fw, toi
                
    readme_content = fetch_readme_content(url)
    if readme_content:
        return detect_adapter_framework(readme_content)
    
    return None, None

def detect_adapter_hardware(content):
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
    name = model.get("name", "")
    full_name = model.get("full_name", "")
    description = model.get("description", "") or ""
    url = model.get("url", "")
    
    search_sources = [name, full_name, description]
    
    for source in search_sources:
        if source:
            hw = detect_adapter_hardware(source)
            if hw:
                return hw
                
    readme_content = fetch_readme_content(url)
    if readme_content:
        return detect_adapter_hardware(readme_content)
    
    return None

def main():
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
        
        # 增加随机休眠，避免被 Actions 环境或防火墙判断为高频攻击
        time.sleep(random.uniform(1.0, 2.5))
        
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

if __name__ == "__main__":
    main()
