#!/usr/bin/env python3
import re

SERIES_RULES = [
    (r"^GLM|^glm|zai-org-GLM", "GLM"),
    (r"^QwQ[-_]", "QwQ"),
    (r"^Qwen3\.5", "Qwen3.5"),
    (r"^Qwen3[-_]|^qwen3[-_]", "Qwen3"),
    (r"^Qwen2\.5|^qwen2\.5", "Qwen2.5"),
    (r"^Qwen2[-_]|^qwen2_", "Qwen2"),
    (r"^Qwen[-_]|^qwen[-_]|^qwen_", "Qwen"),
    (r"^DeepSeek|^deepseek", "DeepSeek"),
    (r"^openPangu|^Pangu", "openPangu"),
    (r"^MiniMax", "MiniMax"),
    (r"^MiniCPM", "MiniCPM"),
    (r"^hunyuan|^hy-", "Hunyuan"),
    (r"^Xiaomi", "Xiaomi"),
    (r"^Intern", "Intern"),
    (r"^Yi[-_]", "Yi"),
    (r"^Llama", "Llama"),
    (r"^Gemma", "Gemma"),
    (r"^GPT[-_]", "GPT"),
    (r"^LLaVA", "LLaVA"),
    (r"^Whisper", "Whisper"),
    (r"^Flux", "Flux"),
    (r"^Wan", "Wan"),
    (r"^CosyVoice|^Fun-CosyVoice", "CosyVoice"),
    (r"^PaddleOCR", "PaddleOCR"),
    (r"^SenseVoice", "SenseVoice"),
    (r"^ERNIE", "ERNIE"),
    (r"^YOLO", "YOLO"),
    (r"^bge-", "BGE"),
    (r"^StepFun|^GOT-OCR", "StepFun"),
]

VENDOR_MAPPING = {
    "GLM": "智谱AI",
    "Qwen": "阿里云",
    "QwQ": "阿里云",
    "Qwen3": "阿里云",
    "Qwen3.5": "阿里云",
    "Qwen2.5": "阿里云",
    "Qwen2": "阿里云",
    "CosyVoice": "阿里云",
    "SenseVoice": "阿里云",
    "DeepSeek": "深度求索",
    "openPangu": "华为",
    "MiniMax": "MiniMax",
    "MiniCPM": "面壁智能",
    "Xiaomi": "小米",
    "PaddleOCR": "百度",
    "PP-OCR": "百度",
    "ERNIE": "百度",
    "Hunyuan": "腾讯",
    "Intern": "上海人工智能实验室",
    "Yi": "零一万物",
    "Llama": "Meta",
    "Gemma": "Google",
    "translategemma": "Google",
    "GPT": "OpenAI",
    "Whisper": "OpenAI",
    "LLaVA": "LLaVA团队",
    "Flux": "BlackForestLabs",
    "Wan": "字节跳动",
    "Index-TTS": "字节跳动",
    "dots.ocr": "字节跳动",
    "LatentSync": "字节跳动",
    "MOSS": "复旦大学",
    "WeNet": "出门问问",
    "StepFun": "阶跃星辰",
    "GOT-OCR": "阶跃星辰",
    "Kimi": "月之暗面",
    "YOLO": "Ultralytics",
    "BGE": "BAAI",
    "Ovis": "阿联酋MBZUAI",
    "MapFormer": "MIT",
    "MinerU": "Magic Data",
}

def detect_model_series(model_name):
    """根据模型名称检测所属系列"""
    if not model_name:
        return None
    
    for pattern, series in SERIES_RULES:
        if re.match(pattern, model_name, re.IGNORECASE):
            return series
    
    return "Unknown"

def detect_model_vendor(series):
    """根据系列检测供应商"""
    if not series:
        return None
    
    return VENDOR_MAPPING.get(series)

def detect_series_and_vendor(model_name):
    """检测模型系列和供应商
    
    Returns:
        dict: {"series": str, "vendor": str}
    """
    series = detect_model_series(model_name)
    vendor = detect_model_vendor(series)
    
    return {
        "series": series or "Unknown",
        "vendor": vendor or "Unknown"
    }

def check_model_series_vendor(model):
    """检查模型的系列和供应商
    
    按顺序检查：
    1. name字段
    2. full_name字段  
    3. description字段
    """
    name = model.get("name", "")
    full_name = model.get("full_name", "")
    description = model.get("description", "") or ""
    
    search_sources = [name, full_name, description]
    
    for source in search_sources:
        if source:
            result = detect_series_and_vendor(source)
            if result and result.get("series") != "Unknown":
                return result
    
    if name:
        return detect_series_and_vendor(name)
    
    return {"series": "Unknown", "vendor": "Unknown"}

if __name__ == "__main__":
    test_cases = [
        "qwen3-tts-12hz-0.6b-base",
        "MiniCPM-V-4_5",
        "GLM4.5-AIR",
        "DeepSeek-V3",
        "Llama3-70B",
    ]
    
    for tc in test_cases:
        result = detect_series_and_vendor(tc)
        print(f"{tc} -> {result}")
