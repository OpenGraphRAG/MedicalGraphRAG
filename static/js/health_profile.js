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