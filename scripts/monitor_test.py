#!/usr/bin/env python3

import time
import os
import sys
import psutil
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tgbot.core.memory import MemoryMonitor


def find_tgbot_process():
    """Find the running tgbot process"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'tgbot.main' in cmdline and 'python' in cmdline:
                return psutil.Process(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def monitor_bot(duration_hours=2, interval_seconds=60):
    """Monitor bot for specified duration"""
    print(f"🔍 Starting {duration_hours}h monitoring test...")
    print(f"📊 Collecting metrics every {interval_seconds}s")
    print("=" * 60)

    # Find tgbot process
    bot_process = find_tgbot_process()
    if not bot_process:
        print("❌ tgbot process not found!")
        return

    print(f"✅ Found tgbot process: PID {bot_process.pid}")

    # Setup monitoring
    monitor = MemoryMonitor()
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)

    # Data collection
    metrics = []
    baseline_memory = None
    max_memory = 0
    min_memory = float('inf')

    try:
        while datetime.now() < end_time:
            try:
                # Get process memory info
                mem_info = bot_process.memory_info()
                rss_mb = mem_info.rss / 1024 / 1024
                vms_mb = mem_info.vms / 1024 / 1024

                # Get system stats
                stats = monitor.get_stats()

                # Record baseline
                if baseline_memory is None:
                    baseline_memory = rss_mb

                # Track min/max
                max_memory = max(max_memory, rss_mb)
                min_memory = min(min_memory, rss_mb)

                # Calculate runtime
                runtime = datetime.now() - start_time
                runtime_minutes = runtime.total_seconds() / 60

                # Store metrics
                metrics.append({
                    'timestamp': datetime.now().isoformat(),
                    'runtime_minutes': runtime_minutes,
                    'rss_mb': rss_mb,
                    'vms_mb': vms_mb,
                    'cpu_percent': bot_process.cpu_percent(),
                    'memory_percent': bot_process.memory_percent(),
                    'gc_objects': stats.gc_objects,
                    'open_files': len(bot_process.open_files()),
                    'threads': bot_process.num_threads(),
                })

                # Print current status
                growth = rss_mb - baseline_memory
                growth_pct = (growth / baseline_memory) * 100 if baseline_memory > 0 else 0

                print(f"{runtime_minutes:6.1f}m | "
                      f"RSS: {rss_mb:6.1f}MB | "
                      f"Growth: {growth:+5.1f}MB ({growth_pct:+5.1f}%) | "
                      f"CPU: {bot_process.cpu_percent():4.1f}% | "
                      f"Files: {len(bot_process.open_files()):3d} | "
                      f"GC: {stats.gc_objects:5d}")

            except psutil.NoSuchProcess:
                print("❌ tgbot process died!")
                break
            except Exception as e:
                print(f"⚠️  Error collecting metrics: {e}")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")

    # Final analysis
    print("\n" + "=" * 60)
    print("📈 MONITORING RESULTS")
    print("=" * 60)

    if metrics:
        final_memory = metrics[-1]['rss_mb']
        total_growth = final_memory - baseline_memory
        total_growth_pct = (total_growth / baseline_memory) * 100 if baseline_memory > 0 else 0

        print(f"⏱️  Duration: {len(metrics)} samples over {(datetime.now() - start_time).total_seconds() / 3600:.1f} hours")
        print(f"🚀 Baseline Memory: {baseline_memory:.1f}MB")
        print(f"🏁 Final Memory: {final_memory:.1f}MB")
        print(f"📊 Total Growth: {total_growth:+.1f}MB ({total_growth_pct:+.1f}%)")
        print(f"📈 Peak Memory: {max_memory:.1f}MB")
        print(f"📉 Min Memory: {min_memory:.1f}MB")
        print(f"🔄 Memory Range: {max_memory - min_memory:.1f}MB")

        # Memory assessment
        if abs(total_growth_pct) < 5:
            print("✅ Memory Stability: EXCELLENT (< 5% growth)")
        elif abs(total_growth_pct) < 10:
            print("✅ Memory Stability: GOOD (< 10% growth)")
        elif abs(total_growth_pct) < 20:
            print("⚠️  Memory Stability: ACCEPTABLE (< 20% growth)")
        else:
            print("❌ Memory Stability: POOR (> 20% growth)")

        # Save detailed metrics
        log_file = f"data/monitoring_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump({
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'baseline_memory_mb': baseline_memory,
                'final_memory_mb': final_memory,
                'total_growth_mb': total_growth,
                'total_growth_percent': total_growth_pct,
                'peak_memory_mb': max_memory,
                'min_memory_mb': min_memory,
                'metrics': metrics
            }, indent=2)
        print(f"📄 Detailed metrics saved to: {log_file}")
    else:
        print("❌ No metrics collected")


if __name__ == "__main__":
    # Default to 2 hours, but accept command line args
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    monitor_bot(duration, interval)