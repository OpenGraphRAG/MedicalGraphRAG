document.addEventListener('DOMContentLoaded', function () {
    console.log('知识库管理脚本初始化');
    initKnowledgeManagement();
});
// 在 initKnowledgeManagement 函数中添加修复按钮事件监听
document.getElementById('fixPathsBtn')?.addEventListener('click', fixDocumentPaths);

// 添加修复文件路径函数
function fixDocumentPaths() {
    Swal.fire({
        title: '确认修复文件路径?',
        text: '这将检查并修复所有文档的文件路径',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: '修复',
        cancelButtonText: '取消',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch('/admin/knowledge/fix_paths', {
                method: 'POST'
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showNotification('成功', `修复了 ${data.fixed_count} 个文档路径`, 'success');
                    setTimeout(() => location.reload(), 2000);
                } else {
                    showNotification('失败', data.error || '修复失败', 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showNotification('错误', '请求失败，请检查网络或控制台', 'error');
            });
        }
    });
}

let documentModal = null;
let currentDocumentId = null;
let currentDocumentType = 'file';
let socket = null;

function initKnowledgeManagement() {
    console.log('初始化知识库管理功能');

    // 初始化模态框
    const modalElement = document.getElementById('documentModal');
    if (modalElement) {
        documentModal = modalElement;
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

    // 使用事件委托绑定所有动态按钮
    document.addEventListener('click', function (e) {
        const target = e.target.closest('button');

        // 删除文档
        if (target?.classList.contains('delete-doc')) {
            const docId = target.dataset.id;
            const docName = target.dataset.name;
            confirmDeleteDocument(docId, docName);
        }

        // 向量化文档
        if (target?.classList.contains('vectorize-doc')) {
            const docId = target.dataset.id;
            const docName = target.dataset.name;
            confirmVectorizeDocument(docId, docName);
        }

        // 编辑文档
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

    // 关闭模态框
    setupModalCloseHandlers();
}

// 删除文档（带确认）
function confirmDeleteDocument(docId, docName) {
    Swal.fire({
        title: `确认删除文档?`,
        text: `您确定要永久删除文档 "${docName}" 吗？此操作不可撤销！`,
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
            deleteDocument(docId);
        }
    });
}

// 向量化文档（带确认）
function confirmVectorizeDocument(docId, docName) {
    Swal.fire({
        title: `确认向量化文档?`,
        text: `您确定要向量化文档 "${docName}" 吗？此操作可能需要一些时间。`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: '开始向量化',
        cancelButtonText: '取消',
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2',
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

// 删除文档（实际请求）
function deleteDocument(docId) {
    fetch(`/admin/knowledge/documents/${docId}`, {
        method: 'DELETE'
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showNotification('已删除', '文档已成功删除', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification('失败', data.error || '删除失败', 'error');
            }
        })
        .catch(err => {
            console.error(err);
            showNotification('错误', '请求失败，请检查网络或控制台', 'error');
        });
}

// 向量化文档（实际请求）
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
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        // 添加处理中样式
        btn.classList.add('processing');
    }

    if (!socket || !socket.connected) {
        showNotification('连接错误', 'WebSocket未连接，请刷新页面重试', 'error');
        return;
    }

    socket.emit('start_vectorization', { doc_id: docId });

    socket.once('vectorization_complete', () => {
        showNotification('成功', '向量化完成', 'success');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-brain"></i>';
            btn.classList.remove('processing');
        }
    });

    socket.once('vectorization_error', (err) => {
        showNotification('失败', err.message || '向量化失败', 'error');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-brain"></i>';
            btn.classList.remove('processing');
        }
    });
}

// 打开编辑模态框
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

    showModal();
}

// 切换标签页
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

