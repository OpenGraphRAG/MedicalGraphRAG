document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('kg-network-container');
    let network = null;
    const typeColors = {
        "人物": "#FF9AA2", "医生": "#FF9AA2", "患者": "#FF9AA2", "专家": "#FF9AA2",
        "组织": "#FFB7B2", "医院": "#FFB7B2", "科室": "#FFB7B2", "机构": "#FFB7B2",
        "地点": "#FFDAC1", "城市": "#FFDAC1", "国家": "#FFDAC1", "区域": "#FFDAC1",
        "事件": "#E2F0CB", "手术": "#E2F0CB", "治疗": "#E2F0CB", "诊断": "#E2F0CB",
        "概念": "#B5EAD7", "理论": "#B5EAD7", "原理": "#B5EAD7", "定义": "#B5EAD7",
        "技术": "#C7CEEA", "方法": "#C7CEEA", "疗法": "#C7CEEA", "技术": "#C7CEEA",
        "疾病": "#9A7FAE", "症状": "#9A7FAE", "综合征": "#9A7FAE", "病症": "#9A7FAE",
        "药物": "#6A9C78", "药品": "#6A9C78", "化合物": "#6A9C78", "药剂": "#6A9C78",
        "默认": "#B0B0B0"
    };

    // 模拟数据
    const sampleData = {
        nodes: [
            {id: 1, name: "维生素C", type: "药物"},
            {id: 2, name: "免疫力", type: "概念"},
            {id: 3, name: "感冒", type: "疾病"},
            {id: 4, name: "抗氧化", type: "概念"},
            {id: 5, name: "皮肤健康", type: "概念"},
            {id: 6, name: "胶原蛋白", type: "概念"},
            {id: 7, name: "柑橘类水果", type: "概念"},
            {id: 8, name: "剂量", type: "概念"},
            {id: 9, name: "医生", type: "人物"},
            {id: 10, name: "患者", type: "人物"}
        ],
        links: [
            {source: 1, target: 2, type: "增强"},
            {source: 1, target: 3, type: "预防"},
            {source: 1, target: 4, type: "具有"},
            {source: 1, target: 5, type: "促进"},
            {source: 1, target: 6, type: "合成"},
            {source: 7, target: 1, type: "富含"},
            {source: 8, target: 1, type: "影响效果"},
            {source: 9, target: 10, type: "建议补充"},
            {source: 9, target: 1, type: "推荐"}
        ]
    };

    function renderGraph(data) {
        if (network) network.destroy();

        if (!data || data.nodes.length === 0) {
            container.innerHTML = `
                <div class="empty-graph-message">
                    <i class="fas fa-project-diagram"></i>
                    <h3>知识图谱为空</h3>
                    <p>请添加医学文本以构建知识图谱</p>
                    <button class="btn btn-outline" onclick="document.getElementById('kg-text-input').focus()">
                        <i class="fas fa-plus"></i> 开始添加
                    </button>
                </div>
            `;
            return;
        }

        const nodes = new vis.DataSet(data.nodes.map(n => ({
            id: n.id,
            label: n.name,
            title: `${n.type}: ${n.name}`,
            color: {
                background: typeColors[n.type] || typeColors["默认"],
                border: "#1a1a2e",
                highlight: {
                    background: typeColors[n.type] || typeColors["默认"],
                    border: "#3498db"
                }
            },
            shape: 'dot',
            size: 25,
            font: {color: '#fff', size: 14, face: 'Segoe UI'},
            borderWidth: 2,
            shadow: true
        })));

        const edges = new vis.DataSet(data.links.map(l => ({
            from: l.source,
            to: l.target,
            label: l.type,
            arrows: 'to',
            color: {color: 'rgba(255, 255, 255, 0.7)', highlight: '#48dbfb'},
            font: {color: '#fff', size: 12, face: 'Segoe UI', strokeWidth: 3, strokeColor: 'rgba(26, 26, 46, 0.8)'},
            smooth: {type: 'cubicBezier', roundness: 0.2},
            shadow: true
        })));

        const dataForVis = {nodes, edges};
        const options = {
            physics: {
                stabilization: true,
                barnesHut: {
                    gravitationalConstant: -2000,
                    springConstant: 0.04,
                    springLength: 150
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: false,
                hideNodesOnDrag: false
            },
            nodes: {
                shape: "dot",
                size: 30,
                font: {
                    size: 14,
                    face: "Segoe UI"
                }
            },
            edges: {
                width: 2,
                color: {
                    color: "rgba(255, 255, 255, 0.5)",
                    highlight: "#48dbfb"
                },
                smooth: {
                    type: "continuous"
                }
            },
            layout: {
                improvedLayout: true
            }
        };

        network = new vis.Network(container, dataForVis, options);

        // 添加交互效果
        network.on("hoverNode", function(params) {
            network.canvas.body.container.style.cursor = "pointer";
        });

        network.on("blurNode", function(params) {
            network.canvas.body.container.style.cursor = "default";
        });
    }

    function refreshGraph() {
        // 模拟API调用
        setTimeout(() => {
            renderGraph(sampleData);
            // 更新统计数据
            document.getElementById('entity-count').textContent = sampleData.nodes.length;
            document.getElementById('relation-count').textContent = sampleData.links.length;

            // 添加数字动画效果
            animateValue('entity-count', 0, sampleData.nodes.length, 1000);
            animateValue('relation-count', 0, sampleData.links.length, 1000);
        }, 500);
    }

    function animateValue(id, start, end, duration) {
        let obj = document.getElementById(id);
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    document.getElementById('kg-process-btn').addEventListener('click', async () => {
        const text = document.getElementById('kg-text-input').value.trim();
        if (!text) {
            Swal.fire({
                icon: 'warning',
                title: '请输入文本',
                text: '请在文本框中输入健康知识文本',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#fff',
                confirmButtonColor: '#48dbfb'
            });
            return;
        }

        // 显示加载动画
        const loadingModal = document.getElementById('loadingModal');
        loadingModal.style.display = 'flex';

        // 模拟处理过程
        setTimeout(() => {
            loadingModal.style.display = 'none';

            // 添加新节点和关系（模拟）
            const newNodeId = sampleData.nodes.length + 1;
            sampleData.nodes.push({id: newNodeId, name: "新实体", type: "概念"});
            sampleData.links.push({source: 1, target: newNodeId, type: "关联"});

            // 显示成功消息
            Swal.fire({
                icon: 'success',
                title: '图谱已更新',
                text: '已成功添加新实体和关系',
                background: 'rgba(26, 26, 46, 0.9)',
                color: '#fff',
                confirmButtonColor: '#48dbfb',
                timer: 2000
            });

            // 刷新图谱
            refreshGraph();
        }, 2000);
    });

    document.getElementById('kg-refresh').addEventListener('click', function() {
        this.innerHTML = '<i class="fas fa-sync fa-spin"></i> 刷新中...';
        refreshGraph();
        setTimeout(() => {
            this.innerHTML = '<i class="fas fa-sync"></i> 刷新图谱';
        }, 1000);
    });

    document.getElementById('kg-export').addEventListener('click', function() {
        Swal.fire({
            icon: 'info',
            title: '导出功能',
            text: '图谱导出功能即将推出',
            background: 'rgba(26, 26, 46, 0.9)',
            color: '#fff',
            confirmButtonColor: '#48dbfb'
        });
    });

    // 控制按钮功能
    document.getElementById('zoom-in').addEventListener('click', function() {
        if (network) {
            network.moveTo({scale: network.getScale() * 1.3});
        }
    });

    document.getElementById('zoom-out').addEventListener('click', function() {
        if (network) {
            network.moveTo({scale: network.getScale() / 1.3});
        }
    });

    document.getElementById('reset-view').addEventListener('click', function() {
        if (network) {
            network.fit();
            network.stabilize();
        }
    });

    // 初始化图谱
    refreshGraph();
});

function kgQuery(type) {
    const promptMap = {
        path: "请输入源节点和目标节点，用逗号分隔：",
        centrality: "正在计算中心性...",
        search: "请输入查询关键词："
    };

    Swal.fire({
        title: '知识图谱查询',
        input: 'text',
        inputLabel: promptMap[type],
        background: 'rgba(26, 26, 46, 0.9)',
        color: '#fff',
        confirmButtonColor: '#48dbfb',
        showCancelButton: true,
        confirmButtonText: '查询',
        cancelButtonText: '取消'
    }).then((result) => {
        if (result.isConfirmed && result.value) {
            // 模拟API调用
            setTimeout(() => {
                Swal.fire({
                    icon: 'info',
                    title: '查询结果',
                    text: `已执行 ${type} 查询: ${result.value}`,
                    background: 'rgba(26, 26, 46, 0.9)',
                    color: '#fff',
                    confirmButtonColor: '#48dbfb'
                });
            }, 1000);
        }
    });
}