# 🛠️ แก้ไขปัญหาการติดตั้ง FPL AI Optimizer

## ❌ ปัญหาที่เกิดขึ้น

```
pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'setuptools.build_meta'
```

**สาเหตุ:** 
- Version conflict ระหว่าง NumPy 1.24.4 กับ Python 3.12
- Missing build tools สำหรับ macOS
- Setuptools เก่าไม่รองรับ Python 3.12

---

## 🔧 วิธีแก้ไขแบบ Step-by-Step

### ขั้นตอนที่ 1: ใช้สคริปต์แก้ไขอัตโนมัติ

```bash
# อยู่ในโฟลเดอร์ fpl-ml-system
# virtual environment ต้องเปิดอยู่
source venv/bin/activate

# รันสคริปต์แก้ไข
./fix_installation.sh
```

### ขั้นตอนที่ 2: หากยังไม่สำเร็จ - แก้ไขแบบ Manual

#### 2.1 ลบ Virtual Environment เดิม
```bash
deactivate  # ออกจาก virtual environment
rm -rf venv  # ลบ virtual environment เดิม
```

#### 2.2 สร้าง Virtual Environment ใหม่
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2.3 ติดตั้ง Build Tools ก่อน
```bash
pip install --upgrade pip setuptools wheel
pip install Cython setuptools-scm build
```

#### 2.4 ติดตั้ง Dependencies ทีละขั้น
```bash
# Step 1: Core numerical libraries
pip install "numpy>=1.26.0"  # ใช้ version ใหม่ที่รองรับ Python 3.12
pip install "pandas>=2.1.0"

# Step 2: Machine Learning libraries  
pip install "scikit-learn>=1.3.0"
pip install "xgboost>=2.0.0" --no-cache-dir

# Step 3: Optimization library
pip install "PuLP>=2.7.0"

# Step 4: Web framework
pip install "Flask>=3.0.0"
pip install "Flask-SQLAlchemy>=3.0.5"
pip install "Flask-Migrate>=4.0.5"

# Step 5: API and validation
pip install "pydantic>=2.4.0"
pip install "requests>=2.31.0"

# Step 6: Development tools
pip install "pytest>=7.4.0"
pip install "black>=23.0.0"
pip install "gunicorn>=21.2.0"
pip install "python-dotenv>=1.0.0"
```

#### 2.5 ตรวจสอบการติดตั้ง
```bash
python -c "
import numpy, pandas, sklearn, xgboost, flask, pulp
print('✅ All core libraries imported successfully!')
print(f'NumPy: {numpy.__version__}')
print(f'Pandas: {pandas.__version__}')
print(f'XGBoost: {xgboost.__version__}')
print(f'Flask: {flask.__version__}')
"
```

---

## 🍎 วิธีแก้ไขเฉพาะ macOS

### หาก Error ยังคงมี - ติดตั้ง Xcode Command Line Tools

```bash
# ติดตั้ง Xcode command line tools
xcode-select --install

# หรือติดตั้งผ่าน Homebrew
brew install python@3.12
```

### ใช้ Homebrew Python แทน System Python

```bash
# ติดตั้ง Python ผ่าน Homebrew
brew install python@3.12

# ใช้ Homebrew Python สร้าง virtual environment
/opt/homebrew/bin/python3.12 -m venv venv
source venv/bin/activate

# ติดตั้ง dependencies
./fix_installation.sh
```

---

## 🐍 วิธีแก้ไขด้วย Conda (Alternative)

หากยังประสบปัญหา ใช้ Conda แทน pip:

```bash
# ติดตั้ง Miniconda (ถ้ายังไม่มี)
# https://docs.conda.io/en/latest/miniconda.html

# สร้าง conda environment
conda create -n fpl-optimizer python=3.11 -y
conda activate fpl-optimizer

# ติดตั้ง core packages ด้วย conda
conda install pandas numpy scikit-learn flask -y
conda install -c conda-forge xgboost pulp -y

# ติดตั้งส่วนที่เหลือด้วย pip
pip install pydantic flask-sqlalchemy flask-migrate requests pytest black gunicorn python-dotenv
```

---

## ✅ หลังแก้ไขเสร็จแล้ว

```bash
# ตั้งค่าฐานข้อมูล
python scripts/setup_database.py

# ดาวน์โหลดข้อมูล FPL และฝึกโมเดล
python scripts/quick_start.py

# เริ่มใช้งาน
flask run
```

---

## 🆘 หากยังแก้ไขไม่ได้

### ตัวเลือกที่ 1: ใช้ Docker (แนะนำ)
```bash
# ไม่ต้องติดตั้ง Python dependencies
docker-compose up -d
```

### ตัวเลือกที่ 2: ใช้ Python 3.11
```bash
# ติดตั้ง Python 3.11 แทน
pyenv install 3.11.7
pyenv local 3.11.7
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ตัวเลือกที่ 3: สร้างรายงานปัญหา
```bash
# สร้างรายงานระบบ
python scripts/system_info.py > installation_error_report.txt

# แนบไฟล์นี้เมื่อขอความช่วยเหลือ
```

---

## 📞 การขอความช่วยเหลือ

หากยังแก้ไขไม่ได้ กรุณาแนบข้อมูลต่อไปนี้:

1. **ระบบปฏิบัติการ:** `sw_vers` (macOS), `uname -a` (Linux)
2. **Python version:** `python3 --version`
3. **Pip version:** `pip --version` 
4. **Error message แบบเต็ม**
5. **การติดตั้ง Xcode tools:** `xcode-select -p`

**🔧 ปัญหานี้แก้ได้แน่นอน! เราจะช่วยให้ระบบทำงานได้** 💪