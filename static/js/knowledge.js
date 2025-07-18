document.addEventListener('DOMContentLoaded', function () {
    console.log('知识库管理脚本初始化');
    initKnowledgeManagement();
});

let documentModal = null;
let currentDocumentId = null;
let currentDocumentType = 'file';
let socket = null;

function initKnowledgeManagement() {
    console.log('初始化知识库管理功能');

    // 初始化模态框
    const modalElement = document.getElementById('documentModal');
    if (modalElement) {
        documentModal = new bootstrap.Modal(modalElement);
    }

    // 绑定新增按钮
    document.getElementById('addDocumentBtn')?.addEventListener('click', openDocumentModal);
    document.getElementById('addFirstDocumentBtn')?.addEventListener('click', openDocumentModal);

    // 初始化标签页切换
    initDocumentTypeTabs();

    // 初始化WebSocket
    initWebSocket();

    // 绑定保存文档按钮
    document.getElementById('saveDocumentBtn')?.addEventListener('click', saveDocument);

    // ✅ 使用事件委托绑定所有动态按钮
    document.addEventListener('click', function (e) {
        const target = e.target.closest('button');

        // ✅ 删除文档
        if (target?.classList.contains('delete-doc')) {
            const docId = target.dataset.id;
            const docName = target.dataset.name;
            confirmDeleteDocument(docId, docName);
        }

        // ✅ 向量化文档
        if (target?.classList.contains('vectorize-doc')) {
            const docId = target.dataset.id;
            const docName = target.dataset.name;
            confirmVectorizeDocument(docId, docName);
        }

        // ✅ 编辑文档
        if (target?.classList.contains('edit-doc')) {
            const docData = {
                id: target.dataset.id,
                name: target.dataset.name,
                type: target.dataset.type,
                path: target.dataset.path,
                tags: target.dataset.tags
            };
            openEditDocumentModal(docData);
        }
    });

    // 清空输出按钮
    document.getElementById('clearOutput')?.addEventListener('click', clearOutput);

    // 文件上传
    setupFileUploadHandlers();
}

// ✅ 删除文档（带确认）
function confirmDeleteDocument(docId, docName) {
    Swal.fire({
        title: `确认删除文档?`,
        text: `您确定要永久删除文档 "${docName}" 吗？此操作不可撤销！`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonColor: '#dc3545',
        customClass: {
            confirmButton: 'btn btn-danger',
            cancelButton: 'btn btn-secondary'
        },
        buttonsStyling: false
    }).then((result) => {
        if (result.isConfirmed) {
            deleteDocument(docId);
        }
    });
}

// ✅ 向量化文档（带确认）
function confirmVectorizeDocument(docId, docName) {
    Swal.fire({
        title: `确认向量化文档?`,
        text: `您确定要向量化文档 "${docName}" 吗？此操作可能需要一些时间。`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: '开始向量化',
        cancelButtonText: '取消',
        customClass: {
            confirmButton: 'btn btn-primary',
            cancelButton: 'btn btn-secondary'
        },
        buttonsStyling: false
    }).then((result) => {
        if (result.isConfirmed) {
            vectorizeDocument(docId, docName);
        }
    });
}

// ✅ 删除文档（实际请求）
function deleteDocument(docId) {
    fetch(`/admin/knowledge/documents/${docId}`, {
        method: 'DELETE'
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                Swal.fire('已删除', '文档已成功删除', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                Swal.fire('失败', data.error || '删除失败', 'error');
            }
        })
        .catch(err => {
            console.error(err);
            Swal.fire('错误', '请求失败，请检查网络或控制台', 'error');
        });
}

// ✅ 向量化文档（实际请求）
function vectorizeDocument(docId, docName) {
    const outputContainer = document.getElementById('vectorOutput');
    if (outputContainer) {
        outputContainer.innerHTML = `
            <div class="processing">
                <i class="fas fa-cog fa-spin me-2"></i> 开始向量化文档: ${docName}...
            </div>`;
    }

    const btn = document.querySelector(`.vectorize-doc[data-id="${docId}"]`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
    }

    if (!socket || !socket.connected) {
        Swal.fire('连接错误', 'WebSocket未连接，请刷新页面重试', 'error');
        return;
    }

    socket.emit('start_vectorization', { doc_id: docId });

    socket.once('vectorization_complete', () => {
        Swal.fire('成功', '向量化完成', 'success');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-brain"></i>';
        }
    });

    socket.once('vectorization_error', (err) => {
        Swal.fire('失败', err.message || '向量化失败', 'error');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-brain"></i>';
        }
    });
}

// ✅ 打开编辑模态框
function openEditDocumentModal(docData) {
    currentDocumentId = docData.id;
    document.getElementById('modalTitle').textContent = '编辑文档';

    // 设置表单内容
    if (docData.type === 'file') {
        document.getElementById('fileDocumentName').value = docData.name;
        document.getElementById('fileTags').value = docData.tags || '';
        switchTab('file');
    } else {
        document.getElementById('urlDocumentName').value = docData.name;
        document.getElementById('urlLink').value = docData.path;
        document.getElementById('urlTags').value = docData.tags || '';
        switchTab('url');
    }

    documentModal.show();
}

// ✅ 切换标签页
function switchTab(type) {
    currentDocumentType = type;

    // 切换标签
    document.querySelectorAll('.document-type-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.type === type);
    });

    // 切换表单
    document.querySelectorAll('.document-form-section').forEach(section => {
        section.classList.toggle('active', section.id === `${type}FormSection`);
    });
}

