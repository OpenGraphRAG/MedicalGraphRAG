/* 健康知识推送 - 完整重构版 */
document.addEventListener('DOMContentLoaded', () => {
  const btn       = document.getElementById('startDiagnosis');
  const textarea  = document.getElementById('userInputText');
  const output    = document.getElementById('outputContent');
  const indicator = document.getElementById('typingIndicator');
  const charCount = document.getElementById('charCount');

  marked.setOptions({
    highlight: (code, lang) => hljs.highlightAuto(code, [lang]).value,
    breaks: true, gfm: true
  });

  /* 粒子背景 */
  if (typeof particlesJS !== 'undefined') {
    particlesJS('particles-js', {
      particles: {
        number: { value: 60 },
        color: { value: '#00f5ff' },
        shape: { type: 'circle' },
        opacity: { value: 0.3 },
        size: { value: 2 },
        move: { speed: 1.5, direction: 'none', outModes: 'bounce' }
      },
      interactivity: {
        events: { onhover: { enable: true, mode: 'repulse' } }
      }
    });
  }

  /* 字符计数 */
  textarea.addEventListener('input', () => {
    charCount.textContent = textarea.value.length;
  });

  /* 主逻辑 */
  btn.addEventListener('click', async () => {
    const userText = textarea.value.trim();

    // 无需强制输入，空文本时直接基于用户健康画像推送
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>AI正在分析，请稍候...</span>';
    indicator.classList.remove('hidden');
    output.innerHTML = '';

    try {
      indicator.innerHTML = `
        <div class="loading-animation">
          <div class="spinner"></div>
          <div class="loading-text">
            <h3>🧠 AI 正在综合分析您的健康信息</h3>
            <p>${userText ? '正在结合您的提问和健康画像...' : '正在基于您的完整健康画像生成个性化推送...'}</p>
            <p>正在检索知识图谱和医学文档库...</p>
            <p class="loading-sub">这可能需要几秒钟，请耐心等待</p>
          </div>
        </div>
      `;

      const res = await fetch('/api/generate_health_knowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_text: userText })
      });

      const data = await res.json();
      if (!data.success) throw new Error(data.error || '生成失败');

      indicator.classList.add('hidden');
      displayResult(data.knowledge_content || '暂无相关健康知识建议', data.user_profile_summary || '', output);

    } catch (e) {
      indicator.classList.add('hidden');
      Swal.fire({
        icon: 'error', title: '生成失败', text: e.message,
        confirmButtonText: '重试',
        background: 'rgba(10,10,26,.95)', color: '#e0f0ff',
        confirmButtonColor: '#00f5ff'
      });
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-bolt"></i><span>健康知识推送</span>';
    }
  });

  /* 展示结果 */
  function displayResult(markdownText, profileSummary, target) {
    const html = marked.parse(markdownText || '暂无相关健康知识建议');

    let profileHtml = '';
    if (profileSummary) {
      // 简化profile展示为关键信息卡片
      const lines = profileSummary.split('\n').filter(l => l.trim());
      const infoItems = lines.filter(l => l.startsWith('- ')).map(l => {
        const text = l.replace(/^-\s*/, '');
        const parts = text.split('：');
        if (parts.length === 2) {
          return `<div class="profile-card-item"><span class="pci-label">${parts[0]}</span><span class="pci-value">${parts[1]}</span></div>`;
        }
        return '';
      }).filter(Boolean).join('');

      if (infoItems) {
        profileHtml = `
          <div class="user-profile-card">
            <div class="upc-header"><i class="fas fa-id-card"></i> 您的健康档案摘要</div>
            <div class="upc-grid">${infoItems}</div>
          </div>
        `;
      }
    }

    target.innerHTML = `
      <div class="result-header">
        <h3>🎯 您的专属健康知识推送</h3>
        <p class="result-subtitle">基于您的完整健康画像、就诊记录和医学知识库生成</p>
      </div>
      ${profileHtml}
      <div class="knowledge-content">${html}</div>
      <div class="result-footer">
        <p>💡 以上知识仅供参考，具体诊疗请咨询专业医师</p>
        <p style="font-size:.85rem;margin-top:5px;">生成时间：${new Date().toLocaleString('zh-CN')}</p>
      </div>
    `;

    target.classList.add('animate__animated', 'animate__fadeInUp');

    setTimeout(() => {
      target.querySelectorAll('a').forEach(link => {
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
      });
    }, 100);
  }

  /* 动态样式 */
  const style = document.createElement('style');
  style.innerHTML = `
    .user-profile-card {
      background: linear-gradient(135deg, rgba(0,245,255,.08), rgba(255,0,255,.05));
      border: 1px solid rgba(0,245,255,.2);
      border-radius: 14px;
      padding: 20px;
      margin-bottom: 25px;
    }
    .upc-header {
      color: var(--primary);
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 15px;
      padding-bottom: 10px;
      border-bottom: 1px solid rgba(0,245,255,.15);
    }
    .upc-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 8px;
    }
    .profile-card-item {
      display: flex;
      justify-content: space-between;
      padding: 6px 10px;
      background: rgba(255,255,255,.03);
      border-radius: 6px;
      font-size: .9rem;
    }
    .pci-label { color: rgba(0,245,255,.7); font-weight: 500; }
    .pci-value { color: var(--text); }

    .loading-animation { text-align: center; padding: 40px 20px; }
    .loading-text h3 { color: var(--primary); margin: 25px 0 15px; font-size: 1.3rem; }
    .loading-text p { color: var(--text-dim); margin: 8px 0; font-size: 1rem; }
    .loading-sub { font-size: .9rem; opacity: .7; }

    .result-header {
      text-align: center; margin-bottom: 30px; padding: 25px;
      background: linear-gradient(135deg, rgba(0,245,255,.08), rgba(255,0,255,.04));
      border-radius: 14px; border-bottom: 1px solid var(--glass-border);
    }
    .result-header h3 { color: var(--primary); font-size: 1.5rem; margin-bottom: 10px; }
    .result-subtitle { color: var(--text-dim); font-size: 1rem; }

    .knowledge-content {
      line-height: 1.9; font-size: 1.1rem;
      background: rgba(255,255,255,.02); border-radius: 12px;
      padding: 25px; border: 1px solid rgba(255,255,255,.08);
    }
    .knowledge-content h1, .knowledge-content h2, .knowledge-content h3 { color: var(--primary); margin-top: 20px; }
    .knowledge-content ul, .knowledge-content ol { padding-left: 20px; }
    .knowledge-content li { margin-bottom: 8px; }
    .knowledge-content a {
      color: var(--secondary); text-decoration: none;
      border-bottom: 1px dotted var(--secondary); transition: .3s;
      padding: 1px 3px; border-radius: 3px;
    }
    .knowledge-content a:hover {
      color: var(--primary); background: rgba(0,245,255,.1);
      box-shadow: 0 0 8px rgba(0,245,255,.3);
    }
    .knowledge-content table { width: 100%; border-collapse: collapse; margin: 15px 0; }
    .knowledge-content th, .knowledge-content td {
      padding: 10px 12px; border: 1px solid rgba(255,255,255,.1);
      text-align: left;
    }
    .knowledge-content th { background: rgba(0,245,255,.1); color: var(--primary); }

    .result-footer {
      margin-top: 30px; padding: 20px; text-align: center;
      color: var(--text-dim); font-size: .95rem;
      background: rgba(0,0,0,.2); border-radius: 10px;
      border-top: 1px solid var(--glass-border);
    }

    @media (max-width: 768px) {
      .upc-grid { grid-template-columns: 1fr; }
      .knowledge-content { padding: 15px; font-size: 1rem; }
    }
  `;
  document.head.appendChild(style);
});