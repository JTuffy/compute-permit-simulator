import sys
import os

sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    print("Importing app...")
    import app

    print("✅ App imported successfully.")
except Exception as e:
    print(f"❌ Error importing app: {e}")
    sys.exit(1)
