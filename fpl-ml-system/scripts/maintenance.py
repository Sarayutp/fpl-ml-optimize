#!/usr/bin/env python3
"""Maintenance script for FPL AI Optimizer - สำหรับการบำรุงรักษาระบบ"""

import os
import sys
import shutil
import gzip
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import subprocess

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def clean_logs(days_to_keep=7):
    """Clean old log files."""
    print(f"🧹 ทำความสะอาดล็อกไฟล์เก่ากว่า {days_to_keep} วัน...")
    
    logs_dir = project_root / "logs"
    if not logs_dir.exists():
        print("📁 ไม่พบโฟลเดอร์ logs")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cleaned_files = 0
    
    for log_file in logs_dir.glob("*.log"):
        if log_file.stat().st_mtime < cutoff_date.timestamp():
            try:
                log_file.unlink()
                cleaned_files += 1
                print(f"  ลบไฟล์: {log_file.name}")
            except Exception as e:
                print(f"  ❌ ไม่สามารถลบ {log_file.name}: {e}")
    
    # Clean old compressed logs
    for gz_file in logs_dir.glob("*.log.gz"):
        if gz_file.stat().st_mtime < cutoff_date.timestamp():
            try:
                gz_file.unlink()
                cleaned_files += 1
                print(f"  ลบไฟล์: {gz_file.name}")
            except Exception as e:
                print(f"  ❌ ไม่สามารถลบ {gz_file.name}: {e}")
    
    print(f"✅ ทำความสะอาดเสร็จสิ้น - ลบไฟล์ {cleaned_files} ไฟล์")


