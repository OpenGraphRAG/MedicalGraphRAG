/* 全面美化版：打字机 + Markdown 渲染 + 动效 + 完整结果展示 */
document.addEventListener('DOMContentLoaded', () => {
  const btn       = document.getElementById('startDiagnosis');
  const textarea  = document.getElementById('userInputText');
  const output    = document.getElementById('outputContent');
  const indicator = document.getElementById('typingIndicator');
  const charCount = document.getElementById('charCount');

  /* ========== 工具 ========== */
  marked.setOptions({
    highlight: (code, lang) => hljs.highlightAuto(code, [lang]).value,
    breaks: true,
    gfm: true
  });
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  /* ========== 粒子背景 ========== */
  particlesJS('particles-js', {
    particles: {
      number: { value: 80 },
      color: { value: '#00f5ff' },
      shape: { type: 'circle' },
      opacity: { value: 0.4 },
      size: { value: 3 },
      move: { speed: 2, direction: 'none', outModes: 'bounce' }
    },
    interactivity: {
      events: { onhover: { enable: true, mode: 'repulse' } }
    }
  });

  /* ========== 字符计数 ========== */
  textarea.addEventListener('input', () => {
    charCount.textContent = textarea.value.length;
  });

  /* ========== 按钮波纹粒子 ========== */
  btn.addEventListener('click', e => {
    let ripple = document.createElement('span');
    ripple.classList.add('ripple');
    btn.appendChild(ripple);
    const rect = btn.getBoundingClientRect();
    ripple.style.left = e.clientX - rect.left + 'px';
    ripple.style.top  = e.clientY - rect.top  + 'px';
    setTimeout(() => ripple.remove(), 600);
  });

  /* ========== 主逻辑 ========== */
  btn.addEventListener('click', async () => {
    const userText = textarea.value.trim();

    // 验证输入
    if (!userText) {
      Swal.fire({
        icon: 'info',
        title: '请输入信息',
        text: '请填写您的健康状况或症状描述，以便AI为您提供更精准的健康知识',
        confirmButtonText: '好的'
      });
      return;
    }

    // 禁用按钮，显示加载状态
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>AI正在分析中，请稍候...</span>';

    indicator.classList.remove('hidden');
    output.innerHTML = '';

    try {
      // 显示更友好的等待提示
      indicator.innerHTML = `
        <div class="loading-animation">
          <div class="spinner"></div>
          <div class="loading-text">
            <h3>🧠 AI 正在为您分析健康信息</h3>
            <p>正在结合您的健康画像和医学知识库生成个性化建议...</p>
            <p class="loading-sub">这可能需要几秒钟时间，请耐心等待</p>
          </div>
        </div>
      `;

      const res = await fetch('/api/generate_health_knowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_text: userText })
      });

      const data = await res.json();

      if (!data.success) {
        throw new Error(data.error || '生成失败，请稍后重试');
      }

      // 隐藏指示器
      indicator.classList.add('hidden');

      // 显示完整的知识内容
      await displayCompleteResult(data.knowledge_content || '暂无相关健康知识建议', output);

    } catch (e) {
      indicator.classList.add('hidden');
      Swal.fire({
        icon: 'error',
        title: '生成失败',
        text: e.message,
        confirmButtonText: '重试'
      });
    } finally {
      // 恢复按钮状态
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-bolt"></i><span>健康知识推送</span>';
    }
  });

  /* ========== 完整结果显示（非打字机效果） ========== */
  async function displayCompleteResult(markdownText, target) {
    const safeText = markdownText || '暂无相关健康知识建议';

    // 使用 marked 解析 Markdown
    const html = marked.parse(safeText);

    // 创建容器并设置内容
    target.innerHTML = `
      <div class="result-header">
        <h3>🎯 您的专属健康知识推送</h3>
        <p class="result-subtitle">基于您的健康画像和最新医学知识生成</p>
      </div>
      <div class="knowledge-content">
        ${html}
      </div>
      <div class="result-footer">
        <p>💡 提示：点击来源链接可以查看详细医学资料</p>
      </div>
    `;

    // 添加动画效果
    target.classList.add('animate__animated', 'animate__fadeInUp');

    // 确保链接在新窗口打开
    setTimeout(() => {
      const links = target.querySelectorAll('a');
      links.forEach(link => {
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
      });
    }, 100);
  }

  /* ========== 动态插入波纹和加载样式 CSS ========== */
  const style = document.createElement('style');
  style.innerHTML = `
    .ripple {
      position: absolute;
      border-radius: 50%;
      transform: scale(0);
      animation: rippleEffect .6s linear;
      background: rgba(255,255,255,.6);
      pointer-events: none;
      width: 20px;
      height: 20px;
      margin: -10px 0 0 -10px;
    }

    .loading-animation {
      text-align: center;
      padding: 30px;
    }

    .loading-text h3 {
      color: var(--primary);
      margin: 20px 0 10px;
      font-size: 1.3rem;
    }

    .loading-text p {
      color: var(--text-dim);
      margin: 5px 0;
    }

    .loading-sub {
      font-size: 0.9rem;
      opacity: 0.8;
    }

    .result-header {
      text-align: center;
      margin-bottom: 30px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--glass-border);
    }

    .result-header h3 {
      color: var(--primary);
      font-size: 1.5rem;
      margin-bottom: 10px;
    }

    .result-subtitle {
      color: var(--text-dim);
      font-size: 1rem;
    }

    .knowledge-content {
      line-height: 1.8;
      font-size: 1.1rem;
    }

    .result-footer {
      margin-top: 30px;
      padding-top: 20px;
      border-top: 1px solid var(--glass-border);
      text-align: center;
      color: var(--text-dim);
      font-size: 0.9rem;
    }

    .knowledge-content a {
      color: var(--secondary);
      text-decoration: none;
      border-bottom: 1px dotted var(--secondary);
      transition: all 0.3s ease;
    }

    .knowledge-content a:hover {
      color: var(--primary);
      border-bottom: 1px solid var(--primary);
    }

    @keyframes rippleEffect {
      to { transform: scale(4); opacity: 0; }
    }
  `;
  document.head.appendChild(style);
});