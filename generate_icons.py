import os
from PIL import Image, ImageDraw, ImageFont

def generate_icons():
    # 1. 创建 icons 文件夹
    icon_dir = "icons"
    if not os.path.exists(icon_dir):
        os.makedirs(icon_dir)
        print(f"Created directory: {icon_dir}")

    # 2. 设置参数
    bg_color = "#1677ff"  # 科技蓝
    text_color = "white"
    text = "OF"
    sizes = [16, 48, 128]

    # 3. 生成不同尺寸的图标
    for size in sizes:
        # 创建画布 (RGBA 支持透明背景，但根据需求我们用底色填充)
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 绘制圆角矩形
        corner_radius = size // 4
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=corner_radius, fill=bg_color)

        # 设置字体 (尽量使用系统默认字体或简单绘制)
        try:
            # 尝试加载一个清晰的字体，如果加载不到则使用默认
            font_size = int(size * 0.6)
            # 尝试 Windows 常见字体路径
            font_paths = ["C:\\Windows\\Fonts\\arialbd.ttf", "C:\\Windows\\Fonts\\arial.ttf"]
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, font_size)
                    break
            if not font:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # 计算文字位置并居中
        # 获取文字边界框
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 居中偏移修正
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - (size // 20) # 视觉微调

        draw.text((x, y), text, fill=text_color, font=font)

        # 4. 保存文件
        file_path = os.path.join(icon_dir, f"icon{size}.png")
        image.save(file_path)
        print(f"Generated: {file_path} ({size}x{size})")

if __name__ == "__main__":
    generate_icons()
