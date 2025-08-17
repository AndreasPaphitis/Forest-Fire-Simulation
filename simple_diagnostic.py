#!/usr/bin/env python3
"""
Simple diagnostic script to check if calibration is stuck.
No external dependencies required.
"""

import os
import time
import subprocess
import sys
from datetime import datetime

def check_python_processes():
    """Check for Python processes using basic system commands."""
    print("🔍 Checking for Python processes...")
    print("-" * 40)
    
    try:
        # Use tasklist on Windows
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            python_processes = [line for line in lines if 'python.exe' in line]
            
            if python_processes:
                print(f"✅ Found {len(python_processes)} Python process(es)")
                for i, proc in enumerate(python_processes[:5]):  # Show first 5
                    print(f"   {i+1}. {proc}")
                if len(python_processes) > 5:
                    print(f"   ... and {len(python_processes) - 5} more")
                return True
            else:
                print("❌ No Python processes found")
                return False
        else:
            print("⚠️  Could not check for Python processes")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Timeout checking for Python processes")
        return False
    except Exception as e:
        print(f"⚠️  Error checking processes: {e}")
        return False

def check_system_resources():
    """Check basic system resources."""
    print("\n🖥️  System Resources:")
    print("-" * 25)
    
    # Check available memory using wmic
    try:
        result = subprocess.run(['wmic', 'computersystem', 'get', 'TotalPhysicalMemory'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                total_memory = int(lines[1]) / (1024**3)
                print(f"💾 Total Memory: {total_memory:.1f}GB")
    except:
        print("💾 Memory: Cannot check")
    
    # Check disk space
    try:
        result = subprocess.run(['wmic', 'logicaldisk', 'where', 'DeviceID="C:"', 'get', 'FreeSpace,Size'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].strip().split()
                if len(parts) >= 2:
                    free_space = int(parts[0]) / (1024**3)
                    total_space = int(parts[1]) / (1024**3)
                    used_percent = ((total_space - free_space) / total_space) * 100
                    print(f"💿 Disk C: {used_percent:.1f}% used ({free_space:.1f}GB free)")
    except:
        print("💿 Disk: Cannot check")

def check_calibration_files():
    """Check for calibration-related files."""
    print("\n📁 Calibration Files:")
    print("-" * 25)
    
    # Check for common calibration output files
    calibration_files = []
    
    # Look for potential output directories
    potential_dirs = ['calibration_results', 'hpc_sensitivity_results', 'test_output']
    
    for dir_name in potential_dirs:
        if os.path.exists(dir_name):
            files = os.listdir(dir_name)
            if files:
                calibration_files.append(f"{dir_name}/ ({len(files)} files)")
    
    # Look for log files
    log_files = [f for f in os.listdir('.') if f.endswith('.log') or 'calibration' in f.lower()]
    if log_files:
        calibration_files.extend(log_files[:5])  # Show first 5
    
    if calibration_files:
        print("✅ Found calibration-related files:")
        for file in calibration_files:
            print(f"   📄 {file}")
    else:
        print("📄 No obvious calibration files found")

def main():
    print("🔍 Simple Calibration Diagnostic")
    print("=" * 40)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check Python processes
    python_running = check_python_processes()
    
    # Check system resources
    check_system_resources()
    
    # Check calibration files
    check_calibration_files()
    
    print("\n" + "=" * 40)
    print("📋 Analysis:")
    
    if python_running:
        print("✅ Python processes detected")
        print("💡 If calibration appears stuck:")
        print("   - Wait 5-10 minutes for first results")
        print("   - Check the main output for progress messages")
        print("   - Look for error messages in the output")
        print("   - The process may be initializing large models")
    else:
        print("❌ No Python processes found")
        print("💡 The calibration may have:")
        print("   - Crashed during startup")
        print("   - Completed already")
        print("   - Not started properly")
    
    print("\n🔧 Next steps:")
    print("   - Check the main calibration output for recent activity")
    print("   - Look for progress messages or error messages")
    print("   - If stuck for >10 minutes, consider restarting")

if __name__ == "__main__":
    main()
