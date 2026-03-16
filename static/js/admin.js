document.addEventListener('DOMContentLoaded', function () {
    console.log('用户健康档案管理脚本初始化');
    initAdminDashboard();
});

// 全局变量
let currentPatientId = null;
let currentMetrics = [];
let addUserMetrics = [];

function initAdminDashboard() {
    console.log('初始化用户健康档案管理功能');

    // 绑定事件
    bindEvents();

    // 初始化搜索功能
    initSearch();

    // 初始化模态框
    initModals();
}

function bindEvents() {
    console.log('绑定事件...');

    // 刷新按钮
    const refreshBtn = document.getElementById('refreshPatients');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }

    // 新增用户按钮
    const addUserBtn = document.getElementById('addUserBtn');
    if (addUserBtn) {
        addUserBtn.addEventListener('click', openAddModal);
    }

    // 使用事件委托处理表格中的操作按钮
    document.addEventListener('click', function(e) {
        // 编辑按钮
        if (e.target.closest('.btn-icon.edit')) {
            const btn = e.target.closest('.btn-icon.edit');
            const userId = btn.getAttribute('data-id');
            console.log('点击编辑按钮:', userId);
            openEditModal(userId);
        }

        // 查看按钮
        if (e.target.closest('.btn-icon.view')) {
            const btn = e.target.closest('.btn-icon.view');
            const userId = btn.getAttribute('data-id');
            console.log('点击查看按钮:', userId);
            openDetailModal(userId);
        }

        // 删除按钮
        if (e.target.closest('.btn-icon.delete')) {
            const btn = e.target.closest('.btn-icon.delete');
            const userId = btn.getAttribute('data-id');
            const userName = btn.closest('tr').querySelector('.user-name').textContent;
            console.log('点击删除按钮:', userId);
            confirmDeleteUser(userId, userName);
        }
    });

    // 标签页切换
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('tab-button')) {
            const tabButton = e.target;
            handleTabClick(tabButton);
        }
    });

    // 关闭模态框按钮
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', closeModals);
    });

    // 取消按钮
    document.getElementById('cancelEditBtn')?.addEventListener('click', closeModals);
    document.getElementById('cancelAddBtn')?.addEventListener('click', closeModals);
    document.getElementById('cancelMetricBtn')?.addEventListener('click', closeModals);

    // 保存按钮
    document.getElementById('saveEditBtn')?.addEventListener('click', saveUserChanges);
    document.getElementById('saveAddBtn')?.addEventListener('click', addNewUser);
    document.getElementById('saveMetricBtn')?.addEventListener('click', saveMetric);

    // 健康指标相关按钮
    document.getElementById('addMetricBtn')?.addEventListener('click', () => openMetricModal('edit'));
    document.getElementById('addFirstMetricBtn')?.addEventListener('click', () => openMetricModal('edit'));
    document.getElementById('addUserMetricBtn')?.addEventListener('click', () => openMetricModal('add'));
    document.getElementById('addUserFirstMetricBtn')?.addEventListener('click', () => openMetricModal('add'));

    // 健康指标表格中的编辑和删除按钮使用事件委托
    document.addEventListener('click', function(e) {
        // 编辑指标按钮
        if (e.target.closest('.btn-edit')) {
            const btn = e.target.closest('.btn-edit');
            const index = parseInt(btn.getAttribute('data-index'));
            const context = btn.getAttribute('data-context');
            console.log('点击编辑指标按钮:', index, context);
            if (context === 'add') {
                editAddMetric(index);
            } else {
                editMetric(index);
            }
        }

        // 删除指标按钮
        if (e.target.closest('.btn-delete')) {
            const btn = e.target.closest('.btn-delete');
            const index = parseInt(btn.getAttribute('data-index'));
            const context = btn.getAttribute('data-context');
            console.log('点击删除指标按钮:', index, context);
            if (context === 'add') {
                deleteAddMetric(index);
            } else {
                deleteMetric(index);
            }
        }
    });

    console.log('所有事件绑定完成');
}