// 在保存文档函数中添加 socket_id
function saveDocument() {
    const isEdit = !!currentDocumentId;
    const endpoint = isEdit ? `/admin/knowledge/documents/${currentDocumentId}` : '/admin/knowledge/documents';
    const method = isEdit ? 'PUT' : 'POST';

    const formData = new FormData();

    if (currentDocumentType === 'file') {
        const name = document.getElementById('fileDocumentName').value.trim();
        const tags = document.getElementById('fileTags').value.trim();
        const file = document.getElementById('fileInput').files[0];

        if (!name) return showNotification('警告', '请输入文档名称', 'warning');
        if (!isEdit && !file) return showNotification('警告', '请选择文件', 'warning');

        formData.append('name', name);
        formData.append('type', 'file');
        formData.append('tags', tags);
        if (file) formData.append('file', file);

    } else {
        const name = document.getElementById('urlDocumentName').value.trim();
        const url = document.getElementById('urlLink').value.trim();
        const tags = document.getElementById('urlTags').value.trim();

        if (!name || !url) return showNotification('警告', '请填写名称和URL', 'warning');

        formData.append('name', name);
        formData.append('type', 'url');
        formData.append('url', url);
        formData.append('tags', tags);
        formData.append('socket_id', socket.id); // 添加 socket_id

        // 显示爬取状态
        const crawlerStatus = document.getElementById('crawlerStatus');
        if (crawlerStatus) {
            crawlerStatus.style.display = 'block';
        }

        // 在输出区域显示消息
        const output = document.getElementById('vectorOutput');
        if (output && output.querySelector('.empty-output')) {
            output.innerHTML = '';
        }
        if (output) {
            output.innerHTML += '<div class="output-message">开始处理URL文档...</div>';
        }
    }

    // 显示加载中状态
    const saveBtn = document.getElementById('saveDocumentBtn');
    const originalHtml = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
    saveBtn.disabled = true;

    fetch(endpoint, {
        method: method,
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showNotification('成功', isEdit ? '更新成功' : '添加成功', 'success');

                // 如果是URL文档，不立即关闭模态框，等待爬取完成
                if (currentDocumentType === 'url' && !isEdit) {
                    saveBtn.innerHTML = '<i class="fas fa-check"></i> 已保存，正在爬取内容...';
                    saveBtn.disabled = true;
                } else {
                    hideModal();
                    setTimeout(() => location.reload(), 1000);
                }
            } else {
                showNotification('失败', data.error || '操作失败', 'error');
                const crawlerStatus = document.getElementById('crawlerStatus');
                if (crawlerStatus) {
                    crawlerStatus.style.display = 'none';
                }
            }
        })
        .catch(err => {
            console.error(err);
            showNotification('错误', '请求失败，请检查网络或控制台', 'error');
            const crawlerStatus = document.getElementById('crawlerStatus');
            if (crawlerStatus) {
                crawlerStatus.style.display = 'none';
            }
        })
        .finally(() => {
            if (currentDocumentType !== 'url' || isEdit) {
                saveBtn.innerHTML = originalHtml;
                saveBtn.disabled = false;
            }
        });
}

// 初始化WebSocket
function initWebSocket() {
    socket = io({
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 3000
    });

    socket.on('connect', () => console.log('WebSocket已连接'));
    socket.on('disconnect', () => console.warn('WebSocket断开'));
    socket.on('connect_error', (err) => console.error('WebSocket连接失败', err));

    // 向量化更新消息
    socket.on('vectorization_update', (data) => {
        const output = document.getElementById('vectorOutput');
        if (output) {
            // 移除空状态
            if (output.querySelector('.empty-output')) {
                output.innerHTML = '';
            }

            output.innerHTML += `<div class="output-message">${data.message}</div>`;
            output.scrollTop = output.scrollHeight;
        }
    });

    socket.on('vectorization_complete', (data) => {
        const output = document.getElementById('vectorOutput');
        if (output) {
            output.innerHTML += '<div class="success-message">✅ 向量化处理完成</div>';
        }
    });

    socket.on('vectorization_error', (err) => {
        const output = document.getElementById('vectorOutput');
        if (output) {
            output.innerHTML += `<div class="error-message">❌ ${err.message}</div>`;
        }
    });

    // 网页爬取更新消息
    socket.on('crawling_update', (data) => {
        const output = document.getElementById('vectorOutput');
        const crawlerStatus = document.getElementById('crawlerStatus');
        const progressBar = crawlerStatus?.querySelector('.progress-bar');
        const messageElement = crawlerStatus?.querySelector('.crawler-message');

        if (output) {
            // 移除空状态
            if (output.querySelector('.empty-output')) {
                output.innerHTML = '';
            }

            output.innerHTML += `<div class="output-message">📄 ${data.message}</div>`;
            output.scrollTop = output.scrollHeight;
        }

        // 更新进度条
        if (crawlerStatus && progressBar && messageElement) {
            crawlerStatus.style.display = 'block';
            progressBar.style.width = `${data.progress}%`;
            messageElement.textContent = data.message;

            // 如果完成，隐藏进度条
            if (data.completed) {
                setTimeout(() => {
                    crawlerStatus.style.display = 'none';
                }, 3000);
            }
        }
    });

    socket.on('crawling_error', (data) => {
        const output = document.getElementById('vectorOutput');
        const crawlerStatus = document.getElementById('crawlerStatus');

        if (output) {
            output.innerHTML += `<div class="error-message">❌ ${data.message}</div>`;
        }

        if (crawlerStatus) {
            crawlerStatus.style.display = 'none';
        }
    });
}

