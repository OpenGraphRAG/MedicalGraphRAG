window.toggleFullscreen = toggleFullscreen;
window.exitFullscreen = exitFullscreen;
window.showSingleNodeQuery = showSingleNodeQuery;
window.showMultiHopQuery = showMultiHopQuery;
window.showTripleQuery = showTripleQuery;
window.changeLayout = changeLayout;
window.updateTripleCount = updateTripleCount;

// SweetAlert2 全局配置
document.addEventListener('DOMContentLoaded', function() {
    // 配置 SweetAlert2 默认参数
    if (typeof Swal !== 'undefined') {
        Swal.mixin({
            background: 'rgba(26, 26, 46, 0.95)',
            color: '#fff',
            confirmButtonColor: '#48dbfb',
            cancelButtonColor: '#6c757d',
            customClass: {
                popup: 'kg-swal-popup'
            }
        });
    }

    // 初始化图谱
    initKnowledgeGraph();
});

// 全屏状态管理
let isFullscreen = false;
let originalParent = null;
let fullscreenContainer = null;
let networkInstance = null; // 存储网络实例引用

// 全屏切换功能
function toggleFullscreen() {
    const container = document.getElementById('kg-network-container');

    if (!isFullscreen) {
        enterFullscreen(container);
    } else {
        exitFullscreen();
    }
}

function enterFullscreen(element) {
    isFullscreen = true;
    originalParent = element.parentNode;
    networkInstance = network; // 保存当前网络实例

    // 创建全屏容器
    fullscreenContainer = document.createElement('div');
    fullscreenContainer.id = 'kg-fullscreen-container';
    fullscreenContainer.className = 'kg-fullscreen';

    // 构建全屏界面HTML
    fullscreenContainer.innerHTML = `
        <!-- 顶部中央查询控制区 -->
        <div class="fullscreen-top-controls">
            <div class="query-section">
                <button class="btn btn-outline" id="fs-single-node-btn">
                    <i class="fas fa-search"></i> 节点查询
                </button>
                <button class="btn btn-outline" id="fs-multi-hop-btn">
                    <i class="fas fa-route"></i> 多跳查询
                </button>
                <button class="btn btn-outline" id="fs-triple-btn">
                    <i class="fas fa-project-diagram"></i> 三元组查询
                </button>
            </div>
        </div>

        <!-- 左侧布局控制区 -->
        <div class="fullscreen-left-controls">
            <h4>布局控制</h4>
            <div class="layout-buttons">
                <button class="btn btn-sm btn-outline active" data-layout="forceAtlas2Based">
                    <i class="fas fa-project-diagram"></i> 力导向
                </button>
                <button class="btn btn-sm btn-outline" data-layout="hierarchical">
                    <i class="fas fa-sitemap"></i> 层次
                </button>
                <button class="btn btn-sm btn-outline" data-layout="circular">
                    <i class="fas fa-circle"></i> 环形
                </button>
                <button class="btn btn-sm btn-outline" data-layout="random">
                    <i class="fas fa-random"></i> 随机
                </button>
            </div>
        </div>

        <!-- 左下角三元组数量控制 -->
        <div class="fullscreen-bottom-left">
            <div class="triple-count-control">
                <label>显示三元组数量</label>
                <input type="range" id="tripleCountSlider" min="50" max="500" value="100">
                <div id="tripleCountValue">100</div>
            </div>
        </div>

        <!-- 退出全屏按钮 -->
        <button class="btn btn-danger fullscreen-exit" id="fullscreen-exit-btn">
            <i class="fas fa-compress"></i> 退出全屏
        </button>

        <!-- 图谱容器 -->
        <div id="kg-network-container-fullscreen" style="width:100%;height:100%;"></div>

        <!-- 详情面板 -->
        <div class="node-details-panel" id="nodeDetailsPanelFullscreen" style="display:none;">
            <div class="panel-header">
                <h3 id="panelTitleFullscreen">节点详情</h3>
                <button class="btn-icon close-panel" onclick="closeNodeDetails()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="panel-content" id="nodeDetailsContentFullscreen"></div>
        </div>
    `;

    document.body.appendChild(fullscreenContainer);

    // 移动网络容器到全屏区域
    fullscreenContainer.querySelector('#kg-network-container-fullscreen').appendChild(element);

    // 绑定事件（关键修复：使用addEventListener而不是onclick）
    document.getElementById('fullscreen-exit-btn').addEventListener('click', exitFullscreen);
    document.getElementById('fs-single-node-btn').addEventListener('click', showSingleNodeQuery);
    document.getElementById('fs-multi-hop-btn').addEventListener('click', showMultiHopQuery);
    document.getElementById('fs-triple-btn').addEventListener('click', showTripleQuery);
    document.getElementById('tripleCountSlider').addEventListener('input', function() {
        updateTripleCount(this.value);
    });

    // 绑定布局按钮事件
    fullscreenContainer.querySelectorAll('.layout-buttons .btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const layout = this.dataset.layout;
            // 更新active状态
            fullscreenContainer.querySelectorAll('.layout-buttons .btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            changeLayout(layout);
        });
    });

    // 请求浏览器全屏
    if (fullscreenContainer.requestFullscreen) {
        fullscreenContainer.requestFullscreen().catch(err => {
            console.log('全屏请求失败:', err);
        });
    } else if (fullscreenContainer.webkitRequestFullscreen) {
        fullscreenContainer.webkitRequestFullscreen();
    } else if (fullscreenContainer.msRequestFullscreen) {
        fullscreenContainer.msRequestFullscreen();
    }

    // 重新初始化网络
    setTimeout(() => {
        if (networkInstance) {
            networkInstance.fit();
            networkInstance.redraw();
        }
    }, 100);
}
function cleanupFullscreen() {
    // 恢复网络容器到原始位置
    if (originalParent && fullscreenContainer) {
        const element = fullscreenContainer.querySelector('#kg-network-container-fullscreen');
        originalParent.appendChild(element);
        document.body.removeChild(fullscreenContainer);
    }

    // 清理变量
    isFullscreen = false;
    fullscreenContainer = null;
    originalParent = null;
    networkInstance = null;

    // 重新初始化网络
    setTimeout(() => {
        if (network) {
            network.fit();
            network.redraw();
        }
    }, 100);
}

