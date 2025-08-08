#!/usr/bin/env python3
"""Quick start script for FPL AI Optimizer - ดาวน์โหลดข้อมูลและฝึกโมเดลครั้งแรก"""

import os
import sys
from pathlib import Path
import subprocess
import time

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    print(f"💻 Running: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=project_root
        )
        print(f"✅ {description} - สำเร็จ!")
        if result.stdout:
            print(f"📄 Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - ล้มเหลว!")
        print(f"🚨 Error: {e.stderr}")
        return False


def check_environment():
    """Check if virtual environment is activated."""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment ถูกเปิดใช้งานแล้ว")
        return True
    else:
        print("⚠️  Virtual environment ไม่ได้เปิดใช้งาน")
        print("กรุณารัน: source venv/bin/activate (Linux/Mac) หรือ venv\\Scripts\\activate (Windows)")
        return False


def main():
    """Main quick start process."""
    print("🏆 FPL AI Optimizer - Quick Start")
    print("=" * 50)
    print("สคริปต์นี้จะช่วยดาวน์โหลดข้อมูลและตั้งค่าระบบให้พร้อมใช้งาน")
    print()
    
    # Check environment
    if not check_environment():
        return 1
    
    # Step 1: Validate system
    print("\n📋 ขั้นตอนที่ 1: ตรวจสอบระบบ")
    if not run_command("python scripts/validate_system.py", "ตรวจสอบความพร้อมของระบบ"):
        print("🚨 ระบบไม่พร้อม กรุณาแก้ไขปัญหาก่อนดำเนินการต่อ")
        return 1
    
    # Step 2: Setup database  
    print("\n📋 ขั้นตอนที่ 2: ตั้งค่าฐานข้อมูล")
    if not run_command("python scripts/setup_database.py", "สร้างตารางในฐานข้อมูล"):
        print("🚨 ไม่สามารถตั้งค่าฐานข้อมูลได้")
        return 1
    
    # Step 3: Fetch FPL data
    print("\n📋 ขั้นตอนที่ 3: ดาวน์โหลดข้อมูล FPL")
    if not run_command("python scripts/fetch_fpl_data.py", "ดาวน์โหลดข้อมูลจาก FPL API"):
        print("🚨 ไม่สามารถดาวน์โหลดข้อมูลได้ - ตรวจสอบการเชื่อมต่ออินเทอร์เน็ต")
        return 1
    
    # Step 4: Train ML models  
    print("\n📋 ขั้นตอนที่ 4: ฝึกโมเดล Machine Learning")
    print("⏰ การฝึกโมเดลอาจใช้เวลา 2-5 นาที กรุณารอสักครู่...")
    if not run_command("python scripts/train_models.py", "ฝึกโมเดล XGBoost สำหรับการทำนาย"):
        print("🚨 ไม่สามารถฝึกโมเดลได้ - ตรวจสอบข้อมูลในฐานข้อมูล")
        return 1
    
    # Step 5: Final validation
    print("\n📋 ขั้นตอนที่ 5: ตรวจสอบความพร้อมสุดท้าย")
    if not run_command("python scripts/validate_system.py", "ตรวจสอบระบบหลังการตั้งค่า"):
        print("🚨 ระบบยังไม่พร้อมใช้งาน")
        return 1
    
    # Success message
    print("\n" + "=" * 50)
    print("🎉 ตั้งค่าเสร็จสมบูรณ์!")
    print("=" * 50)
    print()
    print("📋 คำสั่งการใช้งาน:")
    print("1. เริ่มเซิร์ฟเวอร์:     flask run")
    print("2. เข้าใช้งานที่:       http://localhost:5000")
    print("3. ดู API Doc:        http://localhost:5000/api")
    print("4. อัพเดทข้อมูล:       python scripts/fetch_fpl_data.py")
    print("5. ฝึกโมเดลใหม่:       python scripts/train_models.py")
    print()
    print("📚 คู่มือการใช้งาน:     USER_GUIDE_TH.md")
    print("🐛 แก้ไขปัญหา:        ดูส่วน Troubleshooting ในคู่มือ")
    print()
    print("🚀 พร้อมใช้งาน FPL AI Optimizer แล้ว!")
    print("=" * 50)
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  การตั้งค่าถูกยกเลิก")
        print("สามารถรันสคริปต์นี้อีกครั้งเมื่อต้องการ")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n🚨 เกิดข้อผิดพลาดไม่คาดคิด: {e}")
        print("กรุณาแจ้งปัญหาใน GitHub Issues")
        sys.exit(1)