function handleTabClick(tabButton) {
    console.log('处理标签页点击:', tabButton.getAttribute('data-tab'));

    const tabContainer = tabButton.closest('.form-tabs');
    if (!tabContainer) return;

    const tabButtons = tabContainer.querySelectorAll('.tab-button');
    const tabContents = tabContainer.querySelectorAll('.tab-content');

    // 移除所有active类
    tabButtons.forEach(btn => btn.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));

    // 激活当前标签
    tabButton.classList.add('active');
    const tabId = tabButton.getAttribute('data-tab') + '-tab';
    const tabContent = document.getElementById(tabId);

    if (tabContent) {
        tabContent.classList.add('active');
        console.log('激活标签页内容:', tabId);
    }
}

function initSearch() {
    const searchInput = document.getElementById('searchPatients');
    if (searchInput) {
        let searchTimer = null;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimer);
            const searchTerm = this.value.trim();
            searchTimer = setTimeout(() => {
                if (searchTerm.length === 0) {
                    window.location.href = '/admin/dashboard';
                } else {
                    window.location.href = '/admin/dashboard?search=' + encodeURIComponent(searchTerm);
                }
            }, 600);
        });
        // 保持搜索框内容
        const urlParams = new URLSearchParams(window.location.search);
        const currentSearch = urlParams.get('search');
        if (currentSearch) {
            searchInput.value = currentSearch;
        }
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

    // ESC键关闭模态框
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModals();
        }
    });
}

function refreshData() {
    console.log('刷新数据...');
    const btn = document.getElementById('refreshPatients');
    if (btn) {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 刷新中...';
        btn.disabled = true;

        setTimeout(() => {
            location.reload();
        }, 1000);
    }
}

function openEditModal(userId) {
    console.log('打开编辑模态框:', userId);
    currentPatientId = userId;

    showLoading('正在获取用户数据...');

    Promise.all([
        fetch(`/admin/patient/${userId}/preview`).then(r => {
            if (!r.ok) throw new Error('获取用户信息失败');
            return r.json();
        }),
        fetch(`/admin/patient/${userId}/metrics`).then(r => {
            if (!r.ok) throw new Error('获取健康指标失败');
            return r.json();
        })
    ])
    .then(([patient, metrics]) => {
        hideLoading();

        populateEditForm(patient);
        currentMetrics = metrics;
        renderMetricsTable('edit');

        // 重置标签页到第一个
        resetTabs('editUserModal');

        const modal = document.getElementById('editUserModal');
        if (modal) {
            modal.style.display = 'block';
            console.log('编辑模态框显示成功');
        }
    })
    .catch(err => {
        hideLoading();
        console.error('打开编辑模态框失败:', err);
        showError('获取用户信息失败: ' + err.message);
    });
}

function populateEditForm(patient) {
    console.log('填充编辑表单:', patient.id);

    const userIdElement = document.getElementById('editUserId');
    if (userIdElement) {
        userIdElement.value = patient.id;
    }

    function safeSetValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element && value !== undefined) {
            element.value = value || '';
        }
    }

    const fields = [
        'name', 'phone', 'age', 'gender', 'blood_type', 'height', 'weight',
        'conditions', 'allergies', 'occupation', 'ethnicity', 'education',
        'marital_status', 'is_smoker', 'is_drinker', 'regular_exercise',
        'systolic_bp', 'diastolic_bp', 'bp_measure_time', 'surgery_history',
        'medications', 'disease_history', 'family_history'
    ];

    fields.forEach(field => {
        safeSetValue(`edit_${field}`, patient[field]);
    });
}

