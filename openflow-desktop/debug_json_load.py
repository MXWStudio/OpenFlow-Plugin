import re
import json
import os

def load_check(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw = f.read()
        
        # 1. 移除 UTF-8 BOM (\ufeff)
        clean = raw.lstrip('\ufeff')
        
        # 2. 移除 // 单行注释
        clean = re.sub(r'(?<![:/])//.*', '', clean)
        
        # 3. 使用 strict=False 允许控制字符
        data = json.loads(clean, strict=False)
        print(f"Successfully loaded {len(data)} items from JSON.")
        
        # Check specific items I modified
        for item in data:
            proj = item.get("项目名称", "")
            comp = item.get("公司名称", "")
            group = item.get("集团", "")
            if proj in ["夏日冰淇淋", "指尖挑战", "旋转飞盘"]:
                print(f"Project: {proj}, Company: {comp}, Group: {group}")
                if comp != "游梦" or group != "游梦":
                    print(f"ERROR: Incorrect data for {proj}")
            elif proj in ["怪兽组合大挑战", "火柴人闯关侠"]:
                print(f"Project: {proj}, Company: {comp}, Group: {group}")
                if comp != "恒骏" or group != "恒骏":
                    print(f"ERROR: Incorrect data for {proj}")
                    
    except Exception as e:
        print(f"FAILED to load JSON: {e}")

if __name__ == "__main__":
    json_path = r"d:\openflow-plugin\openflow-desktop\20260311-孟祥伟数据表.json"
    load_check(json_path)
