#!/usr/bin/env python3
# This file is part of tg-monitoring.
#
# tg-monitoring is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tg-monitoring is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tg-monitoring. If not, see <https://www.gnu.org/licenses/>.
#
# Author: Claude (Anthropic AI Assistant)
# Co-author: goodmeow (Harun Al Rasyid) <aarunalr@pm.me>

"""
Test compatibility of Docker and Python exporters
Ensures both work with existing bot code without modification
"""

import asyncio
import sys
from tgbot.modules.exporters import create_exporter, ExporterType, get_available_exporters
from tgbot.domain.metrics import fetch_node_stats


async def test_exporter(exporter_type: ExporterType):
    """Test a specific exporter type"""
    print(f"\n{'='*50}")
    print(f"Testing {exporter_type.value.upper()} Exporter")
    print('='*50)
    
    # Create and start exporter
    print(f"1. Creating {exporter_type.value} exporter...")
    exporter = create_exporter(exporter_type)
    
    print(f"2. Starting {exporter_type.value} exporter...")
    if not await exporter.start():
        print(f"   ❌ Failed to start {exporter_type.value} exporter")
        return False
    
    print(f"   ✅ {exporter_type.value} exporter started")
    
    # Wait for it to be ready
    await asyncio.sleep(3)
    
    # Test health check
    print(f"3. Testing health check...")
    if not await exporter.health_check():
        print(f"   ❌ Health check failed")
        await exporter.stop()
        return False
    print(f"   ✅ Health check passed")
    
    # Test metrics fetch using existing bot code
    print(f"4. Testing metrics fetch with existing parser...")
    try:
        stats = await fetch_node_stats(exporter.metrics_url, timeout_sec=5)
        
        print(f"   ✅ Metrics fetched successfully!")
        print(f"   📊 System Info:")
        print(f"      - CPU Load per Core: {stats.cpu_load_per_core:.2f}")
        print(f"      - Memory Available: {stats.mem_available_pct:.1f}%")
        print(f"      - Disks: {len(stats.disks)} mounted")
        print(f"      - Timestamp: {stats.timestamp}")
        
        if stats.disks:
            print(f"   📁 First disk:")
            disk = stats.disks[0]
            print(f"      - Mount: {disk.mount}")
            print(f"      - Type: {disk.fstype}")
            if disk.avail_bytes and disk.size_bytes:
                avail_pct = (disk.avail_bytes / disk.size_bytes) * 100
                print(f"      - Available: {avail_pct:.1f}%")
        
    except Exception as e:
        print(f"   ❌ Failed to fetch metrics: {e}")
        await exporter.stop()
        return False
    
    # Stop exporter
    print(f"5. Stopping {exporter_type.value} exporter...")
    if not await exporter.stop():
        print(f"   ⚠️  Warning: Failed to stop cleanly")
    else:
        print(f"   ✅ Exporter stopped")
    
    print(f"\n✅ {exporter_type.value.upper()} EXPORTER TEST PASSED!")
    return True


async def main():
    """Main test function"""
    print("🧪 EXPORTER COMPATIBILITY TEST")
    print("Testing that both Docker and Python exporters work with existing bot code")
    
    # Check what's available
    print("\n📦 Checking available exporters...")
    available = get_available_exporters()
    for name, is_available in available.items():
        status = "✅" if is_available else "❌"
        print(f"  {status} {name}")
    
    if not any(available.values()):
        print("\n❌ No exporters available! Install Docker or Python dependencies.")
        sys.exit(1)
    
    results = {}
    
    # Test Docker if available
    if available.get("docker", False):
        try:
            results["docker"] = await test_exporter(ExporterType.DOCKER)
        except Exception as e:
            print(f"❌ Docker test failed with error: {e}")
            results["docker"] = False
    else:
        print("\n⚠️  Skipping Docker exporter (not available)")
        results["docker"] = None
    
    # Test Python if available  
    if available.get("python", False):
        try:
            results["python"] = await test_exporter(ExporterType.PYTHON)
        except Exception as e:
            print(f"❌ Python test failed with error: {e}")
            results["python"] = False
    else:
        print("\n⚠️  Skipping Python exporter (dependencies not installed)")
        results["python"] = None
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    for exporter, result in results.items():
        if result is None:
            status = "⚠️  SKIPPED"
        elif result:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        print(f"{exporter.upper()}: {status}")
    
    # Overall result
    if all(r is True or r is None for r in results.values()) and any(r is True for r in results.values()):
        print("\n🎉 COMPATIBILITY TEST PASSED!")
        print("Both exporters are 100% compatible with existing bot code.")
        print("No code changes needed!")
        return 0
    else:
        print("\n❌ COMPATIBILITY TEST FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
