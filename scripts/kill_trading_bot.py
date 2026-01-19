"""
Script to kill all running trading bot processes.

Use this if the bot doesn't stop properly and log files are locked.
"""

import os
import sys
import subprocess
import signal

def kill_python_processes():
    """Kill all Python processes related to trading bot."""
    try:
        # Get all Python processes
        if sys.platform == "win32":
            # Windows
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True,
                text=True,
            )
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            
            killed = 0
            for line in lines:
                if line.strip():
                    parts = line.split(",")
                    if len(parts) >= 2:
                        pid = parts[1].strip('"')
                        try:
                            pid_int = int(pid)
                            # Try to get process info to see if it's our bot
                            proc_info = subprocess.run(
                                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                                capture_output=True,
                                text=True,
                            )
                            # Kill the process
                            subprocess.run(["taskkill", "/F", "/PID", pid], check=False)
                            print(f"✅ Killed process {pid}")
                            killed += 1
                        except (ValueError, subprocess.CalledProcessError):
                            pass
            
            if killed == 0:
                print("ℹ️ No Python processes found to kill")
            else:
                print(f"✅ Killed {killed} Python process(es)")
        else:
            # Unix/Linux/Mac
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True
            )
            lines = result.stdout.strip().split("\n")
            
            killed = 0
            for line in lines:
                if "python" in line.lower() and "trading" in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = parts[1]
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(f"✅ Killed process {pid}")
                            killed += 1
                        except (ValueError, ProcessLookupError, PermissionError):
                            pass
            
            if killed == 0:
                print("ℹ️ No trading bot processes found to kill")
            else:
                print(f"✅ Killed {killed} process(es)")
                
    except Exception as e:
        print(f"❌ Error killing processes: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("🔍 Searching for trading bot processes...")
    print("⚠️  This will kill ALL Python processes. Make sure no other important Python scripts are running!")
    
    response = input("Continue? (yes/no): ")
    if response.lower() in ["yes", "y"]:
        kill_python_processes()
    else:
        print("❌ Cancelled")

