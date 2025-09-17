document.addEventListener('DOMContentLoaded', function () {
    console.log('用户健康档案管理脚本初始化');
    initAdminDashboard();
});

function initAdminDashboard() {
    console.log('初始化用户健康档案管理功能');
    
    // 绑定事件
    bindEvents();
    
    // 初始化搜索功能
    initSearch();
    
    // 初始化模态框
    initModals();

    // 初始化新增用户功能
    initAddUser();
}

function bindEvents() {
    // 刷新按钮
    document.getElementById('refreshPatients')?.addEventListener('click', refreshData);

    // 编辑按钮
    document.querySelectorAll('.btn-icon.edit').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            openEditModal(userId);
        });
    });

    // 查看按钮
    document.querySelectorAll('.btn-icon.view').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            openDetailModal(userId);
        });
    });

    // 删除按钮
    document.querySelectorAll('.btn-icon.delete').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            const userName = this.closest('tr').querySelector('.user-name').textContent;
            confirmDeleteUser(userId, userName);
        });
    });

    // 关闭模态框
    document.querySelectorAll('.close, .modal-footer .btn-outline').forEach(btn => {
        btn.addEventListener('click', closeModals);
    });

    // 新增用户按钮
    document.querySelector('.btn-primary')?.addEventListener('click', function() {
        openAddModal();
    });
}

function initSearch() {
    const searchInput = document.getElementById('searchPatients');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = document.querySelectorAll('.patients-table tbody tr');

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    row.style.display = '';
                    // 添加高亮动画
                    row.classList.add('highlight');
                    setTimeout(() => row.classList.remove('highlight'), 1000);
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
}

