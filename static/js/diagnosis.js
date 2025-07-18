document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('startDiagnosis');
  const textarea = document.getElementById('userInputText');
  const output = document.getElementById('outputContent');
  const indicator = document.getElementById('typingIndicator');
  const charCount = document.getElementById('charCount');

  /* ---------- 工具函数 ---------- */
  marked.setOptions({
    highlight: (code, lang) => hljs.highlightAuto(code, [lang]).value,
    breaks: true,
    gfm: true
  });

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  /* ---------- 字符计数 ---------- */
  textarea.addEventListener('input', () => charCount.textContent = textarea.value.length);

  /* ---------- 粒子背景 ---------- */
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

  /* ---------- 按钮事件 ---------- */
  btn.addEventListener('click', async () => {
    const userText = textarea.value.trim();
    btn.disabled = true;
    indicator.classList.remove('hidden');
    output.innerHTML = '';

    try {
      const res = await fetch('/api/generate_health_knowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_text: userText })
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || '生成失败');
      indicator.classList.add('hidden');
      await typeWriter(data.knowledge_content || '暂无建议', output);
    } catch (e) {
      indicator.classList.add('hidden');
      Swal.fire('生成失败', e.message, 'error');
    } finally {
      btn.disabled = false;
    }
  });

  /* ---------- 打字机 + Markdown 渲染 ---------- */
  async function typeWriter(markdownText, target) {
    const safeText = markdownText || '暂无建议';
    const html = marked.parse(safeText);
    target.innerHTML = '';
    const temp = document.createElement('div');
    temp.innerHTML = html;

    const walker = document.createTreeWalker(temp, NodeFilter.SHOW_TEXT, null);
    const nodes = [];
    let node;
    while (node = walker.nextNode()) nodes.push(node);

    for (const n of nodes) {
      const text = n.textContent;
      n.textContent = '';
      const parent = n.parentNode;
      for (const ch of text) {
        n.textContent += ch;
        await sleep(20);
      }
      parent.normalize();
    }
    target.appendChild(temp);
  }
});