// 全局变量
let currentPatientId = null;
let medicalRecords = [];
let checkMetrics = [];

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 模态框功能
    const modal = document.getElementById('patientModal');
    const closeModal = document.getElementById('closeModal');
    const editButtons = document.querySelectorAll('.btn-icon.edit');

    // 打开模态框
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            currentPatientId = this.getAttribute('data-id');
            loadPatientData(currentPatientId);
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });
    });

    // 关闭模态框
    closeModal.addEventListener('click', closeModalHandler);
    modal.addEventListener('click', function(e) {
        if (e.target === modal) closeModalHandler();
    });

    // 选项卡切换
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));

            this.classList.add('active');
            const tabId = this.getAttribute('data-tab') + 'Tab';
            document.getElementById(tabId).classList.add('active');

            if (tabId === 'medicalTab') loadMedicalRecords();
            else if (tabId === 'metricsTab') loadCheckMetrics();
        });
    });

    // 刷新按钮
    document.getElementById('refreshPatients')?.addEventListener('click', function() {
        location.reload();
    });
});

// 点击模态框外部关闭预览
document.getElementById('previewModal').addEventListener('click', function(e) {
    if (e.target === this) {
        this.style.display = 'none';
    }
});

// 关闭模态框处理
function closeModalHandler() {
    const modal = document.getElementById('patientModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
    currentPatientId = null;
    medicalRecords = [];
    checkMetrics = [];
}

// 加载患者数据
function loadPatientData(patientId) {
    fetch(`/admin/patient/${patientId}`)
        .then(response => response.json())
        .then(data => {
            // 填充基本信息
            document.getElementById('patientName').value = data.name || '';
            document.getElementById('patientAge').value = data.age || '';
            document.getElementById('patientGender').value = data.gender || '男';
            document.getElementById('patientPhone').value = data.phone || '';
            document.getElementById('patientBloodType').value = data.blood_type || 'O型';
            document.getElementById('patientHeight').value = data.height || '';
            document.getElementById('patientWeight').value = data.weight || '';
            document.getElementById('patientAllergies').value = data.allergies || '';
            document.getElementById('patientConditions').value = data.conditions || '';

            // 填充新增字段
            document.getElementById('patientOccupation').value = data.occupation || '';
            document.getElementById('patientEthnicity').value = data.ethnicity || '';
            document.getElementById('patientMainActivity').value = data.main_activity || '';
            document.getElementById('patientEducation').value = data.education || '';
            document.getElementById('patientEmployment').value = data.employment || '';
            document.getElementById('patientMaritalStatus').value = data.marital_status || '';
            document.getElementById('patientIsSmoker').value = data.is_smoker || '否';
            document.getElementById('patientIsDrinker').value = data.is_drinker || '否';
            document.getElementById('patientSurgeryHistory').value = data.surgery_history || '';
            document.getElementById('patientMedications').value = data.medications || '';
            document.getElementById('patientDiseaseHistory').value = data.disease_history || '';
            document.getElementById('patientSystolicBp').value = data.systolic_bp || '';
            document.getElementById('patientDiastolicBp').value = data.diastolic_bp || '';
            document.getElementById('patientBpMeasureTime').value = data.bp_measure_time || '';
            document.getElementById('patientFamilyHistory').value = data.family_history || '';
            document.getElementById('patientRegularExercise').value = data.regular_exercise || '否';

            // 更新模态框标题
            document.querySelector('.modal-header h2').innerHTML =
                `<i class="fas fa-user-edit"></i> 编辑患者健康信息: ${data.name}`;

            // 保存记录数据
            medicalRecords = data.medical_records || [];
            checkMetrics = data.check_metrics || [];

            // 计算BMI
            calculateBMI();
        })
        .catch(error => {
            console.error('Error loading patient data:', error);
            showNotification('加载患者数据失败', 'error');
        });
}

// 保存基本信息
const basicInfoForm = document.getElementById('basicInfoForm');
if (basicInfoForm) {
    basicInfoForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = {
            name: document.getElementById('patientName').value,
            age: document.getElementById('patientAge').value,
            gender: document.getElementById('patientGender').value,
            blood_type: document.getElementById('patientBloodType').value,
            height: document.getElementById('patientHeight').value,
            weight: document.getElementById('patientWeight').value,
            conditions: document.getElementById('patientConditions').value,
            allergies: document.getElementById('patientAllergies').value,
            occupation: document.getElementById('patientOccupation').value,
            ethnicity: document.getElementById('patientEthnicity').value,
            main_activity: document.getElementById('patientMainActivity').value,
            education: document.getElementById('patientEducation').value,
            employment: document.getElementById('patientEmployment').value,
            marital_status: document.getElementById('patientMaritalStatus').value,
            is_smoker: document.getElementById('patientIsSmoker').value,
            is_drinker: document.getElementById('patientIsDrinker').value,
            surgery_history: document.getElementById('patientSurgeryHistory').value,
            medications: document.getElementById('patientMedications').value,
            disease_history: document.getElementById('patientDiseaseHistory').value,
            systolic_bp: document.getElementById('patientSystolicBp').value,
            diastolic_bp: document.getElementById('patientDiastolicBp').value,
            bp_measure_time: document.getElementById('patientBpMeasureTime').value,
            family_history: document.getElementById('patientFamilyHistory').value,
            regular_exercise: document.getElementById('patientRegularExercise').value
        };

        fetch(`/admin/patient/${currentPatientId}/update_basic`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('患者基本信息已成功更新！', 'success');
                // 更新本地数据
                Object.keys(formData).forEach(key => {
                    if (key in medicalRecords[0]) {
                        medicalRecords[0][key] = formData[key];
                    }
                });
            } else {
                showNotification(`更新失败: ${data.error || '未知错误'}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error updating patient:', error);
            showNotification('更新患者信息时出错', 'error');
        });
    });
}

// 加载健康记录
function loadMedicalRecords() {
    const recordsList = document.getElementById('recordsList');
    recordsList.innerHTML = '<div class="loading">加载中...</div>';

    setTimeout(() => {
        recordsList.innerHTML = '';

        if (medicalRecords.length > 0) {
            medicalRecords.forEach(record => {
                addMedicalRecordToDOM(record);
            });
        } else {
            recordsList.innerHTML = '<div class="no-records">没有就诊记录</div>';
        }
    }, 500);
}


// 查看详情按钮事件
document.querySelectorAll('.btn-icon.view').forEach(button => {
    button.addEventListener('click', function() {
        const patientId = this.getAttribute('data-id');
        previewPatientDetails(patientId);
    });
});

// 预览患者详情
function previewPatientDetails(patientId) {
    fetch(`/admin/patient/${patientId}/preview`)
        .then(response => response.json())
        .then(data => {
            // 填充预览模态框
            document.getElementById('previewName').textContent = data.name || '未填写';
            document.getElementById('previewAge').textContent = data.age || '未填写';
            document.getElementById('previewGender').textContent = data.gender || '未填写';
            document.getElementById('previewPhone').textContent = data.phone || '未填写';
            document.getElementById('previewHeight').textContent = data.height || '未填写';
            document.getElementById('previewWeight').textContent = data.weight || '未填写';
            document.getElementById('previewBMI').textContent = data.bmi || '未计算';
            document.getElementById('previewBMICategory').textContent = data.bmi_category || '';
            document.getElementById('previewBloodType').textContent = data.blood_type || '未填写';
            document.getElementById('previewConditions').textContent = data.conditions || '无';
            document.getElementById('previewAllergies').textContent = data.allergies || '无';
            document.getElementById('previewDiseaseHistory').textContent = data.disease_history || '无';
            document.getElementById('previewFamilyHistory').textContent = data.family_history || '无';
            document.getElementById('previewSurgeryHistory').textContent = data.surgery_history || '无';
            document.getElementById('previewMedications').textContent = data.medications || '无';
            document.getElementById('previewIsSmoker').textContent = data.is_smoker || '否';
            document.getElementById('previewIsDrinker').textContent = data.is_drinker || '否';
            document.getElementById('previewRegularExercise').textContent = data.regular_exercise || '否';
            document.getElementById('previewOccupation').textContent = data.occupation || '未填写';

            // 显示预览模态框
            document.getElementById('previewModal').style.display = 'flex';
        })
        .catch(error => {
            console.error('Error loading patient preview:', error);
            showNotification('加载患者预览信息失败', 'error');
        });
}

// 关闭预览模态框
document.getElementById('closePreviewModal').addEventListener('click', function() {
    document.getElementById('previewModal').style.display = 'none';
});


// 添加健康记录到DOM
function addMedicalRecordToDOM(record) {
    const recordsList = document.getElementById('recordsList');
    const recordItem = document.createElement('div');
    recordItem.className = 'record-item';
    recordItem.dataset.id = record.id;
    recordItem.innerHTML = `
        <div class="record-header">
            <div class="record-date">
                <i class="far fa-calendar-alt"></i> ${record.date}
            </div>
            <div class="record-actions">
                <button class="btn-icon edit" title="编辑" data-id="${record.id}">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-icon delete" title="删除" data-id="${record.id}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
        <div class="record-details">
            <div class="record-department">
                <i class="fas fa-hospital"></i> ${record.department} - ${record.doctor}
            </div>
            <div class="record-description">
                ${record.description}
            </div>
        </div>
    `;

    recordsList.appendChild(recordItem);

    // 添加编辑事件
    recordItem.querySelector('.btn-icon.edit').addEventListener('click', function() {
        openMedicalRecordEditor(record);
    });

    // 添加删除事件
    recordItem.querySelector('.btn-icon.delete').addEventListener('click', function() {
        deleteMedicalRecord(record.id);
    });
}

// 打开健康记录编辑器
function openMedicalRecordEditor(record) {
    const recordsList = document.getElementById('recordsList');
    const recordItem = document.querySelector(`.record-item[data-id="${record.id}"]`);

    // 创建编辑表单
    const formContainer = document.createElement('div');
    formContainer.className = 'record-form-container';

    formContainer.innerHTML = `
        <div class="record-form">
            <h4>编辑就诊记录</h4>
            <div class="form-group">
                <label>日期</label>
                <input type="date" class="form-control" id="editRecordDate" value="${record.date}">
            </div>
            <div class="form-group">
                <label>科室</label>
                <input type="text" class="form-control" id="editRecordDepartment" value="${record.department}">
            </div>
            <div class="form-group">
                <label>医生</label>
                <input type="text" class="form-control" id="editRecordDoctor" value="${record.doctor}">
            </div>
            <div class="form-group">
                <label>就诊描述</label>
                <textarea class="form-control" id="editRecordDescription" rows="3">${record.description}</textarea>
            </div>
            <div class="form-buttons">
                <button type="button" class="btn btn-primary" id="updateRecordBtn">更新记录</button>
                <button type="button" class="btn btn-outline" id="cancelEditRecordBtn">取消</button>
            </div>
        </div>
    `;

    // 插入到当前记录前面
    recordItem.parentNode.insertBefore(formContainer, recordItem);
    recordItem.style.display = 'none';

    // 更新记录
    document.getElementById('updateRecordBtn').addEventListener('click', function() {
        const recordData = {
            id: record.id,
            date: document.getElementById('editRecordDate').value,
            department: document.getElementById('editRecordDepartment').value,
            doctor: document.getElementById('editRecordDoctor').value,
            description: document.getElementById('editRecordDescription').value
        };

        // 验证必填字段
        if (!recordData.date || !recordData.department || !recordData.doctor) {
            showNotification('请填写日期、科室和医生信息', 'error');
            return;
        }

        saveMedicalRecord(recordData, false);
        formContainer.remove();
        recordItem.style.display = '';
    });

    // 取消编辑
    document.getElementById('cancelEditRecordBtn').addEventListener('click', function() {
        formContainer.remove();
        recordItem.style.display = '';
    });
}

// 保存健康记录
function saveMedicalRecord(recordData, isNew) {
    const url = isNew
        ? `/admin/patient/${currentPatientId}/add_medical_record`
        : `/admin/medical_record/${recordData.id}/update`;

    fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(recordData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('就诊记录已成功保存!', 'success');

            // 更新本地数据
            if (isNew) {
                recordData.id = data.record_id;
                medicalRecords.unshift(recordData);
                addMedicalRecordToDOM(recordData);
            } else {
                // 更新现有记录
                const index = medicalRecords.findIndex(r => r.id === recordData.id);
                if (index !== -1) {
                    medicalRecords[index] = {...medicalRecords[index], ...recordData};
                    const recordItem = document.querySelector(`.record-item[data-id="${recordData.id}"]`);
                    if (recordItem) {
                        recordItem.querySelector('.record-date').innerHTML =
                            `<i class="far fa-calendar-alt"></i> ${recordData.date}`;
                        recordItem.querySelector('.record-department').textContent =
                            `${recordData.department} - ${recordData.doctor}`;
                        recordItem.querySelector('.record-description').textContent =
                            recordData.description;
                    }
                }
            }
        } else {
            showNotification(`保存失败: ${data.error || '未知错误'}`, 'error');
        }
    })
    .catch(error => {
        showNotification(`保存失败: ${error}`, 'error');
    });
}

// 删除健康记录
function deleteMedicalRecord(recordId) {
    if (!confirm('确定要删除这条就诊记录吗？此操作不可恢复。')) return;

    fetch(`/admin/medical_record/${recordId}/delete`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('就诊记录已成功删除!', 'success');

            // 从本地数据中移除
            const index = medicalRecords.findIndex(r => r.id === recordId);
            if (index !== -1) {
                medicalRecords.splice(index, 1);
            }

            // 从DOM中移除
            const recordItem = document.querySelector(`.record-item[data-id="${recordId}"]`);
            if (recordItem) {
                recordItem.remove();

                // 如果没有记录了，显示提示
                if (document.querySelectorAll('.record-item').length === 0) {
                    document.getElementById('recordsList').innerHTML =
                        '<div class="no-records">没有就诊记录</div>';
                }
            }
        } else {
            showNotification(`删除失败: ${data.error || '未知错误'}`, 'error');
        }
    })
    .catch(error => {
        showNotification(`删除失败: ${error}`, 'error');
    });
}

// 加载健康指标
function loadCheckMetrics() {
    const metricsTable = document.getElementById('metricsTable').querySelector('tbody');
    metricsTable.innerHTML = '<tr><td colspan="7" class="loading">加载中...</td></tr>';

    setTimeout(() => {
        metricsTable.innerHTML = '';

        if (checkMetrics.length > 0) {
            checkMetrics.forEach(metric => {
                addCheckMetricToDOM(metric);
            });
        } else {
            metricsTable.innerHTML = '<tr><td colspan="7" class="no-metrics">没有检查指标记录</td></tr>';
        }
    }, 500);
}

// 添加健康指标到DOM
function addCheckMetricToDOM(metric) {
    const metricsTable = document.getElementById('metricsTable').querySelector('tbody');
    const row = document.createElement('tr');
    row.dataset.id = metric.id;
    row.innerHTML = `
        <td>
            <input type="text" class="form-control small" value="${metric.item}" readonly>
        </td>
        <td>
            <input type="text" class="form-control small" value="${metric.result}">
        </td>
        <td>
            <input type="text" class="form-control small" value="${metric.reference_range}" readonly>
        </td>
        <td>
            <input type="text" class="form-control small" value="${metric.unit}" readonly>
        </td>
        <td>
            <input type="date" class="form-control small" value="${metric.date}">
        </td>
        <td>
            <select class="form-control small">
                <option value="normal" ${metric.status === 'normal' ? 'selected' : ''}>正常</option>
                <option value="warning" ${metric.status === 'warning' ? 'selected' : ''}>偏高</option>
                <option value="danger" ${metric.status === 'danger' ? 'selected' : ''}>严重异常</option>
            </select>
        </td>
        <td class="actions">
            <button class="btn-icon save" title="保存" data-id="${metric.id}">
                <i class="fas fa-save"></i>
            </button>
            <button class="btn-icon delete" title="删除" data-id="${metric.id}">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;

    metricsTable.appendChild(row);

    // 添加保存事件
    row.querySelector('.btn-icon.save').addEventListener('click', function() {
        const inputs = row.querySelectorAll('input, select');
        const metricData = {
            id: metric.id,
            item: inputs[0].value,
            result: inputs[1].value,
            reference_range: inputs[2].value,
            unit: inputs[3].value,
            date: inputs[4].value,
            status: inputs[5].value
        };

        saveCheckMetric(metricData, false);
    });

    // 添加删除事件
    row.querySelector('.btn-icon.delete').addEventListener('click', function() {
        deleteCheckMetric(metric.id);
    });
}

// 保存健康指标
function saveCheckMetric(metricData, isNew) {
    const url = isNew
        ? `/admin/patient/${currentPatientId}/add_check_metric`
        : `/admin/check_metric/${metricData.id}/update`;

    fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(metricData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('健康指标已成功保存!', 'success');

            // 更新本地数据
            if (isNew) {
                metricData.id = data.metric_id;
                checkMetrics.push(metricData);
                addCheckMetricToDOM(metricData);
            } else {
                // 更新现有指标
                const index = checkMetrics.findIndex(m => m.id === metricData.id);
                if (index !== -1) {
                    checkMetrics[index] = {...checkMetrics[index], ...metricData};
                }
            }
        } else {
            showNotification(`保存失败: ${data.error || '未知错误'}`, 'error');
        }
    })
    .catch(error => {
        showNotification(`保存失败: ${error}`, 'error');
    });
}

// 删除健康指标
function deleteCheckMetric(metricId) {
    if (!confirm('确定要删除这条健康指标吗？此操作不可恢复。')) return;

    fetch(`/admin/check_metric/${metricId}/delete`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('健康指标已成功删除!', 'success');

            // 从本地数据中移除
            const index = checkMetrics.findIndex(m => m.id === metricId);
            if (index !== -1) {
                checkMetrics.splice(index, 1);
            }

            // 从DOM中移除
            const row = document.querySelector(`tr[data-id="${metricId}"]`);
            if (row) {
                row.remove();

                // 如果没有指标了，显示提示
                if (document.querySelectorAll('#metricsTable tbody tr').length === 0) {
                    document.querySelector('#metricsTable tbody').innerHTML =
                        '<tr><td colspan="7" class="no-metrics">没有检查指标记录</td></tr>';
                }
            }
        } else {
            showNotification(`删除失败: ${data.error || '未知错误'}`, 'error');
        }
    })
    .catch(error => {
        showNotification(`删除失败: ${error}`, 'error');
    });
}

