// 基础功能脚本
document.addEventListener('DOMContentLoaded', function() {
    // 表单输入效果增强
    document.querySelectorAll('.input-with-icon input').forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.style.boxShadow = '0 0 0 3px rgba(77, 179, 211, 0.2)';
        });

        input.addEventListener('blur', function() {
            this.parentElement.style.boxShadow = 'none';
        });
    });

    // 按钮悬停效果
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.1)';
        });

        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = 'none';
        });
    });
});