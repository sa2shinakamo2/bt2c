import sys
import importlib.util
import traceback

def check_module(module_path):
    """Check if a module can be imported without errors."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"Module {module_path} loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading module {module_path}:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Path to the test file
    test_file = "/Users/segosounonfranck/Documents/Projects/bt2c/tests/test_replay_protection_fixed.py"
    check_module(test_file)