function renderMetricsTable(context) {
    console.log('渲染健康指标表格:', context);

    const metrics = context === 'add' ? addUserMetrics : currentMetrics;
    const tableId = context === 'add' ? 'add-metrics-table' : 'edit-metrics-table';
    const noDataId = context === 'add' ? 'add-no-metrics' : 'edit-no-metrics';

    const tbody = document.querySelector(`#${tableId} tbody`);
    const noDataMsg = document.getElementById(noDataId);

    if (!tbody) {
        console.error('找不到表格tbody:', tableId);
        return;
    }

    tbody.innerHTML = '';

    if (metrics.length === 0) {
        tbody.style.display = 'none';
        if (noDataMsg) noDataMsg.style.display = 'flex';
        return;
    }

    tbody.style.display = 'table-row-group';
    if (noDataMsg) noDataMsg.style.display = 'none';

    metrics.forEach((metric, index) => {
        const statusClass = metric.status === 'normal' ? 'badge-success' : 'badge-warning';
        const statusText = metric.status === 'normal' ? '正常' : '异常';

        tbody.insertAdjacentHTML('beforeend', `
            <tr data-index="${index}">
                <td>${metric.item || ''}</td>
                <td>${metric.result || ''}</td>
                <td>${metric.reference_range || ''}</td>
                <td>${metric.unit || ''}</td>
                <td>${metric.date || ''}</td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
                <td>
                    <button class="btn-icon btn-edit" data-index="${index}" data-context="${context}" title="编辑">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon btn-delete" data-index="${index}" data-context="${context}" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `);
    });
}

function openMetricModal(context) {
    console.log('打开健康指标模态框，上下文:', context);

    document.getElementById('metricForm').reset();
    document.getElementById('metricId').value = '';
    document.getElementById('metricContext').value = context;

    const today = new Date().toISOString().split('T')[0];
    document.getElementById('mDate').value = today;

    const modal = document.getElementById('metricModal');
    if (modal) {
        modal.style.display = 'block';
        console.log('健康指标模态框显示成功');
    }
}

function editMetric(index) {
    console.log('编辑指标:', index);
    const metric = currentMetrics[index];
    if (!metric) {
        console.error('找不到指标:', index);
        return;
    }

    document.getElementById('metricId').value = metric.id || '';
    document.getElementById('metricContext').value = 'edit';
    document.getElementById('mItem').value = metric.item || '';
    document.getElementById('mResult').value = metric.result || '';
    document.getElementById('mRange').value = metric.reference_range || '';
    document.getElementById('mUnit').value = metric.unit || '';
    document.getElementById('mDate').value = metric.date || '';
    document.getElementById('mStatus').value = metric.status || 'normal';

    const modal = document.getElementById('metricModal');
    if (modal) {
        modal.style.display = 'block';
        console.log('健康指标编辑模态框显示成功');
    }
}

function editAddMetric(index) {
    console.log('编辑新增用户指标:', index);
    const metric = addUserMetrics[index];
    if (!metric) {
        console.error('找不到新增用户指标:', index);
        return;
    }

    document.getElementById('metricId').value = metric.tempId || '';
    document.getElementById('metricContext').value = 'add';
    document.getElementById('mItem').value = metric.item || '';
    document.getElementById('mResult').value = metric.result || '';
    document.getElementById('mRange').value = metric.reference_range || '';
    document.getElementById('mUnit').value = metric.unit || '';
    document.getElementById('mDate').value = metric.date || '';
    document.getElementById('mStatus').value = metric.status || 'normal';

    const modal = document.getElementById('metricModal');
    if (modal) {
        modal.style.display = 'block';
        console.log('健康指标编辑模态框显示成功');
    }
}

function saveMetric() {
    console.log('保存健康指标');

    const context = document.getElementById('metricContext').value;
    const metricId = document.getElementById('metricId').value;
    const metricData = {
        item: document.getElementById('mItem').value.trim(),
        result: document.getElementById('mResult').value.trim(),
        reference_range: document.getElementById('mRange').value.trim(),
        unit: document.getElementById('mUnit').value.trim(),
        date: document.getElementById('mDate').value,
        status: document.getElementById('mStatus').value
    };

    console.log('指标数据:', metricData);
    console.log('上下文:', context, '指标ID:', metricId);

    if (!metricData.item || !metricData.result || !metricData.date) {
        showError('请填写检查项目、结果和日期');
        return;
    }

    if (context === 'edit') {
        saveEditMetric(metricId, metricData);
    } else {
        saveAddMetric(metricId, metricData);
    }
}

