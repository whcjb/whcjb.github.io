/**
 * Typo Marker - 错别字标记工具
 * 提交时生成预填 GitHub Issue 链接，同时在本地高亮标记。
 */
(function() {
    var STORAGE_KEY = 'typo_marks';
    var GITHUB_REPO = 'whcjb/whcjb.github.io';
    var isActive = false;
    var pageId = location.pathname;
    var isMobile = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    function loadMarks() {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch(e) { return []; }
    }
    function saveMarks(marks) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(marks));
    }
    function addMark(mark) {
        var marks = loadMarks();
        mark.page = pageId;
        mark.time = new Date().toISOString();
        marks.push(mark);
        saveMarks(marks);
    }

    var btn = document.getElementById('typo-toggle-btn');
    if (!btn) return;

    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        isActive = !isActive;
        btn.classList.toggle('active', isActive);
        btn.textContent = isActive ? '退出标记' : '标记错字';
        document.body.classList.toggle('typo-mode', isActive);
        hidePopup();
    });

    // --- Popup ---
    var popup = document.createElement('div');
    popup.id = 'typo-popup';
    popup.innerHTML =
        '<div class="typo-popup-title">&#9998; 标记错别字</div>' +
        '<label class="typo-label">错字 / 原文</label>' +
        '<input id="typo-original-input" type="text" placeholder="输入有误的文字" class="typo-input">' +
        '<label class="typo-label">修正建议</label>' +
        '<input id="typo-fix" type="text" placeholder="输入正确的文字（可留空）" class="typo-input">' +
        '<div class="typo-popup-actions">' +
        '<button id="typo-submit">提交到 GitHub</button>' +
        '<button id="typo-local">仅本地标记</button>' +
        '<button id="typo-cancel">取消</button>' +
        '</div>' +
        '<div class="typo-popup-hint">提交将跳转到 GitHub 新建 Issue（需要登录）</div>';
    document.body.appendChild(popup);

    var currentParagraph = null;

    function showPopup(x, y, originalText) {
        var origInput = document.getElementById('typo-original-input');
        origInput.value = originalText || '';
        document.getElementById('typo-fix').value = '';
        if (isMobile) {
            popup.style.left = '50%';
            popup.style.top = '50%';
            popup.style.transform = 'translate(-50%, -50%)';
            popup.style.position = 'fixed';
        } else {
            popup.style.left = Math.min(x, window.innerWidth - 280) + 'px';
            popup.style.top = (y + 10) + 'px';
            popup.style.transform = '';
            popup.style.position = 'absolute';
        }
        popup.classList.add('visible');
        origInput.focus();
    }
    function hidePopup() {
        popup.classList.remove('visible');
        currentParagraph = null;
    }

    document.getElementById('typo-cancel').addEventListener('click', function(e) {
        e.stopPropagation();
        hidePopup();
    });

    // 提交到 GitHub Issue
    document.getElementById('typo-submit').addEventListener('click', function(e) {
        e.stopPropagation();
        var original = document.getElementById('typo-original-input').value.trim();
        var fix = document.getElementById('typo-fix').value.trim();
        if (!original) { document.getElementById('typo-original-input').focus(); return; }

        var context = currentParagraph ? currentParagraph.textContent.substring(0, 120).trim() : '';
        var pageUrl = location.href;

        var title = encodeURIComponent('错字报告：「' + original + '」');
        var body = encodeURIComponent(
            '**页面：** ' + pageUrl + '\n\n' +
            '**错字 / 原文：** `' + original + '`\n\n' +
            '**修正建议：** ' + (fix || '（未填写）') + '\n\n' +
            (context ? '**所在段落（节选）：**\n> ' + context + '\n\n' : '') +
            '---\n*由「标记错字」功能自动生成*'
        );
        var issueUrl = 'https://github.com/' + GITHUB_REPO + '/issues/new?title=' + title + '&body=' + body;

        // 本地高亮
        if (currentParagraph && original) highlightInElement(currentParagraph, original, fix);
        addMark({ original: original, fix: fix || '', context: context });
        updateCount();
        hidePopup();

        window.open(issueUrl, '_blank');
    });

    // 仅本地标记
    document.getElementById('typo-local').addEventListener('click', function(e) {
        e.stopPropagation();
        var original = document.getElementById('typo-original-input').value.trim();
        var fix = document.getElementById('typo-fix').value.trim();
        if (!original) { document.getElementById('typo-original-input').focus(); return; }
        var context = currentParagraph ? currentParagraph.textContent.substring(0, 80) : '';
        if (currentParagraph && original) highlightInElement(currentParagraph, original, fix);
        addMark({ original: original, fix: fix || '', context: context });
        updateCount();
        hidePopup();
    });

    function highlightInElement(el, text, fix) {
        var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        while (walker.nextNode()) {
            var idx = walker.currentNode.textContent.indexOf(text);
            if (idx >= 0) {
                var range = document.createRange();
                range.setStart(walker.currentNode, idx);
                range.setEnd(walker.currentNode, idx + text.length);
                var span = document.createElement('span');
                span.className = 'typo-marked';
                span.title = fix ? '修正建议：' + fix : '已标记';
                range.surroundContents(span);
                break;
            }
        }
    }

    function getContentContainer() {
        return document.querySelector('.reading-content, #mhenry-col, .post-container');
    }

    function handleTap(e) {
        if (!isActive) return;
        if (popup.contains(e.target)) return;
        if (e.target.id === 'typo-toggle-btn') return;

        var container = getContentContainer();
        if (!container) return;

        var target = e.target;
        while (target && target !== container) {
            if (target.matches && target.matches('p, li, .mh-verse, .mh-l1, .mh-l2, .mh-overview, h3, td, blockquote')) break;
            target = target.parentElement;
        }
        if (!target || target === container) return;

        e.preventDefault();
        e.stopPropagation();
        currentParagraph = target;

        var selectedText = '';
        var sel = window.getSelection();
        if (sel && !sel.isCollapsed && sel.toString().trim().length > 0 && sel.toString().trim().length < 100) {
            selectedText = sel.toString().trim();
        }

        var rect = target.getBoundingClientRect();
        showPopup(rect.left + window.scrollX, rect.bottom + window.scrollY, selectedText);
    }

    document.addEventListener('click', handleTap);
    popup.addEventListener('click', function(e) { e.stopPropagation(); });

    // --- Badge count ---
    var badge = document.getElementById('typo-count');
    function updateCount() {
        var count = loadMarks().length;
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    }
    updateCount();

    // --- Restore highlights on page load ---
    (function restoreMarks() {
        var marks = loadMarks().filter(function(m) { return m.page === pageId; });
        if (!marks.length) return;
        var container = getContentContainer();
        if (!container) return;
        marks.forEach(function(m) { highlightInElement(container, m.original, m.fix); });
    })();
})();
