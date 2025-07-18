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

    function renderGraph(data) {
        if (network) network.destroy();
        if (!data || data.nodes.length === 0) {
            container.innerHTML = '<div class="empty-graph-message"><i class="fas fa-project-diagram"></i><h3>知识图谱为空</h3><p>请添加医学文本以构建知识图谱</p></div>';
            return;
        }
        const nodes = new vis.DataSet(data.nodes.map(n => ({
            id: n.id, label: n.name, title: `${n.type}: ${n.name}`,
            color: { background: typeColors[n.type] || typeColors["默认"] }, shape: 'dot', size: 20
        })));
        const edges = new vis.DataSet(data.links.map(l => ({
            from: l.source, to: l.target, label: l.type, arrows: 'to'
        })));
        network = new vis.Network(container, { nodes, edges }, {
            physics: { barnesHut: { gravitationalConstant: -3000, springLength: 150 } },
            interaction: { hover: true }
        });
    }

    function refreshGraph() {
        fetch('/api/kg_data').then(r => r.json()).then(renderGraph);
    }

    document.getElementById('kg-process-btn').addEventListener('click', async () => {
        const text = document.getElementById('kg-text-input').value.trim();
        if (!text) return alert('请输入文本');
        const toast = Swal.mixin({ toast: true, position: 'top-end', showConfirmButton: false, timer: 3000 });
        toast.fire({ icon: 'info', title: '后台更新中...' });
        await fetch('/api/async_update_kg', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
        const poll = setInterval(async () => {
            const res = await fetch('/api/kg_status');
            const data = await res.json();
            if (data.status === 'done') {
                clearInterval(poll); toast.fire({ icon: 'success', title: data.msg }); refreshGraph();
            } else if (data.status === 'error') {
                clearInterval(poll); toast.fire({ icon: 'error', title: data.msg });
            }
        }, 1000);
    });

    document.getElementById('kg-refresh').addEventListener('click', refreshGraph);

    function kgQuery(type) {
        const promptMap = { path: "请输入源节点和目标节点，用逗号分隔：", centrality: "正在计算中心性...", search: "请输入查询关键词：" };
        const input = prompt(promptMap[type]);
        if (!input) return;
        fetch(`/api/kg_${type}?q=${encodeURIComponent(input)}`).then(r => r.json()).then(data => {
            if (data.error) return alert(data.error);
            if (data.nodes) renderGraph(data); else alert(JSON.stringify(data, null, 2));
        });
    }

    refreshGraph();
});