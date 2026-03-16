document.addEventListener('DOMContentLoaded', function () {
    console.log('实体关系属性配置脚本初始化');
    initEntityConfig();
    // 使用事件委托处理编辑按钮点击
    document.addEventListener('click', function(event) {
        const editBtn = event.target.closest('.edit-btn');
        if (editBtn && editBtn.dataset.elementType && editBtn.dataset.elementId) {
            event.preventDefault();
            event.stopPropagation();

            const elementType = editBtn.dataset.elementType;
            const elementId = editBtn.dataset.elementId;

            console.log(`点击编辑按钮: ${elementType} - ${elementId}`);
            editProperties(elementType, elementId, editBtn);
        }
    });
});

let currentPage = 1;
let perPage = 5;
let searchTerm = '';
let propertiesToEdit = [];

function initEntityConfig() {
    console.log('初始化实体关系属性配置功能');

    // 绑定事件
    bindEvents();

    // 首次加载：只加载统计信息
    loadStats();

    // 首次加载第一页数据
    currentPage = 1;
    loadTriples();
}

function bindEvents() {
    // 刷新按钮
    document.getElementById('refreshTriples')?.addEventListener('click', () => {
        currentPage = 1;
        loadTriples();
    });

    // 搜索框 - 带防抖
    const searchInput = document.getElementById('searchTriples');
    let searchTimer = null;
    searchInput?.addEventListener('input', function() {
        clearTimeout(searchTimer);
        searchTerm = this.value;
        searchTimer = setTimeout(() => {
            currentPage = 1;
            loadTriples();
        }, 500);
    });

    // 每页数量选择
    const perPageSelect = document.getElementById('perPageSelect');
    perPageSelect?.addEventListener('change', function() {
        perPage = parseInt(this.value);
        currentPage = 1;
        loadTriples();
    });

    // 模态框事件
    document.getElementById('cancelEditBtn')?.addEventListener('click', closeModals);
    document.getElementById('savePropertiesBtn')?.addEventListener('click', saveProperties);
    document.getElementById('addPropertyBtn')?.addEventListener('click', addPropertyField);

    // 关闭按钮
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', closeModals);
    });

    // ESC键关闭模态框
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModals();
        }
    });
}

// 使用AbortController取消之前未完成的请求
let currentTriplesController = null;

function loadTriples() {
    console.log(`加载第${currentPage}页三元组，每页${perPage}条`);

    // 取消之前的请求
    if (currentTriplesController) {
        currentTriplesController.abort();
    }
    currentTriplesController = new AbortController();

    showLoading('正在加载三元组数据...');

    const url = `/api/entity_config/triples?page=${currentPage}&per_page=${perPage}&search=${encodeURIComponent(searchTerm)}`;

    fetch(url, { signal: currentTriplesController.signal })
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应异常: ' + response.status);
            }
            return response.json();
        })
        .then(result => {
            hideLoading();
            currentTriplesController = null;

            let triples = [];
            let pagination = {};

            if (result.success) {
                if (result.data && result.data.triples) {
                    triples = result.data.triples;
                    pagination = result.data.pagination || {};
                } else if (result.triples) {
                    triples = result.triples;
                    pagination = result.pagination || {};
                }

                renderTriples(triples);
                renderPagination(pagination);

                document.getElementById('currentCount').textContent = triples.length;
                if (pagination.total_items) {
                    document.getElementById('totalCount').textContent = pagination.total_items;
                }
            } else {
                throw new Error(result.error || '加载失败');
            }
        })
        .catch(error => {
            if (error.name === 'AbortError') {
                console.log('请求已取消');
                return;
            }
            hideLoading();
            currentTriplesController = null;
            console.error('加载三元组失败:', error);
            showError('加载数据失败: ' + error.message);
        });
}

function loadStats() {
    // 使用专用统计接口获取真实的实体和关系总数
    fetch('/api/entity_config/stats')
        .then(response => response.json())
        .then(result => {
            if (result.success && result.data) {
                document.getElementById('totalEntities').textContent = result.data.entities || 0;
                document.getElementById('totalRelations').textContent = result.data.relationships || 0;
            }
        })
        .catch(err => {
            console.error('获取统计信息失败:', err);
        });
}

