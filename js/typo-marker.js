/**
 * Typo Marker - 错别字标记工具
 * 读者可以选中文字标记错别字，建议修正，存储到localStorage。
 * 管理员可在 /typo-report/ 页面查看所有标记。
 */
(function() {
    var STORAGE_KEY = 'typo_marks';
    var isActive = false;
    var pageId = location.pathname;

    // --- Storage ---
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

    // --- UI: Toggle Button ---
    var btn = document.getElementById('typo-toggle-btn');
    if (!btn) return;

    btn.addEventListener('click', function() {
        isActive = !isActive;
        btn.classList.toggle('active', isActive);
        btn.textContent = isActive ? '退出标记' : '标记错字';
        document.body.classList.toggle('typo-mode', isActive);
    });

    // --- UI: Selection popup ---
    var popup = document.createElement('div');
    popup.id = 'typo-popup';
    popup.innerHTML =
        '<div class="typo-popup-title">标记错别字</div>' +
        '<div class="typo-popup-row"><label>原文：</label><span id="typo-original"></span></div>' +
        '<div class="typo-popup-row"><label>修正：</label><input id="typo-fix" type="text" placeholder="输入正确的文字"></div>' +
        '<div class="typo-popup-actions">' +
        '<button id="typo-submit">提交</button>' +
        '<button id="typo-cancel">取消</button>' +
        '</div>';
    document.body.appendChild(popup);

    var currentRange = null;

    function showPopup(x, y, text) {
        document.getElementById('typo-original').textContent = text;
        document.getElementById('typo-fix').value = '';
        popup.style.left = Math.min(x, window.innerWidth - 260) + 'px';
        popup.style.top = (y + 10) + 'px';
        popup.classList.add('visible');
        document.getElementById('typo-fix').focus();
    }
    function hidePopup() {
        popup.classList.remove('visible');
        currentRange = null;
    }

    document.getElementById('typo-cancel').addEventListener('click', hidePopup);
    document.getElementById('typo-submit').addEventListener('click', function() {
        var original = document.getElementById('typo-original').textContent;
        var fix = document.getElementById('typo-fix').value.trim();
        if (!original) { hidePopup(); return; }
        addMark({ original: original, fix: fix || '(未填写)' });
        // Highlight in page
        if (currentRange) {
            var span = document.createElement('span');
            span.className = 'typo-marked';
            span.title = '修正建议：' + (fix || '(未填写)');
            currentRange.surroundContents(span);
        }
        hidePopup();
        updateCount();
    });

    // --- Listen for text selection ---
    document.addEventListener('mouseup', function(e) {
        if (!isActive) return;
        var sel = window.getSelection();
        if (!sel || sel.isCollapsed || !sel.toString().trim()) return;
        // Only allow selection within content area
        var container = document.querySelector('.reading-content, .post-container, #mhenry-col');
        if (!container) return;
        var node = sel.anchorNode;
        while (node && node !== document.body) {
            if (node === container) break;
            node = node.parentNode;
        }
        if (node !== container) return;

        var text = sel.toString().trim();
        if (text.length > 100) return; // too long
        currentRange = sel.getRangeAt(0).cloneRange();
        var rect = sel.getRangeAt(0).getBoundingClientRect();
        showPopup(rect.left + window.scrollX, rect.bottom + window.scrollY, text);
    });

    // Close popup on click outside
    document.addEventListener('mousedown', function(e) {
        if (popup.classList.contains('visible') && !popup.contains(e.target)) {
            hidePopup();
        }
    });

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
        var container = document.querySelector('.reading-content, .post-container, #mhenry-col');
        if (!container) return;
        // Simple restore: find text and wrap (best effort)
        pageMarks.forEach(function(m) {
            var walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
            while (walker.nextNode()) {
                var idx = walker.currentNode.textContent.indexOf(m.original);
                if (idx >= 0) {
                    var range = document.createRange();
                    range.setStart(walker.currentNode, idx);
                    range.setEnd(walker.currentNode, idx + m.original.length);
                    var span = document.createElement('span');
                    span.className = 'typo-marked';
                    span.title = '修正建议：' + m.fix;
                    range.surroundContents(span);
                    break;
                }
            }
        });
    })();
})();
