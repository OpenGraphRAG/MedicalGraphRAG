/* 健康画像 - 辅助脚本 (主逻辑已内联到health_profile.html) */
document.addEventListener('DOMContentLoaded', () => {
  // 表格行悬停效果
  document.querySelectorAll('tbody tr').forEach(row => {
    row.addEventListener('mouseenter', () => row.classList.add('hover-glow'));
    row.addEventListener('mouseleave', () => row.classList.remove('hover-glow'));
  });
});