function renderTriples(triples) {
    const container = document.getElementById('triplesContainer');
    container.innerHTML = '';

    if (triples.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>暂无三元组数据</p>
            </div>`;
        return;
    }

    // 添加三元组计数
    document.getElementById('currentCount').textContent = triples.length;

    triples.forEach(triple => {
        const card = createTripleCard(triple);
        container.appendChild(card);
    });
}

function createTripleCard(triple) {
    const card = document.createElement('div');
    card.className = 'triple-card';

    // 计算属性数量
    const headPropsCount = Object.keys(triple.head.properties || {}).length;
    const tailPropsCount = Object.keys(triple.tail.properties || {}).length;
    const relPropsCount = Object.keys(triple.relation.properties || {}).length;

    // 创建唯一ID，避免特殊字符问题
    const headId = escapeHtml(triple.head.tid || '');
    const tailId = escapeHtml(triple.tail.tid || '');
    const relId = escapeHtml(triple.relation.rid || '');

    card.innerHTML = `
        <div class="triple-header">
            <div class="triple-title">
                <span class="entity-badge head">${escapeHtml(triple.head.type)}</span>
                <span class="relation-badge">${escapeHtml(triple.relation.type)}</span>
                <span class="entity-badge tail">${escapeHtml(triple.tail.type)}</span>
            </div>
            <div class="triple-id">
                ID: ${escapeHtml(triple.head.tid)} → ${escapeHtml(triple.relation.rid)} → ${escapeHtml(triple.tail.tid)}
            </div>
        </div>
        
        <div class="triple-body">
            <div class="entity-section">
                <div class="section-header">
                    <div class="section-title">
                        <i class="fas fa-circle"></i> 头节点: ${escapeHtml(triple.head.name)}
                    </div>
                    <button class="edit-btn" data-element-type="head" data-element-id="${headId}">
                        <i class="fas fa-edit"></i> 编辑
                    </button>
                </div>
                <div class="properties-list" id="head-${headId}">
                    ${renderProperties(triple.head.properties, headPropsCount)}
                </div>
            </div>
            
            <div class="relation-section">
                <div class="section-header">
                    <div class="section-title">
                        <i class="fas fa-arrows-alt-h"></i> 关系属性
                    </div>
                    <button class="edit-btn" data-element-type="relation" data-element-id="${relId}">
                        <i class="fas fa-edit"></i> 编辑
                    </button>
                </div>
                <div class="properties-list" id="relation-${relId}">
                    ${renderProperties(triple.relation.properties, relPropsCount)}
                </div>
            </div>
            
            <div class="entity-section">
                <div class="section-header">
                    <div class="section-title">
                        <i class="fas fa-circle"></i> 尾节点: ${escapeHtml(triple.tail.name)}
                    </div>
                    <button class="edit-btn" data-element-type="tail" data-element-id="${tailId}">
                        <i class="fas fa-edit"></i> 编辑
                    </button>
                </div>
                <div class="properties-list" id="tail-${tailId}">
                    ${renderProperties(triple.tail.properties, tailPropsCount)}
                </div>
            </div>
        </div>
    `;

    return card;
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


function renderProperties(properties, count) {
    if (count === 0 || !properties || Object.keys(properties).length === 0) {
        return '<div class="no-properties">暂无属性</div>';
    }

    let propsHtml = '';
    Object.entries(properties).forEach(([key, value]) => {
        // 如果value是对象或数组，转换为JSON字符串
        if (typeof value === 'object' && value !== null) {
            value = JSON.stringify(value, null, 2);
        }

        // 截断过长的值
        const displayValue = String(value).length > 50
            ? String(value).substring(0, 50) + '...'
            : String(value);

        propsHtml += `
            <div class="property-item">
                <span class="property-key">${escapeHtml(key)}:</span>
                <span class="property-value" title="${escapeHtml(value)}">${escapeHtml(displayValue)}</span>
            </div>
        `;
    });

    return propsHtml;
}

function editProperties(elementType, elementId, buttonElement) {
    console.log(`编辑${elementType}属性:`, elementId, typeof elementId);

    // 确保elementId是字符串（处理可能的数据类型问题）
    if (typeof elementId !== 'string') {
        elementId = String(elementId);
    }

    // 清理elementId（移除可能的引号）
    if (elementId.startsWith('"') && elementId.endsWith('"')) {
        elementId = elementId.slice(1, -1);
    }
    if (elementId.startsWith("'") && elementId.endsWith("'")) {
        elementId = elementId.slice(1, -1);
    }

    // 获取当前属性
    const propsContainer = document.getElementById(`${elementType}-${elementId}`);
    if (!propsContainer) {
        console.error(`找不到属性容器: ${elementType}-${elementId}`);
        return;
    }

    const propertyItems = propsContainer.querySelectorAll('.property-item');

    propertiesToEdit = [];

    if (propertyItems.length === 0) {
        // 如果没有属性，添加一个空属性
        propertiesToEdit.push({ key: '', value: '' });
    } else {
        propertyItems.forEach(item => {
            const keyElem = item.querySelector('.property-key');
            const valueElem = item.querySelector('.property-value');

            if (keyElem && valueElem) {
                // 移除冒号并去除空格
                const key = keyElem.textContent.replace(':', '').trim();
                const value = valueElem.textContent.trim();
                propertiesToEdit.push({ key, value });
            }
        });
    }

    // 渲染属性编辑表单
    renderPropertiesForm();

    // 显示模态框
    const modal = document.getElementById('editPropertiesModal');
    document.getElementById('editModalTitle').textContent = `编辑${elementType === 'relation' ? '关系' : '实体'}属性`;
    modal.style.display = 'block';

    // 保存编辑上下文
    modal.dataset.elementType = elementType;
    modal.dataset.elementId = elementId;
}

function renderPropertiesForm() {
    const container = document.getElementById('propertiesContainer');
    container.innerHTML = '';

    propertiesToEdit.forEach((prop, index) => {
        const group = document.createElement('div');
        group.className = 'property-input-group';
        group.innerHTML = `
            <input type="text" placeholder="属性名" value="${prop.key}" class="prop-key" data-index="${index}">
            <input type="text" placeholder="属性值" value="${prop.value}" class="prop-value" data-index="${index}">
            <button type="button" class="remove-property-btn" onclick="removeProperty(${index})">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(group);
    });
}

