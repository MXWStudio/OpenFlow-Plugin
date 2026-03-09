
import sys
import os
from PySide6.QtWidgets import QApplication

# 将当前目录添加到路径以便导入 main_window
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def smoke_test():
    print("Starting GUI smoke test...")
    app = QApplication(sys.argv)
    try:
        from main_window import MaterialProcessorGUI
        # 实例化窗口，这会运行 init_ui()
        window = MaterialProcessorGUI()
        print("Success: MaterialProcessorGUI instantiated without errors.")
        return True
    except Exception as e:
        print(f"FAILED: Smoke test caught an error during instantiation: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        app.quit()

if __name__ == "__main__":
    success = smoke_test()
    sys.exit(0 if success else 1)
