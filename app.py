import nltk
import os
import sqlite3
import traceback
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import config
import json
from flask_socketio import SocketIO, emit
from rag_system import GraphRAGSystem
from vector_db import VectorDBManager
from knowledge_graph import KnowledgeGraphManager
from flask import jsonify

nltk.data.path.append(os.path.join(os.path.dirname(__file__), 'nltk_data'))
app = Flask(__name__)
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'doc', 'docx', 'md'}
app.secret_key = 'hospital_secret_key_123'
app.config['DATABASE'] = 'data/hospital.db'
app.config['KNOWLEDGE_BASE'] = config.EXTERNAL_FILE
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'docx', 'md'}
app.config['VECTOR_DB_PATH'] = config.VECTOR_DB_PATH
app.config['DOCUMENTS_DIR'] = config.DOCUMENTS_DIR
socketio = SocketIO(app, cors_allowed_origins="*")

# 确保知识库目录存在
os.makedirs(app.config['KNOWLEDGE_BASE'], exist_ok=True)
os.makedirs(app.config['VECTOR_DB_PATH'], exist_ok=True)
os.makedirs(app.config['DOCUMENTS_DIR'], exist_ok=True)  # 确保文档目录存在

# 初始化GraphRAG系统
kg_manager = KnowledgeGraphManager()
vdb_manager = VectorDBManager()
graph_rag = GraphRAGSystem(kg_manager, vdb_manager)


# 获取默认配置
@app.route('/admin/system_settings/defaults')
def get_default_config():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(config.DEFAULT_CONFIG)


