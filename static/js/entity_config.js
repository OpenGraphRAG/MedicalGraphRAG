document.addEventListener('DOMContentLoaded', function () {
    console.log('实体关系属性配置脚本初始化');
    initEntityConfig();
});

let currentPage = 1;
let perPage = 3;
let searchTerm = '';
let propertiesToEdit = [];

function initEntityConfig() {
    console.log('初始化实体关系属性配置功能');
    
    // 绑定事件
    bindEvents();
    
    // 加载数据
    loadTriples();
    loadStats();
}

function bindEvents() {
    // 刷新按钮
    document.getElementById('refreshTriples')?.addEventListener('click', () => {
        currentPage = 1;
        loadTriples();
    });

    // 搜索框
    const searchInput = document.getElementById('searchTriples');
    searchInput?.addEventListener('input', function() {
        searchTerm = this.value;
        currentPage = 1;
        loadTriples();
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

function loadTriples() {
    console.log(`加载第${currentPage}页三元组，每页${perPage}条`);
    
    showLoading('正在加载三元组数据...');
    
    const url = `/api/entity_config/triples?page=${currentPage}&per_page=${perPage}&search=${encodeURIComponent(searchTerm)}`;
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应异常: ' + response.status);
            }
            return response.json();
        })
        .then(result => {
            hideLoading();
            
            if (result.success) {
                renderTriples(result.triples);
                renderPagination(result.pagination);
            } else {
                throw new Error(result.error || '加载失败');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('加载三元组失败:', error);
            showError('加载数据失败: ' + error.message);
        });
}

function loadStats() {
    // 简单的统计信息（可以从三元组数据计算）
    fetch('/api/entity_config/triples?page=1&per_page=1')
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                document.getElementById('totalEntities').textContent = result.pagination.total_items * 2;
                document.getElementById('totalRelations').textContent = result.pagination.total_items;
            }
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
    
    triples.forEach(triple => {
        const card = createTripleCard(triple);
        container.appendChild(card);
    });
    
    // 更新计数
    document.getElementById('currentCount').textContent = triples.length;
    document.getElementById('totalCount').textContent = document.getElementById('totalCount').textContent || '0';
}

function createTripleCard(triple) {
    const card = document.createElement('div');
    card.className = 'triple-card';
    
    const headPropsCount = Object.keys(triple.head.properties || {}).length;
    const tailPropsCount = Object.keys(triple.tail.properties || {}).length;
    const relPropsCount = Object.keys(triple.relation.properties || {}).length;
    
    card.innerHTML = `
        <div class="triple-header">
            <div class="triple-title">
                <span class="entity-badge head">${triple.head.type}</span>
                <span class="relation-badge">${triple.relation.type}</span>
                <span class="entity-badge tail">${triple.tail.type}</span>
            </div>
            <div class="triple-id">ID: ${triple.head.tid} → ${triple.relation.rid} → ${triple.tail.tid}</div>
        </div>
        
        <div class="triple-body">
            <div class="entity-section">
                <div class="section-header">
                    <div class="section-title">
                        <i class="fas fa-circle"></i> 头节点: ${triple.head.name}
                    </div>
                    <button class="edit-btn" onclick="editProperties('head', ${triple.head.tid})">
                        <i class="fas fa-edit"></i> 编辑
                    </button>
                </div>
                <div class="properties-list" id="head-${triple.head.tid}">
                    ${renderProperties(triple.head.properties, headPropsCount)}
                </div>
            </div>
            
            <div class="relation-section">
                <div class="section-header">
                    <div class="section-title">
                        <i class="fas fa-arrows-alt-h"></i> 关系属性
                    </div>
                    <button class="edit-btn" onclick="editProperties('relation', ${triple.relation.rid})">
                        <i class="fas fa-edit"></i> 编辑
                    </button>
                </div>
                <div class="properties-list" id="relation-${triple.relation.rid}">
                    ${renderProperties(triple.relation.properties, relPropsCount)}
                </div>
            </div>
            
            <div class="entity-section">
                <div class="section-header">
                    <div class="section-title">
                        <i class="fas fa-circle"></i> 尾节点: ${triple.tail.name}
                    </div>
                    <button class="edit-btn" onclick="editProperties('tail', ${triple.tail.tid})">
                        <i class="fas fa-edit"></i> 编辑
                    </button>
                </div>
                <div class="properties-list" id="tail-${triple.tail.tid}">
                    ${renderProperties(triple.tail.properties, tailPropsCount)}
                </div>
            </div>
        </div>
    `;
    
    return card;
}