// ✅ 保存文档
function saveDocument() {
    const isEdit = !!currentDocumentId;
    const endpoint = isEdit ? `/admin/knowledge/documents/${currentDocumentId}` : '/admin/knowledge/documents';
    const method = isEdit ? 'PUT' : 'POST';

    const formData = new FormData();

    if (currentDocumentType === 'file') {
        const name = document.getElementById('fileDocumentName').value.trim();
        const tags = document.getElementById('fileTags').value.trim();
        const file = document.getElementById('fileInput').files[0];

        if (!name) return alert('请输入文档名称');
        if (!isEdit && !file) return alert('请选择文件');

        formData.append('name', name);
        formData.append('type', 'file');
        formData.append('tags', tags);
        if (file) formData.append('file', file);

    } else {
        const name = document.getElementById('urlDocumentName').value.trim();
        const url = document.getElementById('urlLink').value.trim();
        const tags = document.getElementById('urlTags').value.trim();

        if (!name || !url) return alert('请填写名称和URL');

        formData.append('name', name);
        formData.append('type', 'url');
        formData.append('url', url);
        formData.append('tags', tags);
    }

    fetch(endpoint, {
        method: method,
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                Swal.fire('成功', isEdit ? '更新成功' : '添加成功', 'success');
                documentModal.hide();
                setTimeout(() => location.reload(), 1000);
            } else {
                Swal.fire('失败', data.error || '操作失败', 'error');
            }
        })
        .catch(err => {
            console.error(err);
            Swal.fire('错误', '请求失败，请检查网络或控制台', 'error');
        });
}

// ✅ 初始化WebSocket
function initWebSocket() {
    socket = io({
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 3000
    });

    socket.on('connect', () => console.log('WebSocket已连接'));
    socket.on('disconnect', () => console.warn('WebSocket断开'));
    socket.on('connect_error', (err) => console.error('WebSocket连接失败', err));

    socket.on('vectorization_update', (data) => {
        const output = document.getElementById('vectorOutput');
        if (output) {
            output.innerHTML += data.message;
            output.scrollTop = output.scrollHeight;
        }
    });

    socket.on('vectorization_complete', (data) => {
        const output = document.getElementById('vectorOutput');
        if (output) {
            output.innerHTML += '<div class="success-message">✅ 向量化处理完成</div>';
            if (data.stats) updateVectorDBStats(data.stats);
        }
    });

    socket.on('vectorization_error', (err) => {
        const output = document.getElementById('vectorOutput');
        if (output) {
            output.innerHTML += `<div class="error-message">❌ ${err.message}</div>`;
        }
    });
}

// ✅ 更新向量数据库状态
function updateVectorDBStats(stats) {
    const cards = document.querySelectorAll('.stat-card h3');
    if (cards.length >= 4) {
        cards[0].textContent = stats.document_count || 'N/A';
        cards[1].textContent = stats.chunk_size || 'N/A';
        cards[2].textContent = stats.embedding_model || 'N/A';
        cards[3].textContent = stats.status || 'N/A';
    }
}

// ✅ 清空输出
function clearOutput() {
    const output = document.getElementById('vectorOutput');
    if (output) {
        output.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="fas fa-info-circle fa-2x mb-3"></i>
                <p>选择文档并点击"向量化"按钮开始处理</p>
            </div>`;
    }
}

// ✅ 初始化标签页
function initDocumentTypeTabs() {
    document.addEventListener('click', function (e) {
        const tab = e.target.closest('.document-type-tab');
        if (tab) {
            switchTab(tab.dataset.type);
        }
    });
}

// ✅ 文件上传处理
function setupFileUploadHandlers() {
    const fileInput = document.getElementById('fileInput');
    const dropArea = document.getElementById('dropArea');
    const selectBtn = document.getElementById('selectFileBtn');

    selectBtn?.addEventListener('click', () => fileInput.click());

    fileInput?.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (file) {
            const valid = ['pdf', 'doc', 'docx', 'txt', 'md'];
            const ext = file.name.split('.').pop().toLowerCase();
            if (!valid.includes(ext)) {
                alert(`不支持的文件类型: .${ext}`);
                fileInput.value = '';
                return;
            }

            document.getElementById('fileName').textContent = file.name;
            document.getElementById('fileSize').textContent = (file.size / 1024).toFixed(2) + ' KB';
            document.getElementById('fileInfo').classList.remove('d-none');
            dropArea?.classList.add('d-none');

            const nameInput = document.getElementById('fileDocumentName');
            if (!nameInput.value) nameInput.value = file.name.replace(/\.[^/.]+$/, '');
        }
    });

    document.getElementById('removeFile')?.addEventListener('click', () => {
        fileInput.value = '';
        document.getElementById('fileInfo').classList.add('d-none');
        dropArea?.classList.remove('d-none');
    });
}

// ✅ 打开新增模态框
function openDocumentModal() {
    currentDocumentId = null;
    document.getElementById('modalTitle').textContent = '新增文档';
    document.getElementById('fileInput').value = '';
    document.getElementById('fileDocumentName').value = '';
    document.getElementById('fileTags').value = '';
    document.getElementById('urlDocumentName').value = '';
    document.getElementById('urlLink').value = '';
    document.getElementById('urlTags').value = '';
    document.getElementById('fileInfo').classList.add('d-none');
    document.getElementById('dropArea')?.classList.remove('d-none');
    switchTab('file');
    documentModal.show();
}