function initModals() {
    // 点击模态框外部关闭
    window.addEventListener('click', function(event) {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

function initAddUser() {
    // 初始化新增用户表单验证
    const addForm = document.getElementById('addUserForm');
    if (addForm) {
        addForm.addEventListener('submit', function(e) {
            e.preventDefault();
            addNewUser();
        });
    }
}

function refreshData() {
    const btn = document.getElementById('refreshPatients');
    if (btn) {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 刷新中...';
        btn.disabled = true;

        // 模拟刷新过程
        setTimeout(() => {
            // 实际应用中这里应该是API调用
            location.reload();
        }, 1000);
    }
}

function openEditModal(userId) {
    console.log('编辑用户:', userId);

    // 显示加载状态
    Swal.fire({
        title: '加载中...',
        text: '正在获取用户数据',
        icon: 'info',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        showConfirmButton: false,
        allowOutsideClick: false
    });

    // 获取用户详细信息
    fetch(`/admin/patient/${userId}/preview`)
        .then(response => response.json())
        .then(patient => {
            Swal.close();

            // 填充编辑表单
            populateEditForm(patient);

            // 显示编辑模态框
            document.getElementById('editUserModal').style.display = 'block';
        })
        .catch(err => {
            console.error(err);
            Swal.fire({
                title: '错误',
                text: '获取用户信息失败',
                icon: 'error',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#e2e2e2',
                confirmButtonColor: '#48dbfb'
            });
        });
}
// 在 populateEditForm 函数中添加所有健康信息字段
function populateEditForm(patient) {
    // 设置用户ID
    const userIdElement = document.getElementById('editUserId');
    if (userIdElement) {
        userIdElement.value = patient.id;
    }

    // 辅助函数：安全设置表单值
    function safeSetValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element && value !== undefined) {
            element.value = value || '';
        }
    }

    // 填充所有表单字段
    const fields = [
        'name', 'phone', 'age', 'gender', 'blood_type', 'height', 'weight',
        'conditions', 'allergies', 'occupation', 'ethnicity', 'main_activity',
        'education', 'employment', 'marital_status', 'is_smoker', 'is_drinker',
        'surgery_history', 'medications', 'disease_history', 'systolic_bp',
        'diastolic_bp', 'bp_measure_time', 'family_history', 'regular_exercise'
    ];

    fields.forEach(field => {
        safeSetValue(`edit_${field}`, patient[field]);
    });
}

// 在 populateDetailModal 函数中添加所有健康信息字段
function populateDetailModal(patient) {
    // 辅助函数：安全设置文本内容
    function safeSetText(elementId, text, defaultValue = '未填写') {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text || defaultValue;
        }
    }

    // 更新基本信息
    safeSetText('detail-name', patient.name);
    safeSetText('detail-id', patient.id);
    safeSetText('detail-phone', patient.phone);
    safeSetText('detail-age', patient.age);
    safeSetText('detail-gender', patient.gender);
    safeSetText('detail-blood-type', patient.blood_type);
    safeSetText('detail-height', patient.height);
    safeSetText('detail-weight', patient.weight);
    safeSetText('detail-created-at', patient.created_at, '未知');

    // 更新健康信息
    safeSetText('detail-conditions', patient.conditions, '无');
    safeSetText('detail-allergies', patient.allergies, '无');
    safeSetText('detail-occupation', patient.occupation);
    safeSetText('detail-ethnicity', patient.ethnicity);
    safeSetText('detail-main-activity', patient.main_activity);
    safeSetText('detail-education', patient.education);
    safeSetText('detail-employment', patient.employment);
    safeSetText('detail-marital-status', patient.marital_status);
    safeSetText('detail-is-smoker', patient.is_smoker, '否');
    safeSetText('detail-is-drinker', patient.is_drinker, '否');
    safeSetText('detail-surgery-history', patient.surgery_history, '无');
    safeSetText('detail-medications', patient.medications, '无');
    safeSetText('detail-disease-history', patient.disease_history, '无');
    safeSetText('detail-systolic-bp', patient.systolic_bp, '未测量');
    safeSetText('detail-diastolic-bp', patient.diastolic_bp, '未测量');
    safeSetText('detail-bp-measure-time', patient.bp_measure_time, '未记录');
    safeSetText('detail-family-history', patient.family_history, '无');
    safeSetText('detail-regular-exercise', patient.regular_exercise, '否');

    // 计算并显示BMI
    try {
        const height = parseFloat(patient.height) || 0;
        const weight = parseFloat(patient.weight) || 0;

        if (height > 0 && weight > 0) {
            const heightInM = height / 100;
            const bmi = (weight / (heightInM * heightInM)).toFixed(1);

            let bmiCategory = '';
            if (bmi < 18.5) bmiCategory = '偏瘦';
            else if (bmi < 24) bmiCategory = '正常';
            else if (bmi < 28) bmiCategory = '超重';
            else bmiCategory = '肥胖';

            safeSetText('detail-bmi', `${bmi} (${bmiCategory})`);
        } else {
            safeSetText('detail-bmi', '无法计算');
        }
    } catch (e) {
        safeSetText('detail-bmi', '无法计算');
    }
}
// 在 saveUserChanges 函数中，确保发送正确的数据格式
function saveUserChanges() {
    const userId = document.getElementById('editUserId').value;

    // 收集表单数据
    const formData = new FormData(document.getElementById('editUserForm'));

    // 转换为JSON对象，同时处理字段名（移除edit_前缀）
    const data = {};
    formData.forEach((value, key) => {
        // 移除字段名中的"edit_"前缀
        const cleanKey = key.replace('edit_', '');
        data[cleanKey] = value;
    });

    // 显示加载状态
    Swal.fire({
        title: '保存中...',
        text: '正在更新用户信息',
        icon: 'info',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        showConfirmButton: false,
        allowOutsideClick: false
    });

    // 发送更新请求
    fetch(`/admin/patient/${userId}/update_basic`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应异常: ' + response.status);
        }
        return response.json();
    })
    .then(result => {
        if (result.success) {
            Swal.fire({
                title: '成功',
                text: '用户信息已更新',
                icon: 'success',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#e2e2e2',
                confirmButtonColor: '#48dbfb'
            }).then(() => {
                // 关闭模态框并刷新页面
                closeModals();
                location.reload();
            });
        } else {
            throw new Error(result.error || '更新失败');
        }
    })
    .catch(err => {
        console.error(err);
        Swal.fire({
            title: '错误',
            text: '更新用户信息失败: ' + err.message,
            icon: 'error',
            background: 'rgba(26, 26, 46, 0.9)',
            color: '#e2e2e2',
            confirmButtonColor: '#48dbfb'
        });
    });
}

