# 🚀 คู่มือติดตั้ง FPL AI Optimizer

**คู่มือติดตั้งและเริ่มใช้งานแบบละเอียดสำหรับผู้ใช้ทุกระดับ**

---

## 📋 ตารางเนื้อหา

1. [ข้อกำหนดระบบ](#-ข้อกำหนดระบบ)
2. [การติดตั้งแบบง่าย (แนะนำ)](#-การติดตั้งแบบง่าย-แนะนำ)
3. [การติดตั้งแบบละเอียด](#-การติดตั้งแบบละเอียด)
4. [การติดตั้งด้วย Docker](#-การติดตั้งด้วย-docker)
5. [การตรวจสอบการติดตั้ง](#-การตรวจสอบการติดตั้ง)
6. [การแก้ไขปัญหาการติดตั้ง](#-การแก้ไขปัญหาการติดตั้ง)

---

## 🖥️ ข้อกำหนดระบบ

### ข้อกำหนดขั้นต่ำ
- **CPU**: 2 cores
- **RAM**: 4GB ขึ้นไป
- **Storage**: 2GB พื้นที่ว่าง
- **Internet**: สำหรับดาวน์โหลดข้อมูล FPL

### ข้อกำหนดที่แนะนำ
- **CPU**: 4+ cores
- **RAM**: 8GB ขึ้นไป
- **Storage**: 5GB พื้นที่ว่าง
- **Internet**: ความเร็วเสถียร

### ซอฟต์แวร์ที่จำเป็น

#### สำหรับทุกระบบ
- **Python 3.11+** ([ดาวน์โหลด](https://python.org/downloads/))
- **Git** ([ดาวน์โหลด](https://git-scm.com/downloads))

#### เสริม (ไม่บังคับ)
- **Docker & Docker Compose** ([ดาวน์โหลด](https://docker.com/get-started))
- **Visual Studio Code** ([ดาวน์โหลด](https://code.visualstudio.com/))

---

## 🎯 การติดตั้งแบบง่าย (แนะนำ)

**ใช้เวลาประมาณ 10-15 นาที**

### ขั้นตอนที่ 1: ดาวน์โหลดโปรเจค

```bash
# สำหรับ Mac/Linux
git clone <repository-url>
cd fpl-ml-system

# สำหรับ Windows (ใช้ Command Prompt หรือ PowerShell)
git clone <repository-url>
cd fpl-ml-system
```

### ขั้นตอนที่ 2: รันสคริปต์ติดตั้งอัตโนมัติ

#### สำหรับ Mac/Linux:
```bash
# ให้สิทธิ์ในการรัน
chmod +x setup.sh

# รันสคริปต์ติดตั้ง
./setup.sh
```

#### สำหรับ Windows:
```cmd
# รันสคริปต์ติดตั้ง
setup.bat
```

### ขั้นตอนที่ 3: เปิดใช้งาน Virtual Environment

```bash
# สำหรับ Mac/Linux
source venv/bin/activate

# สำหรับ Windows
venv\Scripts\activate
```

### ขั้นตอนที่ 4: เริ่มใช้งานด่วน

```bash
# รันสคริปต์เริ่มต้นใช้งาน (ดาวน์โหลดข้อมูล + ฝึกโมเดล)
python scripts/quick_start.py

# เริ่มเซิร์ฟเวอร์
flask run
```

### ขั้นตอนที่ 5: เข้าใช้งาน

เปิดบราวเซอร์ไปที่: **http://localhost:5000**

---

## 🔧 การติดตั้งแบบละเอียด

**สำหรับผู้ที่ต้องการควบคุมการติดตั้งเอง**

### ขั้นตอนที่ 1: ตรวจสอบ Python

```bash
# ตรวจสอบเวอร์ชั่น Python
python3 --version
# ควรแสดง: Python 3.11.x หรือสูงกว่า

# หากไม่มี Python 3.11+ กรุณาติดตั้งก่อน
```

### ขั้นตอนที่ 2: โคลนโปรเจค

```bash
git clone <repository-url>
cd fpl-ml-system

# ตรวจสอบไฟล์ที่จำเป็น
ls -la
# ควรเห็น: requirements.txt, setup.sh, src/, scripts/
```

### ขั้นตอนที่ 3: สร้าง Virtual Environment

```bash
# สร้าง virtual environment
python3 -m venv venv

# เปิดใช้งาน
# สำหรับ Mac/Linux:
source venv/bin/activate

# สำหรับ Windows:
venv\Scripts\activate

# ตรวจสอบ (ต้องเห็น (venv) หน้าชื่อ terminal)
which python  # ควรชี้ไปที่ venv/bin/python
```

### ขั้นตอนที่ 4: ติดตั้ง Dependencies

```bash
# อัพเกรด pip
pip install --upgrade pip

# ติดตั้ง dependencies
pip install -r requirements.txt

# ตรวจสอบการติดตั้ง
pip list | grep -E "(flask|pandas|xgboost|pulp)"
```

### ขั้นตอนที่ 5: ตั้งค่า Environment

```bash
# คัดลอกไฟล์ตั้งค่า
cp .env.example .env

# แก้ไขการตั้งค่า (ไม่บังคับสำหรับการใช้งานพื้นฐาน)
nano .env  # หรือเปิดด้วย text editor อื่น
```

**การตั้งค่าที่สำคัญใน .env:**
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=sqlite:///data/fpl.db
FPL_API_BASE_URL=https://fantasy.premierleague.com/api/
CACHE_TTL=3600
```

### ขั้นตอนที่ 6: สร้างไดเร็กทอรีที่จำเป็น

```bash
mkdir -p data logs models backups
```

### ขั้นตอนที่ 7: ตั้งค่าฐานข้อมูล

```bash
# สร้างตารางในฐานข้อมูล
python scripts/setup_database.py

# ตรวจสอบว่าฐานข้อมูลถูกสร้าง
ls -la data/
# ควรเห็น: fpl.db
```

### ขั้นตอนที่ 8: ดาวน์โหลดข้อมูล FPL

```bash
# ดาวน์โหลดข้อมูลจาก FPL API
python scripts/fetch_fpl_data.py

# ตรวจสอบข้อมูล
python -c "
from src.services.data_service import DataService
ds = DataService()
print(f'Teams: {len(ds.get_teams())}')
print(f'Players: {len(ds.get_players())}')
"
```

### ขั้นตอนที่ 9: ฝึกโมเดล Machine Learning

```bash
# ฝึกโมเดล (อาจใช้เวลา 2-5 นาที)
python scripts/train_models.py

# ตรวจสอบโมเดลที่ถูกสร้าง
ls -la models/
# ควรเห็น: *.pkl files
```

### ขั้นตอนที่ 10: ตรวจสอบระบบ

```bash
# ตรวจสอบความพร้อมของระบบ
python scripts/validate_system.py

# ควรเห็น: "All validations PASSED! System is ready."
```

### ขั้นตอนที่ 11: เริ่มใช้งาน

```bash
# เริ่มเซิร์ฟเวอร์
flask run

# หรือรันแบบ debug mode
flask run --debug

# เซิร์ฟเวอร์จะเริ่มที่ http://localhost:5000
```

---

## 🐳 การติดตั้งด้วย Docker

**วิธีที่ง่ายที่สุดสำหรับ Production**

### ข้อกำหนด
- Docker 20.0+
- Docker Compose 2.0+
- 4GB RAM available for Docker

### ขั้นตอนที่ 1: โคลนและเตรียมไฟล์

```bash
git clone <repository-url>
cd fpl-ml-system

# คัดลอกไฟล์ environment
cp .env.example .env
```

### ขั้นตอนที่ 2: ปรับแต่ง Docker Configuration (ไม่บังคับ)

แก้ไขไฟล์ `docker-compose.yml` ตามความต้องการ:

```yaml
# เปลี่ยน port หากต้องการ
ports:
  - "8080:5000"  # ใช้ port 8080 แทน 5000

# เพิ่ม environment variables
environment:
  - SECRET_KEY=your-production-secret-key
  - FLASK_ENV=production
```

### ขั้นตอนที่ 3: สร้างและรัน Container

```bash
# สร้าง images และเริ่มใช้งาน
docker-compose up -d

# ตรวจสอบสถานะ
docker-compose ps

# ดู logs
docker-compose logs -f fpl-optimizer
```

### ขั้นตอนที่ 4: ตั้งค่าข้อมูลใน Container

```bash
# เข้าไปใน container
docker-compose exec fpl-optimizer bash

# ตั้งค่าฐานข้อมูล
python scripts/setup_database.py

# ดาวน์โหลดข้อมูล
python scripts/fetch_fpl_data.py

# ฝึกโมเดล
python scripts/train_models.py

# ออกจาก container
exit
```

### ขั้นตอนที่ 5: เข้าใช้งาน

เปิดบราวเซอร์ไปที่: **http://localhost:5000**

### การจัดการ Docker

```bash
# หยุดระบบ
docker-compose down

# เริ่มใหม่
docker-compose up -d

# อัพเดท images
docker-compose pull
docker-compose up -d --force-recreate

# ดูการใช้ทรัพยากร
docker-compose top

# ลบทุกอย่างรวมถึงข้อมูล
docker-compose down -v
```

---

## ✅ การตรวจสอบการติดตั้ง

### 1. ตรวจสอบความพร้อมของระบบ

```bash
# รันสคริปต์ตรวจสอบระบบ
python scripts/validate_system.py

# ควรเห็นผลลัพธ์:
# ✅ Directory Structure: PASS
# ✅ Model Imports: PASS  
# ✅ Configuration: PASS
# ✅ Database Schema: PASS
```

### 2. ตรวจสอบข้อมูลระบบ

```bash
# สร้างรายงานระบบ
python scripts/system_info.py

# จะสร้างไฟล์ system_report.json และแสดงรายงานบนหน้าจอ
```

### 3. ทดสอบ API

```bash
# ทดสอบ API health check
curl http://localhost:5000/api/health

# ควรได้ผลลัพธ์:
# {"success": true, "message": "API is healthy"}
```

### 4. ทดสอบเว็บไซต์

เปิดบราวเซอร์ไปที่ http://localhost:5000 และตรวจสอบ:

- [ ] หน้า Dashboard โหลดได้
- [ ] เมนูต่างๆ ทำงานได้
- [ ] หน้า Team Optimizer โหลดได้
- [ ] หน้า Player Scouting โหลดได้

### 5. ทดสอบฟีเจอร์หลัก

```bash
# ทดสอบการปรับทีม
curl -X POST http://localhost:5000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{"budget": 100.0, "max_players_per_team": 3}'

# ควรได้ผลลัพธ์ที่มี players, captain_id, total_cost, expected_points
```

---

## 🛠️ การแก้ไขปัญหาการติดตั้ง

### ปัญหาที่พบบ่อย

#### 1. Python Version ไม่ถูกต้อง

**ปัญหา:** `python3 --version` แสดงเวอร์ชั่นต่ำกว่า 3.11

**วิธีแก้:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# macOS (ใช้ Homebrew)
brew install python@3.11

# Windows: ดาวน์โหลดจาก python.org
```

#### 2. pip install ล้มเหลว

**ปัญหา:** ติดตั้ง requirements.txt ไม่สำเร็จ

**วิธีแก้:**
```bash
# อัพเกรด pip
pip install --upgrade pip setuptools wheel

# ติดตั้งทีละตัว
pip install flask pandas numpy scikit-learn xgboost pulp pydantic sqlalchemy

# หรือใช้ conda แทน pip
conda install pandas numpy scikit-learn
pip install flask xgboost pulp pydantic sqlalchemy
```

#### 3. Permission Error

**ปัญหา:** "Permission denied" บน Mac/Linux

**วิธีแก้:**
```bash
# ให้สิทธิ์ไฟล์ script
chmod +x setup.sh
chmod +x scripts/*.py

# หรือรันด้วย python โดยตรง
python setup.py  # แทน ./setup.sh
```

#### 4. Database Error

**ปัญหา:** ไม่สามารถสร้างฐานข้อมูลได้

**วิธีแก้:**
```bash
# สร้างไดเร็กทอรี data
mkdir -p data

# ลบฐานข้อมูลเก่า (ถ้ามี)
rm -f data/fpl.db

# สร้างใหม่
python scripts/setup_database.py

# ตรวจสอบสิทธิ์
ls -la data/
chmod 755 data/
```

#### 5. FPL API Connection Error

**ปัญหา:** ไม่สามารถดาวน์โหลดข้อมูลจาก FPL API

**วิธีแก้:**
```bash
# ทดสอบการเชื่อมต่อ
curl https://fantasy.premierleague.com/api/bootstrap-static/

# หากไม่สามารถเชื่อมต่อได้:
# 1. ตรวจสอบ internet connection
# 2. ตรวจสอบ firewall/proxy
# 3. ลองใหม่ภายหลัง (FPL API อาจไม่พร้อมใช้งานชั่วคราว)
```

#### 6. Memory Error

**ปัญหา:** หน่วยความจำไม่เพียงพอ

**วิธีแก้:**
```bash
# ลด batch size ในการฝึกโมเดล
# แก้ไขไฟล์ src/services/prediction_service.py
# เปลี่ยน n_estimators จาก 200 เป็น 100

# หรือเพิ่ม swap space (Linux)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 7. Port Already in Use

**ปัญหา:** Port 5000 ถูกใช้งานแล้ว

**วิธีแก้:**
```bash
# หา process ที่ใช้ port 5000
lsof -i :5000

# หยุด process (ถ้าไม่จำเป็น)
kill -9 <PID>

# หรือใช้ port อื่น
flask run --port 8000
```

### การขอความช่วยเหลือ

หากยังแก้ไขปัญหาไม่ได้:

1. **รันสคริปต์รายงานระบบ:**
```bash
python scripts/system_info.py > system_report.txt
```

2. **รวบรวมข้อมูลปัญหา:**
   - ระบบปฏิบัติการและเวอร์ชั่น
   - เวอร์ชั่น Python
   - ข้อความ error แบบเต็ม
   - ขั้นตอนที่ทำก่อนเกิดปัญหา

3. **สร้าง GitHub Issue พร้อมข้อมูลข้างต้น**

---

## 🚀 ขั้นตอนถัดไป

หลังจากติดตั้งสำเร็จแล้ว:

1. **อ่านคู่มือการใช้งาน**: `USER_GUIDE_TH.md`
2. **ทดลองใช้ฟีเจอร์ต่างๆ**: เริ่มจาก Team Optimizer
3. **ตั้งค่า Cron Job** (ไม่บังคับ): อัพเดทข้อมูลอัตโนมัติ
4. **เรียนรู้ API**: ดู API endpoints ที่พร้อมใช้งาน

**ขอให้สนุกกับการใช้งาน FPL AI Optimizer! 🏆⚽**