// 添加就诊记录按钮
document.getElementById('addRecordBtn')?.addEventListener('click', function() {
    const recordsList = document.getElementById('recordsList');

    // 创建表单容器
    const formContainer = document.createElement('div');
    formContainer.className = 'record-form-container';

    // 创建表单
    formContainer.innerHTML = `
        <div class="record-form">
            <h4>添加新就诊记录</h4>
            <div class="form-group">
                <label>日期</label>
                <input type="date" class="form-control" id="newRecordDate" value="${new Date().toISOString().split('T')[0]}">
            </div>
            <div class="form-group">
                <label>科室</label>
                <input type="text" class="form-control" id="newRecordDepartment" placeholder="例如：心血管内科">
            </div>
            <div class="form-group">
                <label>医生</label>
                <input type="text" class="form-control" id="newRecordDoctor" placeholder="例如：王主任">
            </div>
            <div class="form-group">
                <label>就诊描述</label>
                <textarea class="form-control" id="newRecordDescription" rows="3" placeholder="详细描述就诊情况"></textarea>
            </div>
            <div class="form-buttons">
                <button type="button" class="btn btn-primary" id="saveNewRecordBtn">保存记录</button>
                <button type="button" class="btn btn-outline" id="cancelNewRecordBtn">取消</button>
            </div>
        </div>
    `;

    recordsList.prepend(formContainer);

    // 保存记录
    document.getElementById('saveNewRecordBtn').addEventListener('click', function() {
        const recordData = {
            date: document.getElementById('newRecordDate').value,
            department: document.getElementById('newRecordDepartment').value,
            doctor: document.getElementById('newRecordDoctor').value,
            description: document.getElementById('newRecordDescription').value
        };

        // 验证必填字段
        if (!recordData.date || !recordData.department || !recordData.doctor) {
            showNotification('请填写日期、科室和医生信息', 'error');
            return;
        }

        saveMedicalRecord(recordData, true);
        formContainer.remove();
    });

    // 取消添加
    document.getElementById('cancelNewRecordBtn').addEventListener('click', function() {
        formContainer.remove();
    });
});