// 在 openDetailModal 函数中，确保正确获取用户详情
function openDetailModal(userId) {
    console.log('查看用户详情:', userId);

    // 显示加载状态
    Swal.fire({
        title: '加载中...',
        text: '正在获取用户详细信息',
        icon: 'info',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        showConfirmButton: false,
        allowOutsideClick: false
    });

    // 获取用户详细信息 - 确保使用正确的API端点
    fetch(`/admin/patient/${userId}/preview`)
        .then(response => {
            if (!response.ok) {
                throw new Error('获取用户信息失败: ' + response.status);
            }
            return response.json();
        })
        .then(patient => {
            Swal.close();

            // 填充详情模态框
            populateDetailModal(patient);

            // 显示详情模态框
            document.getElementById('userDetailModal').style.display = 'block';
        })
        .catch(err => {
            console.error(err);
            Swal.fire({
                title: '错误',
                text: '获取用户信息失败: ' + err.message,
                icon: 'error',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#e2e2e2',
                confirmButtonColor: '#48dbfb'
            });
        });
}

function populateDetailModal(patient) {
    // 辅助函数：安全设置文本内容
    function safeSetText(elementId, text, defaultValue = '未填写') {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text || defaultValue;
        }
    }

    // 更新基本信息
    safeSetText('detail-name', patient.name);
    safeSetText('detail-id', patient.id);
    safeSetText('detail-phone', patient.phone);
    safeSetText('detail-age', patient.age);
    safeSetText('detail-gender', patient.gender);
    safeSetText('detail-blood-type', patient.blood_type);
    safeSetText('detail-height', patient.height);
    safeSetText('detail-weight', patient.weight);

    // 更新健康信息
    safeSetText('detail-conditions', patient.conditions, '无');
    safeSetText('detail-allergies', patient.allergies, '无');
    safeSetText('detail-occupation', patient.occupation);
    safeSetText('detail-ethnicity', patient.ethnicity);
    safeSetText('detail-main-activity', patient.main_activity);
    safeSetText('detail-education', patient.education);
    safeSetText('detail-employment', patient.employment);
    safeSetText('detail-marital-status', patient.marital_status);
    safeSetText('detail-is-smoker', patient.is_smoker, '否');
    safeSetText('detail-is-drinker', patient.is_drinker, '否');
    safeSetText('detail-surgery-history', patient.surgery_history, '无');
    safeSetText('detail-medications', patient.medications, '无');
    safeSetText('detail-disease-history', patient.disease_history, '无');
    safeSetText('detail-systolic-bp', patient.systolic_bp, '未测量');
    safeSetText('detail-diastolic-bp', patient.diastolic_bp, '未测量');
    safeSetText('detail-bp-measure-time', patient.bp_measure_time, '未记录');
    safeSetText('detail-family-history', patient.family_history, '无');
    safeSetText('detail-regular-exercise', patient.regular_exercise, '否');

    // 计算并显示BMI
    try {
        const height = parseFloat(patient.height) || 0;
        const weight = parseFloat(patient.weight) || 0;

        if (height > 0 && weight > 0) {
            const heightInM = height / 100;
            const bmi = (weight / (heightInM * heightInM)).toFixed(1);

            let bmiCategory = '';
            if (bmi < 18.5) bmiCategory = '偏瘦';
            else if (bmi < 24) bmiCategory = '正常';
            else if (bmi < 28) bmiCategory = '超重';
            else bmiCategory = '肥胖';

            safeSetText('detail-bmi', `${bmi} (${bmiCategory})`);
        } else {
            safeSetText('detail-bmi', '无法计算');
        }
    } catch (e) {
        safeSetText('detail-bmi', '无法计算');
    }
}

// 修复 populateEditForm 函数，添加元素存在性检查
function populateEditForm(patient) {
    // 设置用户ID
    const userIdElement = document.getElementById('editUserId');
    if (userIdElement) {
        userIdElement.value = patient.id;
    }

    // 辅助函数：安全设置表单值
    function safeSetValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element && value !== undefined) {
            element.value = value || '';
        }
    }

    // 填充基本表单字段
    const fields = [
        'name', 'phone', 'age', 'gender', 'blood_type', 'height', 'weight',
        'conditions', 'allergies', 'occupation', 'ethnicity', 'main_activity',
        'education', 'employment', 'marital_status', 'is_smoker', 'is_drinker',
        'surgery_history', 'medications', 'disease_history', 'systolic_bp',
        'diastolic_bp', 'bp_measure_time', 'family_history', 'regular_exercise'
    ];

    fields.forEach(field => {
        safeSetValue(`edit_${field}`, patient[field]);
    });
}