function exitFullscreen() {
    if (!isFullscreen) return;

    // 退出浏览器全屏（关键修复：确保在正确的上下文中调用）
    if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().then(() => {
            cleanupFullscreen();
        }).catch(err => {
            console.log('退出全屏失败:', err);
            cleanupFullscreen();
        });
    } else {
        cleanupFullscreen();
    }
}

// 绑定全屏模式事件
function bindFullscreenEvents() {
    // 重新绑定节点点击事件
    network.on('selectNode', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = network.body.data.nodes.get(String(nodeId));
            showNodeDetailsFullscreen(node);
        }
    });

    network.on('selectEdge', function(params) {
        if (params.edges.length > 0) {
            const edgeId = params.edges[0];
            const edge = network.body.data.edges.get(edgeId);
            showEdgeDetailsFullscreen(edge);
        }
    });
}

// 全屏模式显示节点详情
function showNodeDetailsFullscreen(node) {
    const panel = document.getElementById('nodeDetailsPanelFullscreen');
    const content = document.getElementById('nodeDetailsContentFullscreen');

    // 使用同普通模式的内容生成逻辑
    fetch(`/api/entity_config/node/${node.id}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const properties = data.node.properties || {};
                const propsCount = Object.keys(properties).length;

                let propsHtml = '';
                if (propsCount === 0) {
                    propsHtml = '<div class="no-properties">暂无属性</div>';
                } else {
                    const tabs = Object.keys(properties);
                    propsHtml = `
                        <div class="property-tabs">
                            <div class="tab-nav">
                                ${tabs.map((key, idx) => `
                                    <button class="tab-nav-btn ${idx === 0 ? 'active' : ''}"
                                            data-tab="fs-prop-${idx}">
                                        ${key.substring(0, 10)}${key.length > 10 ? '...' : ''}
                                    </button>
                                `).join('')}
                            </div>
                            <div class="tab-content-wrapper">
                                ${tabs.map((key, idx) => `
                                    <div class="tab-pane ${idx === 0 ? 'active' : ''}" id="fs-prop-${idx}">
                                        <div class="property-item">
                                            <span class="property-key">${key}:</span>
                                            <span class="property-value" title="${properties[key]}">${properties[key]}</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }

                content.innerHTML = `
                    <div class="node-info">
                        <h4>${node.label}</h4>
                        <div class="info-grid">
                            <div class="info-item">
                                <label>类型</label>
                                <span>${node.type || '未知'}</span>
                            </div>
                            <div class="info-item">
                                <label>ID</label>
                                <span>${node.id}</span>
                            </div>
                        </div>
                    </div>
                    <div class="properties-section">
                        <h5>属性列表 (${propsCount})</h5>
                        ${propsHtml}
                    </div>
                `;

                bindPropertyTabs();

                panel.style.display = 'block';
                panel.style.position = 'absolute';
                panel.style.top = '80px';
                panel.style.right = '30px';
                panel.style.width = '420px';
                panel.style.maxHeight = '85vh';
                panel.style.zIndex = '1001';
            }
        });
}

// 全屏模式显示关系详情
function showEdgeDetailsFullscreen(edge) {
    // 实现类似 showNodeDetailsFullscreen 的逻辑
    // 为简洁省略具体实现，可参考普通模式的 showEdgeDetails
}

// 查询功能实现
function showSingleNodeQuery() {
    Swal.fire({
        title: '节点查询',
        input: 'text',
        inputPlaceholder: '输入节点名称',
        showCancelButton: true,
        confirmButtonText: '查询',
        target: isFullscreen ? '#kg-fullscreen-container' : 'body',
        preConfirm: (value) => {
            if (!value) {
                Swal.showValidationMessage('请输入节点名称');
                return false;
            }
            return value;
        }
    }).then(result => {
        if (result.isConfirmed && result.value) {
            executeKGSearch(result.value);
        }
    });
}

function showMultiHopQuery() {
    Swal.fire({
        title: '多跳查询',
        html: `
            <input type="text" id="sourceNode" class="swal2-input" placeholder="源节点名称">
            <input type="text" id="targetNode" class="swal2-input" placeholder="目标节点名称">
            <input type="number" id="hopCount" class="swal2-input" placeholder="跳数 (1-5)" min="1" max="5">
        `,
        showCancelButton: true,
        confirmButtonText: '查询',
        target: isFullscreen ? '#kg-fullscreen-container' : 'body',
        preConfirm: () => {
            const source = document.getElementById('sourceNode').value;
            const target = document.getElementById('targetNode').value;
            const hops = document.getElementById('hopCount').value;

            if (!source || !target || !hops) {
                Swal.showValidationMessage('请填写所有字段');
                return false;
            }
            return { source, target, hops: parseInt(hops) };
        }
    }).then(result => {
        if (result.isConfirmed) {
            executeMultiHopQuery(result.value.source, result.value.target, result.value.hops);
        }
    });
}


function showTripleQuery() {
    Swal.fire({
        title: '三元组查询',
        html: `
            <input type="text" id="headNode" class="swal2-input" placeholder="头节点 (可选)">
            <input type="text" id="relation" class="swal2-input" placeholder="关系类型 (可选)">
            <input type="text" id="tailNode" class="swal2-input" placeholder="尾节点 (可选)">
            <small style="display:block; margin-top:10px; color:#6c757d;">
                至少填写一个字段
            </small>
        `,
        showCancelButton: true,
        confirmButtonText: '查询',
        target: isFullscreen ? '#kg-fullscreen-container' : 'body',
        preConfirm: () => {
            const head = document.getElementById('headNode').value;
            const relation = document.getElementById('relation').value;
            const tail = document.getElementById('tailNode').value;

            if (!head && !relation && !tail) {
                Swal.showValidationMessage('请至少填写一个字段');
                return false;
            }
            return { head, relation, tail };
        }
    }).then(result => {
        if (result.isConfirmed) {
            executeTripleQuery(result.value);
        }
    });
}

// 三元组数量控制
function updateTripleCount(value) {
    document.getElementById('tripleCountValue').textContent = value;
    // 重新加载图谱数据
    refreshGraphWithLimit(parseInt(value));
}

function refreshGraphWithLimit(limit) {
    showLoading('正在重新加载图谱...');

    fetch(`/api/kg_data?limit=${limit}`)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.nodes) {
                renderGraph(data);
                showSuccess(`已加载 ${limit} 个三元组`);
            }
        })
        .catch(error => {
            hideLoading();
            showError('加载图谱失败: ' + error.message);
        });
}

// 布局控制
function changeLayout(layoutType) {
    if (!network) return;

    // 配置布局选项
    let options = {};
    switch(layoutType) {
        case 'hierarchical':
            options = {
                layout: {
                    hierarchical: {
                        enabled: true,
                        direction: 'UD',
                        sortMethod: 'directed'
                    }
                }
            };
            break;
        case 'circular':
            applyCircularLayout();
            return;
        case 'random':
            options = {
                layout: {
                    randomSeed: Math.floor(Math.random() * 1000)
                }
            };
            break;
        default: // forceAtlas2Based
            options = {
                physics: {
                    solver: 'forceAtlas2Based'
                }
            };
            break;
    }

    network.setOptions(options);
    network.stabilize();
}

function applyCircularLayout() {
    if (!network) return;

    const nodes = network.body.data.nodes.get();
    const nodeCount = nodes.length;
    const radius = 300;

    const positions = {};
    nodes.forEach((node, index) => {
        const angle = (2 * Math.PI * index) / nodeCount;
        positions[node.id] = {
            x: radius * Math.cos(angle),
            y: radius * Math.sin(angle)
        };
    });

    network.setData({
        nodes: network.body.data.nodes,
        edges: network.body.data.edges
    });

    // 手动设置位置
    Object.keys(positions).forEach(nodeId => {
        network.moveNode(nodeId, positions[nodeId].x, positions[nodeId].y);
    });
}

// 知识图谱可视化管理
let network = null;
let container = null;
let allNodes = [];
let allEdges = [];
let nodeColorMap = new Map();
let edgeColorMap = new Map();

// 预定义颜色调色板
const COLOR_PALETTE = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD',
    '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9', '#F8C471',
    '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2', '#F9E79F', '#AED6F1',
    '#A3E4D7', '#FAD7A0', '#E8DAEF', '#ABEBC6', '#F5B7B1', '#D6EAF8'
];

document.addEventListener('DOMContentLoaded', function() {
    console.log('知识图谱管理页面初始化');
    container = document.getElementById('kg-network-container');

    // 初始化图谱
    initKnowledgeGraph();

    // 绑定事件
    bindKGEvents();

    // 初始化搜索
    initSearch();
});

function initKnowledgeGraph() {
    // 立即加载真实数据
    refreshGraph();
}

function initSearch() {
    const searchInput = document.getElementById('searchNodes');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            filterGraph(searchTerm);
        });
    }
}

function filterGraph(searchTerm) {
    if (!searchTerm) {
        // 显示所有节点和边
        if (network) {
            network.setData({
                nodes: allNodes,
                edges: allEdges
            });
        }
        return;
    }

    // 过滤节点
    const filteredNodes = allNodes.filter(node =>
        node.label.toLowerCase().includes(searchTerm) ||
        node.title.toLowerCase().includes(searchTerm)
    );

    // 获取过滤后节点的ID
    const visibleNodeIds = new Set(filteredNodes.map(node => node.id));

    // 过滤边：只显示连接可见节点的边
    const filteredEdges = allEdges.filter(edge =>
        visibleNodeIds.has(edge.from) && visibleNodeIds.has(edge.to)
    );

    // 更新网络
    if (network) {
        network.setData({
            nodes: filteredNodes,
            edges: filteredEdges
        });

        // 调整视图以适应过滤后的内容
        setTimeout(() => {
            network.fit({ animation: true });
        }, 300);
    }
}

function bindKGEvents() {
    // 处理文本按钮
    document.getElementById('kg-process-btn').addEventListener('click', processKGText);

    // 刷新按钮
    document.getElementById('kg-refresh').addEventListener('click', function() {
        this.innerHTML = '<i class="fas fa-sync fa-spin"></i> 刷新中...';
        refreshGraph();
        setTimeout(() => {
            this.innerHTML = '<i class="fas fa-sync"></i> 刷新图谱';
        }, 1000);
    });

    // 导出按钮
    document.getElementById('kg-export').addEventListener('click', exportKGData);

    // 控制按钮
    document.getElementById('zoom-in').addEventListener('click', function() {
        if (network) network.moveTo({scale: network.getScale() * 1.3});
    });

    document.getElementById('zoom-out').addEventListener('click', function() {
        if (network) network.moveTo({scale: network.getScale() / 1.3});
    });

    document.getElementById('reset-view').addEventListener('click', function() {
        if (network) {
            network.fit({ animation: true });
            network.stabilize();
        }
    });

    document.getElementById('fit-view').addEventListener('click', function() {
        if (network) {
            network.fit({ animation: true });
        }
    });
}

// 从Neo4j获取真实数据并渲染
function refreshGraph() {
    showLoading('正在加载知识图谱数据...');

    fetch('/api/kg_data')
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应异常: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            hideLoading();
            processGraphData(data);
            renderGraph(data);
            updateStats(data);
        })
        .catch(error => {
            hideLoading();
            console.error('加载知识图谱失败:', error);
            showError('加载知识图谱失败: ' + error.message);

            // 显示空状态
            showEmptyGraphState();
        });
}

function processGraphData(data) {
    if (!data || !data.nodes) return;

    // 重置颜色映射
    nodeColorMap.clear();
    edgeColorMap.clear();

    // 处理节点颜色
    data.nodes.forEach((node, index) => {
        const nodeType = node.type || '默认';
        if (!nodeColorMap.has(nodeType)) {
            // 为新的节点类型分配颜色
            const colorIndex = nodeColorMap.size % COLOR_PALETTE.length;
            nodeColorMap.set(nodeType, COLOR_PALETTE[colorIndex]);
        }
    });

    // 处理边颜色
    if (data.links) {
        data.links.forEach(link => {
            const edgeType = link.type || '相关';
            if (!edgeColorMap.has(edgeType)) {
                // 为新的关系类型分配颜色（使用较暗的颜色）
                const colorIndex = edgeColorMap.size % COLOR_PALETTE.length;
                const baseColor = COLOR_PALETTE[colorIndex];
                edgeColorMap.set(edgeType, darkenColor(baseColor, 0.2));
            }
        });
    }
}

function darkenColor(color, amount) {
    // 简单的颜色变暗函数
    const hex = color.replace('#', '');
    const num = parseInt(hex, 16);
    const amt = Math.round(2.55 * amount * 100);
    const R = (num >> 16) - amt;
    const G = (num >> 8 & 0x00FF) - amt;
    const B = (num & 0x0000FF) - amt;
    return '#' + (
        0x1000000 +
        (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
        (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
        (B < 255 ? B < 1 ? 0 : B : 255)
    ).toString(16).slice(1);
}

// 渲染图谱
function renderGraph(data) {
    if (!container) {
        console.error('图谱容器未找到');
        return;
    }

    // 清除现有图谱
    if (network) {
        network.destroy();
        network = null;
    }

    // 检查数据是否为空
    if (!data || !data.nodes || data.nodes.length === 0) {
        showEmptyGraphState();
        return;
    }

    try {
        // 创建节点数据集
        const nodes = new vis.DataSet(data.nodes.map(node => {
            const nodeType = node.type || '默认';
            const nodeColor = nodeColorMap.get(nodeType) || '#B0B0B0';

            return {
                id: node.id,
                label: node.name.length > 20 ? node.name.substring(0, 20) + '...' : node.name,
                title: `
                    <div class="node-tooltip">
                        <strong>${node.name}</strong><br/>
                        类型: ${nodeType}<br/>
                        ID: ${node.id}
                    </div>
                `,
                color: {
                    background: nodeColor,
                    border: darkenColor(nodeColor, 0.3),
                    highlight: {
                        background: lightenColor(nodeColor, 0.2),
                        border: '#48dbfb'
                    },
                    hover: {
                        background: lightenColor(nodeColor, 0.1),
                        border: '#48dbfb'
                    }
                },
                shape: 'dot',
                size: calculateNodeSize(node),
                font: {
                    color: '#ffffff',
                    size: 14,
                    face: 'Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif',
                    strokeWidth: 3,
                    strokeColor: 'rgba(0, 0, 0, 0.7)'
                },
                borderWidth: 2,
                shadow: true,
                mass: 1.5,
                physics: true,
                type: nodeType,
                originalData: node
            };
        }));

        // 创建边数据集
        const edges = new vis.DataSet(data.links.map(link => {
            const edgeType = link.type || '相关';
            const edgeColor = edgeColorMap.get(edgeType) || 'rgba(255, 255, 255, 0.6)';

            return {
                id: `${link.source}-${link.target}-${link.type}`,
                from: link.source,
                to: link.target,
                label: edgeType.length > 15 ? edgeType.substring(0, 15) + '...' : edgeType,
                arrows: 'to',
                color: {
                    color: edgeColor,
                    highlight: '#48dbfb',
                    opacity: 0.8
                },
                font: {
                    color: '#ffffff',
                    size: 11,
                    face: 'Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif',
                    strokeWidth: 2,
                    strokeColor: 'rgba(26, 26, 46, 0.8)'
                },
                smooth: {
                    type: 'cubicBezier',
                    roundness: 0.2
                },
                width: 2 + (Math.random() * 2), // 随机宽度增加视觉层次
                shadow: true,
                length: 200,
                physics: true,
                type: edgeType,
                originalData: link
            };
        }));

        // 保存所有节点和边用于搜索过滤
        allNodes = nodes.get();
        allEdges = edges.get();

        const graphData = { nodes, edges };

        // 配置选项
        const options = {
            physics: {
                enabled: true,
                stabilization: {
                    iterations: 100
                },
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springConstant: 0.08,
                    springLength: 100,
                    damping: 0.4
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: false,
                hideNodesOnDrag: false,
                navigationButtons: true,
                keyboard: {
                    enabled: true,
                    speed: { x: 10, y: 10, zoom: 0.02 }
                }
            },
            nodes: {
                shape: 'dot',
                font: {
                    size: 14,
                    face: 'Segoe UI'
                },
                borderWidth: 2,
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.5)',
                    size: 10,
                    x: 5,
                    y: 5
                }
            },
            edges: {
                width: 2,
                smooth: {
                    type: 'continuous',
                    roundness: 0.5
                },
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.3)',
                    size: 5,
                    x: 3,
                    y: 3
                },
                selectionWidth: 4
            },
            layout: {
                improvedLayout: true,
                hierarchical: {
                    enabled: false
                }
            },
            groups: {
                useDefaultGroups: false
            }
        };

        // 创建网络
        network = new vis.Network(container, graphData, options);


    // 添加节点点击事件
    network.on('selectNode', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            showNodeDetails(node);
        }
    });

    // 添加关系点击事件
    network.on('selectEdge', function(params) {
        if (params.edges.length > 0) {
            const edgeId = params.edges[0];
            const edge = edges.get(edgeId);
            showEdgeDetails(edge);
        }
    });

    // 移除 hover 事件（不再显示临时卡片）
    // network.on("hoverNode", function(params) { ... }); // 已删除
    // network.on("hoverEdge", function(params) { ... }); // 已删除
    // network.on("blurNode", function(params) { ... }); // 已删除
    // network.on("blurEdge", function(params) { ... }); // 已删除

        network.on('afterDrawing', function(ctx) {
            // 可选的后期绘制效果
        });

        // 生成动态图例
        generateDynamicLegend();

    } catch (error) {
        console.error('渲染知识图谱失败:', error);
        container.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>渲染失败</h3>
                <p>${error.message}</p>
                <button class="btn btn-outline" onclick="refreshGraph()">
                    <i class="fas fa-redo"></i> 重试
                </button>
            </div>
        `;
    }
}

function calculateNodeSize(node) {
    // 根据节点重要性或类型计算大小
    const baseSize = 20;
    const typeMultipliers = {
        '疾病': 1.4,
        '药物': 1.3,
        '症状': 1.2,
        '治疗': 1.3,
        '检查': 1.1,
        '默认': 1.0
    };

    const multiplier = typeMultipliers[node.type] || 1.0;
    return baseSize * multiplier + (Math.random() * 8); // 添加一些随机变化
}

function lightenColor(color, amount) {
    // 简单的颜色变亮函数
    const hex = color.replace('#', '');
    const num = parseInt(hex, 16);
    const amt = Math.round(2.55 * amount * 100);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return '#' + (
        0x1000000 +
        (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
        (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
        (B < 255 ? B < 1 ? 0 : B : 255)
    ).toString(16).slice(1);
}

function highlightConnectedNodes(nodeId) {
    if (!network) return;

    const connectedEdges = network.getConnectedEdges(nodeId);
    const connectedNodes = new Set();

    connectedEdges.forEach(edgeId => {
        const edge = allEdges.find(e => e.id === edgeId);
        if (edge) {
            connectedNodes.add(edge.from);
            connectedNodes.add(edge.to);
        }
    });

    // 可以在这里实现高亮效果
}

function unhighlightAllNodes() {
    // 取消所有高亮
}

function generateDynamicLegend() {
    const legendContainer = document.getElementById('dynamic-legend');
    if (!legendContainer) return;

    let legendHTML = '<div class="legend-section"><h4>实体类型</h4>';

    // 添加节点类型图例
    nodeColorMap.forEach((color, type) => {
        legendHTML += `
            <div class="legend-item">
                <span class="color-dot" style="background-color: ${color}"></span>
                <span class="legend-label">${type}</span>
                <span class="legend-count">(${countNodesByType(type)})</span>
            </div>
        `;
    });

    legendHTML += '</div><div class="legend-section"><h4>关系类型</h4>';

    // 添加关系类型图例
    edgeColorMap.forEach((color, type) => {
        legendHTML += `
            <div class="legend-item">
                <span class="color-line" style="background-color: ${color}"></span>
                <span class="legend-label">${type}</span>
                <span class="legend-count">(${countEdgesByType(type)})</span>
            </div>
        `;
    });

    legendHTML += '</div>';
    legendContainer.innerHTML = legendHTML;
}

function countNodesByType(type) {
    return allNodes.filter(node => node.type === type).length;
}

function countEdgesByType(type) {
    return allEdges.filter(edge => edge.type === type).length;
}

function showNodeDetails(node) {
    const panel = document.getElementById('nodeDetailsPanel');
    const content = document.getElementById('nodeDetailsContent');

    if (!panel || !content) return;

    // 从图数据库获取最新属性
    fetch(`/api/entity_config/node/${node.id}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const properties = data.node.properties || {};
                const propsCount = Object.keys(properties).length;

                // 构建标签页结构
                let propsHtml = '';
                if (propsCount === 0) {
                    propsHtml = '<div class="no-properties">暂无属性</div>';
                } else {
                    const tabs = Object.keys(properties);
                    propsHtml = `
                        <div class="property-tabs">
                            <div class="tab-nav">
                                ${tabs.map((key, idx) => `
                                    <button class="tab-nav-btn ${idx === 0 ? 'active' : ''}"
                                            data-tab="prop-${idx}">
                                        ${key.substring(0, 10)}${key.length > 10 ? '...' : ''}
                                    </button>
                                `).join('')}
                            </div>
                            <div class="tab-content-wrapper">
                                ${tabs.map((key, idx) => `
                                    <div class="tab-pane ${idx === 0 ? 'active' : ''}" id="prop-${idx}">
                                        <div class="property-item">
                                            <span class="property-key">${key}:</span>
                                            <span class="property-value" title="${properties[key]}">${properties[key]}</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }

                content.innerHTML = `
                    <div class="node-info">
                        <h4>${node.label}</h4>
                        <div class="info-grid">
                            <div class="info-item">
                                <label>类型</label>
                                <span>${node.type || '未知'}</span>
                            </div>
                            <div class="info-item">
                                <label>ID</label>
                                <span>${node.id}</span>
                            </div>
                        </div>
                    </div>
                    <div class="properties-section">
                        <h5>属性列表 (${propsCount})</h5>
                        ${propsHtml}
                    </div>
                `;

                bindPropertyTabs();

                // 设置面板样式 - 缩小版
                panel.style.display = 'block';
                panel.style.position = 'absolute';
                panel.style.top = '20px';
                panel.style.right = '20px';
                panel.style.width = '320px';  // 缩小到320px
                panel.style.maxHeight = '70vh'; // 缩小到70vh
                panel.style.zIndex = '10';
                panel.style.background = 'rgba(255, 255, 255, 0.95)';
                panel.style.backdropFilter = 'blur(15px)';
                panel.style.border = '1px solid rgba(0, 0, 0, 0.1)';
                panel.style.borderRadius = '12px';
                panel.style.padding = '20px';
                panel.style.overflow = 'hidden';
                panel.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.2)';
                panel.style.fontSize = '13px'; // 缩小字体
            }
        });
}

function showEdgeDetails(edge) {
    const panel = document.getElementById('nodeDetailsPanel');
    const content = document.getElementById('nodeDetailsContent');
    const sourceNode = allNodes.find(n => n.id === edge.from);
    const targetNode = allNodes.find(n => n.id === edge.to);

    Swal.fire({
        title: '关系详情',
        html: `
            <div style="text-align: left;">
                <p><strong>关系类型:</strong> ${edge.type}</p>
                <p><strong>源节点:</strong> ${sourceNode?.label || edge.from}</p>
                <p><strong>目标节点:</strong> ${targetNode?.label || edge.to}</p>
                <p><strong>关系ID:</strong> ${edge.id}</p>
            </div>
        `,
        background: 'rgba(26, 26, 46, 0.95)',
        color: '#fff',
        confirmButtonColor: '#48dbfb',
        width: '500px'
    });
}

function closeNodeDetails() {
    const panel = document.getElementById('nodeDetailsPanel');
    if (panel) {
        panel.style.display = 'none';
    }
}

function showEmptyGraphState() {
    container.innerHTML = `
        <div class="empty-graph-message">
            <i class="fas fa-project-diagram"></i>
            <h3>知识图谱为空</h3>
            <p>请添加医学文本以构建知识图谱</p>
            <button class="btn btn-primary" onclick="document.getElementById('kg-text-input').focus()">
                <i class="fas fa-plus"></i> 开始添加
            </button>
        </div>
    `;

    // 更新统计信息
    updateStats({ nodes: [], links: [] });
}

// 处理文本输入
function processKGText() {
    const textInput = document.getElementById('kg-text-input');
    const text = textInput.value.trim();

    if (!text) {
        showWarning('请输入要分析的文本内容');
        textInput.focus();
        return;
    }

    showLoading('正在分析文本并更新知识图谱...');

    fetch('/api/process_kg_text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text })
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
            showSuccess('知识图谱更新成功！');
            textInput.value = ''; // 清空输入框
            refreshGraph(); // 刷新图谱显示
        } else {
            throw new Error(result.message || '处理失败');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('处理文本失败:', error);
        showError('处理文本失败: ' + error.message);
    });
}

// 更新统计信息
function updateStats(data) {
    const entityCount = document.getElementById('entity-count');
    const relationCount = document.getElementById('relation-count');

    if (entityCount) {
        entityCount.textContent = data.nodes ? data.nodes.length : 0;
    }
    if (relationCount) {
        relationCount.textContent = data.links ? data.links.length : 0;
    }
}

// 导出功能
function exportKGData() {
    const data = {
        nodes: allNodes,
        edges: allEdges,
        exportTime: new Date().toISOString(),
        statistics: {
            totalNodes: allNodes.length,
            totalEdges: allEdges.length,
            nodeTypes: Array.from(nodeColorMap.keys()),
            edgeTypes: Array.from(edgeColorMap.keys())
        }
    };

    const dataStr = JSON.stringify(data, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});

    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `knowledge_graph_${new Date().toISOString().split('T')[0]}.json`;
    link.click();

    showSuccess('数据导出成功！');
}

// 图查询功能
function kgQuery(type) {
    const promptMap = {
        path: "请输入源节点和目标节点名称（用逗号分隔）：",
        centrality: "正在计算节点中心性...",
        search: "请输入搜索关键词："
    };

    Swal.fire({
        title: '知识图谱查询',
        input: type === 'centrality' ? null : 'text',
        inputLabel: promptMap[type],
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#fff',
        confirmButtonColor: '#48dbfb',
        showCancelButton: true,
        confirmButtonText: '查询',
        cancelButtonText: '取消'
    }).then((result) => {
        if (result.isConfirmed && (type === 'centrality' || result.value)) {
            executeKGQuery(type, result.value);
        }
    });
}

function executeKGQuery(type, value) {
    let url = '';
    let params = {};

    switch(type) {
        case 'path':
            const [source, target] = value.split(',').map(s => s.trim());
            url = `/api/kg_path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`;
            break;
        case 'centrality':
            url = '/api/kg_centrality';
            break;
        case 'search':
            url = `/api/kg_search?q=${encodeURIComponent(value)}`;
            break;
    }

    showLoading('正在执行查询...');

    fetch(url)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.error) {
                showError('查询失败: ' + data.error);
            } else {
                handleQueryResult(type, data);
            }
        })
        .catch(error => {
            hideLoading();
            showError('查询失败: ' + error.message);
        });
}

function handleQueryResult(type, data) {
    switch(type) {
        case 'path':
            if (data.path && data.path.length > 0) {
                showSuccess(`找到路径，包含 ${data.path.length} 个节点`);
                highlightPath(data.path);
            } else {
                showInfo('未找到路径');
            }
            break;
        case 'centrality':
            const topNodes = Object.entries(data).slice(0, 5);
            let message = '中心性最高的节点：\n';
            topNodes.forEach(([node, score], index) => {
                message += `${index + 1}. ${node}: ${score.toFixed(4)}\n`;
            });
            showInfo(message);
            break;
        case 'search':
            if (data.nodes && data.nodes.length > 0) {
                showSuccess(`找到 ${data.nodes.length} 个相关节点`);
                // 可以渲染搜索结果子图
                renderGraph(data);
            } else {
                showInfo('未找到相关节点');
            }
            break;
    }
}

function highlightPath(path) {
    if (!network) return;

    // 高亮显示路径中的节点和边
    const nodeIds = path.map(node => node.id);
    const edgeIds = [];

    for (let i = 0; i < path.length - 1; i++) {
        const edge = allEdges.find(e =>
            (e.from === path[i].id && e.to === path[i+1].id) ||
            (e.from === path[i+1].id && e.to === path[i].id)
        );
        if (edge) edgeIds.push(edge.id);
    }

    network.selectNodes(nodeIds);
    network.selectEdges(edgeIds);
}

// 工具函数
function showLoading(message) {
    const loadingModal = document.getElementById('loadingModal');
    if (loadingModal) {
        loadingModal.querySelector('h3').textContent = message;
        loadingModal.style.display = 'flex';
    }
}

function hideLoading() {
    const loadingModal = document.getElementById('loadingModal');
    if (loadingModal) {
        loadingModal.style.display = 'none';
    }
}

function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: '成功',
        text: message,
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#fff',
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
        color: '#fff',
        confirmButtonColor: '#48dbfb'
    });
}

function showWarning(message) {
    Swal.fire({
        icon: 'warning',
        title: '提示',
        text: message,
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#fff',
        confirmButtonColor: '#48dbfb'
    });
}

function showInfo(message) {
    Swal.fire({
        icon: 'info',
        title: '信息',
        text: message,
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#fff',
        confirmButtonColor: '#48dbfb'
    });
}

function executeKGSearch(keyword) {
    showLoading('正在搜索节点...');

    fetch(`/api/kg_search?q=${encodeURIComponent(keyword)}`)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.nodes && data.nodes.length > 0) {
                // 高亮显示搜索结果
                network.selectNodes(data.nodes.map(n => n.id));
                network.focus(data.nodes[0].id, { scale: 1.5 });
                showSuccess(`找到 ${data.nodes.length} 个相关节点`);
            } else {
                showInfo('未找到相关节点');
            }
        })
        .catch(error => {
            hideLoading();
            showError('搜索失败: ' + error.message);
        });
}

function executeMultiHopQuery(source, target, hops) {
    showLoading('正在执行多跳查询...');

    fetch(`/api/kg_path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}&hops=${hops}`)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.path && data.path.length > 0) {
                // 高亮路径
                const nodeIds = data.path.map(p => p.id);
                network.selectNodes(nodeIds);
                network.selectEdges(data.edges || []);
                network.focus(nodeIds[0], { scale: 1.2 });
                showSuccess(`找到路径，共 ${data.path.length} 个节点`);
            } else {
                showInfo('未找到路径');
            }
        })
        .catch(error => {
            hideLoading();
            showError('查询失败: ' + error.message);
        });
}

function executeTripleQuery(query) {
    showLoading('正在执行三元组查询...');

    const params = new URLSearchParams();
    if (query.head) params.append('head', query.head);
    if (query.relation) params.append('relation', query.relation);
    if (query.tail) params.append('tail', query.tail);

    fetch(`/api/kg_triple?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.nodes && data.nodes.length > 0) {
                renderGraph(data);
                showSuccess(`找到 ${data.nodes.length} 个节点和 ${data.links.length} 条关系`);
            } else {
                showInfo('未找到匹配的三元组');
            }
        })
        .catch(error => {
            hideLoading();
            showError('查询失败: ' + error.message);
        });
}

// 标签页切换事件
function bindPropertyTabs() {
    const tabButtons = document.querySelectorAll('.tab-nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // 移除所有active类
            tabButtons.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            // 激活当前标签
            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });
}

// SweetAlert2容器样式修复
const style = document.createElement('style');
style.textContent = `
    .kg-swal-popup {
        z-index: 10000 !important;
    }
    body.kg-fullscreen-active {
        overflow: hidden !important;
    }
`;
document.head.appendChild(style);