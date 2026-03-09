import os
import cv2
from PIL import Image
from datetime import datetime

class MaterialProcessor:
    def __init__(self):
        # 支持的媒体文件扩展名配置
        self.supported_image_exts = ['.png', '.jpg', '.jpeg']
        self.supported_video_exts = ['.mp4']
        self.supported_exts = self.supported_image_exts + self.supported_video_exts

    def get_media_dimensions(self, file_path: str) -> tuple:
        """
        精确获取图片或视频的分辨率宽与高
        :param file_path: 文件的绝对路径或相对路径
        :return: (width, height) 成功返回元组，失败返回 (0, 0)
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext not in self.supported_exts:
            return 0, 0

        try:
            if ext in self.supported_video_exts:
                # 使用 cv2 读取视频流属性
                cap = cv2.VideoCapture(file_path)
                if not cap.isOpened():
                    raise ValueError(f"无法打开视频文件或视频损坏")
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                return width, height
                
            elif ext in self.supported_image_exts:
                # 使用 Pillow 读取图片属性
                with Image.open(file_path) as img:
                    return img.size  # img.size 返回 (width, height)
                    
        except Exception as e:
            # 捕获权限不足、文件损坏或缺少解码器等异常
            print(f"[警告] 获取文件宽高失败: {file_path} | 错误信息: {e}")
            return 0, 0

    def validate_folder(self, folder_path: str, required_specs: dict) -> list:
        """
        校验文件夹下的媒体文件尺寸是否匹配需求并统计数量
        :param folder_path: 目标文件夹路径
        :param required_specs: 需求分辨率数据，例如 {"1080*607": 5, "1080*1920": 5}
        :return: 校验详情报告 (List of Dicts)
        """
        report = []
        actual_size_counts = {}

        try:
            if not os.path.isdir(folder_path):
                raise FileNotFoundError("提供的路径不是有效文件夹")
                
            # 获取目标文件夹下所有支持的子文件
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        except Exception as e:
            print(f"[错误] 访问文件夹失败: {e}")
            return [{"file": folder_path, "status": "严重错误", "reason": str(e)}]

        for file in files:
            file_path = os.path.join(folder_path, file)
            _, ext = os.path.splitext(file_path)
            
            if ext.lower() not in self.supported_exts:
                continue

            width, height = self.get_media_dimensions(file_path)
            
            # 判断尺寸提取是否成功
            if width == 0 or height == 0:
                report.append({
                    "file": file,
                    "status": "格式错误",
                    "reason": "文件损坏或无法读取尺寸",
                    "actual_size": "未知"
                })
                continue

            size_str = f"{width}*{height}"
            actual_size_counts[size_str] = actual_size_counts.get(size_str, 0) + 1

            # 核对单个文件是否在需求列表中
            if size_str in required_specs:
                report.append({
                    "file": file,
                    "status": "校验通过",
                    "reason": "尺寸匹配所提需求",
                    "actual_size": size_str
                })
            else:
                report.append({
                    "file": file,
                    "status": "尺寸错误",
                    "reason": f"未包含在所需尺寸列表中",
                    "actual_size": size_str
                })

        # 添加「数量校验」作为报告的一部分
        for req_size, req_count in required_specs.items():
            actual_count = actual_size_counts.get(req_size, 0)
            if actual_count < req_count:
                report.append({
                    "file": "[整体统计]",
                    "status": "数量不足",
                    "reason": f"尺寸 {req_size} 需要 {req_count} 个，只有 {actual_count} 个",
                    "actual_size": req_size
                })
            else:
                report.append({
                    "file": "[整体统计]",
                    "status": "数量达标",
                    "reason": f"尺寸 {req_size} 需要 {req_count} 个，实际找到 {actual_count} 个",
                    "actual_size": req_size
                })

        return report

    def rename_files(self, folder_path: str, project_name: str, maker_abbr: str = "MXW") -> bool:
        """
        依据公式自动重命名文件夹中的资源，应在 validate_folder 确认达标后调用
        :param folder_path: 目标文件夹路径
        :param project_name: 变量名 - 项目游戏名
        :param maker_abbr: 制作人缩写（全大写），例如 MXW
        :return: True 表示处理完毕，False 表示执行时发生中断及错误
        """
        try:
            if not os.path.isdir(folder_path):
                return False

            today_str = datetime.now().strftime("%Y%m%d")
            
            # 过滤支持的文件
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
            # 为了让每次批量处理时，序列号的分配尽可能跟文件的时间先后相关联，最好按字母或创建时间排个序
            files.sort()

            # 序列号计数器（视频与图片相互独立）
            video_seq = 1
            image_seq = 1

            for file in files:
                file_path = os.path.join(folder_path, file)
                _, ext = os.path.splitext(file)
                ext_lower = ext.lower()

                if ext_lower not in self.supported_exts:
                    continue

                width, height = self.get_media_dimensions(file_path)
                if width == 0 or height == 0:
                    continue  # 忽略错误文件
                
                # 分配新文件名
                if ext_lower in self.supported_video_exts:
                    # 视频逻辑：RSyyyymmdd-项目游戏名-制作人缩写-奇觅-横竖-(序列号).mp4
                    orientation = "横" if width >= height else "竖"
                    base_new_name = f"RS{today_str}-{project_name}-{maker_abbr}-奇觅-{orientation}-({video_seq}){ext_lower}"
                    video_seq += 1
                else:
                    # 图片逻辑：RSQyyyymmdd-项目游戏名-版位尺寸-制作人缩写-(序列号).jpg/png
                    size_str = f"{width}x{height}"
                    base_new_name = f"RSQ{today_str}-{project_name}-{size_str}-{maker_abbr}-({image_seq}){ext_lower}"
                    image_seq += 1

                new_file_path = os.path.join(folder_path, base_new_name)

                # 容错：防止重命名导致的名称冲突
                conflict_index = 1
                while os.path.exists(new_file_path):
                    # 如果原名字跟新名字恰巧完全一致，则什么都不做
                    if os.path.abspath(file_path) == os.path.abspath(new_file_path):
                        break
                    
                    # 命名被占用时追加 "_1", "_2" 后缀防止覆盖
                    name_without_ext = os.path.splitext(base_new_name)[0]
                    adjusted_new_name = f"{name_without_ext}_{conflict_index}{ext_lower}"
                    new_file_path = os.path.join(folder_path, adjusted_new_name)
                    conflict_index += 1

                # 开始实际重命名
                if os.path.abspath(file_path) != os.path.abspath(new_file_path):
                    os.rename(file_path, new_file_path)

            return True

        except Exception as e:
            print(f"[错误] 重命名过程遇到致命异常: {e}")
            return False

if __name__ == "__main__":
    processor = MaterialProcessor()
    base_folder = r"c:\Users\mxw86\Documents\openflow-desktop\小火车呜呜呜"
    project_name = "小火车游戏"
    
    test_cases = [
        ("1280-720", {"1280*720": 5}),
        ("640-360", {"640*360": 5}),
        ("720-1280", {"720*1280": 5})
    ]
    
    for folder_name, required_specs in test_cases:
        target_folder = os.path.join(base_folder, folder_name)
        print(f"\n{'='*40}")
        print(f"正在处理文件夹：{folder_name}")
        print(f"{'='*40}")
        
        # 1. 执行校验
        print("开始校验文件夹：")
        report = processor.validate_folder(target_folder, required_specs)
        for index, info in enumerate(report, 1):
            print(f"[{index}] 文件:{info['file']} | 状态:{info['status']} | 详情:{info['reason']} | 尺寸:{info['actual_size']}")
            
        # 分析是否所有校验都达标
        can_rename = all(item["status"] in ["校验通过", "数量达标"] for item in report)
        
        # 2. 如果校验通过，执行重命名
        if can_rename:
            print(f"\n[{folder_name}] 校验通过，开始执行重命名...")
            success = processor.rename_files(target_folder, project_name)
            if success:
                print(f"[{folder_name}] 重命名全部成功！")
            else:
                print(f"[{folder_name}] 重命名过程中出现了错误。")
        else:
            print(f"\n[{folder_name}] 校验未完全通过，跳过批量重命名！")