def compress_logs():
    """Compress large log files."""
    print("📦 บีบอัดไฟล์ล็อกขนาดใหญ่...")
    
    logs_dir = project_root / "logs"
    if not logs_dir.exists():
        print("📁 ไม่พบโฟลเดอร์ logs")
        return
    
    max_size_mb = 10  # ไฟล์ที่ใหญ่กว่า 10MB จะถูกบีบอัด
    compressed_files = 0
    
    for log_file in logs_dir.glob("*.log"):
        size_mb = log_file.stat().st_size / (1024 * 1024)
        
        if size_mb > max_size_mb:
            compressed_path = log_file.with_suffix(log_file.suffix + ".gz")
            
            try:
                with open(log_file, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove original file
                log_file.unlink()
                compressed_files += 1
                print(f"  บีบอัด: {log_file.name} ({size_mb:.1f}MB)")
                
            except Exception as e:
                print(f"  ❌ ไม่สามารถบีบอัด {log_file.name}: {e}")
    
    print(f"✅ บีบอัดเสร็จสิ้น - บีบอัด {compressed_files} ไฟล์")


def vacuum_database():
    """Vacuum SQLite database to reclaim space."""
    print("🗄️  ปรับปรุงฐานข้อมูล (VACUUM)...")
    
    try:
        from src import create_app
        from src.models.db_models import db
        
        app = create_app('development')
        with app.app_context():
            # Get database size before
            db_file = project_root / "data" / "fpl.db"
            if db_file.exists():
                size_before = db_file.stat().st_size / (1024 * 1024)
                print(f"  ขนาดฐานข้อมูลก่อน: {size_before:.2f}MB")
                
                # Run VACUUM
                with db.engine.connect() as conn:
                    conn.execute(db.text("VACUUM"))
                    conn.commit()
                
                # Get size after
                size_after = db_file.stat().st_size / (1024 * 1024)
                saved = size_before - size_after
                print(f"  ขนาดฐานข้อมูลหลัง: {size_after:.2f}MB")
                print(f"  ประหยัดพื้นที่: {saved:.2f}MB")
                
                print("✅ ปรับปรุงฐานข้อมูลเสร็จสิ้น")
            else:
                print("❌ ไม่พบไฟล์ฐานข้อมูล")
                
    except Exception as e:
        print(f"❌ ไม่สามารถปรับปรุงฐานข้อมูลได้: {e}")


def clean_cache():
    """Clear application cache."""
    print("🔄 ล้างแคช...")
    
    try:
        from src import create_app
        
        app = create_app('development')
        with app.app_context():
            # Clear Redis cache if available
            try:
                import redis
                r = redis.Redis(host='localhost', port=6379, db=0)
                r.flushdb()
                print("✅ ล้าง Redis cache แล้ว")
            except:
                print("ℹ️  Redis ไม่พร้อมใช้งาน")
            
            # Clear file-based cache if exists
            cache_dir = project_root / "cache"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                print("✅ ล้าง File cache แล้ว")
            
            print("✅ ล้างแคชเสร็จสิ้น")
            
    except Exception as e:
        print(f"❌ ไม่สามารถล้างแคชได้: {e}")


def backup_database():
    """Create database backup."""
    print("💾 สำรองฐานข้อมูล...")
    
    db_file = project_root / "data" / "fpl.db"
    if not db_file.exists():
        print("❌ ไม่พบไฟล์ฐานข้อมูล")
        return
    
    # Create backups directory
    backups_dir = project_root / "backups"
    backups_dir.mkdir(exist_ok=True)
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backups_dir / f"fpl_backup_{timestamp}.db"
    
    try:
        shutil.copy2(db_file, backup_file)
        
        # Compress backup
        with open(backup_file, 'rb') as f_in:
            with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed backup
        backup_file.unlink()
        
        size_mb = Path(f"{backup_file}.gz").stat().st_size / (1024 * 1024)
        print(f"✅ สำรองข้อมูลเสร็จสิ้น: {backup_file.name}.gz ({size_mb:.2f}MB)")
        
        # Clean old backups (keep last 10)
        backups = sorted(backups_dir.glob("fpl_backup_*.db.gz"), reverse=True)
        for old_backup in backups[10:]:
            old_backup.unlink()
            print(f"  ลบสำรองเก่า: {old_backup.name}")
            
    except Exception as e:
        print(f"❌ ไม่สามารถสำรองฐานข้อมูลได้: {e}")


def update_data():
    """Update FPL data and retrain models."""
    print("🔄 อัพเดทข้อมูล FPL...")
    
    try:
        # Fetch latest FPL data
        result = subprocess.run([
            sys.executable, "scripts/fetch_fpl_data.py"
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            print("✅ ดาวน์โหลดข้อมูลสำเร็จ")
            
            # Retrain models
            print("🤖 ฝึกโมเดล ML ใหม่...")
            result = subprocess.run([
                sys.executable, "scripts/train_models.py"
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                print("✅ ฝึกโมเดลสำเร็จ")
            else:
                print(f"❌ ฝึกโมเดลไม่สำเร็จ: {result.stderr}")
        else:
            print(f"❌ ดาวน์โหลดข้อมูลไม่สำเร็จ: {result.stderr}")
            
    except Exception as e:
        print(f"❌ ไม่สามารถอัพเดทข้อมูลได้: {e}")


def check_disk_space():
    """Check available disk space."""
    print("💾 ตรวจสอบพื้นที่ดิสก์...")
    
    try:
        total, used, free = shutil.disk_usage(project_root)
        
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        
        print(f"  พื้นที่ทั้งหมด: {total_gb:.1f}GB")
        print(f"  พื้นที่ที่ใช้: {used_gb:.1f}GB")
        print(f"  พื้นที่ว่าง: {free_gb:.1f}GB")
        
        if free_gb < 1.0:  # Less than 1GB free
            print("⚠️  เหลือพื้นที่น้อย - ควรทำความสะอาด")
            return False
        else:
            print("✅ พื้นที่ดิสก์เพียงพอ")
            return True
            
    except Exception as e:
        print(f"❌ ไม่สามารถตรวจสอบพื้นที่ดิสก์ได้: {e}")
        return None


def system_health_check():
    """Perform system health check."""
    print("🏥 ตรวจสอบสุขภาพระบบ...")
    
    health_status = {
        "database": False,
        "ml_models": False,
        "disk_space": False,
        "api_connectivity": False
    }
    
    # Check database
    try:
        from src import create_app
        from src.models.db_models import db
        
        app = create_app('development')
        with app.app_context():
            with db.engine.connect() as conn:
                conn.execute(db.text('SELECT COUNT(*) FROM players'))
            health_status["database"] = True
            print("  ✅ ฐานข้อมูล: ปกติ")
    except:
        print("  ❌ ฐานข้อมูล: มีปัญหา")
    
    # Check ML models
    models_dir = project_root / "models"
    if models_dir.exists() and list(models_dir.glob("*.pkl")):
        health_status["ml_models"] = True
        print("  ✅ โมเดล ML: พร้อมใช้งาน")
    else:
        print("  ❌ โมเดล ML: ไม่พบโมเดล")
    
    # Check disk space
    disk_ok = check_disk_space()
    if disk_ok:
        health_status["disk_space"] = True
    
    # Check API connectivity
    try:
        import requests
        response = requests.get(
            "https://fantasy.premierleague.com/api/bootstrap-static/",
            timeout=10
        )
        if response.status_code == 200:
            health_status["api_connectivity"] = True
            print("  ✅ FPL API: เชื่อมต่อได้")
        else:
            print(f"  ❌ FPL API: สถานะ {response.status_code}")
    except:
        print("  ❌ FPL API: เชื่อมต่อไม่ได้")
    
    # Summary
    healthy_components = sum(health_status.values())
    total_components = len(health_status)
    
    print(f"\n📊 สรุป: {healthy_components}/{total_components} ระบบทำงานปกติ")
    
    if healthy_components == total_components:
        print("🎉 ระบบทำงานปกติทุกส่วน!")
    elif healthy_components >= total_components * 0.75:
        print("⚠️  ระบบส่วนใหญ่ทำงานปกติ แต่มีบางส่วนต้องแก้ไข")
    else:
        print("🚨 ระบบมีปัญหาหลายส่วน ควรตรวจสอบและแก้ไข")
    
    return health_status


def generate_maintenance_report():
    """Generate maintenance report."""
    print("📄 สร้างรายงานการบำรุงรักษา...")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "maintenance_performed": [],
        "system_health": {},
        "recommendations": []
    }
    
    # Run health check
    health = system_health_check()
    report["system_health"] = health
    
    # Generate recommendations
    if not health.get("database", False):
        report["recommendations"].append("ตั้งค่าฐานข้อมูลใหม่: python scripts/setup_database.py")
    
    if not health.get("ml_models", False):
        report["recommendations"].append("ฝึกโมเดล ML: python scripts/train_models.py")
    
    if not health.get("api_connectivity", False):
        report["recommendations"].append("ตรวจสอบการเชื่อมต่ออินเทอร์เน็ต")
    
    # Save report
    try:
        report_file = project_root / "maintenance_report.json"
        import json
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ สร้างรายงาน: {report_file}")
    except Exception as e:
        print(f"❌ ไม่สามารถสร้างรายงานได้: {e}")
    
    return report


def main():
    """Main maintenance function."""
    parser = argparse.ArgumentParser(description="FPL AI Optimizer Maintenance Script")
    parser.add_argument("--clean-logs", action="store_true", help="Clean old log files")
    parser.add_argument("--compress-logs", action="store_true", help="Compress large log files")
    parser.add_argument("--vacuum-db", action="store_true", help="Vacuum database")
    parser.add_argument("--clear-cache", action="store_true", help="Clear application cache")
    parser.add_argument("--backup-db", action="store_true", help="Backup database")
    parser.add_argument("--update-data", action="store_true", help="Update FPL data and retrain models")
    parser.add_argument("--health-check", action="store_true", help="Perform system health check")
    parser.add_argument("--full-maintenance", action="store_true", help="Perform full maintenance")
    parser.add_argument("--days-to-keep", type=int, default=7, help="Days of logs to keep (default: 7)")
    
    args = parser.parse_args()
    
    if not any(vars(args).values()) or args.health_check:
        # Default: just health check
        system_health_check()
        return
    
    print("🔧 FPL AI Optimizer - Maintenance Script")
    print("=" * 50)
    print(f"เริ่มต้น: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    if args.full_maintenance or args.clean_logs:
        clean_logs(args.days_to_keep)
    
    if args.full_maintenance or args.compress_logs:
        compress_logs()
    
    if args.full_maintenance or args.backup_db:
        backup_database()
    
    if args.full_maintenance or args.vacuum_db:
        vacuum_database()
    
    if args.full_maintenance or args.clear_cache:
        clean_cache()
    
    if args.update_data:
        update_data()
    
    # Always do health check at the end
    print("\n" + "=" * 50)
    final_health = system_health_check()
    
    print("\n" + "=" * 50)
    print("🏁 การบำรุงรักษาเสร็จสิ้น!")
    print(f"สิ้นสุด: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  การบำรุงรักษาถูกยกเลิก")
    except Exception as e:
        print(f"\n🚨 เกิดข้อผิดพลาดในการบำรุงรักษา: {e}")
        import traceback
        traceback.print_exc()