function openAddModal() {
    // 显示新增用户模态框
    document.getElementById('addUserModal').style.display = 'block';
}

// 在 addNewUser 函数中，确保发送正确的数据格式
function addNewUser() {
    const formData = new FormData(document.getElementById('addUserForm'));

    // 转换为JSON对象
    const data = {};
    formData.forEach((value, key) => {
        data[key] = value;
    });

    // 显示加载状态
    Swal.fire({
        title: '创建中...',
        text: '正在创建新用户',
        icon: 'info',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        showConfirmButton: false,
        allowOutsideClick: false
    });

    // 发送创建请求
    fetch('/admin/patient/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应异常: ' + response.status);
        }
        return response.json();
    })
    .then(result => {
        if (result.success) {
            Swal.fire({
                title: '成功',
                text: '用户创建成功',
                icon: 'success',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#e2e2e2',
                confirmButtonColor: '#48dbfb'
            }).then(() => {
                // 关闭模态框并刷新页面
                closeModals();
                location.reload();
            });
        } else {
            throw new Error(result.error || '创建失败');
        }
    })
    .catch(err => {
        console.error(err);
        Swal.fire({
            title: '错误',
            text: '创建用户失败: ' + err.message,
            icon: 'error',
            background: 'rgba(26, 26, 46, 0.9)',
            color: '#e2e2e2',
            confirmButtonColor: '#48dbfb'
        });
    });
}

function confirmDeleteUser(userId, userName) {
    Swal.fire({
        title: `确认删除用户?`,
        text: `您确定要永久删除用户 "${userName}" 吗？此操作不可撤销！`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonColor: '#dc3545',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        customClass: {
            confirmButton: 'btn btn-danger',
            cancelButton: 'btn btn-secondary'
        },
        buttonsStyling: false
    }).then((result) => {
        if (result.isConfirmed) {
            deleteUser(userId);
        }
    });
}

function deleteUser(userId) {
    // 模拟API调用
    fetch(`/admin/patient/${userId}`, {
        method: 'DELETE'
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                Swal.fire({
                    title: '已删除',
                    text: '用户已成功删除',
                    icon: 'success',
                    background: 'rgba(26, 26, 46, 0.9)',
                    color: '#e2e2e2',
                    confirmButtonColor: '#48dbfb'
                });
                setTimeout(() => location.reload(), 1000);
            } else {
                Swal.fire({
                    title: '失败',
                    text: data.error || '删除失败',
                    icon: 'error',
                    background: 'rgba(26, 26, 46, 0.9)',
                    color: '#e2e2e2',
                    confirmButtonColor: '#48dbfb'
                });
            }
        })
        .catch(err => {
            console.error(err);
            Swal.fire({
                title: '错误',
                text: '请求失败，请检查网络或控制台',
                icon: 'error',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#e2e2e2',
                confirmButtonColor: '#48dbfb'
            });
        });
}

function closeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
}

// 添加高亮动画CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes highlight {
        0% { background-color: rgba(72, 219, 251, 0.1); }
        100% { background-color: transparent; }
    }

    .highlight {
        animation: highlight 1s ease;
    }

    .detail-section {
        margin-bottom: 20px;
        padding: 15px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
    }

    .detail-section h4 {
        margin-bottom: 15px;
        color: var(--accent-4);
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 8px;
    }

    .detail-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 15px;
    }

    .detail-item {
        display: flex;
        flex-direction: column;
    }

    .detail-item label {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 5px;
    }

    .detail-item span {
        font-weight: 500;
    }

    .form-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 15px;
        max-height: 60vh;
        overflow-y: auto;
        padding: 10px;
    }

    .form-group {
        margin-bottom: 15px;
    }

    .form-group label {
        display: block;
        margin-bottom: 5px;
        font-weight: 500;
    }

    .form-group input,
    .form-group select,
    .form-group textarea {
        width: 100%;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.08);
        color: var(--text);
    }

    .form-group textarea {
        min-height: 80px;
        resize: vertical;
    }
`;
document.head.appendChild(style);