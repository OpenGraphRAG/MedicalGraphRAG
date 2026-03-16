document.addEventListener('DOMContentLoaded', function() {
    // 初始化系统设置页面
    initSystemSettings();
});

function initSystemSettings() {
    console.log('初始化系统设置页面');

    // 加载当前配置
    loadCurrentConfig();

    // 绑定事件
    bindSettingsEvents();
}

function loadCurrentConfig() {
    // 显示加载状态
    Swal.fire({
        title: '加载中...',
        text: '正在获取系统配置',
        icon: 'info',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        showConfirmButton: false,
        allowOutsideClick: false
    });

    // 获取当前配置
    fetch('/admin/system_settings/config')
        .then(response => response.json())
        .then(config => {
            Swal.close();
            // 填充表单
            populateForm(config);
        })
        .catch(err => {
            console.error(err);
            Swal.fire({
                title: '错误',
                text: '获取系统配置失败',
                icon: 'error',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#e2e2e2',
                confirmButtonColor: '#48dbfb'
            });
        });
}

function populateForm(config) {
    // 填充所有表单字段
    for (const key in config) {
        const element = document.getElementById(key);
        if (element) {
            // 处理数组类型配置
            if (Array.isArray(config[key])) {
                element.value = config[key].join(',');
            } else {
                element.value = config[key] || '';
            }
        }
    }
}
function bindSettingsEvents() {
    // 表单提交事件
    document.getElementById('systemSettingsForm').addEventListener('submit', function(e) {
        e.preventDefault();
        saveSettings();
    });

    // 重置按钮事件
    document.getElementById('resetSettings').addEventListener('click', function() {
        Swal.fire({
            title: '确认重置',
            text: '您确定要重置所有设置为默认值吗？',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: '重置',
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
                resetToDefaults();
            }
        });
    });
}

function saveSettings() {
    // 收集表单数据
    const formData = new FormData(document.getElementById('systemSettingsForm'));
    const data = {};

    formData.forEach((value, key) => {
        // 处理特殊类型配置
        if (key === 'ALLOWED_EXTENSIONS') {
            // 保持为字符串格式，后端会处理为数组
            data[key] = value;
        } else if (['CHUNK_SIZE', 'CHUNK_OVERLAP', 'VECTOR_TOP_K', 'GRAPH_TOP_K'].includes(key)) {
            // 数字类型转换
            data[key] = value ? parseInt(value) : 0;
        } else {
            data[key] = value;
        }
    });

    // 显示加载状态
    Swal.fire({
        title: '保存中...',
        text: '正在保存系统配置',
        icon: 'info',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        showConfirmButton: false,
        allowOutsideClick: false
    });

    // 发送保存请求
    fetch('/admin/system_settings/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            Swal.fire({
                title: '配置已保存',
                text: result.message || '系统配置已保存并即时生效，无需重启服务',
                icon: 'success',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#e2e2e2',
                confirmButtonColor: '#48dbfb'
            });
        } else {
            throw new Error(result.error || '保存失败');
        }
    })
    .catch(err => {
        console.error(err);
        Swal.fire({
            title: '错误',
            text: '保存系统配置失败: ' + err.message,
            icon: 'error',
            background: 'rgba(26, 26, 46, 0.9)',
            color: '#e2e2e2',
            confirmButtonColor: '#48dbfb'
        });
    });
}
function resetToDefaults() {
    // 显示加载状态
    Swal.fire({
        title: '重置中...',
        text: '正在重置为默认配置',
        icon: 'info',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        showConfirmButton: false,
        allowOutsideClick: false
    });

    // 获取默认配置
    fetch('/admin/system_settings/defaults')
        .then(response => response.json())
        .then(defaultConfig => {
            Swal.close();
            // 填充表单
            populateForm(defaultConfig);

            Swal.fire({
                title: '成功',
                text: '已重置为默认配置',
                icon: 'success',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#e2e2e2',
                confirmButtonColor: '#48dbfb'
            });
        })
        .catch(err => {
            console.error(err);
            Swal.fire({
                title: '错误',
                text: '获取默认配置失败',
                icon: 'error',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#e2e2e2',
                confirmButtonColor: '#48dbfb'
            });
        });
}