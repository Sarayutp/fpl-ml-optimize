#!/bin/bash

echo "🏆 FPL AI Optimizer - Setup Script"
echo "=================================="

# Check Python version
echo "📋 ตรวจสอบเวอร์ชั่น Python..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 ไม่พบ กรุณาติดตั้ง Python 3.11+ ก่อน"
    exit 1
fi

# Create virtual environment
echo "📦 สร้าง Virtual Environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment มีอยู่แล้ว กำลังลบและสร้างใหม่..."
    rm -rf venv
fi

python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ สร้าง Virtual Environment ไม่สำเร็จ"
    exit 1
fi

# Activate virtual environment
echo "🔗 เปิดใช้งาน Virtual Environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  อัพเกรด pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 ติดตั้ง Dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ ติดตั้ง Dependencies ไม่สำเร็จ"
    exit 1
fi

# Create necessary directories
echo "📁 สร้าง Directory ที่จำเป็น..."
mkdir -p data logs models backups

# Copy environment file
echo "🔧 ตั้งค่า Environment Variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ สร้างไฟล์ .env จาก .env.example แล้ว"
    echo "⚠️  กรุณาแก้ไขไฟล์ .env ตามความต้องการ"
else
    echo "ℹ️  ไฟล์ .env มีอยู่แล้ว"
fi

# Setup database
echo "🗄️  ตั้งค่า Database..."
python scripts/setup_database.py
if [ $? -ne 0 ]; then
    echo "❌ ตั้งค่า Database ไม่สำเร็จ"
    exit 1
fi

# Validate system
echo "🔍 ตรวจสอบระบบ..."
python scripts/validate_system.py
if [ $? -ne 0 ]; then
    echo "❌ ตรวจสอบระบบไม่ผ่าน"
    exit 1
fi

echo ""
echo "🎉 Setup เสร็จสมบูรณ์!"
echo "=================================="
echo "📋 คำสั่งที่ต้องใช้:"
echo "1. เปิดใช้งาน virtual environment: source venv/bin/activate"
echo "2. ดาวน์โหลดข้อมูล FPL: python scripts/fetch_fpl_data.py"
echo "3. ฝึกโมเดล ML: python scripts/train_models.py"
echo "4. รันแอพพลิเคชั่น: flask run"
echo "5. เข้าใช้งานที่: http://localhost:5000"
echo ""
echo "📚 หรือดูคู่มือการใช้งานที่ USER_GUIDE_TH.md"
echo "=================================="