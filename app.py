from typing import Dict
import nltk
import os
import uuid
import sqlite3
import traceback
import time as time_module
import threading
import tempfile
import base64
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import config
import json
from flask_socketio import SocketIO, emit
from rag_system import GraphRAGSystem
from vector_db import VectorDBManager
from knowledge_graph import KnowledgeGraphManager

app = Flask(__name__)
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'doc', 'docx', 'md', 'xlsx', 'xls', 'pptx', 'rtf', 'odt', 'html'}
app.secret_key = 'hospital_secret_key_123'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['DATABASE'] = os.path.join(BASE_DIR, 'data/hospital.db')
app.config['KNOWLEDGE_BASE'] = config.EXTERNAL_FILE
app.config['VECTOR_DB_PATH'] = os.path.join(BASE_DIR, config.VECTOR_DB_PATH)
# 强制使用项目目录下的 documents 文件夹，忽略配置文件中可能的绝对路径
app.config['DOCUMENTS_DIR'] = os.path.join(BASE_DIR, 'documents')

os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
os.makedirs(app.config['KNOWLEDGE_BASE'], exist_ok=True)
os.makedirs(app.config['VECTOR_DB_PATH'], exist_ok=True)
os.makedirs(app.config['DOCUMENTS_DIR'], exist_ok=True)

nltk_data_path = os.path.join(BASE_DIR, 'nltk_data')
nltk.data.path.append(nltk_data_path)

socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化系统组件
kg_manager = KnowledgeGraphManager()
vdb_manager = VectorDBManager()
graph_rag = GraphRAGSystem(kg_manager, vdb_manager)


# ============================== 工具函数 ==============================
def get_row_field(row, field_name, default_value=''):
    if row is None:
        return default_value
    if field_name not in row.keys():
        return default_value
    value = row[field_name]
    return value if value is not None else default_value


def api_response(success=True, data=None, error=None, status_code=200):
    response = {
        'success': success,
        'data': data or {},
        'error': error,
        'timestamp': datetime.now().isoformat()
    }
    return jsonify(response), status_code