// 更新向量数据库状态
function updateVectorDBStats(stats) {
    const cards = document.querySelectorAll('.stat-card h3');
    if (cards.length >= 4) {
        cards[0].textContent = stats.document_count || 'N/A';
        cards[1].textContent = stats.chunk_size || 'N/A';
        cards[2].textContent = stats.embedding_model || 'N/A';
        cards[3].textContent = stats.status || 'N/A';
    }
}

// 清空输出
function clearOutput() {
    const output = document.getElementById('vectorOutput');
    if (output) {
        output.innerHTML = `
            <div class="empty-output">
                <i class="fas fa-info-circle"></i>
                <p>选择文档并点击"向量化"按钮开始处理</p>
            </div>`;
    }
}

// 初始化标签页
function initDocumentTypeTabs() {
    document.addEventListener('click', function (e) {
        const tab = e.target.closest('.document-type-tab');
        if (tab) {
            switchTab(tab.dataset.type);
        }
    });
}

// 文件上传处理
function setupFileUploadHandlers() {
    const fileInput = document.getElementById('fileInput');
    const dropArea = document.getElementById('dropArea');
    const selectBtn = document.getElementById('selectFileBtn');
    const fileInfo = document.getElementById('fileInfo');
    const removeFileBtn = document.getElementById('removeFile');

    selectBtn?.addEventListener('click', () => fileInput.click());

    fileInput?.addEventListener('change', handleFileSelect);

    // 拖放功能
    dropArea?.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropArea.classList.add('dragover');
    });

    dropArea?.addEventListener('dragleave', () => {
        dropArea.classList.remove('dragover');
    });

    dropArea?.addEventListener('drop', (e) => {
        e.preventDefault();
        dropArea.classList.remove('dragover');

        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });

    removeFileBtn?.addEventListener('click', () => {
        fileInput.value = '';
        fileInfo.style.display = 'none';
        dropArea.style.display = 'block';
    });

    function handleFileSelect() {
        const file = fileInput.files[0];
        if (file) {
            const valid = ['pdf', 'doc', 'docx', 'txt', 'md'];
            const ext = file.name.split('.').pop().toLowerCase();
            if (!valid.includes(ext)) {
                showNotification('错误', `不支持的文件类型: .${ext}`, 'error');
                fileInput.value = '';
                return;
            }

            document.getElementById('fileName').textContent = file.name;
            document.getElementById('fileSize').textContent = formatFileSize(file.size);
            fileInfo.style.display = 'flex';
            dropArea.style.display = 'none';

            const nameInput = document.getElementById('fileDocumentName');
            if (!nameInput.value) {
                nameInput.value = file.name.replace(/\.[^/.]+$/, '');
            }
        }
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 打开新增模态框
function openDocumentModal() {
    currentDocumentId = null;
    document.getElementById('modalTitle').textContent = '新增文档';
    document.getElementById('fileInput').value = '';
    document.getElementById('fileDocumentName').value = '';
    document.getElementById('fileTags').value = '';
    document.getElementById('urlDocumentName').value = '';
    document.getElementById('urlLink').value = '';
    document.getElementById('urlTags').value = '';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('dropArea').style.display = 'block';
    switchTab('file');
    showModal();
}

// 显示模态框
function showModal() {
    if (documentModal) {
        documentModal.style.display = 'block';
    }
}

// 隐藏模态框
function hideModal() {
    if (documentModal) {
        documentModal.style.display = 'none';
    }
}

// 设置模态框关闭处理
function setupModalCloseHandlers() {
    const closeBtn = document.querySelector('.close');
    const cancelBtn = document.querySelector('[data-dismiss="modal"]');

    if (closeBtn) {
        closeBtn.addEventListener('click', hideModal);
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', hideModal);
    }

    // 点击模态框外部关闭
    window.addEventListener('click', (e) => {
        if (e.target === documentModal) {
            hideModal();
        }
    });
}

// 显示通知
function showNotification(title, text, icon) {
    Swal.fire({
        title: title,
        text: text,
        icon: icon,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#e2e2e2'
    });
}

// 添加处理中样式
const style = document.createElement('style');
style.textContent = `
    .btn-icon.processing {
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }

    .dragover {
        background: rgba(77, 179, 211, 0.15) !important;
        border: 2px dashed #2c7fb8 !important;
    }

    .output-message {
        margin-bottom: 10px;
        line-height: 1.6;
    }

    .success-message {
        color: #2ecc71;
        font-weight: 500;
    }

    .error-message {
        color: #e74c3c;
        font-weight: 500;
    }

    .processing {
        color: #3498db;
        display: flex;
        align-items: center;
    }
`;
document.head.appendChild(style);