#!/usr/bin/env python3
"""
Quick diagnostic script to check for common stuck conditions.
Run this to get immediate feedback on what might be wrong.
"""

import psutil
import time
import os
import sys

def check_calibration_status():
    """Quick check of calibration process status."""
    print("🔍 Quick Calibration Diagnostic")
    print("=" * 40)
    
    # Find calibration processes
    calibration_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
        try:
            if proc.info['name'] in ['python', 'python.exe']:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if any(keyword in cmdline.lower() for keyword in ['calibration', 'grid_search', 'fire_simulation']):
                    calibration_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if not calibration_processes:
        print("❌ No calibration processes found!")
        print("   The calibration may have crashed or not started properly.")
        return False
    
    print(f"✅ Found {len(calibration_processes)} calibration process(es)")
    
    for i, proc in enumerate(calibration_processes):
        try:
            status = proc.status()
            memory = proc.memory_info()
            cpu_percent = proc.cpu_percent()
            
            print(f"\n📊 Process {i+1} (PID {proc.pid}):")
            print(f"   Status: {status}")
            print(f"   Memory: {memory.rss/1024**3:.1f}GB")
            print(f"   CPU: {cpu_percent}%")
            
            # Check if process is responsive
            if status == 'running' and cpu_percent > 0:
                print("   🟢 Process appears active")
            elif status == 'sleeping':
                print("   🟡 Process is sleeping (may be waiting for I/O)")
            else:
                print("   🔴 Process may be stuck")
                
        except psutil.NoSuchProcess:
            print(f"   ❌ Process {proc.pid} has terminated")
        except Exception as e:
            print(f"   ⚠️  Error checking process: {e}")
    
    return True

def check_system_health():
    """Check system resources for potential issues."""
    print("\n🖥️  System Health Check:")
    print("-" * 30)
    
    # Memory
    memory = psutil.virtual_memory()
    print(f"💾 Memory: {memory.percent}% used")
    if memory.percent > 90:
        print("   ⚠️  HIGH MEMORY USAGE - may cause issues")
    elif memory.percent > 80:
        print("   🟡 Moderate memory usage")
    else:
        print("   🟢 Memory usage looks good")
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"🖥️  CPU: {cpu_percent}%")
    if cpu_percent > 90:
        print("   ⚠️  HIGH CPU USAGE - system may be overloaded")
    elif cpu_percent < 10:
        print("   🟡 Low CPU usage - processes may be stuck")
    else:
        print("   🟢 CPU usage looks normal")
    
    # Disk space (Windows compatible)
    try:
        disk = psutil.disk_usage('C:\\')
        print(f"💿 Disk: {disk.percent}% used")
        if disk.percent > 95:
            print("   ⚠️  LOW DISK SPACE - may cause failures")
    except:
        print("💿 Disk: Cannot check disk usage")

def check_common_issues():
    """Check for common calibration issues."""
    print("\n🔍 Common Issues Check:")
    print("-" * 25)
    
    # Check if shared memory is being used
    try:
        import mmap
        print("✅ Shared memory module available")
    except ImportError:
        print("❌ Shared memory module not available")
    
    # Check for zombie processes
    zombie_count = 0
    for proc in psutil.process_iter(['status']):
        try:
            if proc.status() == 'zombie':
                zombie_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if zombie_count > 0:
        print(f"⚠️  Found {zombie_count} zombie processes")
    else:
        print("✅ No zombie processes found")

def main():
    print("🚀 Running quick diagnostic...")
    print()
    
    # Check if calibration is running
    calibration_running = check_calibration_status()
    
    # Check system health
    check_system_health()
    
    # Check common issues
    check_common_issues()
    
    print("\n" + "=" * 40)
    print("📋 Summary:")
    
    if calibration_running:
        print("✅ Calibration process detected")
        print("💡 If it appears stuck:")
        print("   - Wait 5-10 minutes for first results")
        print("   - Check the main output for error messages")
        print("   - Monitor memory usage")
        print("   - Consider reducing number of workers")
    else:
        print("❌ No calibration process found")
        print("💡 Possible solutions:")
        print("   - Restart the calibration")
        print("   - Check for error messages in the main output")
        print("   - Verify configuration settings")
    
    print("\n🔧 For detailed monitoring, run: python monitor_calibration.py")

if __name__ == "__main__":
    main()
