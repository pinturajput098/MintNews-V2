import sys
import os
import re

print("\n" + "="*50)
print("🔍 JARVIS CODEBASE DIAGNOSTIC AUDIT REPORT 🔍")
print("="*50)

# 1. Environment & Runtime Details
print(f"\n[1] Python Environment:")
print(f"    - Current Version: {sys.version.split()[0]}")
print(f"    - Working Directory: {os.getcwd()}")

# 2. Package Verifications
print(f"\n[2] Installed Dependencies Check:")
dependencies = ['flask', 'flask_socketio', 'engineio', 'eventlet', 'gunicorn']
for dep in dependencies:
    try:
        mod = __import__(dep)
        version = getattr(mod, '__version__', 'Installed (Version N/A)')
        print(f"    ✅ {dep}: {version}")
    except ImportError:
        print(f"    ❌ {dep}: NOT INSTALLED in local environment")

# 3. Code Inspection for app.py
print(f"\n[3] Inspection of 'app.py' Initialization:")
if os.path.exists('app.py'):
    with open('app.py', 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Locate target configurations
    print("    - Target Initialization Lines found:")
    found_any = False
    for i, line in enumerate(lines):
        if any(keyword in line for keyword in ['SocketIO', 'socketio', 'async_mode', 'sys.path']):
            print(f"      Line {i+1}: {line.strip()}")
            found_any = True
    if not found_any:
        print("      ❌ No SocketIO configuration lines detected!")
        
    # Check for syntax anomalies (like stray commas or duplicate declarations)
    if 'SocketIO(,' in content or 'SocketIO( ,' in content:
        print("    ⚠️ ALERT: Stray comma detected inside SocketIO initialization!")
else:
    print("    ❌ CRITICAL: 'app.py' file not found in current directory!")

print("\n" + "="*50)
print("🔍 END OF DIAGNOSTIC REPORT 🔍")
print("="*50 + "\n")