function saveEditMetric(metricId, metricData) {
    console.log('保存编辑指标:', metricId, metricData);

    if (!currentPatientId) {
        showError('用户ID不存在');
        return;
    }

    const isEdit = !!metricId;
    const url = isEdit
        ? `/admin/metrics/${metricId}`
        : `/admin/patient/${currentPatientId}/metrics`;
    const method = isEdit ? 'PUT' : 'POST';

    console.log('请求URL:', url, '方法:', method);

    showLoading(isEdit ? '更新指标中...' : '新增指标中...');

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(metricData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应异常: ' + response.status);
        }
        return response.json();
    })
    .then(result => {
        hideLoading();

        if (result.success) {
            showSuccess(isEdit ? '指标更新成功' : '指标新增成功');
            closeModals();
            loadPatientMetrics(currentPatientId);
        } else {
            throw new Error(result.error || '操作失败');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('保存指标失败:', error);
        showError('保存指标失败: ' + error.message);
    });
}

function saveAddMetric(metricId, metricData) {
    console.log('保存新增指标:', metricId, metricData);

    const isEdit = !!metricId;

    if (isEdit) {
        const index = addUserMetrics.findIndex(m => m.tempId === metricId);
        if (index !== -1) {
            addUserMetrics[index] = { ...addUserMetrics[index], ...metricData };
            console.log('更新指标成功，索引:', index);
        }
    } else {
        metricData.tempId = 'temp_' + Date.now();
        addUserMetrics.push(metricData);
        console.log('新增指标成功，总数:', addUserMetrics.length);
    }

    showSuccess(isEdit ? '指标更新成功' : '指标新增成功');
    closeModals();
    renderMetricsTable('add');
}

function deleteMetric(index) {
    console.log('删除指标:', index);
    const metric = currentMetrics[index];
    if (!metric || !metric.id) {
        console.error('找不到要删除的指标:', index);
        return;
    }

    Swal.fire({
        title: '确认删除',
        text: `确定要删除"${metric.item}"这项指标记录吗？`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonColor: '#dc3545',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2'
    }).then((result) => {
        if (result.isConfirmed) {
            showLoading('删除指标中...');

            fetch(`/admin/metrics/${metric.id}`, {
                method: 'DELETE'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应异常: ' + response.status);
                }
                return response.json();
            })
            .then(result => {
                hideLoading();

                if (result.success) {
                    showSuccess('指标删除成功');
                    loadPatientMetrics(currentPatientId);
                } else {
                    throw new Error(result.error || '删除失败');
                }
            })
            .catch(error => {
                hideLoading();
                console.error('删除指标失败:', error);
                showError('删除指标失败: ' + error.message);
            });
        }
    });
}

function deleteAddMetric(index) {
    console.log('删除新增用户指标:', index);
    const metric = addUserMetrics[index];
    if (!metric) {
        console.error('找不到要删除的新增用户指标:', index);
        return;
    }

    Swal.fire({
        title: '确认删除',
        text: `确定要删除"${metric.item}"这项指标记录吗？`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonColor: '#dc3545',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2'
    }).then((result) => {
        if (result.isConfirmed) {
            addUserMetrics.splice(index, 1);
            showSuccess('指标删除成功');
            renderMetricsTable('add');
        }
    });
}

function loadPatientMetrics(patientId) {
    console.log('加载患者指标:', patientId);

    fetch(`/admin/patient/${patientId}/metrics`)
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应异常: ' + response.status);
            }
            return response.json();
        })
        .then(metrics => {
            currentMetrics = metrics;
            renderMetricsTable('edit');
        })
        .catch(error => {
            console.error('加载健康指标失败:', error);
            showError('加载健康指标失败');
        });
}

