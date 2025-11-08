/* 赛博健康画像 - 动效脚本 */
document.addEventListener('DOMContentLoaded', () => {
  // 自动滚动时间线到底部
  const timeline = document.querySelector('.timeline');
  if (timeline) timeline.scrollTop = timeline.scrollHeight;

  // 表格行悬停霓虹
  document.querySelectorAll('tbody tr').forEach(row => {
    row.addEventListener('mouseenter', () => row.classList.add('hover-glow'));
    row.addEventListener('mouseleave', () => row.classList.remove('hover-glow'));
  });

  // 自动刷新 & 手动刷新
  const toggle = document.getElementById('autoRefreshToggle');
  const btn    = document.getElementById('manualRefreshBtn');
  let timer;

  const refresh = () => {
    document.body.classList.add('refreshing');
    setTimeout(() => location.reload(), 600);
  };

  const startAuto = () => {
    clearInterval(timer);
    timer = setInterval(refresh, 30000);
  };

  const stopAuto = () => clearInterval(timer);

  toggle.addEventListener('change', () => toggle.checked ? startAuto() : stopAuto());
  btn.addEventListener('click', refresh);

  toggle.checked && startAuto();
});
// 健康指标分页和筛选功能
let currentPage = 1;
let currentStartDate = '';
let currentEndDate = '';

// 加载健康指标数据
function loadHealthMetrics(page = 1, startDate = '', endDate = '') {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const metricsBody = document.getElementById('metricsBody');
    const pagination = document.getElementById('pagination');

    // 显示加载状态
    loadingIndicator.style.display = 'block';
    metricsBody.innerHTML = '';
    pagination.innerHTML = '';

    // 构建查询参数
    const params = new URLSearchParams({
        page: page
    });

    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    fetch(`/api/health_metrics?${params}`)
        .then(response => response.json())
        .then(data => {
            loadingIndicator.style.display = 'none';

            if (data.metrics && data.metrics.length > 0) {
                // 渲染表格数据
                renderMetricsTable(data.metrics);
                // 渲染分页控件
                renderPagination(data.pagination);
            } else {
                metricsBody.innerHTML = `
                    <tr>
                        <td colspan="6" style="text-align: center; padding: 40px; color: var(--text-dim);">
                            <i class="fas fa-inbox"></i><br>
                            暂无健康指标数据
                        </td>
                    </tr>
                `;
            }
        })
        .catch(error => {
            console.error('加载健康指标失败:', error);
            loadingIndicator.style.display = 'none';
            metricsBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 40px; color: var(--secondary);">
                        <i class="fas fa-exclamation-triangle"></i><br>
                        加载失败，请重试
                    </td>
                </tr>
            `;
        });
}

// 渲染表格数据
function renderMetricsTable(metrics) {
    const metricsBody = document.getElementById('metricsBody');

    metricsBody.innerHTML = metrics.map(metric => `
        <tr>
            <td>${metric.item}</td>
            <td>${metric.result}</td>
            <td>${metric.reference_range}</td>
            <td>${metric.unit}</td>
            <td>${metric.date}</td>
            <td><span class="status ${metric.status}">${metric.status === 'normal' ? '正常' : '异常'}</span></td>
        </tr>
    `).join('');
}

// 渲染分页控件
function renderPagination(pagination) {
    const paginationEl = document.getElementById('pagination');
    const { current_page, total_pages, total_items } = pagination;

    if (total_pages <= 1) return;

    let paginationHTML = '';

    // 上一页按钮
    if (current_page > 1) {
        paginationHTML += `
            <button class="page-btn" onclick="changePage(${current_page - 1})">
                <i class="fas fa-chevron-left"></i>
            </button>
        `;
    }

    // 页码按钮
    for (let i = 1; i <= total_pages; i++) {
        if (i === current_page) {
            paginationHTML += `
                <button class="page-btn active">${i}</button>
            `;
        } else {
            paginationHTML += `
                <button class="page-btn" onclick="changePage(${i})">${i}</button>
            `;
        }
    }

    // 下一页按钮
    if (current_page < total_pages) {
        paginationHTML += `
            <button class="page-btn" onclick="changePage(${current_page + 1})">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;
    }

    // 添加总数信息
    paginationHTML += `
        <span style="margin-left: 15px; font-size: 0.9rem;">
            共 ${total_items} 条记录
        </span>
    `;

    paginationEl.innerHTML = paginationHTML;
}

// 切换页码
function changePage(page) {
    currentPage = page;
    loadHealthMetrics(page, currentStartDate, currentEndDate);
    // 滚动到表格位置
    document.getElementById('metricsTable').scrollIntoView({ behavior: 'smooth' });
}

// 应用筛选
function applyFilter() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    // 验证日期范围
    if (startDate && endDate && startDate > endDate) {
        alert('开始日期不能晚于结束日期');
        return;
    }

    currentStartDate = startDate;
    currentEndDate = endDate;
    currentPage = 1;

    loadHealthMetrics(1, startDate, endDate);
}

// 重置筛选
function resetFilter() {
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    currentStartDate = '';
    currentEndDate = '';
    currentPage = 1;

    loadHealthMetrics(1);
}

// 在DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 原有的代码...

    // 初始化健康指标加载
    setTimeout(() => {
        loadHealthMetrics(1);
    }, 100);

    // 绑定筛选按钮事件
    const filterBtn = document.getElementById('filterBtn');
    const resetFilterBtn = document.getElementById('resetFilterBtn');

    if (filterBtn) {
        filterBtn.addEventListener('click', applyFilter);
    }
    if (resetFilterBtn) {
        resetFilterBtn.addEventListener('click', resetFilter);
    }

    // 添加分页按钮样式
    const style = document.createElement('style');
    style.textContent = `
        .page-btn {
            background: var(--glass);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 8px 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            margin: 0 2px;
        }
        .page-btn:hover {
            border-color: var(--primary);
            color: var(--primary);
        }
        .page-btn.active {
            background: var(--primary);
            color: var(--bg);
            border-color: var(--primary);
        }
        .filter-input:focus {
            outline: none;
            border-color: var(--primary) !important;
            box-shadow: 0 0 5px var(--primary);
        }
    `;
    document.head.appendChild(style);
});