// 添加健康指标按钮
document.getElementById('addMetricBtn')?.addEventListener('click', function() {
    const metricsTable = document.querySelector('#metricsTable tbody');

    // 创建新行
    const newRow = document.createElement('tr');
    newRow.className = 'new-metric-row';
    newRow.innerHTML = `
        <td>
            <input type="text" class="form-control small" placeholder="检查项目" required>
        </td>
        <td>
            <input type="text" class="form-control small" placeholder="结果" required>
        </td>
        <td>
            <input type="text" class="form-control small" placeholder="参考范围" required>
        </td>
        <td>
            <input type="text" class="form-control small" placeholder="单位" required>
        </td>
        <td>
            <input type="date" class="form-control small" value="${new Date().toISOString().split('T')[0]}" required>
        </td>
        <td>
            <select class="form-control small" required>
                <option value="normal">正常</option>
                <option value="warning">偏高</option>
                <option value="danger">严重异常</option>
            </select>
        </td>
        <td class="actions">
            <button class="btn-icon save" title="保存">
                <i class="fas fa-save"></i>
            </button>
            <button class="btn-icon cancel" title="取消">
                <i class="fas fa-times"></i>
            </button>
        </td>
    `;

    metricsTable.appendChild(newRow);

    // 保存新指标
    newRow.querySelector('.btn-icon.save').addEventListener('click', function() {
        const inputs = newRow.querySelectorAll('input, select');
        const metricData = {
            item: inputs[0].value,
            result: inputs[1].value,
            reference_range: inputs[2].value,
            unit: inputs[3].value,
            date: inputs[4].value,
            status: inputs[5].value
        };

        // 验证必填字段
        let isValid = true;
        inputs.forEach(input => {
            if (!input.value) {
                input.style.borderColor = 'red';
                isValid = false;
            } else {
                input.style.borderColor = '';
            }
        });

        if (!isValid) {
            showNotification('请填写所有必填字段', 'error');
            return;
        }

        saveCheckMetric(metricData, true);
        newRow.remove();
    });

    // 取消添加
    newRow.querySelector('.btn-icon.cancel').addEventListener('click', function() {
        newRow.remove();
    });
});

// 显示通知
function showNotification(message, type = 'success') {
    // 移除现有通知
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    // 创建新通知
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    // 3秒后自动移除
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// 计算BMI
function calculateBMI() {
    const heightInput = document.getElementById('patientHeight');
    const weightInput = document.getElementById('patientWeight');
    const bmiInput = document.getElementById('patientBMI');

    if (!heightInput || !weightInput || !bmiInput) return;

    try {
        const height = parseFloat(heightInput.value.replace('cm', '')) || 0;
        const weight = parseFloat(weightInput.value.replace('kg', '')) || 0;

        if (height > 0 && weight > 0) {
            const heightInM = height / 100;
            const bmi = (weight / (heightInM * heightInM)).toFixed(1);
            bmiInput.value = bmi;
        } else {
            bmiInput.value = '';
        }
    } catch {
        bmiInput.value = '';
    }
}

// 添加BMI计算监听
const heightInput = document.getElementById('patientHeight');
const weightInput = document.getElementById('patientWeight');
if (heightInput && weightInput) {
    heightInput.addEventListener('input', calculateBMI);
    weightInput.addEventListener('input', calculateBMI);
}