function renderProperties(properties, count) {
    if (count === 0) {
        return '<div class="no-properties">暂无属性</div>';
    }
    
    const propsHtml = Object.entries(properties).map(([key, value]) => `
        <div class="property-item">
            <span class="property-key">${key}:</span>
            <span class="property-value" title="${value}">${value}</span>
        </div>
    `).join('');
    
    return propsHtml;
}

function editProperties(elementType, elementId) {
    console.log(`编辑${elementType}属性:`, elementId);
    
    // 获取当前属性
    const propsContainer = document.getElementById(`${elementType}-${elementId}`);
    const propertyItems = propsContainer.querySelectorAll('.property-item');
    
    propertiesToEdit = [];
    
    if (propertyItems.length === 0) {
        // 如果没有属性，添加一个空属性
        propertiesToEdit.push({ key: '', value: '' });
    } else {
        propertyItems.forEach(item => {
            const key = item.querySelector('.property-key').textContent.replace(':', '');
            const value = item.querySelector('.property-value').textContent;
            propertiesToEdit.push({ key, value });
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
    const elementId = modal.dataset.elementId;
    
    // 收集表单数据
    const keyInputs = document.querySelectorAll('.prop-key');
    const valueInputs = document.querySelectorAll('.prop-value');
    
    const properties = {};
    for (let i = 0; i < keyInputs.length; i++) {
        const key = keyInputs[i].value.trim();
        const value = valueInputs[i].value.trim();
        
        if (key) {
            properties[key] = value;
        }
    }
    
    if (Object.keys(properties).length === 0) {
        showWarning('请至少添加一个属性');
        return;
    }
    
    showLoading('正在保存属性...');
    
    let url = '';
    let data = { properties: properties };
    
    if (elementType === 'relation') {
        url = `/api/entity_config/relation/${elementId}`;
    } else {
        url = `/api/entity_config/node/${elementId}`;
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
        
        if (result.success) {
            showSuccess('属性更新成功');
            closeModals();
            loadTriples(); // 刷新数据
        } else {
            throw new Error(result.error || '更新失败');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('保存属性失败:', error);
        showError('保存属性失败: ' + error.message);
    });
}

function renderPagination(pagination) {
    const container = document.getElementById('pagination');
    container.innerHTML = '';
    
    const { current_page, total_pages } = pagination;
    
    if (total_pages <= 1) return;
    
    // 上一页
    if (current_page > 1) {
        const prevBtn = document.createElement('button');
        prevBtn.className = 'page-btn';
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
        prevBtn.onclick = () => changePage(current_page - 1);
        container.appendChild(prevBtn);
    }
    
    // 页码
    for (let i = 1; i <= total_pages; i++) {
        if (i === 1 || i === total_pages || (i >= current_page - 1 && i <= current_page + 1)) {
            const btn = document.createElement('button');
            btn.className = `page-btn ${i === current_page ? 'active' : ''}`;
            btn.textContent = i;
            btn.onclick = () => changePage(i);
            container.appendChild(btn);
        } else if (i === current_page - 2 || i === current_page + 2) {
            const span = document.createElement('span');
            span.textContent = '...';
            container.appendChild(span);
        }
    }
    
    // 下一页
    if (current_page < total_pages) {
        const nextBtn = document.createElement('button');
        nextBtn.className = 'page-btn';
        nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
        nextBtn.onclick = () => changePage(current_page + 1);
        container.appendChild(nextBtn);
    }
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