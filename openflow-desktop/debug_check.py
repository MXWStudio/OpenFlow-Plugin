"""
调试脚本：检查文件夹名与 skip_validation_folders 集合的匹配情况
"""
import os

skip_validation_folders = {"奇觅生成", "截屏素材", "录屏素材", "模糊处理"}

# 模拟用户拖入的路径
test_paths = [
    r"D:\3月项目\20260310_MXW\穿越地平线挑战\奇觅生成",
    r"D:\3月项目\20260310_MXW\穿越地平线挑战\录屏素材",
    r"D:\3月项目\20260310_MXW\穿越地平线挑战\截屏素材",
    r"D:\3月项目\20260310_MXW\穿越地平线挑战\模糊处理",
]

print("=== 集合内容（bytes repr）===")
for s in skip_validation_folders:
    print(f"  {repr(s)} -> bytes: {s.encode('utf-8')}")

print("\n=== 文件夹名匹配测试 ===")
for path in test_paths:
    name = os.path.basename(path)
    in_set = name in skip_validation_folders
    print(f"  {repr(name)} (bytes: {name.encode('utf-8')}) -> in_set: {in_set}")

# 如果有实际文件夹路径，也可以真实测试
real_base = input("\n请输入实际的项目父文件夹路径（直接回车跳过）: ").strip()
if real_base and os.path.isdir(real_base):
    print(f"\n=== 实际文件夹名测试 ({real_base}) ===")
    for sub in os.listdir(real_base):
        sub_path = os.path.join(real_base, sub)
        if os.path.isdir(sub_path):
            in_set = sub in skip_validation_folders
            print(f"  {repr(sub)} (bytes: {sub.encode('utf-8')}) -> in_set: {in_set}")

print("\n完成！")
