document.addEventListener('DOMContentLoaded', function () {
    console.log('Prompt模板管理脚本初始化');
    initPromptTemplates();
});

let templates = [];
let currentTemplateId = null;

function initPromptTemplates() {
    console.log('初始化Prompt模板管理功能');

    // 绑定事件
    bindEvents();

    // 加载数据
    loadTemplates();
    loadActiveTemplate();
}

function bindEvents() {
    console.log('绑定事件...');

    // 刷新按钮
    document.getElementById('refreshTemplates')?.addEventListener('click', loadTemplates);

    // 创建模板按钮
    document.getElementById('createTemplateBtn')?.addEventListener('click', openCreateModal);
    document.getElementById('createFirstTemplateBtn')?.addEventListener('click', openCreateModal);

    // 模态框按钮
    document.getElementById('cancelTemplateBtn')?.addEventListener('click', closeModals);
    document.getElementById('saveTemplateBtn')?.addEventListener('click', saveTemplate);

    // 删除确认按钮
    document.getElementById('cancelDeleteBtn')?.addEventListener('click', closeModals);
    document.getElementById('confirmDeleteBtn')?.addEventListener('click', confirmDeleteTemplate);

    // 关闭按钮
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', closeModals);
    });

    // 搜索功能
    const searchInput = document.getElementById('searchTemplates');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            filterTemplates(searchTerm);
        });
    }

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

function loadTemplates() {
    console.log('加载模板列表...');

    showLoading('正在加载模板...');

    fetch('/api/prompt_templates')
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应异常: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            hideLoading();
            templates = data;
            renderTemplates();
            updateTemplatesCount();
        })
        .catch(error => {
            hideLoading();
            console.error('加载模板失败:', error);
            showError('加载模板失败: ' + error.message);
        });
}

