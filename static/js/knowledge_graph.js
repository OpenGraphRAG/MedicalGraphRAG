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

        // 添加交互事件
        network.on('hoverNode', function(params) {
            container.style.cursor = 'pointer';
            highlightConnectedNodes(params.node);
        });

        network.on('blurNode', function(params) {
            container.style.cursor = 'default';
            unhighlightAllNodes();
        });

        network.on('selectNode', function(params) {
            console.log('选中节点:', params.nodes);
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                showNodeDetails(node);
            }
        });

        network.on('doubleClick', function(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                showNodeDetails(node);
            } else if (params.edges.length > 0) {
                const edgeId = params.edges[0];
                const edge = edges.get(edgeId);
                showEdgeDetails(edge);
            }
        });

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
        (R < 255 ? R : 255) * 0x10000 +
        (G < 255 ? G : 255) * 0x100 +
        (B < 255 ? B : 255)
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
                <div class="info-item full-width">
                    <label>完整名称</label>
                    <span>${node.originalData?.name || node.label}</span>
                </div>
            </div>
        </div>
        <div class="connected-info">
            <h5>关联关系</h5>
            <div class="relations-list">
                ${getNodeRelations(node.id)}
            </div>
        </div>
    `;

    panel.style.display = 'block';
}

function getNodeRelations(nodeId) {
    const connectedEdges = allEdges.filter(edge =>
        edge.from === nodeId || edge.to === nodeId
    );

    if (connectedEdges.length === 0) {
        return '<div class="no-relations">暂无关联关系</div>';
    }

    let html = '';
    connectedEdges.forEach(edge => {
        const isOutgoing = edge.from === nodeId;
        const targetNodeId = isOutgoing ? edge.to : edge.from;
        const targetNode = allNodes.find(n => n.id === targetNodeId);
        const direction = isOutgoing ? '→' : '←';

        if (targetNode) {
            html += `
                <div class="relation-item">
                    <span class="relation-direction">${direction}</span>
                    <span class="relation-type">${edge.type}</span>
                    <span class="relation-target">${targetNode.label}</span>
                </div>
            `;
        }
    });

    return html;
}

function showEdgeDetails(edge) {
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