function addPropertyField() {
    propertiesToEdit.push({ key: '', value: '' });
    renderPropertiesForm();
}

function removeProperty(index) {
    propertiesToEdit.splice(index, 1);
    renderPropertiesForm();
}

function saveProperties() {
    const modal = document.getElementById('editPropertiesModal');
    const elementType = modal.dataset.elementType;
    let elementId = modal.dataset.elementId;

    // 确保elementId是字符串
    if (typeof elementId !== 'string') {
        elementId = String(elementId);
    }

    // 收集表单数据
    const keyInputs = document.querySelectorAll('.prop-key');
    const valueInputs = document.querySelectorAll('.prop-value');

    const properties = {};
    let hasValidProperties = false;

    for (let i = 0; i < keyInputs.length; i++) {
        const key = keyInputs[i].value.trim();
        const value = valueInputs[i].value.trim();

        if (key) {
            properties[key] = value;
            hasValidProperties = true;
        }
    }

    // 如果没有属性，可以保存空对象来清除所有属性
    if (!hasValidProperties) {
        if (!confirm('没有设置任何属性，这将清除所有现有属性。确定继续吗？')) {
            return;
        }
    }

    showLoading('正在保存属性...');

    // 构建URL
    let url = '';
    const encodedElementId = encodeURIComponent(elementId);
    const data = { properties: properties };

    if (elementType === 'relation') {
        url = `/api/entity_config/relation/${encodedElementId}`;
    } else {
        url = `/api/entity_config/node/${encodedElementId}`;
    }

    fetch(url, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
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
        hideLoading();

        // 检查是否保存成功
        if (result.success || result.message) {
            showSuccess('属性保存成功！');
            closeModals();

            // 立即更新显示，不需要重新加载整个页面
            updatePropertyDisplay(elementType, elementId, properties);
        } else {
            throw new Error(result.error || '保存失败');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('保存失败:', error);
        showError('保存失败: ' + error.message);
    });
}