def get_active_prompt_content():
    """获取当前激活的Prompt模板内容"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT content FROM prompt_templates WHERE is_active = 1')
    row = c.fetchone()
    conn.close()
    if row:
        return row['content']
    return None


# ============================== 数据库初始化 ==============================
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            blood_type TEXT,
            height TEXT,
            weight TEXT,
            conditions TEXT,
            allergies TEXT,
            occupation TEXT,
            ethnicity TEXT,
            main_activity TEXT,
            education TEXT,
            employment TEXT,
            marital_status TEXT,
            is_smoker TEXT,
            is_drinker TEXT,
            surgery_history TEXT,
            medications TEXT,
            disease_history TEXT,
            systolic_bp TEXT,
            diastolic_bp TEXT,
            bp_measure_time TEXT,
            family_history TEXT,
            regular_exercise TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    columns_to_add = [
        ('occupation', 'TEXT'), ('ethnicity', 'TEXT'), ('main_activity', 'TEXT'),
        ('education', 'TEXT'), ('employment', 'TEXT'), ('marital_status', 'TEXT'),
        ('is_smoker', 'TEXT'), ('is_drinker', 'TEXT'), ('surgery_history', 'TEXT'),
        ('medications', 'TEXT'), ('disease_history', 'TEXT'), ('systolic_bp', 'TEXT'),
        ('diastolic_bp', 'TEXT'), ('bp_measure_time', 'TEXT'), ('family_history', 'TEXT'),
        ('regular_exercise', 'TEXT')
    ]

    c.execute("PRAGMA table_info(patients)")
    existing_columns = [col[1] for col in c.fetchall()]
    for column, col_type in columns_to_add:
        if column not in existing_columns:
            c.execute(f"ALTER TABLE patients ADD COLUMN {column} {col_type}")

    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS medical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            department TEXT NOT NULL,
            doctor TEXT NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS check_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            result TEXT NOT NULL,
            reference_range TEXT NOT NULL,
            unit TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            path TEXT NOT NULL,
            tags TEXT,
            file_size INTEGER DEFAULT 0,
            is_vectorized BOOLEAN DEFAULT 0,
            vector_size INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 检查knowledge_documents表新字段
    c.execute("PRAGMA table_info(knowledge_documents)")
    kd_columns = [col[1] for col in c.fetchall()]
    for col, ctype in [('file_size', 'INTEGER DEFAULT 0'), ('is_vectorized', 'BOOLEAN DEFAULT 0'), ('vector_size', 'INTEGER DEFAULT 0')]:
        if col not in kd_columns:
            c.execute(f"ALTER TABLE knowledge_documents ADD COLUMN {col} {ctype}")

    c.execute('''
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            content TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            is_active BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 医学影像分析记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS image_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            image_type TEXT NOT NULL,
            analysis_result TEXT NOT NULL,
            diagnosis TEXT,
            treatment_plan TEXT,
            is_saved_to_profile BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    ''')

    # 默认管理员: admin / admin123
    c.execute("SELECT COUNT(*) FROM admins WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        hashed_password = generate_password_hash('admin123')
        c.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ('admin', hashed_password))

    # 默认Prompt模板
    c.execute("SELECT COUNT(*) FROM prompt_templates")
    if c.fetchone()[0] == 0:
        default_templates = [
            ('健康知识推送模板', '用于生成个性化健康知识推送的模板',
             '''你是一名资深健康知识助手。请基于下方用户的**完整健康画像**与知识检索结果，生成**个性化健康知识推送**。

## 输出要求
1. 首先用一个信息卡片展示用户关键健康数据摘要
2. 针对用户的具体健康状况，分模块推送相关知识（如饮食、运动、用药、复查、注意事项）
3. 每条知识要标注来源：[来源](URL)
4. 以 Markdown 格式输出，使用小标题、列表、表情符号使内容易读
5. 内容必须与用户实际健康状况强相关，不可泛泛而谈

---
### 👤 用户健康画像
{user_input}

---
### 🔍 知识图谱匹配结果
{kg_results}

---
### 📄 相关文档片段
{vdb_results}

---
请开始生成专属健康知识推送：''', 'health_knowledge', 1),

            ('通用问答模板', '适用于一般知识问答场景',
             '''你是一个专业的知识问答助手，请基于以下知识回答用户问题：

### 相关知识：
{kg_results}

### 相关文档：
{vdb_results}

### 用户问题：
{user_input}

请给出专业、准确的回答：''', 'general', 0),

            ('医学诊断建议模板', '用于生成医学诊断建议',
             '''你是一名专业的医学顾问，请基于患者的健康信息和相关医学知识提供诊断建议：

### 患者信息：
{user_input}

### 医学知识图谱：
{kg_results}

### 相关医学文献：
{vdb_results}

请提供专业的医学建议，包括可能的诊断、建议检查和注意事项：''', 'medical', 0)
        ]
        c.executemany('''
            INSERT INTO prompt_templates (name, description, content, category, is_active) VALUES (?, ?, ?, ?, ?)
        ''', default_templates)

    conn.commit()
    conn.close()


def check_and_fix_database_tables():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prompt_templates'")
        if not c.fetchone():
            c.execute('''
                CREATE TABLE prompt_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL, description TEXT,
                    content TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'general',
                    is_active BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        conn.commit()
    except Exception as e:
        print(f"检查数据库表时出错: {e}")
        conn.rollback()
    finally:
        conn.close()


def add_test_patients():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    patients = [
        ('张伟', '13800138000', generate_password_hash('password123'), 42, '男', 'O型', '175cm', '72kg', '轻度高血压', '青霉素、花粉'),
        ('李娜', '13900139000', generate_password_hash('abc123'), 35, '女', 'A型', '162cm', '55kg', 'II型糖尿病', '无'),
        ('王强', '13700137000', generate_password_hash('pass1234'), 58, '男', 'B型', '178cm', '80kg', '冠心病', '海鲜'),
        ('赵敏', '13600136000', generate_password_hash('securepwd'), 29, '女', 'AB型', '168cm', '58kg', '健康', '无'),
        ('刘洋', '13500135000', generate_password_hash('mypassword'), 65, '男', 'O型', '170cm', '68kg', '慢性支气管炎', '花粉、尘螨')
    ]
    try:
        c.executemany('''
            INSERT INTO patients (name, phone, password, age, gender, blood_type, height, weight, conditions, allergies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', patients)
        conn.commit()
    except sqlite3.IntegrityError:
        pass

    for patient_id in range(1, 6):
        records = [
            (patient_id, '2024-10-15', '心血管内科', '王主任', '患者主诉近期偶有头晕现象，血压测量为145/92mmHg'),
            (patient_id, '2024-08-22', '体检中心', '李医生', '年度体检结果显示：血脂略高（LDL 3.5mmol/L）'),
            (patient_id, '2024-06-10', '呼吸科', '张医生', '患者因季节性花粉过敏就诊，症状包括打喷嚏、流涕')
        ]
        c.executemany('INSERT INTO medical_records (patient_id, date, department, doctor, description) VALUES (?, ?, ?, ?, ?)', records)

    for patient_id in range(1, 6):
        metrics = [
            (patient_id, '血压', '142/88', '90-120/60-80', 'mmHg', '2024-10-15', 'warning'),
            (patient_id, '空腹血糖', '5.8', '3.9-6.1', 'mmol/L', '2024-10-15', 'normal'),
            (patient_id, '总胆固醇', '5.3', '<5.2', 'mmol/L', '2024-08-22', 'warning')
        ]
        c.executemany('INSERT INTO check_metrics (patient_id, item, result, reference_range, unit, date, status) VALUES (?, ?, ?, ?, ?, ?, ?)', metrics)

    conn.commit()
    conn.close()


def init_all_db_and_patients():
    db_exists = os.path.exists(app.config['DATABASE'])
    init_db()
    check_and_fix_database_tables()
    if not db_exists:
        print("首次启动，添加测试数据...")
        add_test_patients()
    else:
        print("数据库已存在，跳过添加测试数据")


# ============================== 前台路由 ==============================
@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('SELECT * FROM patients WHERE phone = ?', (phone,))
        patient = c.fetchone()
        conn.close()
        if patient and check_password_hash(patient[3], password):
            session['user_id'] = patient[0]
            session['user_name'] = patient[1]
            return redirect(url_for('health_profile'))
        else:
            flash('手机号或密码不正确，请重试', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        age = request.form.get('age', '')
        gender = request.form.get('gender', '')
        blood_type = request.form.get('blood_type', '')
        height = request.form.get('height', '')
        weight = request.form.get('weight', '')
        conditions = request.form.get('conditions', '')
        allergies = request.form.get('allergies', '')
        occupation = request.form.get('occupation', '')
        ethnicity = request.form.get('ethnicity', '')
        education = request.form.get('education', '')
        marital_status = request.form.get('marital_status', '')
        is_smoker = request.form.get('is_smoker', '否')
        is_drinker = request.form.get('is_drinker', '否')
        surgery_history = request.form.get('surgery_history', '')
        medications = request.form.get('medications', '')
        disease_history = request.form.get('disease_history', '')
        systolic_bp = request.form.get('systolic_bp', '')
        diastolic_bp = request.form.get('diastolic_bp', '')
        bp_measure_time = request.form.get('bp_measure_time', '')
        family_history = request.form.get('family_history', '')
        regular_exercise = request.form.get('regular_exercise', '否')

        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO patients (
                    name, phone, password, age, gender, blood_type, height, weight,
                    conditions, allergies, occupation, ethnicity,
                    education, marital_status, is_smoker, is_drinker,
                    surgery_history, medications, disease_history, systolic_bp,
                    diastolic_bp, bp_measure_time, family_history, regular_exercise
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, phone, hashed_password, age, gender, blood_type, height, weight,
                  conditions, allergies, occupation, ethnicity, education, marital_status,
                  is_smoker, is_drinker, surgery_history, medications, disease_history,
                  systolic_bp, diastolic_bp, bp_measure_time, family_history, regular_exercise))
            conn.commit()
            flash('注册成功！请登录', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('该手机号已注册，请使用其他手机号', 'error')
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/health_profile')
def health_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    patient_id = session['user_id']
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = c.fetchone()
    c.execute('SELECT * FROM medical_records WHERE patient_id = ? ORDER BY date DESC', (patient_id,))
    medical_records = c.fetchall()
    c.execute('SELECT * FROM check_metrics WHERE patient_id = ? ORDER BY date DESC', (patient_id,))
    check_metrics = c.fetchall()
    conn.close()

    if not patient:
        return redirect(url_for('login'))

    health_data = {}
    fields = ['id', 'name', 'phone', 'age', 'gender', 'blood_type', 'height', 'weight',
              'conditions', 'allergies', 'occupation', 'ethnicity', 'main_activity',
              'education', 'employment', 'marital_status', 'is_smoker', 'is_drinker',
              'surgery_history', 'medications', 'disease_history', 'systolic_bp',
              'diastolic_bp', 'bp_measure_time', 'family_history', 'regular_exercise', 'created_at']
    for f in fields:
        health_data[f] = get_row_field(patient, f)

    # BMI计算
    try:
        height_val = float(health_data['height'].replace('cm', '')) if health_data['height'] else 0
        weight_val = float(health_data['weight'].replace('kg', '')) if health_data['weight'] else 0
        if height_val > 0 and weight_val > 0:
            height_in_m = height_val / 100
            health_data['bmi'] = round(weight_val / (height_in_m * height_in_m), 1)
            if health_data['bmi'] < 18.5:
                health_data['bmi_category'] = '偏瘦'
            elif health_data['bmi'] < 24:
                health_data['bmi_category'] = '正常'
            elif health_data['bmi'] < 28:
                health_data['bmi_category'] = '超重'
            else:
                health_data['bmi_category'] = '肥胖'
        else:
            health_data['bmi'] = ''
            health_data['bmi_category'] = ''
    except:
        health_data['bmi'] = ''
        health_data['bmi_category'] = ''

    formatted_records = [{'id': r['id'], 'date': r['date'], 'department': r['department'],
                          'doctor': r['doctor'], 'description': r['description']} for r in medical_records]
    formatted_metrics = [{'id': m['id'], 'item': m['item'], 'result': m['result'],
                          'range': m['reference_range'], 'unit': m['unit'],
                          'date': m['date'], 'status': m['status']} for m in check_metrics]

    return render_template('health_profile.html', health_data=health_data,
                           medical_records=formatted_records, check_metrics=formatted_metrics)


@app.route('/diagnosis')
def diagnosis():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('diagnosis.html')


@app.route('/profile/settings')
def profile_settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('profile_settings.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ============================== 前台API ==============================
@app.route('/api/health_data')
def get_health_data_api():
    """前台健康画像实时数据API"""
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    patient_id = session['user_id']
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = c.fetchone()
    c.execute('SELECT * FROM medical_records WHERE patient_id = ? ORDER BY date DESC', (patient_id,))
    records = c.fetchall()
    conn.close()

    if not patient:
        return jsonify({'error': '用户不存在'}), 404

    data = dict(patient)
    # BMI
    try:
        h = float(data.get('height', '0').replace('cm', ''))
        w = float(data.get('weight', '0').replace('kg', ''))
        if h > 0 and w > 0:
            data['bmi'] = round(w / ((h / 100) ** 2), 1)
        else:
            data['bmi'] = ''
    except:
        data['bmi'] = ''

    data['medical_records'] = [dict(r) for r in records]
    return jsonify(data)


@app.route('/api/health_metrics')
def get_health_metrics():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    patient_id = session['user_id']
    page = request.args.get('page', 1, type=int)
    per_page = 10
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    query = 'SELECT * FROM check_metrics WHERE patient_id = ?'
    params = [patient_id]
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)

    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    c.execute(count_query, params)
    total = c.fetchone()[0]

    query += ' ORDER BY date DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    c.execute(query, params)
    metrics = c.fetchall()
    conn.close()

    metrics_data = [{'id': m['id'], 'item': m['item'], 'result': m['result'],
                     'reference_range': m['reference_range'], 'unit': m['unit'],
                     'date': m['date'], 'status': m['status']} for m in metrics]
    total_pages = (total + per_page - 1) // per_page

    return jsonify({
        'metrics': metrics_data,
        'pagination': {'current_page': page, 'total_pages': total_pages,
                        'total_items': total, 'per_page': per_page}
    })


@app.route('/api/profile/basic', methods=['GET'])
def get_profile_basic():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    uid = session['user_id']
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, name, phone FROM patients WHERE id=?', (uid,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify(dict(row))


@app.route('/api/profile/basic', methods=['PUT'])
def update_profile_basic():
    """前台个人设置：只能修改姓名和密码，手机号不能修改"""
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    uid = session['user_id']
    data = request.get_json() or {}
    new_name = data.get('name')
    new_pwd = data.get('password')

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    updates = []
    args = []
    if new_name:
        updates.append('name=?')
        args.append(new_name)
    if new_pwd:
        updates.append('password=?')
        args.append(generate_password_hash(new_pwd))

    if not updates:
        conn.close()
        return jsonify({'error': '无更新内容'}), 400

    sql = f"UPDATE patients SET {', '.join(updates)} WHERE id=?"
    args.append(uid)
    c.execute(sql, args)
    conn.commit()
    conn.close()

    if new_name:
        session['user_name'] = new_name

    return jsonify({'success': True})


@app.route('/api/generate_health_knowledge', methods=['POST'])
def generate_health_knowledge():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    user_id = session['user_id']
    data = request.get_json() or {}
    user_text = data.get('user_text', '').strip()

    try:
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM patients WHERE id = ?', (user_id,))
        user = c.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': '用户信息不存在'}), 404

        # 获取最新就诊记录
        c.execute('SELECT * FROM medical_records WHERE patient_id = ? ORDER BY date DESC LIMIT 3', (user_id,))
        recent_records = c.fetchall()
        # 获取最新检查指标
        c.execute('SELECT * FROM check_metrics WHERE patient_id = ? ORDER BY date DESC LIMIT 5', (user_id,))
        recent_metrics = c.fetchall()
        conn.close()

        # 构建完整用户健康画像文本
        lines = [
            f"👤 **患者基本信息**",
            f"- 姓名：{get_row_field(user, 'name', '未填写')}",
            f"- 年龄：{get_row_field(user, 'age', '未记录')}岁",
            f"- 性别：{get_row_field(user, 'gender', '未记录')}",
            f"- 血型：{get_row_field(user, 'blood_type', '未记录')}",
            f"- 身高：{get_row_field(user, 'height', '未记录')}",
            f"- 体重：{get_row_field(user, 'weight', '未记录')}",
            f"- 职业：{get_row_field(user, 'occupation', '未记录')}",
            f"- 民族：{get_row_field(user, 'ethnicity', '未记录')}",
            f"- 婚姻状况：{get_row_field(user, 'marital_status', '未记录')}",
        ]

        lines.append(f"\n🏥 **健康状况**")
        lines.append(f"- 主诊断：{get_row_field(user, 'conditions', '无特殊记录')}")
        lines.append(f"- 过敏史：{get_row_field(user, 'allergies', '无')}")
        lines.append(f"- 疾病史：{get_row_field(user, 'disease_history', '无')}")
        lines.append(f"- 家族病史：{get_row_field(user, 'family_history', '无')}")
        lines.append(f"- 手术史：{get_row_field(user, 'surgery_history', '无')}")
        lines.append(f"- 用药情况：{get_row_field(user, 'medications', '无')}")

        bp_s = get_row_field(user, 'systolic_bp')
        bp_d = get_row_field(user, 'diastolic_bp')
        if bp_s and bp_d:
            lines.append(f"- 血压：{bp_s}/{bp_d} mmHg")

        lines.append(f"\n🏃 **生活习惯**")
        lines.append(f"- 吸烟：{get_row_field(user, 'is_smoker', '否')}")
        lines.append(f"- 饮酒：{get_row_field(user, 'is_drinker', '否')}")
        lines.append(f"- 规律运动：{get_row_field(user, 'regular_exercise', '否')}")

        if recent_records:
            lines.append(f"\n📋 **近期就诊记录**")
            for r in recent_records:
                lines.append(f"- [{r['date']}] {r['department']} - {r['doctor']}：{r['description']}")

        if recent_metrics:
            lines.append(f"\n📊 **近期检查指标**")
            for m in recent_metrics:
                status_text = '⚠️异常' if m['status'] == 'warning' else '✅正常'
                lines.append(f"- {m['item']}：{m['result']} {m['unit']}（参考：{m['reference_range']}）{status_text}")

        if user_text:
            lines.append(f"\n📝 **用户补充信息**：{user_text}")

        health_text = "\n".join(lines)

        # 使用 GraphRAG 系统生成知识（自动使用激活的Prompt模板）
        rag_result = graph_rag.query(
            user_input=health_text,
            depth=2,
            similarity_threshold=0.75,
            top_k=5
        )

        return jsonify({
            'success': True,
            'knowledge_content': rag_result['answer'],
            'user_profile_summary': health_text
        })

    except Exception as e:
        print(f"生成健康知识失败: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'生成健康知识失败: {str(e)}'}), 500


# ============================== 后台路由 ==============================
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('SELECT * FROM admins WHERE username = ?', (username,))
        admin = c.fetchone()
        conn.close()
        if admin and check_password_hash(admin[2], password):
            session['admin_id'] = admin[0]
            session['admin_name'] = admin[1]
            return redirect(url_for('admin_dashboard'))
        else:
            flash('管理员账号或密码错误', 'error')
    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('search', '').strip()

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    if search:
        c.execute('SELECT COUNT(*) FROM patients WHERE name LIKE ? OR phone LIKE ? OR conditions LIKE ?',
                  (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        c.execute('SELECT COUNT(*) FROM patients')
    total = c.fetchone()[0]

    total_pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page

    if search:
        c.execute('SELECT * FROM patients WHERE name LIKE ? OR phone LIKE ? OR conditions LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?',
                  (f'%{search}%', f'%{search}%', f'%{search}%', per_page, offset))
    else:
        c.execute('SELECT * FROM patients ORDER BY id DESC LIMIT ? OFFSET ?', (per_page, offset))
    patients = c.fetchall()
    conn.close()

    patients_data = []
    for p in patients:
        patients_data.append({
            'id': p[0], 'name': p[1], 'phone': p[2], 'age': p[4],
            'gender': p[5], 'blood_type': p[6], 'height': p[7], 'weight': p[8],
            'conditions': p[9], 'allergies': p[10], 'created_at': p[-1] if len(p) > 11 else ''
        })

    return render_template('admin_dashboard.html', patients=patients_data,
                           page=page, per_page=per_page, total=total,
                           total_pages=total_pages, search=search)


# 后台：新增用户（通过手机号与前台联通）
@app.route('/admin/patient/add', methods=['POST'])
def add_patient():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        phone = data.get('phone')
        # 检查手机号是否存在
        c.execute('SELECT id FROM patients WHERE phone = ?', (phone,))
        existing = c.fetchone()
        if existing:
            # 手机号已存在 -> 合并数据（更新健康信息到已存在的用户）
            patient_id = existing[0]
            c.execute('''
                UPDATE patients SET
                    name = COALESCE(?, name), age = COALESCE(?, age), gender = COALESCE(?, gender),
                    blood_type = COALESCE(?, blood_type), height = COALESCE(?, height), weight = COALESCE(?, weight),
                    conditions = COALESCE(?, conditions), allergies = COALESCE(?, allergies),
                    occupation = COALESCE(?, occupation), ethnicity = COALESCE(?, ethnicity),
                    education = COALESCE(?, education), marital_status = COALESCE(?, marital_status),
                    is_smoker = COALESCE(?, is_smoker), is_drinker = COALESCE(?, is_drinker),
                    surgery_history = COALESCE(?, surgery_history), medications = COALESCE(?, medications),
                    disease_history = COALESCE(?, disease_history), systolic_bp = COALESCE(?, systolic_bp),
                    diastolic_bp = COALESCE(?, diastolic_bp), bp_measure_time = COALESCE(?, bp_measure_time),
                    family_history = COALESCE(?, family_history), regular_exercise = COALESCE(?, regular_exercise)
                WHERE id = ?
            ''', (data.get('name'), data.get('age'), data.get('gender'), data.get('blood_type'),
                  data.get('height'), data.get('weight'), data.get('conditions'), data.get('allergies'),
                  data.get('occupation'), data.get('ethnicity'), data.get('education'), data.get('marital_status'),
                  data.get('is_smoker'), data.get('is_drinker'), data.get('surgery_history'), data.get('medications'),
                  data.get('disease_history'), data.get('systolic_bp'), data.get('diastolic_bp'),
                  data.get('bp_measure_time'), data.get('family_history'), data.get('regular_exercise'),
                  patient_id))
            conn.commit()
            return jsonify({'success': True, 'patient_id': patient_id, 'merged': True,
                            'message': '手机号已存在，已合并健康信息'})
        else:
            # 新建用户
            c.execute('''
                INSERT INTO patients (
                    name, phone, password, age, gender, blood_type, height, weight,
                    conditions, allergies, occupation, ethnicity,
                    education, marital_status, is_smoker, is_drinker,
                    surgery_history, medications, disease_history, systolic_bp,
                    diastolic_bp, bp_measure_time, family_history, regular_exercise
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data.get('name'), phone, generate_password_hash(data.get('password', '123456')),
                  data.get('age'), data.get('gender'), data.get('blood_type'), data.get('height'),
                  data.get('weight'), data.get('conditions'), data.get('allergies'), data.get('occupation'),
                  data.get('ethnicity'), data.get('education'), data.get('marital_status'),
                  data.get('is_smoker', '否'), data.get('is_drinker', '否'), data.get('surgery_history'),
                  data.get('medications'), data.get('disease_history'), data.get('systolic_bp'),
                  data.get('diastolic_bp'), data.get('bp_measure_time'), data.get('family_history'),
                  data.get('regular_exercise', '否')))
            conn.commit()
            return jsonify({'success': True, 'patient_id': c.lastrowid})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/patient/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('DELETE FROM medical_records WHERE patient_id = ?', (patient_id,))
        c.execute('DELETE FROM check_metrics WHERE patient_id = ?', (patient_id,))
        c.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/patient/<int:patient_id>/preview')
def preview_patient(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = c.fetchone()
    conn.close()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
    patient_data = dict(patient)
    try:
        h = float(patient_data.get('height', '0').replace('cm', ''))
        w = float(patient_data.get('weight', '0').replace('kg', ''))
        if h > 0 and w > 0:
            patient_data['bmi'] = round(w / ((h / 100) ** 2), 1)
        else:
            patient_data['bmi'] = ''
    except:
        patient_data['bmi'] = ''
    return jsonify(patient_data)


@app.route('/admin/patient/<int:patient_id>/update_basic', methods=['POST'])
def update_patient_basic(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE patients SET
                name = COALESCE(?, name), phone = COALESCE(?, phone),
                age = COALESCE(?, age), gender = COALESCE(?, gender),
                blood_type = COALESCE(?, blood_type), height = COALESCE(?, height),
                weight = COALESCE(?, weight), conditions = COALESCE(?, conditions),
                allergies = COALESCE(?, allergies), occupation = COALESCE(?, occupation),
                ethnicity = COALESCE(?, ethnicity), education = COALESCE(?, education),
                marital_status = COALESCE(?, marital_status), is_smoker = COALESCE(?, is_smoker),
                is_drinker = COALESCE(?, is_drinker), surgery_history = COALESCE(?, surgery_history),
                medications = COALESCE(?, medications), disease_history = COALESCE(?, disease_history),
                systolic_bp = COALESCE(?, systolic_bp), diastolic_bp = COALESCE(?, diastolic_bp),
                bp_measure_time = COALESCE(?, bp_measure_time), family_history = COALESCE(?, family_history),
                regular_exercise = COALESCE(?, regular_exercise)
            WHERE id = ?
        ''', (data.get('name'), data.get('phone'), data.get('age'), data.get('gender'),
              data.get('blood_type'), data.get('height'), data.get('weight'), data.get('conditions'),
              data.get('allergies'), data.get('occupation'), data.get('ethnicity'), data.get('education'),
              data.get('marital_status'), data.get('is_smoker'), data.get('is_drinker'),
              data.get('surgery_history'), data.get('medications'), data.get('disease_history'),
              data.get('systolic_bp'), data.get('diastolic_bp'), data.get('bp_measure_time'),
              data.get('family_history'), data.get('regular_exercise'), patient_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/patient/<int:patient_id>')
def get_patient_details(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = c.fetchone()
    c.execute('SELECT * FROM medical_records WHERE patient_id = ? ORDER BY date DESC', (patient_id,))
    medical_records = c.fetchall()
    c.execute('SELECT * FROM check_metrics WHERE patient_id = ? ORDER BY date DESC', (patient_id,))
    check_metrics = c.fetchall()
    conn.close()

    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    patient_data = dict(patient)
    patient_data['medical_records'] = [dict(r) for r in medical_records]
    patient_data['check_metrics'] = [dict(m) for m in check_metrics]
    return jsonify(patient_data)


@app.route('/admin/patient/<int:patient_id>/update_full', methods=['PUT'])
def admin_update_patient_full(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE patients SET
                name=?, phone=?, age=?, gender=?, blood_type=?, height=?, weight=?,
                conditions=?, allergies=?, occupation=?, ethnicity=?, education=?,
                marital_status=?, is_smoker=?, is_drinker=?, regular_exercise=?,
                systolic_bp=?, diastolic_bp=?, bp_measure_time=?,
                surgery_history=?, medications=?, disease_history=?, family_history=?
            WHERE id=?
        ''', (data.get('name', ''), data.get('phone', ''), data.get('age', ''), data.get('gender', ''),
              data.get('blood_type', ''), data.get('height', ''), data.get('weight', ''),
              data.get('conditions', ''), data.get('allergies', ''), data.get('occupation', ''),
              data.get('ethnicity', ''), data.get('education', ''), data.get('marital_status', ''),
              data.get('is_smoker', '否'), data.get('is_drinker', '否'), data.get('regular_exercise', '否'),
              data.get('systolic_bp', ''), data.get('diastolic_bp', ''), data.get('bp_measure_time', ''),
              data.get('surgery_history', ''), data.get('medications', ''), data.get('disease_history', ''),
              data.get('family_history', ''), patient_id))

        c.execute('DELETE FROM check_metrics WHERE patient_id=?', (patient_id,))
        for m in data.get('metrics', []):
            c.execute(
                'INSERT INTO check_metrics(patient_id,item,result,reference_range,unit,date,status) VALUES (?,?,?,?,?,?,?)',
                (patient_id, m['item'], m['result'], m['reference_range'], m['unit'], m['date'], m['status']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# 健康指标 CRUD (admin)
@app.route('/admin/patient/<int:patient_id>/metrics', methods=['GET'])
def admin_list_metrics(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM check_metrics WHERE patient_id=? ORDER BY date DESC', (patient_id,))
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/admin/patient/<int:patient_id>/metrics', methods=['POST'])
def admin_add_metric(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('INSERT INTO check_metrics(patient_id,item,result,reference_range,unit,date,status) VALUES (?,?,?,?,?,?,?)',
              (patient_id, data['item'], data['result'], data['reference_range'], data['unit'], data['date'], data['status']))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': new_id})


@app.route('/admin/metrics/<int:metric_id>', methods=['PUT'])
def admin_update_metric(metric_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('UPDATE check_metrics SET item=?,result=?,reference_range=?,unit=?,date=?,status=? WHERE id=?',
              (data['item'], data['result'], data['reference_range'], data['unit'], data['date'], data['status'], metric_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/admin/metrics/<int:metric_id>', methods=['DELETE'])
def admin_delete_metric(metric_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('DELETE FROM check_metrics WHERE id=?', (metric_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# 就诊记录 CRUD
@app.route('/admin/patient/<int:patient_id>/add_medical_record', methods=['POST'])
def add_medical_record(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('INSERT INTO medical_records (patient_id, date, department, doctor, description) VALUES (?, ?, ?, ?, ?)',
                  (patient_id, data['date'], data['department'], data['doctor'], data['description']))
        conn.commit()
        return jsonify({'success': True, 'record_id': c.lastrowid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/medical_record/<int:record_id>/update', methods=['POST'])
def update_medical_record(record_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('UPDATE medical_records SET date=?, department=?, doctor=?, description=? WHERE id=?',
                  (data['date'], data['department'], data['doctor'], data['description'], record_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/medical_record/<int:record_id>/delete', methods=['DELETE'])
def delete_medical_record(record_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('DELETE FROM medical_records WHERE id = ?', (record_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/check_metric/<int:metric_id>/update', methods=['POST'])
def update_check_metric(metric_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('UPDATE check_metrics SET item=?, result=?, reference_range=?, unit=?, date=?, status=? WHERE id=?',
                  (data['item'], data['result'], data['reference_range'], data['unit'], data['date'], data['status'], metric_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/check_metric/<int:metric_id>/delete', methods=['DELETE'])
def delete_check_metric(metric_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('DELETE FROM check_metrics WHERE id = ?', (metric_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ============================== 知识库管理 ==============================
@app.route('/admin/knowledge')
def knowledge_management():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    return render_template('knowledge_management.html')


@app.route('/admin/knowledge/stats')
def get_knowledge_stats():
    """获取知识库统计信息"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM knowledge_documents')
    total_docs = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM knowledge_documents WHERE is_vectorized = 1')
    vectorized_count = c.fetchone()[0]
    c.execute('SELECT tags FROM knowledge_documents WHERE tags IS NOT NULL AND tags != ""')
    all_tags = c.fetchall()
    conn.close()

    # 收集所有标签
    tag_set = set()
    for row in all_tags:
        for tag in row[0].split(','):
            tag = tag.strip()
            if tag:
                tag_set.add(tag)

    # 计算文档目录大小
    doc_dir = app.config['DOCUMENTS_DIR']
    total_file_size = 0
    if os.path.exists(doc_dir):
        for f in os.listdir(doc_dir):
            fp = os.path.join(doc_dir, f)
            if os.path.isfile(fp):
                total_file_size += os.path.getsize(fp)

    # 向量库大小
    vdb_path = app.config['VECTOR_DB_PATH']
    total_vector_size = 0
    if os.path.exists(vdb_path):
        for root, dirs, files in os.walk(vdb_path):
            for f in files:
                total_vector_size += os.path.getsize(os.path.join(root, f))

    try:
        vector_stats = vdb_manager.get_stats()
    except:
        vector_stats = {}

    return jsonify({
        'total_docs': total_docs,
        'vectorized_count': vectorized_count,
        'tags': sorted(list(tag_set)),
        'total_file_size': total_file_size,
        'total_vector_size': total_vector_size,
        'vector_stats': vector_stats
    })


