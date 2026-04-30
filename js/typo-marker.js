/**
 * Typo Marker - 错别字标记工具
 * 手机友好：标记模式下点击段落弹出表单，填写原文和修正。
 * 电脑端也支持选中文字后弹出。
 * 管理员可在 /typo-report/ 页面查看所有标记。
 */
(function() {
    var STORAGE_KEY = 'typo_marks';
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

    // --- Popup (works for both mobile tap and desktop selection) ---
    var popup = document.createElement('div');
    popup.id = 'typo-popup';
    popup.innerHTML =
        '<div class="typo-popup-title">标记错别字</div>' +
        '<div class="typo-popup-row"><label>错字/原文：</label></div>' +
        '<input id="typo-original-input" type="text" placeholder="输入有误的文字" class="typo-input">' +
        '<div class="typo-popup-row"><label>修正建议：</label></div>' +
        '<input id="typo-fix" type="text" placeholder="输入正确的文字" class="typo-input">' +
        '<div class="typo-popup-row typo-context" id="typo-context-row"><label>所在段落：</label><span id="typo-context" style="font-size:11px;color:#999;"></span></div>' +
        '<div class="typo-popup-actions">' +
        '<button id="typo-submit">提交</button>' +
        '<button id="typo-cancel">取消</button>' +
        '</div>';
    document.body.appendChild(popup);

    var currentParagraph = null;

    function showPopup(x, y, originalText, contextText) {
        var origInput = document.getElementById('typo-original-input');
        origInput.value = originalText || '';
        document.getElementById('typo-fix').value = '';
        document.getElementById('typo-context').textContent = contextText ? contextText.substring(0, 50) + '...' : '';
        // Center on mobile, position near click on desktop
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
    document.getElementById('typo-submit').addEventListener('click', function(e) {
        e.stopPropagation();
        var original = document.getElementById('typo-original-input').value.trim();
        var fix = document.getElementById('typo-fix').value.trim();
        if (!original) { alert('请输入有误的文字'); return; }
        var context = currentParagraph ? currentParagraph.textContent.substring(0, 80) : '';
        addMark({ original: original, fix: fix || '(未填写)', context: context });
        // Try to highlight
        if (currentParagraph && original) {
            highlightInElement(currentParagraph, original, fix);
        }
        hidePopup();
        updateCount();
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
                span.title = '修正建议：' + (fix || '');
                range.surroundContents(span);
                break;
            }
        }
    }

    // --- Mobile: tap on paragraph ---
    function getContentContainer() {
        return document.querySelector('.reading-content, #mhenry-col');
    }

    function handleTap(e) {
        if (!isActive) return;
        if (popup.contains(e.target)) return;
        if (e.target.id === 'typo-toggle-btn') return;

        var container = getContentContainer();
        if (!container) return;

        // Find the closest paragraph-level element
        var target = e.target;
        while (target && target !== container) {
            if (target.matches && target.matches('p, li, .mh-verse, .mh-l1, .mh-l2, .mh-overview, h3, td, blockquote')) {
                break;
            }
            target = target.parentElement;
        }
        if (!target || target === container) return;

        e.preventDefault();
        e.stopPropagation();
        currentParagraph = target;

        // On desktop with selection, pre-fill original text
        var selectedText = '';
        if (!isMobile) {
            var sel = window.getSelection();
            if (sel && !sel.isCollapsed && sel.toString().trim().length > 0 && sel.toString().trim().length < 100) {
                selectedText = sel.toString().trim();
            }
        }

        var rect = target.getBoundingClientRect();
        showPopup(
            rect.left + window.scrollX,
            rect.bottom + window.scrollY,
            selectedText,
            target.textContent
        );
    }

    // Use click for both mobile and desktop (more reliable than touchend)
    document.addEventListener('click', handleTap);

    // Prevent popup clicks from bubbling
    popup.addEventListener('click', function(e) { e.stopPropagation(); });

    // --- Badge count ---
    var badge = document.getElementById('typo-count');
    function updateCount() {
        var marks = loadMarks();
        var count = marks.length;
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    }
    updateCount();

    // --- Restore highlights on page load ---
    (function restoreMarks() {
        var marks = loadMarks();
        var pageMarks = marks.filter(function(m) { return m.page === pageId; });
        if (!pageMarks.length) return;
        var container = getContentContainer();
        if (!container) return;
        pageMarks.forEach(function(m) {
            highlightInElement(container, m.original, m.fix);
        });
    })();
})();