# 在 init_db() 函数中，确保 prompt_templates 表的创建代码正确添加
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    # 创建患者表（扩展健康信息字段）
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

    # 检查并添加缺失的列
    columns_to_add = [
        ('occupation', 'TEXT'),
        ('ethnicity', 'TEXT'),
        ('main_activity', 'TEXT'),
        ('education', 'TEXT'),
        ('employment', 'TEXT'),
        ('marital_status', 'TEXT'),
        ('is_smoker', 'TEXT'),
        ('is_drinker', 'TEXT'),
        ('surgery_history', 'TEXT'),
        ('medications', 'TEXT'),
        ('disease_history', 'TEXT'),
        ('systolic_bp', 'TEXT'),
        ('diastolic_bp', 'TEXT'),
        ('bp_measure_time', 'TEXT'),
        ('family_history', 'TEXT'),
        ('regular_exercise', 'TEXT')
    ]

    c.execute("PRAGMA table_info(patients)")
    existing_columns = [col[1] for col in c.fetchall()]

    for column, col_type in columns_to_add:
        if column not in existing_columns:
            c.execute(f"ALTER TABLE patients ADD COLUMN {column} {col_type}")

    # 创建管理员表
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # 创建就诊历史表
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

    # 创建检查指标表
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

    # 创建知识文档表
    c.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,  -- 'file' or 'url'
            path TEXT NOT NULL,   -- 文件路径或URL
            tags TEXT,            -- 逗号分隔的标签
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建 Prompt 模板表 - 确保这个表被创建
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

    # 添加默认管理员
    c.execute("SELECT COUNT(*) FROM admins WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        hashed_password = generate_password_hash('admin123')
        c.execute("INSERT INTO admins (username, password) VALUES (?, ?)",
                  ('admin', hashed_password))

    # 添加默认的 Prompt 模板
    c.execute("SELECT COUNT(*) FROM prompt_templates")
    if c.fetchone()[0] == 0:
        default_templates = [
            ('健康知识推送模板', '用于生成个性化健康知识推送的模板',
             '''你是一名健康知识助手，请基于下面用户的健康画像与知识图谱结果，用专业的语句推送出**个性化健康知识**，要求：

- 仅围绕用户 **真实健康状况** 与 **知识图谱中的有效信息**
- 分点推送出有关系的健康知识，并且要明确标注每个知识点的来源网址
- 要求推送的健康知识与用户的健康状况、知识图谱有效信息强相关
- 可以稍微给出在*饮食、运动、用药、复查、注意事项等具体可操作建议
- 以 Markdown 格式输出，可含小标题、列表、表情符号
- **重要**：在每个知识点后面必须用 [来源](URL) 的格式标注来源链接，URL 必须完整可点击

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

请开始生成 **专属健康知识推送**，确保每个知识点都有明确的来源标注：''', 'health_knowledge', 1),

            ('通用问答模板', '适用于一般知识问答场景',
             '''你是一个专业的知识问答助手，请基于以下知识回答用户问题：

### 相关知识：
{kg_results}

### 相关文档：
{vdb_results}

### 用户问题：
{user_input}

请基于以上信息给出专业、准确的回答：''', 'general', 0),

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
            INSERT INTO prompt_templates (name, description, content, category, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', default_templates)

    conn.commit()
    conn.close()


def check_and_fix_database_tables():
    """
    检查并修复数据库表结构，确保所有必要的表都存在
    """
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 检查 prompt_templates 表是否存在
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prompt_templates'")
        if not c.fetchone():
            print("创建缺失的 prompt_templates 表...")

            # 创建 Prompt 模板表
            c.execute('''
                CREATE TABLE prompt_templates (
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

            # 添加默认模板
            default_templates = [
                ('健康知识推送模板', '用于生成个性化健康知识推送的模板',
                 '''你是一名健康知识助手，请基于下面用户的健康画像与知识图谱结果，用专业的语句推送出**个性化健康知识**，要求：

- 仅围绕用户 **真实健康状况** 与 **知识图谱中的有效信息**
- 分点推送出有关系的健康知识，并且要明确标注每个知识点的来源网址
- 要求推送的健康知识与用户的健康状况、知识图谱有效信息强相关
- 可以稍微给出在*饮食、运动、用药、复查、注意事项等具体可操作建议
- 以 Markdown 格式输出，可含小标题、列表、表情符号
- **重要**：在每个知识点后面必须用 [来源](URL) 的格式标注来源链接，URL 必须完整可点击

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

请开始生成 **专属健康知识推送**，确保每个知识点都有明确的来源标注：''', 'health_knowledge', 1),

                ('通用问答模板', '适用于一般知识问答场景',
                 '''你是一个专业的知识问答助手，请基于以下知识回答用户问题：

### 相关知识：
{kg_results}

### 相关文档：
{vdb_results}

### 用户问题：
{user_input}

请基于以上信息给出专业、准确的回答：''', 'general', 0),

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
                INSERT INTO prompt_templates (name, description, content, category, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', default_templates)

            print("prompt_templates 表创建完成")

        conn.commit()

    except Exception as e:
        print(f"检查数据库表时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

# 添加测试患者数据
def add_test_patients():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    patients = [
        ('张伟', '13800138000', generate_password_hash('password123'), 42, '男', 'O型', '175cm', '72kg', '轻度高血压',
         '青霉素、花粉'),
        ('李娜', '13900139000', generate_password_hash('abc123'), 35, '女', 'A型', '162cm', '55kg', 'II型糖尿病', '无'),
        ('王强', '13700137000', generate_password_hash('pass1234'), 58, '男', 'B型', '178cm', '80kg', '冠心病', '海鲜'),
        ('赵敏', '13600136000', generate_password_hash('securepwd'), 29, '女', 'AB型', '168cm', '58kg', '健康', '无'),
        ('刘洋', '13500135000', generate_password_hash('mypassword'), 65, '男', 'O型', '170cm', '68kg', '慢性支气管炎',
         '花粉、尘螨')
    ]

    try:
        c.executemany('''
            INSERT INTO patients (name, phone, password, age, gender, blood_type, height, weight, conditions, allergies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', patients)
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # 数据已存在

    # 添加测试就诊记录
    for patient_id in range(1, 6):
        records = [
            (patient_id, '2023-10-15', '心血管内科', '王主任', '患者主诉近期偶有头晕现象，血压测量为145/92mmHg'),
            (patient_id, '2023-08-22', '体检中心', '李医生', '年度体检结果显示：血脂略高（LDL 3.5mmol/L）'),
            (patient_id, '2023-06-10', '呼吸科', '张医生', '患者因季节性花粉过敏就诊，症状包括打喷嚏、流涕')
        ]
        c.executemany('''
            INSERT INTO medical_records (patient_id, date, department, doctor, description)
            VALUES (?, ?, ?, ?, ?)
        ''', records)

    # 添加测试检查指标
    for patient_id in range(1, 6):
        metrics = [
            (patient_id, '血压', '142/88', '90-120/60-80', 'mmHg', '2023-10-15', 'warning'),
            (patient_id, '空腹血糖', '5.8', '3.9-6.1', 'mmol/L', '2023-10-15', 'normal'),
            (patient_id, '总胆固醇', '5.3', '<5.2', 'mmol/L', '2023-08-22', 'warning')
        ]
        c.executemany('''
            INSERT INTO check_metrics (patient_id, item, result, reference_range, unit, date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', metrics)

    conn.commit()
    conn.close()


# 首页重定向
@app.route('/')
def home():
    return redirect(url_for('login'))


# 患者登录
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


# 患者注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    if request.method == 'POST':
        # 收集所有字段数据
        name = request.form['name']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # 健康信息字段
        age = request.form.get('age', '')
        gender = request.form.get('gender', '')
        blood_type = request.form.get('blood_type', '')
        height = request.form.get('height', '')
        weight = request.form.get('weight', '')
        conditions = request.form.get('conditions', '')
        allergies = request.form.get('allergies', '')
        occupation = request.form.get('occupation', '')
        ethnicity = request.form.get('ethnicity', '')
        # main_activity = request.form.get('main_activity', '')
        education = request.form.get('education', '')
        # employment = request.form.get('employment', '')
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

        try:
            # 使用单个INSERT语句包含所有字段
            c.execute('''
                INSERT INTO patients (
                    name, phone, password, age, gender, blood_type, height, weight, 
                    conditions, allergies, occupation, ethnicity, 
                    education, marital_status, is_smoker, is_drinker,
                    surgery_history, medications, disease_history, systolic_bp, 
                    diastolic_bp, bp_measure_time, family_history, regular_exercise
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, phone, hashed_password, age, gender, blood_type,
                height, weight, conditions, allergies,
                occupation, ethnicity,  education,  marital_status,
                is_smoker, is_drinker, surgery_history, medications, disease_history,
                systolic_bp, diastolic_bp, bp_measure_time, family_history, regular_exercise
            ))
            conn.commit()
            flash('注册成功！请登录', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('该手机号已注册，请使用其他手机号', 'error')
        finally:
            conn.close()

    return render_template('register.html')


# 健康画像
@app.route('/health_profile')
def health_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    patient_id = session['user_id']

    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row  # 启用行工厂以支持列名访问
    c = conn.cursor()

    # 获取患者基本信息
    c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = c.fetchone()

    # 获取就诊历史
    c.execute('SELECT * FROM medical_records WHERE patient_id = ? ORDER BY date DESC', (patient_id,))
    medical_records = c.fetchall()

    # 获取检查指标
    c.execute('SELECT * FROM check_metrics WHERE patient_id = ? ORDER BY date DESC', (patient_id,))
    check_metrics = c.fetchall()

    conn.close()

    if not patient:
        return redirect(url_for('login'))

    # 安全访问字段（避免KeyError）
    # 在 health_profile 函数中，修改健康数据的获取方式
    def get_patient_field(field, default=''):
        # 使用辅助函数
        return get_row_field(patient, field, default)

    # 或者直接使用辅助函数
    health_data = {
        'id': get_row_field(patient, 'id'),
        'name': get_row_field(patient, 'name'),
        'phone': get_row_field(patient, 'phone'),
        'age': get_row_field(patient, 'age'),
        'gender': get_row_field(patient, 'gender'),
        'blood_type': get_row_field(patient, 'blood_type'),
        'height': get_row_field(patient, 'height'),
        'weight': get_row_field(patient, 'weight'),
        'conditions': get_row_field(patient, 'conditions'),
        'allergies': get_row_field(patient, 'allergies'),
        'occupation': get_row_field(patient, 'occupation'),
        'ethnicity': get_row_field(patient, 'ethnicity'),
        'main_activity': get_row_field(patient, 'main_activity'),
        'education': get_row_field(patient, 'education'),
        'employment': get_row_field(patient, 'employment'),
        'marital_status': get_row_field(patient, 'marital_status'),
        'is_smoker': get_row_field(patient, 'is_smoker'),
        'is_drinker': get_row_field(patient, 'is_drinker'),
        'surgery_history': get_row_field(patient, 'surgery_history'),
        'medications': get_row_field(patient, 'medications'),
        'disease_history': get_row_field(patient, 'disease_history'),
        'systolic_bp': get_row_field(patient, 'systolic_bp'),
        'diastolic_bp': get_row_field(patient, 'diastolic_bp'),
        'bp_measure_time': get_row_field(patient, 'bp_measure_time'),
        'family_history': get_row_field(patient, 'family_history'),
        'regular_exercise': get_row_field(patient, 'regular_exercise'),
        'created_at': get_row_field(patient, 'created_at')
    }

    # 计算BMI
    try:
        height_val = float(health_data['height'].replace('cm', '')) if health_data['height'] else 0
        weight_val = float(health_data['weight'].replace('kg', '')) if health_data['weight'] else 0
        if height_val > 0 and weight_val > 0:
            height_in_m = height_val / 100
            health_data['bmi'] = round(weight_val / (height_in_m * height_in_m), 1)

            # BMI分类
            if health_data['bmi'] < 18.5:
                health_data['bmi_category'] = '偏瘦'
            elif 18.5 <= health_data['bmi'] < 24:
                health_data['bmi_category'] = '正常'
            elif 24 <= health_data['bmi'] < 28:
                health_data['bmi_category'] = '超重'
            else:
                health_data['bmi_category'] = '肥胖'
        else:
            health_data['bmi'] = ''
            health_data['bmi_category'] = ''
    except:
        health_data['bmi'] = ''
        health_data['bmi_category'] = ''

    # 格式化就诊历史
    formatted_records = []
    for record in medical_records:
        formatted_records.append({
            'id': record['id'],
            'date': record['date'],
            'department': record['department'],
            'doctor': record['doctor'],
            'description': record['description']
        })

    # 格式化检查指标
    formatted_metrics = []
    for metric in check_metrics:
        formatted_metrics.append({
            'id': metric['id'],
            'item': metric['item'],
            'result': metric['result'],
            'range': metric['reference_range'],
            'unit': metric['unit'],
            'date': metric['date'],
            'status': metric['status']
        })

    return render_template('health_profile.html',
                           health_data=health_data,
                           medical_records=formatted_records,
                           check_metrics=formatted_metrics)


# 后台登录
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


# 后台管理
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 每页显示数量

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    # 获取总记录数
    c.execute('SELECT COUNT(*) FROM patients')
    total = c.fetchone()[0]

    # 计算分页
    total_pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page

    # 获取当前页数据
    c.execute('SELECT * FROM patients LIMIT ? OFFSET ?', (per_page, offset))
    patients = c.fetchall()
    conn.close()

    patients_data = []
    for patient in patients:
        patients_data.append({
            'id': patient[0],
            'name': patient[1],
            'phone': patient[2],
            'age': patient[4],
            'gender': patient[5],
            'blood_type': patient[6],
            'height': patient[7],
            'weight': patient[8],
            'conditions': patient[9],
            'allergies': patient[10],
            'created_at': patient[11]
        })

    return render_template('admin_dashboard.html',
                           patients=patients_data,
                           page=page,
                           per_page=per_page,
                           total=total,
                           total_pages=total_pages)


# 添加删除用户的路由
@app.route('/admin/patient/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 首先删除相关的医疗记录和检查指标
        c.execute('DELETE FROM medical_records WHERE patient_id = ?', (patient_id,))
        c.execute('DELETE FROM check_metrics WHERE patient_id = ?', (patient_id,))

        # 然后删除患者
        c.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
        conn.commit()

        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# 确保预览患者信息的路由正常工作
@app.route('/admin/patient/<int:patient_id>/preview')
def preview_patient(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 获取患者基本信息
    c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = c.fetchone()

    conn.close()

    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    # 转换为字典格式
    patient_data = dict(patient)

    # 计算BMI
    try:
        height_val = float(patient_data['height'].replace('cm', '')) if patient_data.get('height') else 0
        weight_val = float(patient_data['weight'].replace('kg', '')) if patient_data.get('weight') else 0
        if height_val > 0 and weight_val > 0:
            height_in_m = height_val / 100
            patient_data['bmi'] = round(weight_val / (height_in_m * height_in_m), 1)
            if patient_data['bmi'] < 18.5:
                patient_data['bmi_category'] = '偏瘦'
            elif 18.5 <= patient_data['bmi'] < 24:
                patient_data['bmi_category'] = '正常'
            elif 24 <= patient_data['bmi'] < 28:
                patient_data['bmi_category'] = '超重'
            else:
                patient_data['bmi_category'] = '肥胖'
        else:
            patient_data['bmi'] = ''
            patient_data['bmi_category'] = ''
    except:
        patient_data['bmi'] = ''
        patient_data['bmi_category'] = ''

    return jsonify(patient_data)


# 确保更新患者信息的路由正确处理所有字段
@app.route('/admin/patient/<int:patient_id>/update_basic', methods=['POST'])
def update_patient_basic(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 使用参数化查询更新所有字段
        c.execute('''
            UPDATE patients SET 
                name = COALESCE(?, name), 
                phone = COALESCE(?, phone),
                age = COALESCE(?, age), 
                gender = COALESCE(?, gender), 
                blood_type = COALESCE(?, blood_type), 
                height = COALESCE(?, height), 
                weight = COALESCE(?, weight), 
                conditions = COALESCE(?, conditions), 
                allergies = COALESCE(?, allergies),
                occupation = COALESCE(?, occupation),
                ethnicity = COALESCE(?, ethnicity),
                education = COALESCE(?, education),
                marital_status = COALESCE(?, marital_status),
                is_smoker = COALESCE(?, is_smoker),
                is_drinker = COALESCE(?, is_drinker),
                surgery_history = COALESCE(?, surgery_history),
                medications = COALESCE(?, medications),
                disease_history = COALESCE(?, disease_history),
                systolic_bp = COALESCE(?, systolic_bp),
                diastolic_bp = COALESCE(?, diastolic_bp),
                bp_measure_time = COALESCE(?, bp_measure_time),
                family_history = COALESCE(?, family_history),
                regular_exercise = COALESCE(?, regular_exercise)
            WHERE id = ?
        ''', (
            data.get('name'),
            data.get('phone'),
            data.get('age'),
            data.get('gender'),
            data.get('blood_type'),
            data.get('height'),
            data.get('weight'),
            data.get('conditions'),
            data.get('allergies'),
            data.get('occupation'),
            data.get('ethnicity'),
            # data.get('main_activity'),
            data.get('education'),
            # data.get('employment'),
            data.get('marital_status'),
            data.get('is_smoker'),
            data.get('is_drinker'),
            data.get('surgery_history'),
            data.get('medications'),
            data.get('disease_history'),
            data.get('systolic_bp'),
            data.get('diastolic_bp'),
            data.get('bp_measure_time'),
            data.get('family_history'),
            data.get('regular_exercise'),
            patient_id
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"更新失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# 获取患者详细信息
@app.route('/admin/patient/<int:patient_id>')
def get_patient_details(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    # 获取患者基本信息
    c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = c.fetchone()

    # 获取患者就诊历史
    c.execute('SELECT * FROM medical_records WHERE patient_id = ? ORDER BY date DESC', (patient_id,))
    medical_records = c.fetchall()

    # 获取患者检查指标
    c.execute('SELECT * FROM check_metrics WHERE patient_id = ? ORDER BY date DESC', (patient_id,))
    check_metrics = c.fetchall()

    conn.close()

    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    # 格式化就诊历史
    formatted_records = []
    for record in medical_records:
        formatted_records.append({
            'id': record[0],
            'date': record[2],
            'department': record[3],
            'doctor': record[4],
            'description': record[5]
        })

    # 格式化检查指标
    formatted_metrics = []
    for metric in check_metrics:
        formatted_metrics.append({
            'id': metric[0],
            'item': metric[2],
            'result': metric[3],
            'reference_range': metric[4],
            'unit': metric[5],
            'date': metric[6],
            'status': metric[7]
        })

    patient_data = {
        'id': patient[0],
        'name': patient[1],
        'phone': patient[2],
        'age': patient[4],
        'gender': patient[5],
        'blood_type': patient[6],
        'height': patient[7],
        'weight': patient[8],
        'conditions': patient[9],
        'allergies': patient[10],
        'medical_records': formatted_records,
        'check_metrics': formatted_metrics
    }

    return jsonify(patient_data)


# 添加就诊记录API
@app.route('/admin/patient/<int:patient_id>/add_medical_record', methods=['POST'])
def add_medical_record(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        c.execute('''
            INSERT INTO medical_records (patient_id, date, department, doctor, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            patient_id,
            data['date'],
            data['department'],
            data['doctor'],
            data['description']
        ))
        conn.commit()
        return jsonify({'success': True, 'record_id': c.lastrowid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# 添加检查指标API
@app.route('/admin/patient/<int:patient_id>/add_check_metric', methods=['POST'])
def add_check_metric(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        c.execute('''
            INSERT INTO check_metrics (patient_id, item, result, reference_range, unit, date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            data['item'],
            data['result'],
            data['reference_range'],
            data['unit'],
            data['date'],
            data['status']
        ))
        conn.commit()
        return jsonify({'success': True, 'metric_id': c.lastrowid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# 更新健康记录API
@app.route('/admin/medical_record/<int:record_id>/update', methods=['POST'])
def update_medical_record(record_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        c.execute('''
            UPDATE medical_records SET 
                date = ?,
                department = ?,
                doctor = ?,
                description = ?
            WHERE id = ?
        ''', (
            data['date'],
            data['department'],
            data['doctor'],
            data['description'],
            record_id
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# 更新检查指标API
@app.route('/admin/check_metric/<int:metric_id>/update', methods=['POST'])
def update_check_metric(metric_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        c.execute('''
            UPDATE check_metrics SET 
                item = ?,
                result = ?,
                reference_range = ?,
                unit = ?,
                date = ?,
                status = ?
            WHERE id = ?
        ''', (
            data['item'],
            data['result'],
            data['reference_range'],
            data['unit'],
            data['date'],
            data['status'],
            metric_id
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# 删除就诊记录API
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


# 删除检查指标API
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


# ============================== 文档管理路由 ==============================
# 文档管理路由 - 获取文档列表（分页）
@app.route('/admin/knowledge/documents', methods=['GET'])
def list_documents():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 每页显示数量

    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 获取总记录数
    c.execute('SELECT COUNT(*) FROM knowledge_documents')
    total = c.fetchone()[0]

    # 计算分页
    total_pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page

    # 获取当前页数据
    c.execute('SELECT * FROM knowledge_documents ORDER BY created_at DESC LIMIT ? OFFSET ?', (per_page, offset))
    documents = c.fetchall()
    conn.close()

    # 格式化文档数据
    documents_data = []
    for doc in documents:
        documents_data.append({
            'id': doc['id'],
            'name': doc['name'],
            'type': doc['type'],
            'path': doc['path'],
            'tags': doc['tags'].split(',') if doc['tags'] else [],
            'created_at': doc['created_at'],
            'updated_at': doc['updated_at']
        })

    return jsonify({
        'items': documents_data,
        'total': total,
        'pages': total_pages,
        'current_page': page
    })


# 修改 create_document 函数
@app.route('/admin/knowledge/documents', methods=['POST'])
def create_document():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # 获取表单数据
    name = request.form.get('name')
    doc_type = request.form.get('type')
    tags = request.form.get('tags', '')
    socket_id = request.form.get('socket_id')  # 从表单获取 socket_id

    if not name or not doc_type:
        return jsonify({'error': '缺少必要参数: name和type'}), 400

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        if doc_type == 'file':
            # 处理文件上传
            if 'file' not in request.files:
                return jsonify({'error': '未选择文件'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': '未选择文件'}), 400

            # 获取文件扩展名并验证
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1].lower()

            # 检查文件类型是否允许
            allowed_extensions = app.config['ALLOWED_EXTENSIONS']
            if file_ext.lstrip('.') not in allowed_extensions:
                return jsonify({
                    'error': f'不支持的文件类型: {file_ext}',
                    'allowed': list(allowed_extensions)
                }), 400

            # 保存文件到文档目录
            file_path = os.path.join(app.config['DOCUMENTS_DIR'], filename)

            # 处理文件名冲突
            counter = 1
            while os.path.exists(file_path):
                name_part, ext = os.path.splitext(filename)
                new_filename = f"{name_part}_{counter}{ext}"
                file_path = os.path.join(app.config['DOCUMENTS_DIR'], new_filename)
                counter += 1

            file.save(file_path)

            # 确保使用绝对路径
            path = os.path.abspath(file_path)

        elif doc_type == 'url':
            # 处理URL
            url = request.form.get('url')
            if not url:
                return jsonify({'error': '缺少URL参数'}), 400
            path = url

        else:
            return jsonify({'error': '无效的文档类型'}), 400

        # 插入数据库
        c.execute('''
            INSERT INTO knowledge_documents (name, type, path, tags)
            VALUES (?, ?, ?, ?)
        ''', (name, doc_type, path, tags))

        conn.commit()
        doc_id = c.lastrowid

        # 如果是URL类型，启动异步爬取任务
        if doc_type == 'url' and socket_id:
            # 启动后台线程进行网页爬取
            threading.Thread(
                target=crawl_url_content,
                args=(url, doc_id, socket_id),
                daemon=True
            ).start()

        return jsonify({
            'success': True,
            'document_id': doc_id,
            'message': '文档添加成功'
        }), 201

    except Exception as e:
        conn.rollback()
        print(f"创建文档失败: {str(e)}")
        return jsonify({'error': f'创建文档失败: {str(e)}'}), 500
    finally:
        conn.close()


# 添加WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    print(f'客户端连接: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    print(f'客户端断开: {request.sid}')


# 更新文档
@app.route('/admin/knowledge/documents/<int:doc_id>', methods=['PUT'])
def update_document(doc_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # 获取表单数据
    name = request.form.get('name')
    doc_type = request.form.get('type')
    tags = request.form.get('tags', '')
    url = request.form.get('url', '')

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 获取现有文档
        c.execute('SELECT * FROM knowledge_documents WHERE id = ?', (doc_id,))
        document = c.fetchone()

        if not document:
            return jsonify({'error': '文档不存在'}), 404

        # 处理文件上传（如果有）
        new_file_path = None
        if 'file' in request.files and request.files['file']:
            if doc_type != 'file':
                return jsonify({'error': 'URL类型文档不能上传文件'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': '未选择文件'}), 400

            # 验证文件类型
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1].lower()
            allowed_extensions = app.config['ALLOWED_EXTENSIONS']
            if file_ext.lstrip('.') not in allowed_extensions:
                return jsonify({
                    'error': f'不支持的文件类型: {file_ext}',
                    'allowed': list(allowed_extensions)
                }), 400

            # 保存文件到文档目录
            file_path = os.path.join(app.config['DOCUMENTS_DIR'], filename)

            # 处理文件名冲突
            counter = 1
            while os.path.exists(file_path):
                name_part, ext = os.path.splitext(filename)
                new_filename = f"{name_part}_{counter}{ext}"
                file_path = os.path.join(app.config['DOCUMENTS_DIR'], new_filename)
                counter += 1

            file.save(file_path)
            new_file_path = file_path

        # 处理URL更新
        if doc_type == 'url':
            if not url:
                return jsonify({'error': '缺少URL参数'}), 400
            new_path = url
        else:
            # 如果没有新文件上传，保持原路径
            new_path = new_file_path if new_file_path else document[3]

        # 更新数据库
        c.execute('''
            UPDATE knowledge_documents SET 
                name = ?,
                type = ?,
                path = ?,
                tags = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            name if name else document[1],
            doc_type if doc_type else document[2],
            new_path,
            tags if tags else document[4],
            doc_id
        ))

        conn.commit()

        # 如果是文件类型且文件路径变更，删除旧文件
        if document[2] == 'file' and new_path != document[3]:
            try:
                if os.path.exists(document[3]):
                    os.remove(document[3])
            except Exception as e:
                print(f"删除旧文件失败: {str(e)}")

        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        print(f"更新文档失败: {str(e)}")
        return jsonify({'error': f'更新文档失败: {str(e)}'}), 500
    finally:
        conn.close()


# 删除文档
@app.route('/admin/knowledge/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 获取文档信息
        c.execute('SELECT * FROM knowledge_documents WHERE id = ?', (doc_id,))
        document = c.fetchone()

        if not document:
            return jsonify({'error': '文档不存在'}), 404

        # 删除数据库记录
        c.execute('DELETE FROM knowledge_documents WHERE id = ?', (doc_id,))
        conn.commit()

        # 如果是文件类型，删除物理文件
        if document[2] == 'file' and os.path.exists(document[3]):
            try:
                os.remove(document[3])
            except Exception as e:
                print(f"删除文件失败: {str(e)}")
                return jsonify({'error': f'删除文件失败: {str(e)}'}), 500

        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'删除文档失败: {str(e)}'}), 500
    finally:
        conn.close()


# 添加WebSocket处理
socketio = SocketIO(app, cors_allowed_origins="*")

# 向量化任务状态
vectorization_tasks = {}


# ============================== 向量化任务处理 ==============================
# WebSocket事件：开始向量化
@socketio.on('start_vectorization')
def handle_start_vectorization(data):
    doc_id = data['doc_id']
    session_id = request.sid
    print(f"收到向量化请求: 文档ID={doc_id}, session_id={session_id}")

    # 创建新任务
    vectorization_tasks[session_id] = {
        'doc_id': doc_id,
        'status': 'processing',
        'progress': 0
    }

    # 发送初始消息
    emit('vectorization_update', {
        'message': '<div class="info-message">开始向量化处理...</div>'
    }, room=session_id)

    # 在后台线程中执行向量化
    socketio.start_background_task(vectorize_document_task, doc_id, session_id)


def vectorize_document_task(doc_id, session_id):
    try:
        # ✅ 创建日志回调函数（使用 socketio.emit + room）
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
            socketio.emit('vectorization_error', {
                'message': '文档不存在'
            }, room=session_id)
            return

        doc_name, doc_type, doc_path, doc_tags = document[1], document[2], document[3], document[4] or ""

        log_callback(f"开始处理文档: {doc_name}")
        log_callback(f"文档类型: {doc_type}")
        log_callback(f"文档路径: {doc_path}")

        if doc_type == 'file':
            # 检查文件路径是否是绝对路径，如果不是则转换为绝对路径
            if not os.path.isabs(doc_path):
                doc_path = os.path.join(app.config['DOCUMENTS_DIR'], os.path.basename(doc_path))

            if not os.path.exists(doc_path):
                log_callback(f"❌ 文件不存在: {doc_path}", "error")
                socketio.emit('vectorization_error', {
                    'message': f'文件不存在: {doc_path}'
                }, room=session_id)
                return

            try:
                success = vdb_manager.update_single_file(doc_path, doc_tags, log_callback=log_callback)

                if success:
                    log_callback("✅ 向量化处理成功完成", "success")
                    stats = vdb_manager.get_stats()
                    socketio.emit('vectorization_complete', {
                        'stats': stats,
                        'message': '<div class="success-message">✅ 向量化处理成功完成</div>'
                    }, room=session_id)
                else:
                    log_callback("❌ 向量化处理失败", "error")
                    socketio.emit('vectorization_error', {
                        'message': '向量化处理失败'
                    }, room=session_id)
            except Exception as e:
                error_msg = f"❌ 向量化处理异常: {str(e)}"
                log_callback(error_msg, "error")
                socketio.emit('vectorization_error', {
                    'message': error_msg
                }, room=session_id)
                traceback.print_exc()
        else:
            log_callback("❌ URL文档向量化功能尚未实现", "error")
            socketio.emit('vectorization_error', {
                'message': 'URL文档向量化功能尚未实现'
            }, room=session_id)

    except Exception as e:
        error_msg = f"❌ 处理失败: {str(e)}"
        socketio.emit('vectorization_error', {
            'message': error_msg
        }, room=session_id)
        traceback.print_exc()


# 向量化文档
@app.route('/admin/knowledge/documents/<int:doc_id>/vectorize', methods=['POST'])
def vectorize_document(doc_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 获取文档信息
        c.execute('SELECT * FROM knowledge_documents WHERE id = ?', (doc_id,))
        document = c.fetchone()

        if not document:
            return jsonify({'error': '文档不存在'}), 404

        # 获取文档标签
        tags = document[4] or ""

        # 调用向量化处理
        if document[2] == 'file':
            # 文件类型
            file_path = document[3]
            success = vdb_manager.update_single_file(file_path, tags)
            if success:
                return jsonify({'success': True, 'message': '文档向量化成功'})
            else:
                return jsonify({'error': '文档向量化失败'}), 500
        else:
            # URL类型（需要实现URL内容处理）
            return jsonify({'error': 'URL文档向量化功能尚未实现'}), 501

    except Exception as e:
        print(f"向量化失败: {str(e)}")
        return jsonify({'error': f'向量化失败: {str(e)}'}), 500
    finally:
        conn.close()


# 知识库管理页面
@app.route('/admin/knowledge')
def knowledge_management():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    # 获取文档列表
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT id, name, type, path, tags, created_at FROM knowledge_documents ORDER BY created_at DESC')
    knowledge_docs = c.fetchall()
    conn.close()

    # 格式化文档数据
    formatted_docs = []
    for doc in knowledge_docs:
        formatted_docs.append({
            'id': doc[0],
            'name': doc[1],
            'type': doc[2],
            'path': doc[3],
            'tags': doc[4],
            'created_at': doc[5]
        })

    # 获取向量数据库状态
    try:
        vector_db_stats = vdb_manager.get_stats()
    except Exception as e:
        print(f"获取向量数据库状态失败: {str(e)}")
        vector_db_stats = {
            "status": "error",
            "message": "无法获取向量数据库状态"
        }

    return render_template('knowledge_management.html',
                           knowledge_docs=formatted_docs,
                           vector_db_stats=vector_db_stats)


# 获取向量数据库状态
@app.route('/admin/vector_db_stats')
def get_vector_db_stats():
    try:
        stats = vdb_manager.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================== 知识图谱管理 ==============================
kg_update_status = {"status": "idle", "msg": ""}


def _async_update(text: str):
    global kg_update_status
    kg_update_status = {"status": "running", "msg": ""}
    try:
        kg = KnowledgeGraphManager()
        kg.process_user_query(text, save_to_db=True, depth=2,
                              similarity_threshold=0.7, top_k=5)
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


import requests
from bs4 import BeautifulSoup
import threading
from datetime import time


def crawl_url_content(url, doc_id, socket_id):
    """
    异步爬取URL内容并保存为结构化文本
    """
    try:
        # 发送爬取开始消息
        socketio.emit('crawling_update', {
            'doc_id': doc_id,
            'message': '开始爬取网页内容...',
            'progress': 10
        }, room=socket_id)

        # 发送HTTP请求获取网页内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        socketio.emit('crawling_update', {
            'doc_id': doc_id,
            'message': '正在获取网页内容...',
            'progress': 30
        }, room=socket_id)

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # 解析HTML内容
        socketio.emit('crawling_update', {
            'doc_id': doc_id,
            'message': '解析网页内容...',
            'progress': 50
        }, room=socket_id)

        soup = BeautifulSoup(response.content, 'html.parser')

        # 提取标题
        title = soup.find('h1')
        if not title:
            title = soup.find('title')
        title_text = title.get_text().strip() if title else "无标题"

        # 提取摘要/描述
        description = soup.find('meta', attrs={'name': 'description'})
        description_text = description['content'].strip() if description else ""

        # 提取正文内容
        # 尝试多种常见的内容选择器
        content_selectors = [
            'article',
            '.content',
            '.main-content',
            '#content',
            '.post-content',
            '.entry-content'
        ]

        content = None
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                break

        # 如果没有找到特定内容区域，使用body
        if not content:
            content = soup.find('body')

        # 清理不需要的元素
        for element in content.select('script, style, nav, footer, aside, .advertisement'):
            element.decompose()

        # 获取纯文本内容
        content_text = content.get_text() if content else ""
        content_text = '\n'.join([line.strip() for line in content_text.split('\n') if line.strip()])

        socketio.emit('crawling_update', {
            'doc_id': doc_id,
            'message': '生成结构化文档...',
            'progress': 80
        }, room=socket_id)

        # 创建结构化文本
        structured_content = f"""标题: {title_text}

摘要: {description_text}

正文内容:
{content_text}
"""

        # 保存为txt文件
        filename = f"web_content_{doc_id}_{int(time.time())}.txt"
        filepath = os.path.join(app.config['DOCUMENTS_DIR'], filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(structured_content)

        # 更新数据库记录
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('UPDATE knowledge_documents SET path = ? WHERE id = ?', (filepath, doc_id))
        conn.commit()
        conn.close()

        socketio.emit('crawling_update', {
            'doc_id': doc_id,
            'message': '网页内容已成功爬取并保存',
            'progress': 100,
            'completed': True,
            'filepath': filepath
        }, room=socket_id)

    except Exception as e:
        error_msg = f"爬取网页内容失败: {str(e)}"
        socketio.emit('crawling_error', {
            'doc_id': doc_id,
            'message': error_msg
        }, room=socket_id)


# ========= 新增：图查询接口 =========
@app.route('/api/kg_path')
def kg_path():
    q = request.args.get('q', '')
    try:
        src, tgt = q.split(',', 1)
        kg = KnowledgeGraphManager()
        return jsonify(kg.shortest_path(src.strip(), tgt.strip()))
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


# 知识图谱管理
@app.route('/knowledge_graph')
def knowledge_graph():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
        # 把连接参数透传给模板
    return render_template('knowledge_graph.html',
                           neo4j_uri=config.NEO4J_URI,
                           neo4j_user=config.NEO4J_USER,
                           neo4j_password=config.NEO4J_PASSWORD)

# 获取图谱数据API
@app.route('/api/kg_data')
def get_kg_data():
    """获取图谱数据API"""
    try:
        kg = KnowledgeGraphManager()
        return jsonify(kg.query_whole_graph(limit=100))
    except Exception as e:
        print(f"获取图谱数据API错误: {str(e)}")
        return jsonify({"nodes": [], "links": []})


# 处理文本API
@app.route('/api/process_kg_text', methods=['POST'])
def process_kg_text():
    """处理文本API"""
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({
            "success": False,
            "message": "文本内容不能为空"
        })

    try:
        kg = KnowledgeGraphManager()

        # 处理用户查询（提取实体关系并保存到数据库）
        kg.process_user_query(
            text,
            save_to_db=True,
            depth=2,
            similarity_threshold=0.7,
            top_k=5
        )

        # 获取更新后的统计信息
        stats = kg.get_kg_statistics()

        # 获取更新后的图谱数据
        graph_data = kg.query_whole_graph(limit=100)

        return jsonify({
            "success": True,
            "message": "知识图谱更新成功",
            "entity_count": stats["entities"],
            "relation_count": stats["relationships"],
            "graph": graph_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"处理失败: {str(e)}"
        })


# 智能诊断
@app.route('/diagnosis')
def diagnosis():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('diagnosis.html')


# 生成诊断报告
@app.route('/api/generate_diagnosis_report')
def generate_diagnosis_report():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401

    patient_id = session['user_id']

    try:
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()

        # 1. 获取患者基本信息
        c.execute('SELECT name, age, gender, height, weight, conditions, allergies FROM patients WHERE id = ?',
                  (patient_id,))
        patient_data = c.fetchone()

        if not patient_data:
            return jsonify({'error': '患者信息不存在'}), 404

        # 2. 获取最新就诊记录
        c.execute(
            'SELECT date, department, doctor, description FROM medical_records WHERE patient_id = ? ORDER BY date DESC LIMIT 1',
            (patient_id,))
        latest_visit = c.fetchone()

        # 3. 获取近期检查指标（最近3条）
        c.execute(
            'SELECT item, result, reference_range, unit, date FROM check_metrics WHERE patient_id = ? ORDER BY date DESC LIMIT 3',
            (patient_id,))
        recent_metrics = c.fetchall()

        conn.close()

        # 4. 格式化患者数据文本
        text_parts = ["患者基本信息："]
        text_parts.append(f"姓名：{patient_data[0]}")
        text_parts.append(f"年龄：{patient_data[1] or '未记录'}岁")
        text_parts.append(f"性别：{patient_data[2] or '未记录'}")
        text_parts.append(f"身高：{patient_data[3] or '未记录'}")
        text_parts.append(f"体重：{patient_data[4] or '未记录'}")
        text_parts.append(f"健康状况：{patient_data[5] or '无特殊记录'}")
        text_parts.append(f"过敏病史：{patient_data[6] or '无'}")

        # 就诊历史部分
        if latest_visit:
            text_parts.append("\n最新就诊记录：")
            text_parts.append(f"日期：{latest_visit[0]}")
            text_parts.append(f"科室：{latest_visit[1]}")
            text_parts.append(f"医生：{latest_visit[2]}")
            text_parts.append(f"诊断描述：{latest_visit[3]}")
        else:
            text_parts.append("\n无近期就诊记录")

        # 检查指标部分
        if recent_metrics:
            text_parts.append("\n近期检查指标：")
            for metric in recent_metrics:
                text_parts.append(f"{metric[0]}：{metric[1]} {metric[4]}（参考范围：{metric[2]}）")
        else:
            text_parts.append("\n无近期检查指标记录")

        # 组合所有文本
        formatted_text = "\n".join(text_parts)

        # 5. 使用GraphRAG系统生成诊断报告
        response = graph_rag.query(
            user_input=formatted_text,
            depth=2,
            similarity_threshold=0.7,
            top_k=3
        )

        # 6. 返回诊断报告
        return jsonify({
            'success': True,
            'diagnosis_report': response['answer'],
            'formatted_text': formatted_text
        })

    except Exception as e:
        return jsonify({'error': f'生成诊断报告失败: {str(e)}'}), 500


# 退出登录
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# 初始化数据库和测试数据
# 初始化数据库和测试数据
def init_all_db_and_patients():
    # 检查数据库文件是否存在
    db_exists = os.path.exists(app.config['DATABASE'])

    # 总是初始化数据库结构
    init_db()

    # 检查并修复数据库表结构
    check_and_fix_database_tables()

    # 只在数据库文件不存在时添加测试数据
    if not db_exists:
        print("首次启动，添加测试数据...")
        add_test_patients()
    else:
        print("数据库已存在，跳过添加测试数据")

# 手动修复数据库表
@app.route('/admin/fix_database', methods=['POST'])
def fix_database_tables():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        check_and_fix_database_tables()
        return jsonify({'success': True, 'message': '数据库表检查修复完成'})
    except Exception as e:
        return jsonify({'error': f'修复数据库表失败: {str(e)}'}), 500

# 系统设置页面
@app.route('/admin/system_settings')
def system_settings():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    return render_template('system_settings.html')


# 获取当前配置
@app.route('/admin/system_settings/config')
def get_system_config():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify(config.get_config())


# 更新系统配置
@app.route('/admin/system_settings/update', methods=['POST'])
def update_system_config():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        new_config = request.get_json()
        config.update_config(new_config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/patient/add', methods=['POST'])
def add_patient():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 检查手机号是否已存在
        c.execute('SELECT id FROM patients WHERE phone = ?', (data.get('phone'),))
        if c.fetchone():
            return jsonify({'error': '该手机号已注册'}), 400

        # 插入新用户，包含所有字段
        c.execute('''
            INSERT INTO patients (
                name, phone, password, age, gender, blood_type, height, weight, 
                conditions, allergies, occupation, ethnicity,  
                education, marital_status, is_smoker, is_drinker,
                surgery_history, medications, disease_history, systolic_bp, 
                diastolic_bp, bp_measure_time, family_history, regular_exercise
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name'),
            data.get('phone'),
            generate_password_hash('123456'),  # 默认密码
            data.get('age'),
            data.get('gender'),
            data.get('blood_type'),
            data.get('height'),
            data.get('weight'),
            data.get('conditions'),
            data.get('allergies'),
            data.get('occupation'),
            data.get('ethnicity'),
            # data.get('main_activity'),
            data.get('education'),
            # data.get('employment'),
            data.get('marital_status'),
            data.get('is_smoker', '否'),
            data.get('is_drinker', '否'),
            data.get('surgery_history'),
            data.get('medications'),
            data.get('disease_history'),
            data.get('systolic_bp'),
            data.get('diastolic_bp'),
            data.get('bp_measure_time'),
            data.get('family_history'),
            data.get('regular_exercise', '否')
        ))

        conn.commit()
        return jsonify({'success': True, 'patient_id': c.lastrowid})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ---------- 健康推送专用接口 ----------
def get_row_field(row, field_name, default_value=''):
    """
    安全地从数据库行对象中获取字段值

    参数:
        row: sqlite3.Row 对象
        field_name: 字段名
        default_value: 如果字段不存在或为None时的默认值

    返回:
        字段值或默认值
    """
    if row is None:
        return default_value

    # 检查字段是否存在
    if field_name not in row.keys():
        return default_value

    value = row[field_name]
    return value if value is not None else default_value


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

        # 获取用户完整健康信息
        c.execute('SELECT * FROM patients WHERE id = ?', (user_id,))
        user = c.fetchone()

        if not user:
            return jsonify({'error': '用户信息不存在'}), 404

        conn.close()

        # 使用辅助函数安全地获取字段值
        lines = [
            f"👤 患者基本信息：",
            f"姓名：{get_row_field(user, 'name', '未填写')}",
            f"年龄：{get_row_field(user, 'age', '未记录')}岁",
            f"性别：{get_row_field(user, 'gender', '未记录')}",
            f"血型：{get_row_field(user, 'blood_type', '未记录')}",
            f"身高：{get_row_field(user, 'height', '未记录')}",
            f"体重：{get_row_field(user, 'weight', '未记录')}",
            f"健康状况：{get_row_field(user, 'conditions', '无特殊记录')}",
            f"过敏史：{get_row_field(user, 'allergies', '无')}",
            f"吸烟：{get_row_field(user, 'is_smoker', '否')}",
            f"饮酒：{get_row_field(user, 'is_drinker', '否')}",
            f"规律运动：{get_row_field(user, 'regular_exercise', '否')}"
        ]

        # 添加其他健康信息
        disease_history = get_row_field(user, 'disease_history')
        family_history = get_row_field(user, 'family_history')
        medications = get_row_field(user, 'medications')

        if disease_history:
            lines.append(f"疾病史：{disease_history}")
        if family_history:
            lines.append(f"家族病史：{family_history}")
        if medications:
            lines.append(f"用药情况：{medications}")

        if user_text:
            lines.append(f"\n📝 用户补充信息：{user_text}")

        # 组合健康文本
        health_text = "\n".join(lines)

        # 使用 GraphRAG 系统生成知识
        rag_result = graph_rag.query(
            user_input=health_text,
            depth=2,
            similarity_threshold=0.75,
            top_k=5
        )

        return jsonify({
            'success': True,
            'knowledge_content': rag_result['answer'],
            'formatted_text': health_text
        })

    except Exception as e:
        print(f"生成健康知识失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'生成健康知识失败: {str(e)}'}), 500


def check_and_fix_document_paths():
    """
    检查并修复数据库中的文档路径
    """
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 获取所有文件类型的文档
        c.execute('SELECT id, path FROM knowledge_documents WHERE type = "file"')
        documents = c.fetchall()

        fixed_count = 0
        for doc_id, path in documents:
            # 检查路径是否是绝对路径
            if not os.path.isabs(path):
                # 尝试修复路径
                new_path = os.path.join(app.config['DOCUMENTS_DIR'], os.path.basename(path))

                # 如果新路径存在，更新数据库
                if os.path.exists(new_path):
                    c.execute('UPDATE knowledge_documents SET path = ? WHERE id = ?', (new_path, doc_id))
                    fixed_count += 1
                    print(f"修复文档 {doc_id} 的路径: {path} -> {new_path}")

        conn.commit()
        print(f"修复了 {fixed_count} 个文档路径")

    except Exception as e:
        print(f"修复文档路径时出错: {e}")
    finally:
        conn.close()


@app.route('/admin/knowledge/fix_paths', methods=['POST'])
def fix_document_paths():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        check_and_fix_document_paths()
        return jsonify({'success': True, 'fixed_count': '需要返回实际修复数量'})
    except Exception as e:
        return jsonify({'error': f'修复路径失败: {str(e)}'}), 500

# ========== 个人中心 ==========
@app.route('/profile/settings')
def profile_settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('profile_settings.html')


@app.route('/api/profile/basic', methods=['GET'])
def get_profile_basic():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    uid = session['user_id']
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id,name,phone FROM patients WHERE id=?', (uid,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify(dict(row))


@app.route('/api/profile/basic', methods=['PUT'])
def update_profile_basic():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    uid = session['user_id']
    data = request.get_json() or {}
    new_phone = data.get('phone')
    new_name = data.get('name')
    new_pwd = data.get('password')

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    if new_phone:
        c.execute('SELECT id FROM patients WHERE phone=? AND id!=?', (new_phone, uid))
        if c.fetchone():
            return jsonify({'error': '手机号已被占用'}), 400
    sql = 'UPDATE patients SET '
    args = []
    if new_name:
        sql += 'name=?,'
        args.append(new_name)
    if new_phone:
        sql += 'phone=?,'
        args.append(new_phone)
    if new_pwd:
        sql += 'password=?,'
        args.append(generate_password_hash(new_pwd))
    if not args:
        return jsonify({'error': '无更新内容'}), 400
    sql = sql.rstrip(',') + ' WHERE id=?'
    args.append(uid)
    c.execute(sql, args)
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# =========== 健康指标 CRUD ===========
# 1) 查询某患者全部指标
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

# 2) 新增指标
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

# 3) 修改指标
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

# 4) 删除指标
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


@app.route('/admin/patient/<int:patient_id>/update_full', methods=['PUT'])
def admin_update_patient_full(patient_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()

    # 1. 更新 patients 表（基本信息）
    sql_patient = '''
        UPDATE patients SET
          name=?, phone=?, age=?, gender=?, blood_type=?, height=?, weight=?,
          conditions=?, allergies=?, occupation=?, ethnicity=?, education=?,
          marital_status=?, is_smoker=?, is_drinker=?, regular_exercise=?,
          systolic_bp=?, diastolic_bp=?, bp_measure_time=?,
          surgery_history=?, medications=?, disease_history=?, family_history=?
        WHERE id=?
    '''
    params = [data[k] for k in (
        'name','phone','age','gender','blood_type','height','weight',
        'conditions','allergies','occupation','ethnicity','education',
        'marital_status','is_smoker','is_drinker','regular_exercise',
        'systolic_bp','diastolic_bp','bp_measure_time',
        'surgery_history','medications','disease_history','family_history'
    )] + [patient_id]
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute(sql_patient, params)

    # 2. 全量替换健康指标（简单方案：先删后插）
    c.execute('DELETE FROM check_metrics WHERE patient_id=?', (patient_id,))
    for m in data.get('metrics', []):
        c.execute(
            'INSERT INTO check_metrics(patient_id,item,result,reference_range,unit,date,status) VALUES (?,?,?,?,?,?,?)',
            (patient_id, m['item'], m['result'], m['reference_range'], m['unit'], m['date'], m['status'])
        )
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# 获取用户健康指标（分页+筛选）
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

    # 构建查询条件
    query = 'SELECT * FROM check_metrics WHERE patient_id = ?'
    params = [patient_id]

    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)

    # 获取总数
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    c.execute(count_query, params)
    total = c.fetchone()[0]

    # 添加排序和分页
    query += ' ORDER BY date DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])

    c.execute(query, params)
    metrics = c.fetchall()
    conn.close()

    # 格式化数据
    metrics_data = []
    for metric in metrics:
        metrics_data.append({
            'id': metric['id'],
            'item': metric['item'],
            'result': metric['result'],
            'reference_range': metric['reference_range'],
            'unit': metric['unit'],
            'date': metric['date'],
            'status': metric['status']
        })

    total_pages = (total + per_page - 1) // per_page

    return jsonify({
        'metrics': metrics_data,
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total,
            'per_page': per_page
        }
    })


# ============================== Prompt模板管理 ==============================
@app.route('/admin/prompt_templates')
def prompt_templates_management():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    return render_template('prompt_templates.html')


# 获取所有Prompt模板
@app.route('/api/prompt_templates', methods=['GET'])
def get_prompt_templates():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT * FROM prompt_templates 
        ORDER BY is_active DESC, created_at DESC
    ''')
    templates = c.fetchall()
    conn.close()

    templates_data = []
    for template in templates:
        templates_data.append({
            'id': template['id'],
            'name': template['name'],
            'description': template['description'],
            'content': template['content'],
            'category': template['category'],
            'is_active': bool(template['is_active']),
            'created_at': template['created_at'],
            'updated_at': template['updated_at']
        })

    return jsonify(templates_data)


# 获取单个Prompt模板
@app.route('/api/prompt_templates/<int:template_id>', methods=['GET'])
def get_prompt_template(template_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM prompt_templates WHERE id = ?', (template_id,))
    template = c.fetchone()
    conn.close()

    if not template:
        return jsonify({'error': '模板不存在'}), 404

    template_data = {
        'id': template['id'],
        'name': template['name'],
        'description': template['description'],
        'content': template['content'],
        'category': template['category'],
        'is_active': bool(template['is_active']),
        'created_at': template['created_at'],
        'updated_at': template['updated_at']
    }

    return jsonify(template_data)


# 创建新的Prompt模板
@app.route('/api/prompt_templates', methods=['POST'])
def create_prompt_template():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()

    if not data.get('name') or not data.get('content'):
        return jsonify({'error': '模板名称和内容不能为空'}), 400

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        c.execute('''
            INSERT INTO prompt_templates (name, description, content, category, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data.get('description', ''),
            data['content'],
            data.get('category', 'general'),
            data.get('is_active', False)
        ))

        template_id = c.lastrowid
        conn.commit()

        return jsonify({
            'success': True,
            'message': '模板创建成功',
            'template_id': template_id
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'创建模板失败: {str(e)}'}), 500
    finally:
        conn.close()


# 更新Prompt模板
@app.route('/api/prompt_templates/<int:template_id>', methods=['PUT'])
def update_prompt_template(template_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()

    if not data.get('name') or not data.get('content'):
        return jsonify({'error': '模板名称和内容不能为空'}), 400

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        c.execute('''
            UPDATE prompt_templates 
            SET name = ?, description = ?, content = ?, category = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data['name'],
            data.get('description', ''),
            data['content'],
            data.get('category', 'general'),
            template_id
        ))

        conn.commit()

        return jsonify({
            'success': True,
            'message': '模板更新成功'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'更新模板失败: {str(e)}'}), 500
    finally:
        conn.close()


# 删除Prompt模板
@app.route('/api/prompt_templates/<int:template_id>', methods=['DELETE'])
def delete_prompt_template(template_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 检查是否是激活模板
        c.execute('SELECT is_active FROM prompt_templates WHERE id = ?', (template_id,))
        template = c.fetchone()

        if template and template[0]:
            return jsonify({'error': '不能删除当前激活的模板'}), 400

        c.execute('DELETE FROM prompt_templates WHERE id = ?', (template_id,))
        conn.commit()

        return jsonify({
            'success': True,
            'message': '模板删除成功'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'删除模板失败: {str(e)}'}), 500
    finally:
        conn.close()


# 设置激活模板
@app.route('/api/prompt_templates/<int:template_id>/set_active', methods=['POST'])
def set_active_prompt_template(template_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    try:
        # 首先取消所有模板的激活状态
        c.execute('UPDATE prompt_templates SET is_active = 0')

        # 然后设置指定模板为激活状态
        c.execute('UPDATE prompt_templates SET is_active = 1 WHERE id = ?', (template_id,))
        conn.commit()

        return jsonify({
            'success': True,
            'message': '模板已设置为激活状态'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'设置激活模板失败: {str(e)}'}), 500
    finally:
        conn.close()


# 获取当前激活的模板
@app.route('/api/prompt_templates/active', methods=['GET'])
def get_active_prompt_template():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM prompt_templates WHERE is_active = 1')
    active_template = c.fetchone()
    conn.close()

    if not active_template:
        return jsonify({'error': '没有激活的模板'}), 404

    template_data = {
        'id': active_template['id'],
        'name': active_template['name'],
        'description': active_template['description'],
        'content': active_template['content'],
        'category': active_template['category'],
        'is_active': bool(active_template['is_active']),
        'created_at': active_template['created_at']
    }

    return jsonify(template_data)

# 在应用启动时调用此函数
check_and_fix_document_paths()

if __name__ == '__main__':
    init_all_db_and_patients()
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