function loadActiveTemplate() {
    console.log('加载激活模板...');

    fetch('/api/prompt_templates/active')
        .then(response => {
            if (response.status === 404) {
                // 没有激活模板是正常的
                updateActiveTemplateBadge(null);
                return;
            }
            if (!response.ok) {
                throw new Error('网络响应异常: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            updateActiveTemplateBadge(data);
        })
        .catch(error => {
            console.error('加载激活模板失败:', error);
            updateActiveTemplateBadge(null);
        });
}

function updateActiveTemplateBadge(activeTemplate) {
    const badge = document.getElementById('activeTemplateBadge');
    if (!badge) return;

    if (activeTemplate) {
        badge.innerHTML = `<i class="fas fa-check-circle"></i> 当前激活: ${activeTemplate.name}`;
        badge.style.background = 'linear-gradient(135deg, #2ecc71, #27ae60)';
    } else {
        badge.innerHTML = '<i class="fas fa-exclamation-triangle"></i> 暂无激活模板';
        badge.style.background = 'linear-gradient(135deg, #e74c3c, #c0392b)';
    }
}

function renderTemplates() {
    console.log('渲染模板列表:', templates.length);

    const grid = document.getElementById('templatesGrid');
    const emptyState = document.getElementById('emptyState');

    if (!grid) return;

    grid.innerHTML = '';

    if (templates.length === 0) {
        grid.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }

    grid.style.display = 'grid';
    if (emptyState) emptyState.style.display = 'none';

    templates.forEach(template => {
        const templateCard = createTemplateCard(template);
        grid.appendChild(templateCard);
    });
}

function createTemplateCard(template) {
    const card = document.createElement('div');
    card.className = `template-card ${template.is_active ? 'active' : ''}`;

    const contentPreview = template.content.length > 200
        ? template.content.substring(0, 200) + '...'
        : template.content;

    card.innerHTML = `
        <div class="template-header">
            <div>
                <div class="template-title">${escapeHtml(template.name)}</div>
                <span class="template-category">${getCategoryName(template.category)}</span>
            </div>
            <span class="status-badge ${template.is_active ? 'status-active' : 'status-inactive'}">
                ${template.is_active ? '已激活' : '未激活'}
            </span>
        </div>

        <div class="template-description">${escapeHtml(template.description || '暂无描述')}</div>

        <div class="template-content-preview">
            <div class="template-content">${escapeHtml(contentPreview)}</div>
        </div>

        <div class="template-footer">
            <div class="template-meta">
                创建: ${new Date(template.created_at).toLocaleDateString()}
            </div>
            <div class="template-actions">
                ${!template.is_active ? `
                    <button class="btn-icon btn-activate" data-id="${template.id}" title="设为激活">
                        <i class="fas fa-check-circle"></i>
                    </button>
                ` : ''}
                <button class="btn-icon btn-edit" data-id="${template.id}" title="编辑">
                    <i class="fas fa-edit"></i>
                </button>
                ${!template.is_active ? `
                    <button class="btn-icon btn-delete" data-id="${template.id}" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                ` : ''}
            </div>
        </div>
    `;

    // 绑定卡片内按钮事件
    card.querySelector('.btn-activate')?.addEventListener('click', (e) => {
        e.stopPropagation();
        setActiveTemplate(template.id);
    });

    card.querySelector('.btn-edit')?.addEventListener('click', (e) => {
        e.stopPropagation();
        openEditModal(template.id);
    });

    card.querySelector('.btn-delete')?.addEventListener('click', (e) => {
        e.stopPropagation();
        confirmDelete(template);
    });

    // 点击卡片查看详情
    card.addEventListener('click', () => {
        viewTemplateDetails(template);
    });

    return card;
}

function getCategoryName(category) {
    const categories = {
        'health_knowledge': '健康知识',
        'medical': '医学诊断',
        'general': '通用问答',
        'other': '其他'
    };
    return categories[category] || category;
}

function openCreateModal() {
    console.log('打开创建模板模态框');

    document.getElementById('templateForm').reset();
    document.getElementById('templateId').value = '';
    document.getElementById('templateModalTitle').textContent = '新建Prompt模板';

    const modal = document.getElementById('templateModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function openEditModal(templateId) {
    console.log('打开编辑模板模态框:', templateId);

    showLoading('正在加载模板数据...');

    fetch(`/api/prompt_templates/${templateId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应异常: ' + response.status);
            }
            return response.json();
        })
        .then(template => {
            hideLoading();

            document.getElementById('templateId').value = template.id;
            document.getElementById('templateName').value = template.name;
            document.getElementById('templateDescription').value = template.description || '';
            document.getElementById('templateCategory').value = template.category;
            document.getElementById('templateContent').value = template.content;
            document.getElementById('templateModalTitle').textContent = '编辑Prompt模板';

            const modal = document.getElementById('templateModal');
            if (modal) {
                modal.style.display = 'block';
            }
        })
        .catch(error => {
            hideLoading();
            console.error('加载模板数据失败:', error);
            showError('加载模板数据失败: ' + error.message);
        });
}

function saveTemplate() {
    console.log('保存模板');

    const templateId = document.getElementById('templateId').value;
    const isEdit = !!templateId;

    const templateData = {
        name: document.getElementById('templateName').value.trim(),
        description: document.getElementById('templateDescription').value.trim(),
        category: document.getElementById('templateCategory').value,
        content: document.getElementById('templateContent').value.trim()
    };

    if (!templateData.name) {
        showError('请输入模板名称');
        return;
    }

    if (!templateData.content) {
        showError('请输入模板内容');
        return;
    }

    showLoading(isEdit ? '更新模板中...' : '创建模板中...');

    const url = isEdit ? `/api/prompt_templates/${templateId}` : '/api/prompt_templates';
    const method = isEdit ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(templateData)
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
            showSuccess(isEdit ? '模板更新成功' : '模板创建成功');
            closeModals();
            loadTemplates();
        } else {
            throw new Error(result.error || '操作失败');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('保存模板失败:', error);
        showError('保存模板失败: ' + error.message);
    });
}

function setActiveTemplate(templateId) {
    console.log('设置激活模板:', templateId);

    showLoading('设置激活模板中...');

    fetch(`/api/prompt_templates/${templateId}/set_active`, {
        method: 'POST'
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
            showSuccess('模板已设置为激活状态');
            loadTemplates();
            loadActiveTemplate();
        } else {
            throw new Error(result.error || '设置失败');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('设置激活模板失败:', error);
        showError('设置激活模板失败: ' + error.message);
    });
}

function confirmDelete(template) {
    console.log('确认删除模板:', template.id);

    document.getElementById('deleteTemplateName').textContent = template.name;
    currentTemplateId = template.id;

    const modal = document.getElementById('confirmDeleteModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function confirmDeleteTemplate() {
    if (!currentTemplateId) return;

    console.log('删除模板:', currentTemplateId);

    showLoading('删除模板中...');

    fetch(`/api/prompt_templates/${currentTemplateId}`, {
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
            showSuccess('模板删除成功');
            closeModals();
            loadTemplates();
        } else {
            throw new Error(result.error || '删除失败');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('删除模板失败:', error);
        showError('删除模板失败: ' + error.message);
    });
}

function viewTemplateDetails(template) {
    console.log('查看模板详情:', template.id);

    const content = template.content;

    Swal.fire({
        title: template.name,
        html: `
            <div style="text-align: left;">
                <p><strong>描述:</strong> ${template.description || '暂无描述'}</p>
                <p><strong>分类:</strong> ${getCategoryName(template.category)}</p>
                <p><strong>状态:</strong> ${template.is_active ? '已激活' : '未激活'}</p>
                <p><strong>创建时间:</strong> ${new Date(template.created_at).toLocaleString()}</p>
                <hr>
                <div style="background: #1a1a2e; padding: 15px; border-radius: 6px; margin-top: 15px;">
                    <pre style="color: #e2e2e2; white-space: pre-wrap; font-family: monospace; font-size: 12px; line-height: 1.4;">${escapeHtml(content)}</pre>
                </div>
            </div>
        `,
        width: '800px',
        background: 'rgba(26, 26, 46, 0.95)',
        color: '#e2e2e2',
        showCloseButton: true,
        showConfirmButton: false
    });
}

function filterTemplates(searchTerm) {
    if (!searchTerm) {
        renderTemplates();
        return;
    }

    const filteredTemplates = templates.filter(template =>
        template.name.toLowerCase().includes(searchTerm) ||
        (template.description && template.description.toLowerCase().includes(searchTerm)) ||
        template.content.toLowerCase().includes(searchTerm)
    );

    const grid = document.getElementById('templatesGrid');
    if (!grid) return;

    grid.innerHTML = '';

    filteredTemplates.forEach(template => {
        const templateCard = createTemplateCard(template);
        grid.appendChild(templateCard);
    });

    updateTemplatesCount(filteredTemplates.length);
}

function updateTemplatesCount(count) {
    const countElement = document.getElementById('templatesCount');
    if (countElement) {
        countElement.textContent = count !== undefined ? count : templates.length;
    }
}

function closeModals() {
    console.log('关闭所有模态框');

    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });

    currentTemplateId = null;
}

// 工具函数
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

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