@app.route('/admin/knowledge/documents', methods=['GET'])
def list_documents():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    page = request.args.get('page', 1, type=int)
    per_page = 10
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM knowledge_documents')
    total = c.fetchone()[0]
    total_pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page
    c.execute('SELECT * FROM knowledge_documents ORDER BY created_at DESC LIMIT ? OFFSET ?', (per_page, offset))
    documents = c.fetchall()
    conn.close()

    docs_data = []
    for doc in documents:
        d = dict(doc)
        d['tags'] = d['tags'].split(',') if d.get('tags') else []
        # 检查文件是否存在并获取大小
        if d['type'] == 'file' and os.path.exists(d['path']):
            d['file_size'] = os.path.getsize(d['path'])
        docs_data.append(d)

    return jsonify({'items': docs_data, 'total': total, 'pages': total_pages, 'current_page': page})


@app.route('/admin/knowledge/documents', methods=['POST'])
def create_document():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    name = request.form.get('name')
    doc_type = request.form.get('type')
    tags = request.form.get('tags', '')
    socket_id = request.form.get('socket_id')

    if not name or not doc_type:
        return jsonify({'error': '缺少必要参数'}), 400

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        if doc_type == 'file':
            if 'file' not in request.files:
                return jsonify({'error': '未选择文件'}), 400
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': '未选择文件'}), 400

            # 从原始文件名提取扩展名（secure_filename会丢失中文前缀）
            original_filename = file.filename
            original_ext = os.path.splitext(original_filename)[1].lower()  # e.g. '.docx'
            ext_no_dot = original_ext.lstrip('.')

            if not ext_no_dot:
                return jsonify({'error': '无法识别文件类型，请确保文件有扩展名'}), 400

            # 生成安全文件名：用uuid+原始扩展名
            safe_name = secure_filename(original_filename)
            if not safe_name or '.' not in safe_name:
                # secure_filename丢失了扩展名（中文文件名），用uuid代替
                safe_name = f"doc_{uuid.uuid4().hex[:8]}{original_ext}"

            file_path = os.path.join(app.config['DOCUMENTS_DIR'], safe_name)
            counter = 1
            while os.path.exists(file_path):
                name_part, ext = os.path.splitext(safe_name)
                file_path = os.path.join(app.config['DOCUMENTS_DIR'], f"{name_part}_{counter}{ext}")
                counter += 1
            file.save(file_path)
            path = os.path.abspath(file_path)
            file_size = os.path.getsize(path)

        elif doc_type == 'url':
            url = request.form.get('url')
            if not url:
                return jsonify({'error': '缺少URL参数'}), 400
            if not url.startswith('http://') and not url.startswith('https://'):
                return jsonify({'error': 'URL必须以http://或https://开头'}), 400
            # 仅记录URL，不立即爬取，向量化时才爬取
            path = url
            file_size = 0
        else:
            return jsonify({'error': '无效的文档类型'}), 400

        c.execute('INSERT INTO knowledge_documents (name, type, path, tags, file_size) VALUES (?, ?, ?, ?, ?)',
                  (name, doc_type, path, tags, file_size))
        conn.commit()
        doc_id = c.lastrowid

        return jsonify({'success': True, 'document_id': doc_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'创建文档失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/admin/knowledge/documents/<int:doc_id>', methods=['PUT'])
def update_document(doc_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    name = request.form.get('name')
    doc_type = request.form.get('type')
    tags = request.form.get('tags', '')
    url = request.form.get('url', '')
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute('SELECT * FROM knowledge_documents WHERE id = ?', (doc_id,))
        document = c.fetchone()
        if not document:
            return jsonify({'error': '文档不存在'}), 404

        new_file_path = None
        if 'file' in request.files and request.files['file']:
            file = request.files['file']
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['DOCUMENTS_DIR'], filename)
                counter = 1
                while os.path.exists(file_path):
                    name_part, ext = os.path.splitext(filename)
                    file_path = os.path.join(app.config['DOCUMENTS_DIR'], f"{name_part}_{counter}{ext}")
                    counter += 1
                file.save(file_path)
                new_file_path = file_path

        if doc_type == 'url':
            new_path = url if url else document['path']
        else:
            new_path = new_file_path if new_file_path else document['path']

        c.execute('UPDATE knowledge_documents SET name=?, type=?, path=?, tags=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                  (name or document['name'], doc_type or document['type'], new_path, tags or document['tags'], doc_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/knowledge/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute('SELECT * FROM knowledge_documents WHERE id = ?', (doc_id,))
        document = c.fetchone()
        if not document:
            return jsonify({'error': '文档不存在'}), 404
        c.execute('DELETE FROM knowledge_documents WHERE id = ?', (doc_id,))
        conn.commit()
        if document['type'] == 'file' and os.path.exists(document['path']):
            try:
                os.remove(document['path'])
            except:
                pass
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# WebSocket
@socketio.on('connect')
def handle_connect():
    print(f'客户端连接: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    print(f'客户端断开: {request.sid}')


@socketio.on('start_vectorization')
def handle_start_vectorization(data):
    doc_id = data['doc_id']
    session_id = request.sid
    emit('vectorization_update', {'message': '<div class="info-message">🚀 开始向量化处理...</div>'}, room=session_id)
    socketio.start_background_task(vectorize_document_task, doc_id, session_id)


def vectorize_document_task(doc_id, session_id):
    try:
        def log_callback(message, message_type="info"):
            socketio.emit('vectorization_update', {
                'message': f'<div class="{message_type}-message">{message}</div>'
            }, room=session_id)

        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('SELECT * FROM knowledge_documents WHERE id = ?', (doc_id,))
        document = c.fetchone()
        conn.close()

        if not document:
            log_callback("❌ 文档不存在", "error")
            socketio.emit('vectorization_error', {'message': '文档不存在'}, room=session_id)
            return

        doc_name, doc_type, doc_path, doc_tags = document[1], document[2], document[3], document[4] or ""
        log_callback(f"📄 文档: {doc_name}")
        log_callback(f"📂 类型: {doc_type}")

        if doc_type == 'file':
            if not os.path.isabs(doc_path):
                doc_path = os.path.join(app.config['DOCUMENTS_DIR'], os.path.basename(doc_path))
            if not os.path.exists(doc_path):
                log_callback(f"❌ 文件不存在: {doc_path}", "error")
                socketio.emit('vectorization_error', {'message': f'文件不存在: {doc_path}'}, room=session_id)
                return
            try:
                success = vdb_manager.update_single_file(doc_path, doc_tags, log_callback=log_callback)
                if success:
                    # 更新数据库标记为已向量化
                    conn2 = sqlite3.connect(app.config['DATABASE'])
                    c2 = conn2.cursor()
                    c2.execute('UPDATE knowledge_documents SET is_vectorized = 1 WHERE id = ?', (doc_id,))
                    conn2.commit()
                    conn2.close()

                    log_callback("✅ 向量化处理成功完成!", "success")
                    stats = vdb_manager.get_stats()
                    socketio.emit('vectorization_complete', {'stats': stats}, room=session_id)
                else:
                    log_callback("❌ 向量化处理失败", "error")
                    socketio.emit('vectorization_error', {'message': '向量化处理失败'}, room=session_id)
            except Exception as e:
                log_callback(f"❌ 异常: {str(e)}", "error")
                socketio.emit('vectorization_error', {'message': str(e)}, room=session_id)

        elif doc_type == 'url':
            # URL类型：实时爬取网页文本 → 临时文件向量化 → 删除临时文件
            # 始终从URL爬取，不保存永久文件，节省存储
            try:
                url = doc_path  # path字段存储的就是原始URL
                if not url.startswith('http://') and not url.startswith('https://'):
                    log_callback(f"❌ 无效的URL: {url}", "error")
                    socketio.emit('vectorization_error', {'message': f'无效URL: {url}'}, room=session_id)
                    return

                log_callback(f"🌐 正在爬取URL内容: {url}", "info")
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                log_callback(f"📥 网页响应: {response.status_code}, 大小: {len(response.content)} bytes", "info")

                soup = BeautifulSoup(response.content, 'html.parser')
                for el in soup.select('script, style, nav, footer, aside, .advertisement'):
                    el.decompose()
                content_text = soup.get_text()
                content_text = '\n'.join([l.strip() for l in content_text.split('\n') if l.strip()])

                if not content_text or len(content_text) < 50:
                    log_callback("⚠️ 爬取到的文本内容过少，可能页面结构特殊", "error")
                    socketio.emit('vectorization_error', {'message': '爬取内容过少'}, room=session_id)
                    return

                log_callback(f"📝 提取到 {len(content_text)} 字符文本", "success")
                log_callback("🔄 开始向量化（使用临时文件）...", "info")

                # 写入临时文件用于向量化，完成后删除
                tmp_path = None
                try:
                    # 使用固定命名避免乱码，写入UTF-8 BOM确保TextLoader可读
                    tmp_name = f"_url_tmp_{doc_id}.txt"
                    tmp_path = os.path.join(app.config['DOCUMENTS_DIR'], tmp_name)
                    with open(tmp_path, 'w', encoding='utf-8') as f:
                        f.write(content_text)

                    success = vdb_manager.update_single_file(tmp_path, doc_tags, log_callback=log_callback)
                    if success:
                        conn2 = sqlite3.connect(app.config['DATABASE'])
                        c2 = conn2.cursor()
                        c2.execute('UPDATE knowledge_documents SET is_vectorized = 1 WHERE id = ?', (doc_id,))
                        conn2.commit()
                        conn2.close()
                        log_callback("✅ URL文档向量化成功!", "success")
                        stats = vdb_manager.get_stats()
                        socketio.emit('vectorization_complete', {'stats': stats}, room=session_id)
                    else:
                        log_callback("❌ 向量化失败", "error")
                        socketio.emit('vectorization_error', {'message': '向量化失败'}, room=session_id)
                finally:
                    # 删除临时文件，不永久保存
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                            log_callback("🗑️ 临时文件已清理", "info")
                        except:
                            pass

            except requests.exceptions.RequestException as e:
                log_callback(f"❌ 网络请求失败: {str(e)}", "error")
                socketio.emit('vectorization_error', {'message': f'爬取失败: {str(e)}'}, room=session_id)
            except Exception as e:
                log_callback(f"❌ URL处理失败: {str(e)}", "error")
                socketio.emit('vectorization_error', {'message': str(e)}, room=session_id)
    except Exception as e:
        socketio.emit('vectorization_error', {'message': str(e)}, room=session_id)
        traceback.print_exc()


@app.route('/admin/knowledge/documents/<int:doc_id>/vectorize', methods=['POST'])
def vectorize_document(doc_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('SELECT * FROM knowledge_documents WHERE id = ?', (doc_id,))
        document = c.fetchone()
        if not document:
            return jsonify({'error': '文档不存在'}), 404
        tags = document[4] or ""
        if document[2] == 'file':
            success = vdb_manager.update_single_file(document[3], tags)
            if success:
                c.execute('UPDATE knowledge_documents SET is_vectorized = 1 WHERE id = ?', (doc_id,))
                conn.commit()
                return jsonify({'success': True})
            return jsonify({'error': '向量化失败'}), 500
        return jsonify({'error': 'URL向量化请使用WebSocket'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/vector_db_stats')
def get_vector_db_stats():
    try:
        stats = vdb_manager.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def crawl_url_content(url, doc_id, socket_id):
    try:
        socketio.emit('crawling_update', {'doc_id': doc_id, 'message': '开始爬取...', 'progress': 10}, room=socket_id)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        socketio.emit('crawling_update', {'doc_id': doc_id, 'message': '解析内容...', 'progress': 50}, room=socket_id)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('h1') or soup.find('title')
        title_text = title.get_text().strip() if title else "无标题"
        for el in soup.select('script, style, nav, footer, aside'):
            el.decompose()
        content = soup.find('body')
        content_text = content.get_text() if content else ""
        content_text = '\n'.join([l.strip() for l in content_text.split('\n') if l.strip()])

        filename = f"web_content_{doc_id}_{int(time_module.time())}.txt"
        filepath = os.path.join(app.config['DOCUMENTS_DIR'], filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"标题: {title_text}\n\n正文:\n{content_text}")

        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('UPDATE knowledge_documents SET path = ? WHERE id = ?', (filepath, doc_id))
        conn.commit()
        conn.close()

        socketio.emit('crawling_update', {'doc_id': doc_id, 'message': '爬取完成', 'progress': 100, 'completed': True, 'filepath': filepath}, room=socket_id)
    except Exception as e:
        socketio.emit('crawling_error', {'doc_id': doc_id, 'message': f'爬取失败: {str(e)}'}, room=socket_id)


# ============================== 知识图谱管理 ==============================
kg_update_status = {"status": "idle", "msg": ""}


def _async_update(text):
    global kg_update_status
    kg_update_status = {"status": "running", "msg": ""}
    try:
        kg = KnowledgeGraphManager()
        kg.process_user_query(text, save_to_db=True, depth=2, similarity_threshold=0.7, top_k=5)
        kg_update_status = {"status": "done", "msg": "知识图谱更新完成！"}
    except Exception as e:
        kg_update_status = {"status": "error", "msg": str(e)}


@app.route('/api/async_update_kg', methods=['POST'])
def start_async_update():
    text = request.json.get('text', '')
    if not text:
        return jsonify({"error": "文本为空"}), 400
    threading.Thread(target=_async_update, args=(text,), daemon=True).start()
    return jsonify({"status": "started"})


@app.route('/api/kg_status')
def kg_status():
    return jsonify(kg_update_status)


@app.route('/knowledge_graph')
def knowledge_graph():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    return render_template('knowledge_graph.html',
                           neo4j_uri=config.NEO4J_URI,
                           neo4j_user=config.NEO4J_USER,
                           neo4j_password=config.NEO4J_PASSWORD)


@app.route('/api/kg_data')
def get_kg_data():
    try:
        limit = request.args.get('limit', 500, type=int)
        kg = KnowledgeGraphManager()
        return jsonify(kg.query_whole_graph(limit=limit))
    except Exception as e:
        return jsonify({"nodes": [], "links": []})


# 知识图谱可视化页面的节点详情查询（支持?id=参数形式）
@app.route('/api/entity_config/node_details')
def get_node_details_by_query():
    node_id = request.args.get('id', '')
    if not node_id:
        return jsonify({'success': False, 'error': 'Missing id'}), 400
    try:
        kg = KnowledgeGraphManager()
        return jsonify(kg.get_node_details(node_id))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 知识图谱可视化页面的关系详情查询（支持?id=参数形式）
@app.route('/api/entity_config/edge_details')
def get_edge_details_by_query():
    edge_id = request.args.get('id', '')
    if not edge_id:
        return jsonify({'success': False, 'error': 'Missing id'}), 400
    try:
        kg = KnowledgeGraphManager()
        return jsonify(kg.get_relation_details(edge_id))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/process_kg_text', methods=['POST'])
def process_kg_text():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({"success": False, "message": "文本内容不能为空"})
    try:
        kg = KnowledgeGraphManager()
        kg.process_user_query(text, save_to_db=True, depth=2, similarity_threshold=0.7, top_k=5)
        stats = kg.get_kg_statistics()
        graph_data = kg.query_whole_graph(limit=200)
        return jsonify({
            "success": True, "message": "知识图谱更新成功",
            "entity_count": stats["entities"], "relation_count": stats["relationships"],
            "graph": graph_data
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"处理失败: {str(e)}"})


@app.route('/api/kg_path')
def kg_path():
    # Support both ?q=src,tgt and ?source=src&target=tgt formats
    source = request.args.get('source', '')
    target = request.args.get('target', '')
    q = request.args.get('q', '')
    try:
        if source and target:
            src, tgt = source.strip(), target.strip()
        elif q:
            src, tgt = q.split(',', 1)
            src, tgt = src.strip(), tgt.strip()
        else:
            return jsonify({"error": "请提供源节点和目标节点"})
        kg = KnowledgeGraphManager()
        return jsonify(kg.shortest_path(src, tgt))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/kg_centrality')
def kg_centrality():
    kg = KnowledgeGraphManager()
    return jsonify(kg.centrality_analysis())


@app.route('/api/kg_search')
def kg_search():
    keyword = request.args.get('q', '')
    kg = KnowledgeGraphManager()
    return jsonify(kg.search_nodes(keyword))


# ============================== 实体关系属性配置 ==============================
@app.route('/admin/entity_config')
def entity_config():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    return render_template('entity_config.html')


@app.route('/api/entity_config/stats')
def get_entity_config_stats():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        kg = KnowledgeGraphManager()
        stats = kg.get_kg_statistics()
        return jsonify({
            'success': True,
            'data': {'entities': stats.get('entities', 0), 'relationships': stats.get('relationships', 0)}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/entity_config/triples', methods=['GET'])
def get_triples_paginated():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        page = max(1, request.args.get('page', 1, type=int))
        per_page = max(1, min(10, request.args.get('per_page', 5, type=int)))
        search = request.args.get('search', '').strip()

        if not kg_manager.driver:
            kg_manager._get_driver()
            if not kg_manager.driver:
                return jsonify({'success': False, 'error': '图数据库未连接',
                                'data': {'triples': [], 'pagination': {'current_page': page, 'total_pages': 0, 'total_items': 0, 'per_page': per_page}}}), 503

        result = kg_manager.get_triples_paginated(page=page, per_page=per_page, search=search)
        return jsonify({
            'success': True,
            'data': {
                'triples': result.get('triples', []),
                'pagination': {
                    'current_page': result.get('current_page', page),
                    'total_pages': result.get('total_pages', 0),
                    'total_items': result.get('total_items', 0),
                    'per_page': result.get('per_page', per_page)
                }
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e),
                        'data': {'triples': [], 'pagination': {'current_page': 1, 'total_pages': 0, 'total_items': 0, 'per_page': 5}}}), 500


@app.route('/api/entity_config/node/<string:node_id>', methods=['GET'])
def get_node_details_api(node_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        kg = KnowledgeGraphManager()
        result = kg.get_node_details(node_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/entity_config/node/<string:node_id>', methods=['PUT'])
def update_node(node_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        kg = KnowledgeGraphManager()
        success = kg.update_node_properties(node_id, data)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': '更新失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/entity_config/relation/<string:rid>', methods=['GET'])
def get_relation_details_api(rid):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        kg = KnowledgeGraphManager()
        result = kg.get_relation_details(rid)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/entity_config/relation/<string:rid>', methods=['PUT'])
def update_relation(rid):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        kg = KnowledgeGraphManager()
        success = kg.update_relation_properties(rid, data)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': '更新失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================== Prompt模板管理 ==============================
@app.route('/admin/prompt_templates')
def prompt_templates_management():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    return render_template('prompt_templates.html')


@app.route('/api/prompt_templates', methods=['GET'])
def get_prompt_templates():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM prompt_templates ORDER BY is_active DESC, created_at DESC')
    templates = c.fetchall()
    conn.close()
    return jsonify([{
        'id': t['id'], 'name': t['name'], 'description': t['description'],
        'content': t['content'], 'category': t['category'],
        'is_active': bool(t['is_active']), 'created_at': t['created_at'], 'updated_at': t['updated_at']
    } for t in templates])


@app.route('/api/prompt_templates/<int:template_id>', methods=['GET'])
def get_prompt_template(template_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM prompt_templates WHERE id = ?', (template_id,))
    t = c.fetchone()
    conn.close()
    if not t:
        return jsonify({'error': '模板不存在'}), 404
    return jsonify(dict(t))


@app.route('/api/prompt_templates', methods=['POST'])
def create_prompt_template():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    if not data.get('name') or not data.get('content'):
        return jsonify({'error': '名称和内容不能为空'}), 400
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('INSERT INTO prompt_templates (name, description, content, category, is_active) VALUES (?, ?, ?, ?, ?)',
                  (data['name'], data.get('description', ''), data['content'], data.get('category', 'general'), 0))
        conn.commit()
        return jsonify({'success': True, 'template_id': c.lastrowid})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/prompt_templates/<int:template_id>', methods=['PUT'])
def update_prompt_template(template_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('UPDATE prompt_templates SET name=?, description=?, content=?, category=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                  (data['name'], data.get('description', ''), data['content'], data.get('category', 'general'), template_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/prompt_templates/<int:template_id>', methods=['DELETE'])
def delete_prompt_template(template_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('SELECT is_active FROM prompt_templates WHERE id = ?', (template_id,))
        t = c.fetchone()
        if t and t[0]:
            return jsonify({'error': '不能删除当前激活的模板'}), 400
        c.execute('DELETE FROM prompt_templates WHERE id = ?', (template_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/prompt_templates/<int:template_id>/set_active', methods=['POST'])
def set_active_prompt_template(template_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('UPDATE prompt_templates SET is_active = 0')
        c.execute('UPDATE prompt_templates SET is_active = 1 WHERE id = ?', (template_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/prompt_templates/active', methods=['GET'])
def get_active_prompt_template_api():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM prompt_templates WHERE is_active = 1')
    t = c.fetchone()
    conn.close()
    if not t:
        return jsonify({'error': '没有激活的模板'}), 404
    return jsonify(dict(t))


# ============================== 系统设置 ==============================
@app.route('/admin/system_settings')
def system_settings():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    return render_template('system_settings.html')


@app.route('/admin/system_settings/config')
def get_system_config():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(config.get_config())


@app.route('/admin/system_settings/update', methods=['POST'])
def update_system_config():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        new_config = request.get_json()
        config.update_config(new_config)

        # 热重载：重新初始化受影响的组件
        global kg_manager, vdb_manager, graph_rag
        try:
            kg_manager = KnowledgeGraphManager()
            vdb_manager = VectorDBManager()
            graph_rag = GraphRAGSystem(kg_manager, vdb_manager)
        except Exception as reload_err:
            print(f"热重载组件警告: {reload_err}")

        return jsonify({'success': True, 'message': '配置已保存并即时生效'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/system_settings/defaults')
def get_default_config():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(config.DEFAULT_CONFIG)


# ============================== 文档路径修复 ==============================
def check_and_fix_document_paths():
    try:
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('SELECT id, path FROM knowledge_documents WHERE type = "file"')
        documents = c.fetchall()
        for doc_id, path in documents:
            if not os.path.isabs(path):
                new_path = os.path.join(app.config['DOCUMENTS_DIR'], os.path.basename(path))
                if os.path.exists(new_path):
                    c.execute('UPDATE knowledge_documents SET path = ? WHERE id = ?', (new_path, doc_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"修复文档路径时出错: {e}")


# ============================== 医学影像分析 ==============================
@app.route('/image_analysis')
def image_analysis():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('image_analysis.html')


@app.route('/api/analyze_image', methods=['POST'])
def analyze_image():
    """分析上传的医学影像或受伤部位图片"""
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    if 'image' not in request.files:
        return jsonify({'error': '请上传图片'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择图片'}), 400

    image_type = request.form.get('image_type', '通用')
    user_description = request.form.get('description', '')

    try:
        image_data = file.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        user_id = session['user_id']
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT name,age,gender,conditions,allergies,disease_history,medications FROM patients WHERE id=?', (user_id,))
        user = c.fetchone()
        conn.close()

        user_ctx = ""
        if user:
            user_ctx = f"患者：{user['name']}，{user['age']}岁，{user['gender']}，" \
                       f"病史：{user['conditions'] or '无'}，过敏：{user['allergies'] or '无'}，" \
                       f"疾病史：{user['disease_history'] or '无'}，用药：{user['medications'] or '无'}"

        prompt = f"""你是一名资深医学影像诊断专家和临床医生。请仔细分析这张医学图片并给出专业诊断。

## 图片类型: {image_type}
## 患者描述: {user_description or '未提供'}
## 患者背景: {user_ctx}

## 请按以下格式输出：

### 📋 影像分析
详细描述观察到的医学特征和异常。

### 🔍 初步诊断
列出可能诊断（可能性从高到低）。

### 💊 治疗方案
1. 即时处理  2. 用药建议  3. 进一步检查

### ⚠️ 注意事项与就医建议

### 📊 严重程度: （轻微/中等/严重）

**此分析仅供参考，不替代专业医生面诊。**"""

        ext = os.path.splitext(file.filename)[1].lower()
        mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                    '.gif': 'image/gif', '.bmp': 'image/bmp', '.webp': 'image/webp'}
        mime_type = mime_map.get(ext, 'image/jpeg')

        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY", config.TONGYI_KEY),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        response = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                {"type": "text", "text": prompt}
            ]}],
            max_tokens=2048, temperature=0.3
        )
        result_text = response.choices[0].message.content.strip()

        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('INSERT INTO image_analyses (patient_id,image_type,analysis_result) VALUES (?,?,?)',
                  (user_id, image_type, result_text))
        conn.commit()
        aid = c.lastrowid
        conn.close()

        return jsonify({'success': True, 'analysis_id': aid, 'analysis_result': result_text})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'分析失败: {str(e)}'}), 500


@app.route('/api/save_image_analysis', methods=['POST'])
def save_image_analysis():
    """将影像分析结果保存到健康档案"""
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    data = request.get_json()
    analysis_id = data.get('analysis_id')
    if not analysis_id:
        return jsonify({'error': '缺少分析ID'}), 400

    user_id = session['user_id']
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute('SELECT * FROM image_analyses WHERE id=? AND patient_id=?', (analysis_id, user_id))
        analysis = c.fetchone()
        if not analysis:
            return jsonify({'error': '记录不存在'}), 404

        c.execute('UPDATE image_analyses SET is_saved_to_profile=1 WHERE id=?', (analysis_id,))
        c.execute('INSERT INTO medical_records (patient_id,date,department,doctor,description) VALUES (?,?,?,?,?)',
                  (user_id, datetime.now().strftime('%Y-%m-%d'), 'AI影像分析', 'AI诊断助手',
                   f'[AI影像分析-{analysis["image_type"]}] {analysis["analysis_result"][:300]}'))
        conn.commit()
        return jsonify({'success': True, 'message': '已同步到健康档案'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/image_analyses')
def get_image_analyses():
    """获取影像分析历史"""
    pid = request.args.get('patient_id')
    if not pid:
        if 'user_id' in session:
            pid = session['user_id']
        else:
            return jsonify({'error': '未登录'}), 401
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM image_analyses WHERE patient_id=? ORDER BY created_at DESC', (pid,))
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


check_and_fix_document_paths()

if __name__ == '__main__':
    init_all_db_and_patients()
    socketio.run(app, debug=False, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
