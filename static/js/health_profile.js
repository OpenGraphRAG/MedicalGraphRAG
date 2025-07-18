document.addEventListener('DOMContentLoaded', function() {
    // 时间线滚动效果
    const timelineContainer = document.querySelector('.timeline-container');
    if (timelineContainer) {
        timelineContainer.scrollTop = timelineContainer.scrollHeight;
    }

    // 表格行悬停效果
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = 'rgba(44, 127, 184, 0.03)';
        });

        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
});
document.addEventListener('DOMContentLoaded', function() {
    // 时间线滚动效果
    const timelineContainer = document.querySelector('.timeline-container');
    if (timelineContainer) {
        timelineContainer.scrollTop = timelineContainer.scrollHeight;
    }

    // 表格行悬停效果
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = 'rgba(44, 127, 184, 0.03)';
        });

        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });

    // 自动刷新功能
    let refreshInterval;
    const autoRefreshToggle = document.getElementById('autoRefreshToggle');
    const manualRefreshBtn = document.getElementById('manualRefreshBtn');

    function refreshData() {
        // 显示加载指示器
        document.body.classList.add('refreshing');

        // 模拟数据刷新
        setTimeout(() => {
            location.reload();
        }, 500);
    }

    // 初始化自动刷新
    function initAutoRefresh() {
        if (autoRefreshToggle.checked) {
            refreshInterval = setInterval(refreshData, 30000); // 30秒刷新一次
        }
    }

    // 切换自动刷新
    if (autoRefreshToggle) {
        autoRefreshToggle.addEventListener('change', function() {
            if (this.checked) {
                initAutoRefresh();
            } else {
                clearInterval(refreshInterval);
            }
        });

        // 初始化
        initAutoRefresh();
    }

    // 手动刷新按钮
    if (manualRefreshBtn) {
        manualRefreshBtn.addEventListener('click', refreshData);
    }
});