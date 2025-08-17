#!/usr/bin/env python3
"""
Calibration monitoring script to detect if the process is stuck.
Run this in a separate terminal while your calibration is running.
"""

import psutil
import time
import os
import sys
from datetime import datetime

def find_calibration_process():
    """Find the Python process running the calibration."""
    calibration_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python' or proc.info['name'] == 'python.exe':
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if any(keyword in cmdline.lower() for keyword in ['calibration', 'grid_search', 'fire_simulation']):
                    calibration_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return calibration_processes

def monitor_process(proc, duration_minutes=30):
    """Monitor a single process for activity."""
    print(f"🔍 Monitoring process {proc.pid}")
    print(f"📊 Command: {' '.join(proc.cmdline()[:3])}...")
    print("=" * 80)
    
    start_time = time.time()
    last_cpu_times = proc.cpu_times()
    last_io_counters = proc.io_counters()
    
    check_count = 0
    
    while time.time() - start_time < duration_minutes * 60:
        try:
            # Get current process info
            cpu_times = proc.cpu_times()
            io_counters = proc.io_counters()
            memory_info = proc.memory_info()
            
            # Calculate deltas
            cpu_delta = sum(cpu_times) - sum(last_cpu_times)
            io_delta = io_counters.read_bytes + io_counters.write_bytes - (last_io_counters.read_bytes + last_io_counters.write_bytes)
            
            # Check if process is active
            is_active = cpu_delta > 0.1 or io_delta > 1000  # CPU > 0.1s or IO > 1KB
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            elapsed = time.time() - start_time
            
            status = "🟢 ACTIVE" if is_active else "🔴 STUCK"
            
            print(f"[{timestamp}] {status} | "
                  f"Elapsed: {elapsed/60:.1f}min | "
                  f"CPU: {cpu_delta:.2f}s | "
                  f"IO: {io_delta/1024:.1f}KB | "
                  f"Memory: {memory_info.rss/1024**3:.1f}GB")
            
            # Update last values
            last_cpu_times = cpu_times
            last_io_counters = io_counters
            
            # Check for stuck condition
            if not is_active and check_count > 5:  # Stuck for 5+ checks
                print(f"⚠️  WARNING: Process appears stuck for {check_count} consecutive checks!")
                print(f"   Consider checking the main calibration output for errors.")
            
            check_count = check_count + 1 if not is_active else 0
            
            time.sleep(10)  # Check every 10 seconds
            
        except psutil.NoSuchProcess:
            print(f"❌ Process {proc.pid} has terminated")
            break
        except Exception as e:
            print(f"⚠️  Error monitoring process: {e}")
            break

def check_system_resources():
    """Check overall system resource usage."""
    print("🖥️  System Resource Check:")
    print("-" * 40)
    
    # Memory
    memory = psutil.virtual_memory()
    print(f"💾 Memory: {memory.percent}% used ({memory.used/1024**3:.1f}GB / {memory.total/1024**3:.1f}GB)")
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"🖥️  CPU: {cpu_percent}%")
    
    # Disk I/O
    disk_io = psutil.disk_io_counters()
    if disk_io:
        print(f"💿 Disk I/O: {disk_io.read_bytes/1024**2:.1f}MB read, {disk_io.write_bytes/1024**2:.1f}MB written")
    
    print()

def main():
    print("🔍 Calibration Process Monitor")
    print("=" * 50)
    print("This script will help you detect if your calibration is stuck.")
    print("Run this in a separate terminal while your calibration is running.")
    print()
    
    # Check system resources
    check_system_resources()
    
    # Find calibration processes
    processes = find_calibration_process()
    
    if not processes:
        print("❌ No calibration processes found!")
        print("Make sure your calibration is running and try again.")
        return
    
    print(f"✅ Found {len(processes)} calibration process(es):")
    for i, proc in enumerate(processes):
        print(f"   {i+1}. PID {proc.pid}: {' '.join(proc.cmdline()[:3])}...")
    
    print()
    print("🔍 Starting monitoring... (Press Ctrl+C to stop)")
    print()
    
    try:
        # Monitor the first process (usually the main one)
        monitor_process(processes[0], duration_minutes=60)
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")

if __name__ == "__main__":
    main()