function resetTabs(modalId) {
    console.log('重置标签页:', modalId);

    const modal = document.getElementById(modalId);
    if (!modal) {
        console.error('找不到模态框:', modalId);
        return;
    }

    const tabButtons = modal.querySelectorAll('.tab-button');
    const tabContents = modal.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => btn.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));

    if (tabButtons.length > 0) {
        const firstButton = tabButtons[0];
        const firstTabId = firstButton.getAttribute('data-tab') + '-tab';
        const firstTabContent = modal.querySelector(`#${firstTabId}`);

        firstButton.classList.add('active');

        if (firstTabContent) {
            firstTabContent.classList.add('active');
            console.log('激活标签页:', firstTabId);
        }
    }
}

function openDetailModal(userId) {
    console.log('打开详情模态框:', userId);

    showLoading('正在获取用户详细信息...');

    Promise.all([
        fetch(`/admin/patient/${userId}/preview`).then(r => {
            if (!r.ok) throw new Error('获取用户信息失败');
            return r.json();
        }),
        fetch(`/admin/patient/${userId}/metrics`).then(r => {
            if (!r.ok) throw new Error('获取健康指标失败');
            return r.json();
        }),
        fetch(`/api/image_analyses?patient_id=${userId}`).then(r => r.json()).catch(() => [])
    ])
    .then(([patient, metrics, analyses]) => {
        hideLoading();

        populateDetailModal(patient, metrics);
        renderImageAnalyses(analyses);

        const modal = document.getElementById('userDetailModal');
        if (modal) {
            modal.style.display = 'block';
        }
    })
    .catch(err => {
        hideLoading();
        console.error('打开详情模态框失败:', err);
        showError('获取用户信息失败: ' + err.message);
    });
}

function renderImageAnalyses(analyses) {
    const container = document.getElementById('detail-image-analyses');
    const noMsg = document.getElementById('no-analyses-message');
    if (!container) return;

    if (!analyses || analyses.length === 0) {
        if (noMsg) noMsg.style.display = 'flex';
        return;
    }
    if (noMsg) noMsg.style.display = 'none';

    let html = '<div style="max-height:300px;overflow-y:auto;">';
    analyses.forEach(a => {
        const saved = a.is_saved_to_profile ? '<span style="color:#2ecc71;font-size:11px;"><i class="fas fa-check-circle"></i> 已同步</span>' : '<span style="color:#f39c12;font-size:11px;">未同步</span>';
        html += `<div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:14px;margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="color:#48dbfb;font-weight:600;font-size:13px;"><i class="fas fa-x-ray"></i> ${a.image_type||'通用'}</span>
                <span style="font-size:11px;color:rgba(255,255,255,.4);">${(a.created_at||'').substring(0,16)} ${saved}</span>
            </div>
            <div style="color:rgba(255,255,255,.8);font-size:12px;line-height:1.6;max-height:120px;overflow-y:auto;white-space:pre-wrap;">${(a.analysis_result||'').substring(0,500)}${(a.analysis_result||'').length>500?'...':''}</div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

function populateDetailModal(patient, metrics) {
    console.log('填充详情模态框:', patient.id);

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
    safeSetText('detail-education', patient.education);
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

    // 渲染健康指标
    renderDetailMetrics(metrics);
}

function renderDetailMetrics(metrics) {
    console.log('渲染详情健康指标:', metrics.length);

    const tbody = document.getElementById('detail-metrics-body');
    const noDataMsg = document.getElementById('no-metrics-message');

    if (!tbody) {
        console.error('找不到详情指标表格tbody');
        return;
    }

    tbody.innerHTML = '';

    if (metrics.length === 0) {
        tbody.style.display = 'none';
        if (noDataMsg) noDataMsg.style.display = 'flex';
        return;
    }

    tbody.style.display = 'table-row-group';
    if (noDataMsg) noDataMsg.style.display = 'none';

    metrics.forEach((metric, index) => {
        const statusClass = metric.status === 'normal' ? 'badge-success' : 'badge-warning';
        const statusText = metric.status === 'normal' ? '正常' : '异常';

        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td>${metric.item || ''}</td>
                <td>${metric.result || ''}</td>
                <td>${metric.reference_range || ''}</td>
                <td>${metric.unit || ''}</td>
                <td>${metric.date || ''}</td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
            </tr>
        `);
    });
}