function updatePropertyDisplay(elementType, elementId, properties) {
    const propsContainer = document.getElementById(`${elementType}-${elementId}`);
    if (!propsContainer) {
        console.warn(`找不到属性容器: ${elementType}-${elementId}`);
        // 重新加载当前页数据
        loadTriples();
        return;
    }

    // 更新属性显示
    const propsCount = Object.keys(properties).length;
    propsContainer.innerHTML = renderProperties(properties, propsCount);

    // 更新已修改计数
    const modifiedCountElem = document.getElementById('modifiedCount');
    if (modifiedCountElem) {
        let currentCount = parseInt(modifiedCountElem.textContent) || 0;
        modifiedCountElem.textContent = currentCount + 1;
    }
}

// 新增函数：立即更新属性显示
function updatePropertiesDisplay(elementType, elementId, properties) {
    const propsContainer = document.getElementById(`${elementType}-${elementId}`);
    if (!propsContainer) {
        console.warn(`找不到属性容器: ${elementType}-${elementId}`);
        return;
    }

    const propsCount = Object.keys(properties).length;
    propsContainer.innerHTML = renderProperties(properties, propsCount);

    // 更新统计信息
    updateModifiedCount();
}
// 更新已修改计数
function updateModifiedCount() {
    const modifiedCountElem = document.getElementById('modifiedCount');
    if (modifiedCountElem) {
        const currentCount = parseInt(modifiedCountElem.textContent) || 0;
        modifiedCountElem.textContent = currentCount + 1;
    }
}

function renderPagination(pagination) {
    const container = document.getElementById('pagination');
    container.innerHTML = '';

    const { current_page, total_pages, total_items } = pagination;

    if (total_pages <= 1) return;

    // 计算显示的页面范围
    let startPage = Math.max(1, current_page - 2);
    let endPage = Math.min(total_pages, current_page + 2);

    // 上一页按钮
    if (current_page > 1) {
        const prevBtn = document.createElement('button');
        prevBtn.className = 'page-btn';
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
        prevBtn.onclick = () => changePage(current_page - 1);
        container.appendChild(prevBtn);
    }

    // 第一页
    if (startPage > 1) {
        const firstBtn = document.createElement('button');
        firstBtn.className = 'page-btn';
        firstBtn.textContent = '1';
        firstBtn.onclick = () => changePage(1);
        container.appendChild(firstBtn);

        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'page-ellipsis';
            container.appendChild(ellipsis);
        }
    }

    // 中间页面
    for (let i = startPage; i <= endPage; i++) {
        const btn = document.createElement('button');
        btn.className = `page-btn ${i === current_page ? 'active' : ''}`;
        btn.textContent = i;
        btn.onclick = () => changePage(i);
        container.appendChild(btn);
    }

    // 最后一页
    if (endPage < total_pages) {
        if (endPage < total_pages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'page-ellipsis';
            container.appendChild(ellipsis);
        }

        const lastBtn = document.createElement('button');
        lastBtn.className = 'page-btn';
        lastBtn.textContent = total_pages;
        lastBtn.onclick = () => changePage(total_pages);
        container.appendChild(lastBtn);
    }

    // 下一页按钮
    if (current_page < total_pages) {
        const nextBtn = document.createElement('button');
        nextBtn.className = 'page-btn';
        nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
        nextBtn.onclick = () => changePage(current_page + 1);
        container.appendChild(nextBtn);
    }

    // 更新总数显示
    if (document.getElementById('totalCount')) {
        document.getElementById('totalCount').textContent = total_items || 0;
    }
}

function loadStats() {
    fetch('/api/entity_config/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error('获取统计信息失败: ' + response.status);
            }
            return response.json();
        })
        .then(result => {
            if (result.success) {
                const data = result.data || result;
                document.getElementById('totalEntities').textContent = data.entities || 0;
                document.getElementById('totalRelations').textContent = data.relationships || 0;
                document.getElementById('modifiedCount').textContent = '0';
            }
        })
        .catch(error => {
            console.error('加载统计信息失败:', error);
        });
}


function changePage(page) {
    currentPage = page;
    loadTriples();
}

function closeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
    propertiesToEdit = [];
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

function showWarning(message) {
    Swal.fire({
        icon: 'warning',
        title: '提示',
        text: message,
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
        confirmButtonColor: '#48dbfb'
    });
}