@echo off
echo 🏆 FPL AI Optimizer - Setup Script (Windows)
echo ==================================

REM Check Python version
echo 📋 ตรวจสอบเวอร์ชั่น Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python ไม่พบ กรุณาติดตั้ง Python 3.11+ ก่อน
    pause
    exit /b 1
)

REM Create virtual environment
echo 📦 สร้าง Virtual Environment...
if exist venv (
    echo ⚠️  Virtual environment มีอยู่แล้ว กำลังลบและสร้างใหม่...
    rmdir /s /q venv
)

python -m venv venv
if errorlevel 1 (
    echo ❌ สร้าง Virtual Environment ไม่สำเร็จ
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔗 เปิดใช้งาน Virtual Environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️  อัพเกรด pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📥 ติดตั้ง Dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ ติดตั้ง Dependencies ไม่สำเร็จ
    pause
    exit /b 1
)

REM Create necessary directories
echo 📁 สร้าง Directory ที่จำเป็น...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist models mkdir models
if not exist backups mkdir backups

REM Copy environment file
echo 🔧 ตั้งค่า Environment Variables...
if not exist .env (
    copy .env.example .env >nul
    echo ✅ สร้างไฟล์ .env จาก .env.example แล้ว
    echo ⚠️  กรุณาแก้ไขไฟล์ .env ตามความต้องการ
) else (
    echo ℹ️  ไฟล์ .env มีอยู่แล้ว
)

REM Setup database
echo 🗄️  ตั้งค่า Database...
python scripts/setup_database.py
if errorlevel 1 (
    echo ❌ ตั้งค่า Database ไม่สำเร็จ
    pause
    exit /b 1
)

REM Validate system
echo 🔍 ตรวจสอบระบบ...
python scripts/validate_system.py
if errorlevel 1 (
    echo ❌ ตรวจสอบระบบไม่ผ่าน
    pause
    exit /b 1
)

echo.
echo 🎉 Setup เสร็จสมบูรณ์!
echo ==================================
echo 📋 คำสั่งที่ต้องใช้:
echo 1. เปิดใช้งาน virtual environment: venv\Scripts\activate.bat
echo 2. ดาวน์โหลดข้อมูล FPL: python scripts/fetch_fpl_data.py
echo 3. ฝึกโมเดล ML: python scripts/train_models.py
echo 4. รันแอพพลิเคชั่น: flask run
echo 5. เข้าใช้งานที่: http://localhost:5000
echo.
echo 📚 หรือดูคู่มือการใช้งานที่ USER_GUIDE_TH.md
echo ==================================
pause