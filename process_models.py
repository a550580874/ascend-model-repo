#!/usr/bin/env python3
import json
import re
import time
from urllib.parse import urlparse
import subprocess

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

def main():
    input_file = "./data/ascend_model.json"
    output_file = "./ascend_model_with_adapter.json"
    
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

if __name__ == "__main__":
    main()
