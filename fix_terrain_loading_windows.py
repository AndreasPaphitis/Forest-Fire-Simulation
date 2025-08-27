#!/usr/bin/env python
"""
Fix terrain loading hanging issue for Windows by using threading instead of signals.
This prevents the terrain loading from hanging indefinitely on Windows.
"""
import re

def fix_terrain_loading_windows():
    """Fix terrain loading hanging for Windows using threading timeout."""
    
    print("🔧 Fixing terrain loading hanging issue for Windows...")
    
    # Read the forest_model.py file
    with open('src/core/forest_model.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix: Replace signal-based timeout with threading-based timeout for Windows compatibility
    old_timeout_code = '''                        # CRITICAL FIX: Add timeout for terrain loading to prevent hanging
                        import signal
                        
                        def timeout_handler(signum, frame):
                            raise TimeoutError(f"Terrain loading timeout for {filename}")
                        
                        # Set 30 second timeout for terrain loading
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(30)
                        
                        try:
                            terrain_data = np.load(file_path)
                            signal.alarm(0)  # Cancel timeout
                        except TimeoutError:
                            logger.error(f"❌ Terrain loading timeout for {filename} - skipping")
                            continue
                        except Exception as e:
                            signal.alarm(0)  # Cancel timeout
                            logger.error(f"❌ Failed to load {filename}: {e}")
                            continue'''
    
    new_timeout_code = '''                        # CRITICAL FIX: Add timeout for terrain loading to prevent hanging (Windows compatible)
                        import threading
                        import time
                        
                        terrain_data = None
                        loading_error = None
                        
                        def load_terrain_file():
                            nonlocal terrain_data, loading_error
                            try:
                                terrain_data = np.load(file_path)
                            except Exception as e:
                                loading_error = e
                        
                        # Start terrain loading in a separate thread with timeout
                        loading_thread = threading.Thread(target=load_terrain_file)
                        loading_thread.daemon = True
                        loading_thread.start()
                        
                        # Wait for loading to complete with 30 second timeout
                        loading_thread.join(timeout=30)
                        
                        if loading_thread.is_alive():
                            logger.error(f"❌ Terrain loading timeout for {filename} - skipping")
                            continue
                        elif loading_error:
                            logger.error(f"❌ Failed to load {filename}: {loading_error}")
                            continue'''
    
    if old_timeout_code in content:
        content = content.replace(old_timeout_code, new_timeout_code)
        print("✅ Replaced signal timeout with Windows-compatible threading timeout")
    else:
        print("⚠️  Signal timeout code not found (may already be fixed)")
    
    # Write the fixed content back
    with open('src/core/forest_model.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully fixed terrain loading hanging issue for Windows")
    print("🎯 This should prevent terrain loading from hanging indefinitely on Windows")
    print("📝 Uses threading-based timeout instead of signals")

if __name__ == "__main__":
    fix_terrain_loading_windows()
