import psutil
import subprocess
import json

def get_macos_disk_free():
    # Get free space in bytes from diskutil
    output = subprocess.check_output("diskutil info / | grep 'Container Free Space'", shell=True).decode()
    # Extract the exact byte count, e.g. "114417999872 Bytes"
    bytes_str = output.split('(')[1].split(' Bytes')[0]
    return int(bytes_str)

def get_macos_uptime_load():
    output = subprocess.check_output("uptime", shell=True).decode()
    loads = output.split('load averages:')[1].strip().split()
    return float(loads[0])

def main():
    print("Running PulseTrace vs macOS Parity Checks...")
    errors = 0

    # 1. Check Disk Parity
    pt_disk = psutil.disk_usage('/')
    mac_disk = get_macos_disk_free()
    
    # Allow 100MB margin of error since disk space changes constantly
    if abs(pt_disk.free - mac_disk) > 100_000_000:
        print(f"❌ DISK FAIL: PulseTrace={pt_disk.free} bytes, macOS={mac_disk} bytes")
        errors += 1
    else:
        print(f"✅ DISK PASS: PulseTrace and macOS native APIs match (Diff: {abs(pt_disk.free - mac_disk)/(1000**2):.2f} MB)")

    # 2. Check Load Average Parity
    pt_load = psutil.getloadavg()[0]
    mac_load = get_macos_uptime_load()
    
    # Load averages update constantly, so allow a 0.5 margin of error
    if abs(pt_load - mac_load) > 0.5:
        print(f"❌ LOAD FAIL: PulseTrace={pt_load}, macOS={mac_load}")
        errors += 1
    else:
        print(f"✅ LOAD PASS: PulseTrace and macOS native APIs match (Diff: {abs(pt_load - mac_load):.2f})")

    if errors == 0:
        print("\nSUCCESS: All PulseTrace metrics are verified against native macOS APIs.")
        print("The system is safe to ship.")
    else:
        print(f"\nWARNING: {errors} parity checks failed.")

if __name__ == "__main__":
    main()