function saveUserChanges() {
    const userId = document.getElementById('editUserId').value;
    console.log('保存用户更改:', userId);

    const formData = new FormData(document.getElementById('editUserForm'));

    const data = {};
    formData.forEach((value, key) => {
        const cleanKey = key.replace('edit_', '');
        data[cleanKey] = value;
    });

    console.log('保存的用户数据:', data);

    showLoading('正在更新用户信息...');

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
            showSuccess('用户信息已更新');
            closeModals();
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error(result.error || '更新失败');
        }
    })
    .catch(err => {
        console.error('保存用户更改失败:', err);
        showError('更新用户信息失败: ' + err.message);
    });
}

function openAddModal() {
    console.log('打开新增用户模态框');

    document.getElementById('addUserForm').reset();
    addUserMetrics = [];
    renderMetricsTable('add');

    resetTabs('addUserModal');

    const modal = document.getElementById('addUserModal');
    if (modal) {
        modal.style.display = 'block';
        console.log('新增用户模态框显示成功');
    }
}

function addNewUser() {
    console.log('新增用户');

    const formData = new FormData(document.getElementById('addUserForm'));

    const data = {};
    formData.forEach((value, key) => {
        data[key] = value;
    });

    if (addUserMetrics.length > 0) {
        data.metrics = addUserMetrics;
    }

    console.log('新增用户数据:', data);

    showLoading('正在创建新用户...');

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
            if (result.merged) {
                showSuccess('该手机号用户已存在，已自动合并健康信息到该用户');
            } else {
                showSuccess('用户创建成功（默认密码: 123456）');
            }
            closeModals();
            setTimeout(() => location.reload(), 1500);
        } else {
            throw new Error(result.error || '创建失败');
        }
    })
    .catch(err => {
        console.error('新增用户失败:', err);
        showError('创建用户失败: ' + err.message);
    });
}

function confirmDeleteUser(userId, userName) {
    console.log('确认删除用户:', userId, userName);

    Swal.fire({
        title: `确认删除用户?`,
        text: `您确定要永久删除用户 "${userName}" 吗？此操作不可撤销！`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonColor: '#dc3545',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2'
    }).then((result) => {
        if (result.isConfirmed) {
            deleteUser(userId);
        }
    });
}

function deleteUser(userId) {
    console.log('删除用户:', userId);

    fetch(`/admin/patient/${userId}`, {
        method: 'DELETE'
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showSuccess('用户已成功删除');
                setTimeout(() => location.reload(), 1000);
            } else {
                showError(data.error || '删除失败');
            }
        })
        .catch(err => {
            console.error('删除用户失败:', err);
            showError('请求失败，请检查网络或控制台');
        });
}

function closeModals() {
    console.log('关闭所有模态框');

    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
}

// 工具函数
function showLoading(message) {
    Swal.fire({
        title: message,
        text: '请稍候...',
        icon: 'info',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        showConfirmButton: false,
        allowOutsideClick: false
    });
}

function hideLoading() {
    Swal.close();
}

function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: '成功',
        text: message,
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        confirmButtonColor: '#48dbfb',
        timer: 2000
    });
}

function showError(message) {
    Swal.fire({
        icon: 'error',
        title: '错误',
        text: message,
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        confirmButtonColor: '#48dbfb'
    });
}