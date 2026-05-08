function toggleMenu(id) {
    var el = document.getElementById(id);
    if (!el) return;
    document.querySelectorAll('.menu-dropdown').forEach(function(d) {
        if (d.id !== id) d.style.display = 'none';
    });
    el.style.display = el.style.display === 'block' ? 'none' : 'block';
}

document.addEventListener('click', function(e) {
    if (!e.target.closest('.menu-item')) {
        document.querySelectorAll('.menu-dropdown').forEach(function(d) {
            d.style.display = 'none';
        });
    }
});

function waitForPywebview(cb) {
    if (window.pywebview && window.pywebview.api) cb();
    else setTimeout(function() { waitForPywebview(cb); }, 100);
}

let editor, ctxPath = '', ctxIsDir = false;
let chatSessions = {};       // { chatId: { id, name, type, parentId, messages: [] } }
let activeChatId = '';       // currently visible chat
let chatCounter = 0;         // for generating unique chat IDs
let openTabs = [];           // [{path, name}]
let activeTabPath = '';      // currently active file path
let fileContents = {};       // path -> content cache

require.config({ paths: { vs: 'vs' } });
require(['vs/editor/editor.main'], function () {
    monaco.languages.register({ id: 'vigo' });
    monaco.languages.setMonarchTokensProvider('vigo', {
        keywords: ['Fun','as','Ret','if','el','eif','ts','Fin','loop','for','in','go','skip','break','continue','load','and','or','not','null','true','false','ok','no','class','new','extends','this','try','catch','throw','await','switch','case','default','enum','const','sure','static','abstract','interface','spawn'],
        typeKeywords: ['int','float','str','bool','list','dict','set'],
        operators: ['+','-','*','/','%','==','!=','<','>','<=','>=','=','+=','-=','*=','/=','%=','|>','?.','??','..','...','?',':','&','|','^','~','<<','>>'],
        symbols: /[=><!~?:&|+\-*\/\^%]+/,
        tokenizer: {
            root: [
                [/\b\d+\.?\d*\b/, 'number'],
                [/[a-zA-Z_]\w*/, { cases: { '@typeKeywords': 'type', '@keywords': 'keyword', '@default': 'identifier' } }],
                [/"/, { token: 'string.quote', bracket: '@open', next: '@string' }],
                [/#.*$/, 'comment'],
                [/[{}()\[\]]/, '@brackets']
            ],
            string: [
                [/[^\\"]+/, 'string'],
                [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }]
            ]
        }
    });
    monaco.languages.registerCompletionItemProvider('vigo', {
        provideCompletionItems: function(model, pos) {
            var w = model.getWordUntilPosition(pos);
            var r = { startLineNumber: pos.lineNumber, endLineNumber: pos.lineNumber, startColumn: w.startColumn, endColumn: w.endColumn };
            return {
                suggestions: [
                    { label: 'Fun as', kind: 14, insertText: 'Fun as ${1:name}(${2:params}):\n    ${3}\nFin', insertTextRules: 4, range: r },
                    { label: 'if', kind: 14, insertText: 'if ${1:condition} ts\n    ${2}\nFin', insertTextRules: 4, range: r },
                    { label: 'loop', kind: 14, insertText: 'loop ${1:condition} ts\n    ${2}\nFin', insertTextRules: 4, range: r },
                    { label: 'for', kind: 14, insertText: 'for ${1:item} in ${2:items} ts\n    ${3}\nFin', insertTextRules: 4, range: r },
                    { label: 'switch', kind: 14, insertText: 'switch ${1:expr} ts\n    case ${2:val} ts\n        ${3}\n    default ts\n        ${4}\nFin', insertTextRules: 4, range: r },
                    { label: 'class', kind: 14, insertText: 'class ${1:Name} ts\n    ${2}\nFin', insertTextRules: 4, range: r },
                    { label: 'try', kind: 14, insertText: 'try ts\n    ${1}\ncatch ${2:err} ts\n    ${3}\nFin', insertTextRules: 4, range: r },
                    { label: 'Ret', kind: 14, insertText: 'Ret ${1:expr}', insertTextRules: 4, range: r },
                    { label: 'const', kind: 14, insertText: 'const ${1:NAME} = ${2:value}', insertTextRules: 4, range: r },
                    { label: 'ok', kind: 13, insertText: 'ok', range: r },
                    { label: 'no', kind: 13, insertText: 'no', range: r },
                    { label: 'null', kind: 13, insertText: 'null', range: r },
                    { label: 'spawn', kind: 14, insertText: 'spawn ${1:expr}', insertTextRules: 4, range: r },
                    { label: 'ai_ask', kind: 1, insertText: 'ai_ask("${1:prompt}")', insertTextRules: 4, range: r },
                    { label: 'mem_save', kind: 1, insertText: 'mem_save("${1:key}","${2:content}")', insertTextRules: 4, range: r },
                    { label: 'print', kind: 1, insertText: 'print(${1})', insertTextRules: 4, range: r }
                ]
            };
        }
    });
    monaco.languages.setLanguageConfiguration('vigo', {
        brackets: [['{','}'],['[',']'],['(',')']],
        autoClosingPairs: [{open:'{',close:'}'},{open:'[',close:']'},{open:'(',close:')'},{open:'"',close:'"'}],
        surroundingPairs: [{open:'{',close:'}'},{open:'[',close:']'},{open:'(',close:')'},{open:'"',close:'"'}]
    });
    editor = monaco.editor.create(document.getElementById('editor'), {
        value: '// Welcome to ViGo Dev\n// Open a project to start editing.',
        language: 'vigo',
        theme: 'vs-dark',
        fontSize: 13,
        minimap: { enabled: false },
        automaticLayout: true,
        scrollBeyondLastLine: false,
        wordWrap: 'on'
    });

    // Drag & drop files into editor
    var editorDom = editor.getDomNode();
    if (editorDom) {
        editorDom.addEventListener('dragover', function(e) { e.preventDefault(); });
        editorDom.addEventListener('drop', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            var files = e.dataTransfer.files;
            if (!files || files.length === 0) return;
            for (var i = 0; i < files.length; i++) {
                var f = files[i];
                var path = f.path;
                if (!path) continue;
                var name = path.split('\\').pop().split('/').pop();
                openFile(path, name);
            }
        });
    }

    waitForPywebview(function() {
        initApp();
        loadAndApplySettings();
    });
});

async function initApp() {
    await loadProjects();
    createDefaultChat();
    await restoreProjectState();
    window._autoSaveTimer = setInterval(autoSaveCurrentConversation, 60000);
    setInterval(saveProjectStateOnly, 5000);
}

async function saveProjectStateOnly() {
    try {
        var state = {
            open_chats: Object.keys(chatSessions),
            open_editor_tabs: openTabs.map(function(t) { return t.path; })
        };
        var r = await pywebview.api.save_project_state(JSON.stringify(state));
        var parsed = JSON.parse(r);
        if (parsed.status === 'error') {
            console.error('save_project_state error: ' + parsed.message);
        }
    } catch(e) { console.error('saveProjectStateOnly: ' + e.message); }
}

async function restoreProjectState() {
    try {
        var state = JSON.parse(await pywebview.api.load_project_state());
        
        // Restore editor tabs
        var editorTabs = state.open_editor_tabs || [];
        if (editorTabs.length > 0) {
            openTabs = [];
            for (var i = 0; i < editorTabs.length; i++) {
                var filePath = editorTabs[i];
                var fileName = filePath.split('/').pop();
                openTabs.push({path: filePath, name: fileName});
                try {
                    var content = await pywebview.api.read_file(filePath);
                    fileContents[filePath] = content;
                } catch(e) {}
            }
            var lastFile = state.last_file || editorTabs[0];
            if (openTabs.find(function(t) { return t.path === lastFile; })) {
                activeTabPath = lastFile;
            } else {
                activeTabPath = openTabs[0].path;
            }
            editor.setValue(fileContents[activeTabPath] || '');
            var ext = activeTabPath.split('.').pop();
            var m = { py: 'python', vigo: 'vigo', js: 'javascript', html: 'html', css: 'css', json: 'json', md: 'markdown' };
            monaco.editor.setModelLanguage(editor.getModel(), m[ext] || 'plaintext');
            document.getElementById('status-file').textContent = activeTabPath;
            renderTabs();
        }

        // Restore chat tabs
        var openChats = state.open_chats || [];
        if (openChats.length > 0) {
            // Remove default Chat 1
            var defaultId = activeChatId;
            if (defaultId && chatSessions[defaultId]) {
                delete chatSessions[defaultId];
            }
            document.getElementById('chat-messages').innerHTML = '';
            openChats.forEach(function(cid) {
                var name = 'Chat ' + cid.replace('chat_', '');
                chatSessions[cid] = { id: cid, name: name, type: 'master', parentId: null, messages: [], collapsed: false };
            });
            activeChatId = openChats[0];
            switchChat(activeChatId);
        }
    } catch(e) {}
}

async function loadAndApplySettings() {
    try {
        settingsData = JSON.parse(await pywebview.api.get_settings());
    } catch(e) { settingsData = {}; }
    applySettings();
}

function createDefaultChat() {
    chatCounter++;
    var id = 'chat_' + chatCounter;
    chatSessions[id] = { id: id, name: 'Chat 1', type: 'master', parentId: null, messages: [], collapsed: false };
    activeChatId = id;
    renderChatTabs();
    document.getElementById('chat-messages').innerHTML = '';
}

/* ═══════════════════════════════════════
   Custom Modal System
   ═══════════════════════════════════════ */

function createModal() {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    var box = document.createElement('div');
    box.className = 'modal-box';
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    return { overlay: overlay, box: box };
}

function showAlert(title, message) {
    return new Promise(function(resolve) {
        var modal = createModal();
        modal.box.innerHTML =
            '<div class="modal-title">' + escapeHtml(title) + '<span class="modal-close">✖</span></div>' +
            '<div class="modal-body"><div class="modal-message">' + escapeHtml(message) + '</div></div>' +
            '<div class="modal-footer"><button class="modal-btn modal-btn-confirm">OK</button></div>';
        modal.box.querySelector('.modal-close').onclick = close;
        modal.box.querySelector('.modal-btn-confirm').onclick = close;
        modal.overlay.onclick = function(e) { if (e.target === modal.overlay) close(); };
        function close() { modal.overlay.remove(); resolve(true); }
        modal.box.querySelector('.modal-btn-confirm').focus();
    });
}

function showConfirm(title, message) {
    return new Promise(function(resolve) {
        var modal = createModal();
        modal.box.innerHTML =
            '<div class="modal-title">' + escapeHtml(title) + '</div>' +
            '<div class="modal-body"><div class="modal-message">' + escapeHtml(message) + '</div></div>' +
            '<div class="modal-footer">' +
            '<button class="modal-btn modal-btn-cancel">Cancel</button>' +
            '<button class="modal-btn modal-btn-danger">Confirm</button>' +
            '</div>';
        modal.box.querySelector('.modal-btn-cancel').onclick = function() { modal.overlay.remove(); resolve(false); };
        modal.box.querySelector('.modal-btn-danger').onclick = function() { modal.overlay.remove(); resolve(true); };
        modal.overlay.onclick = function(e) { if (e.target === modal.overlay) { modal.overlay.remove(); resolve(false); } };
        modal.box.querySelector('.modal-btn-cancel').focus();
    });
}

function showInput(title, placeholder, defaultValue) {
    return new Promise(function(resolve) {
        var modal = createModal();
        modal.box.innerHTML =
            '<div class="modal-title">' + escapeHtml(title) + '</div>' +
            '<div class="modal-body"><input type="text" placeholder="' + escapeHtml(placeholder || '') + '" value="' + escapeHtml(defaultValue || '') + '" autofocus></div>' +
            '<div class="modal-footer">' +
            '<button class="modal-btn modal-btn-cancel">Cancel</button>' +
            '<button class="modal-btn modal-btn-confirm">OK</button>' +
            '</div>';
        var input = modal.box.querySelector('input');
        modal.box.querySelector('.modal-btn-cancel').onclick = function() { modal.overlay.remove(); resolve(null); };
        modal.box.querySelector('.modal-btn-confirm').onclick = function() { modal.overlay.remove(); resolve(input.value.trim()); };
        modal.overlay.onclick = function(e) { if (e.target === modal.overlay) { modal.overlay.remove(); resolve(null); } };
        input.onkeydown = function(e) { if (e.key === 'Enter') { modal.overlay.remove(); resolve(input.value.trim()); } };
        input.focus();
        input.select();
    });
}

function showBackupPicker(title, backups, filePath) {
    return new Promise(function(resolve) {
        var modal = createModal();
        var selectedIdx = 0;

        var listHtml = '';
        backups.forEach(function(b, i) {
            listHtml += '<div class="modal-backup-item' + (i === 0 ? ' selected' : '') + '" data-idx="' + i + '">' +
                '<span class="modal-backup-time">' + escapeHtml(b.time) + '</span>' +
                '<span class="modal-backup-size">' + b.size + ' bytes</span>' +
                '</div>';
        });

        modal.box.innerHTML =
            '<div class="modal-title">' + escapeHtml(title) + '</div>' +
            '<div class="modal-body">' +
            '<div class="modal-message" style="margin-bottom:8px">' + escapeHtml(filePath) + '</div>' +
            '<div class="modal-backup-list">' + listHtml + '</div>' +
            '</div>' +
            '<div class="modal-footer">' +
            '<button class="modal-btn modal-btn-cancel">Cancel</button>' +
            '<button class="modal-btn modal-btn-confirm">Restore</button>' +
            '</div>';

        var items = modal.box.querySelectorAll('.modal-backup-item');
        items.forEach(function(item) {
            item.onclick = function() {
                items.forEach(function(i) { i.classList.remove('selected'); });
                this.classList.add('selected');
                selectedIdx = parseInt(this.getAttribute('data-idx'));
            };
        });

        modal.box.querySelector('.modal-btn-cancel').onclick = function() { modal.overlay.remove(); resolve(-1); };
        modal.box.querySelector('.modal-btn-confirm').onclick = function() { modal.overlay.remove(); resolve(selectedIdx); };
        modal.overlay.onclick = function(e) { if (e.target === modal.overlay) { modal.overlay.remove(); resolve(-1); } };
    });
}

function showListPicker(title, items) {
    return new Promise(function(resolve) {
        var modal = createModal();
        var listHtml = '';
        items.forEach(function(item, i) {
            listHtml += '<div class="modal-backup-item' + (i === 0 ? ' selected' : '') + '" data-value="' + escapeHtml(item.value || item) + '">' +
                '<span>' + escapeHtml(item.label || item) + '</span>' +
                '</div>';
        });
        modal.box.innerHTML =
            '<div class="modal-title">' + escapeHtml(title) + '</div>' +
            '<div class="modal-body"><div class="modal-backup-list">' + listHtml + '</div></div>' +
            '<div class="modal-footer">' +
            '<button class="modal-btn modal-btn-cancel">Cancel</button>' +
            '<button class="modal-btn modal-btn-confirm">Select</button>' +
            '</div>';
        var selectedValue = items[0] ? (items[0].value || items[0]) : null;
        var itemsEl = modal.box.querySelectorAll('.modal-backup-item');
        itemsEl.forEach(function(el) {
            el.onclick = function() {
                itemsEl.forEach(function(i) { i.classList.remove('selected'); });
                this.classList.add('selected');
                selectedValue = this.getAttribute('data-value');
            };
        });
        modal.box.querySelector('.modal-btn-cancel').onclick = function() { modal.overlay.remove(); resolve(null); };
        modal.box.querySelector('.modal-btn-confirm').onclick = function() { modal.overlay.remove(); resolve(selectedValue); };
        modal.overlay.onclick = function(e) { if (e.target === modal.overlay) { modal.overlay.remove(); resolve(null); } };
    });
}

/* ═══════════════════════════════════════
   Project Management
   ═══════════════════════════════════════ */

async function loadProjects() {
    try {
        var d = JSON.parse(await pywebview.api.list_projects());
        var projects = d.projects || [];
        var current = d.current;
        var dd = document.getElementById('project-list-dropdown');
        dd.innerHTML = '';
        projects.forEach(function(p) {
            var div = document.createElement('div');
            div.className = 'menu-dropdown-item';
            div.textContent = p.name;
            div.onclick = function(e) { e.stopPropagation(); openProject(p.name); };
            dd.appendChild(div);
        });
        var el = document.getElementById('project-name');
        if (current) {
            el.textContent = current;
            el.className = 'active';
            loadFileTree();
        } else {
            el.textContent = 'No project open';
            el.className = '';
        }
    } catch(e) { console.error(e); }
}

async function createNewProject() {
    var name = prompt('Enter new project name:');
    if (!name || !name.trim()) return;
    try {
        var r = JSON.parse(await pywebview.api.create_project(name.trim()));
        if (r.status === 'ok') {
            await loadProjects();
            loadFileTree();
            if (r.last_file) openFile(r.last_file, r.last_file.split('/').pop());
        } else {
            await showAlert('Error', r.message || 'Failed');
        }
    } catch(e) { await showAlert('Error', e.message); }
}

async function importProject() {
    try {
        var folder = await pywebview.api.open_folder_dialog();
        if (!folder) return;
        var name = folder.split('\\').pop().split('/').pop();
        name = prompt('Project name:', name);
        if (!name || !name.trim()) return;
        var r = JSON.parse(await pywebview.api.import_project(name.trim(), folder));
        if (r.status === 'ok') {
            await loadProjects();
            loadFileTree();
            if (r.last_file) openFile(r.last_file, r.last_file.split('/').pop());
        } else {
            await showAlert('Error', r.message || 'Failed');
        }
    } catch(e) { await showAlert('Error', e.message); }
}

async function openProject(name) {
    try {
        var r = JSON.parse(await pywebview.api.open_project(name));
        if (r.status === 'ok') {
            openTabs = [];
            fileContents = {};
            activeTabPath = '';
            editor.setValue('// Welcome to ViGo Dev');
            renderTabs();
            var labelEl = document.getElementById('tab-label');
            if (labelEl) labelEl.textContent = 'Welcome';
            await loadProjects();
            loadFileTree();
            if (r.last_file) openFile(r.last_file, r.last_file.split('/').pop());
        }
    } catch(e) { await showAlert('Error', e.message); }
}

async function closeProject() {
    await pywebview.api.close_project();
    await loadProjects();
    document.getElementById('file-tree').innerHTML = '<div class="tree-item" style="color:#8b949e">Open a project to browse files</div>';
    editor.setValue('// Welcome to ViGo Dev');
    openTabs = [];
    activeTabPath = '';
    fileContents = {};
    renderTabs();
    document.getElementById('tab-label').textContent = 'Welcome';
    document.getElementById('status-file').textContent = 'No file open';
    saveProjectStateOnly();
}

/* ═══════════════════════════════════════
   File Tree
   ═══════════════════════════════════════ */

async function loadFileTree() {
    try {
        var tree = JSON.parse(await pywebview.api.get_file_tree());
        var c = document.getElementById('file-tree');
        if (tree.length === 0) {
            c.innerHTML = '<div class="tree-item" style="color:#8b949e">Project is empty</div>';
            return;
        }
        renderTree(tree, c);
    } catch(e) {
        c.innerHTML = '<div class="tree-item" style="color:#f85149">Error: ' + e.message + '</div>';
    }
}

function renderTree(items, container, depth) {
    depth = depth || 0;
    container.innerHTML = '';
    items.forEach(function(item) {
        var div = document.createElement('div');
        div.className = 'tree-item ' + item.type + (item.type === 'file' ? ' ' + (item.ext || '').replace('.', '') : '');
        div.style.paddingLeft = (14 + depth * 14) + 'px';
        div.textContent = (item.type === 'dir' ? '📁 ' : '📄 ') + item.name;
        div.setAttribute('data-path', item.path);
        div.addEventListener('contextmenu', function(e) {
            e.preventDefault(); e.stopPropagation();
            ctxPath = item.path; ctxIsDir = item.type === 'dir';
            showCtxMenu(e.clientX, e.clientY, ctxIsDir);
        });
        if (item.type === 'file') {
            div.onclick = function() { openFile(item.path, item.name); };
            container.appendChild(div);
        } else {
            div.onclick = async function(e) {
                e.stopPropagation();
                var cd = this.nextElementSibling;
                if (cd && cd.classList.contains('tree-children')) {
                    cd.style.display = cd.style.display === 'none' ? 'block' : 'none';
                } else {
                    try {
                        var children = JSON.parse(await pywebview.api.get_dir_children(item.path));
                        var cc = document.createElement('div');
                        cc.className = 'tree-children';
                        renderTree(children, cc, depth + 1);
                        container.insertBefore(cc, this.nextSibling);
                    } catch(e) { console.error(e); }
                }
            };
            container.appendChild(div);
        }
    });
}

var ctxMenu = document.createElement('div');
ctxMenu.id = 'ctx-menu';
ctxMenu.style.cssText = 'display:none;position:fixed;background:#1c2128;border:1px solid #30363d;border-radius:6px;padding:4px 0;z-index:2000;min-width:160px;';
document.body.appendChild(ctxMenu);
document.addEventListener('click', function() { ctxMenu.style.display = 'none'; });

function ctxItem(text, fn) {
    var d = document.createElement('div');
    d.className = 'menu-dropdown-item';
    d.textContent = text;
    d.onclick = fn;
    return d;
}

function showCtxMenu(x, y, isDir) {
    ctxMenu.innerHTML = '';
    if (isDir) {
        ctxMenu.appendChild(ctxItem('📄 New File', async function() {
            var n = await showInput('New File', 'Enter file name:');
            if (n) { await pywebview.api.create_file(ctxPath, n); loadFileTree(); }
        }));
        ctxMenu.appendChild(ctxItem('📁 New Folder', async function() {
            var n = await showInput('New Folder', 'Enter folder name:');
            if (n) { await pywebview.api.create_folder(ctxPath, n); loadFileTree(); }
        }));
    }
    if (!isDir) {
        ctxMenu.appendChild(ctxItem('🔍 Compare with Backup', async function() {
            await showDiff(ctxPath);
        }));
        ctxMenu.appendChild(ctxItem('🔄 Restore Backup...', async function() {
            await showRestoreDialog(ctxPath);
        }));
    }
    ctxMenu.appendChild(ctxItem('✏️ Rename', async function() {
        var oldName = ctxPath.split('/').pop();
        var baseName = oldName.indexOf('.') !== -1 ? oldName.substring(0, oldName.lastIndexOf('.')) : oldName;
        var n = await showInput('Rename', 'Enter new name (extension preserved):', baseName);
        if (n) {
            var r = JSON.parse(await pywebview.api.rename_item(ctxPath, n));
            if (r.status === 'ok') { loadFileTree(); if (r.new_path) openFile(r.new_path, r.new_name); }
            else await showAlert('Error', r.message);
        }
    }));
    ctxMenu.appendChild(ctxItem('🗑️ Delete', async function() {
        var ok = await showConfirm('Delete', 'Delete "' + ctxPath + '"?');
        if (ok) {
            var r = JSON.parse(await pywebview.api.delete_item(ctxPath));
            if (r.status === 'ok') loadFileTree(); else await showAlert('Error', r.message);
        }
    }));
    ctxMenu.style.display = 'block';
    ctxMenu.style.left = x + 'px';
    ctxMenu.style.top = y + 'px';
}

async function showRestoreDialog(filePath) {
    try {
        var backups = JSON.parse(await pywebview.api.list_backups(filePath));
        if (backups.length === 0) {
            await showAlert('Restore Backup', 'No backups found for this file.');
            return;
        }
        var idx = await showBackupPicker('Restore Backup', backups, filePath);
        if (idx < 0) return;
        var ok = await showConfirm('Restore Backup', 'Restore version from ' + backups[idx].time + '? This will overwrite the current file.');
        if (!ok) return;
        var r = JSON.parse(await pywebview.api.restore_backup(backups[idx].filename, filePath));
        if (r.status === 'ok') {
            await showAlert('Restore Backup', 'Restored successfully!');
            openFile(filePath, filePath.split('/').pop());
            loadFileTree();
        } else {
            await showAlert('Error', r.message);
        }
    } catch(e) { await showAlert('Error', e.message); }
}

document.getElementById('file-tree').addEventListener('contextmenu', function(e) {
    e.preventDefault();
    ctxPath = ''; ctxIsDir = true;
    showCtxMenu(e.clientX, e.clientY, true);
});

async function showDiff(filePath) {
    var backups = JSON.parse(await pywebview.api.list_backups(filePath));
    if (backups.length === 0) {
        await showAlert('Diff', 'No backups found for this file.');
        return;
    }
    // Use the most recent backup
    var latestBackup = backups[0];
    var backupContent = await pywebview.api.read_backup(latestBackup.filename, filePath);
    var currentContent = await pywebview.api.read_file(filePath);
    if (typeof currentContent !== 'string') currentContent = '';

    var modal = createModal();
    modal.box.style.cssText = 'width:90vw;max-width:1200px;height:80vh;';
    modal.box.innerHTML =
        '<div class="modal-title">🔍 Diff: ' + escapeHtml(filePath) +
        ' <span style="font-size:11px;color:#8b949e;">Backup: ' + escapeHtml(latestBackup.time) + '</span>' +
        '<span class="modal-close">✖</span></div>' +
        '<div class="modal-body" style="flex:1;padding:0;overflow:hidden;" id="diff-container"></div>' +
        '<div class="modal-footer"><button class="modal-btn modal-btn-cancel" id="diff-close">Close</button></div>';

    modal.box.querySelector('.modal-close').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#diff-close').onclick = function() { modal.overlay.remove(); };
    modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };

    document.body.appendChild(modal.overlay);

    // Monaco Diff Editor
    var ext = filePath.split('.').pop();
    var langMap = { py:'python', vigo:'vigo', js:'javascript', html:'html', css:'css', json:'json', md:'markdown' };
    var lang = langMap[ext] || 'plaintext';

    var diffEditor = monaco.editor.createDiffEditor(document.getElementById('diff-container'), {
        theme: 'vs-dark',
        fontSize: 13,
        enableSplitViewResizing: true,
        renderSideBySide: true,
        readOnly: true,
    });
    diffEditor.setModel({
        original: monaco.editor.createModel(backupContent, lang),
        modified: monaco.editor.createModel(currentContent, lang),
    });
}

async function openFile(path, name) {
    // Check if tab already exists
    var existing = openTabs.find(function(t) { return t.path === path; });
    if (!existing) {
        openTabs.push({path: path, name: name});
    }
    activeTabPath = path;
    renderTabs();
    // Load content from cache or disk
    if (fileContents[path] !== undefined) {
        editor.setValue(fileContents[path]);
    } else {
        try {
            var content = await pywebview.api.read_file(path);
            fileContents[path] = content;
            editor.setValue(content);
        } catch(e) { console.error(e); }
    }
    var ext = path.split('.').pop();
    var m = { py: 'python', vigo: 'vigo', js: 'javascript', html: 'html', css: 'css', json: 'json', md: 'markdown' };
    monaco.editor.setModelLanguage(editor.getModel(), m[ext] || 'plaintext');
    document.getElementById('status-file').textContent = path;
    saveProjectStateOnly();
}

function renderTabs() {
    var container = document.getElementById('editor-tabs');
    container.innerHTML = '';
    openTabs.forEach(function(tab) {
        var span = document.createElement('span');
        span.className = 'tab' + (tab.path === activeTabPath ? ' active' : '');
        span.textContent = tab.name;
        span.onclick = function() { switchTab(tab.path); };
        // Close button
        var closeBtn = document.createElement('span');
        closeBtn.textContent = ' ✖';
        closeBtn.style.cssText = 'font-size:10px;color:#484f58;cursor:pointer;margin-left:4px;';
        closeBtn.onclick = function(e) {
            e.stopPropagation();
            closeTab(tab.path);
        };
        span.appendChild(closeBtn);
        container.appendChild(span);
    });
}

function switchTab(path) {
    // Save current editor content to cache
    if (activeTabPath) {
        fileContents[activeTabPath] = editor.getValue();
    }
    activeTabPath = path;
    editor.setValue(fileContents[path] || '');
    var ext = path.split('.').pop();
    var m = { py: 'python', vigo: 'vigo', js: 'javascript', html: 'html', css: 'css', json: 'json', md: 'markdown' };
    monaco.editor.setModelLanguage(editor.getModel(), m[ext] || 'plaintext');
    document.getElementById('status-file').textContent = path;
    pywebview.api.read_file(path);  // Update backend current_file
    renderTabs();
}

function closeTab(path) {
    if (openTabs.length <= 1) return;  // Keep at least one tab
    // Save content before closing
    if (activeTabPath === path) {
        fileContents[path] = editor.getValue();
    }
    openTabs = openTabs.filter(function(t) { return t.path !== path; });
    delete fileContents[path];
    if (activeTabPath === path) {
        activeTabPath = openTabs[0].path;
        editor.setValue(fileContents[activeTabPath] || '');
        var ext = activeTabPath.split('.').pop();
        var m = { py: 'python', vigo: 'vigo', js: 'javascript', html: 'html', css: 'css', json: 'json', md: 'markdown' };
        monaco.editor.setModelLanguage(editor.getModel(), m[ext] || 'plaintext');
        document.getElementById('status-file').textContent = activeTabPath;
    }
    renderTabs();
    saveProjectStateOnly();
}

async function saveCurrentFile() {
    try {
        if (activeTabPath) {
            var content = editor.getValue();
            fileContents[activeTabPath] = content;
            await pywebview.api.save_file(activeTabPath, content);
        }
    } catch(e) { console.error(e); }
}

/* ═══════════════════════════════════════
   Drag & Drop Files into Editor
   ═══════════════════════════════════════ */
document.addEventListener('dragover', function(e) { e.preventDefault(); });
document.addEventListener('drop', async function(e) {
    e.preventDefault();
    var files = e.dataTransfer.files;
    if (!files || files.length === 0) return;
    for (var i = 0; i < files.length; i++) {
        var f = files[i];
        var path = f.path;
        if (!path) continue;
        var name = path.split('\\').pop().split('/').pop();
        var ext = name.split('.').pop().toLowerCase();
        openFile(path, name);
    }
});

document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); saveCurrentFile(); }
});

/* ═══════════════════════════════════════
   Models
   ═══════════════════════════════════════ */

async function loadModels() {
    // Models are loaded on-demand via showModelPicker, nothing to pre-populate
}

function mi(m, isActive) {
    var d = document.createElement('div');
    d.className = 'menu-dropdown-item';
    d.innerHTML = (isActive ? '<span class="model-active-dot"></span>' : '<span style="display:inline-block;width:12px"></span>') + '  ' + escapeHtml(m.name || m.id);
    d.onclick = function(e) { e.stopPropagation(); selectModel(m.id, m.provider); };
    return d;
}

async function showModelPicker() {
    try {
        var models = JSON.parse(await pywebview.api.list_models());
        if (models.length === 0) {
            await showAlert('Model', 'No models available.');
            return;
        }
        var currentModelText = document.getElementById('status-model').textContent.replace('Model: ', '').trim();
        var modal = createModal();
        var listHtml = '';
        models.forEach(function(m) {
            var mid = m.id || m.name || '';
            var isActive = (mid === currentModelText || m.name === currentModelText);
            listHtml += '<div class="modal-backup-item' + (isActive ? ' selected' : '') + '" data-id="' + escapeHtml(mid) + '" data-provider="' + escapeHtml(m.provider || 'ollama') + '">' +
                (isActive ? '<span class="model-active-dot"></span>' : '') +
                '<span>' + escapeHtml(m.name || mid) + '</span>' +
                '</div>';
        });
        modal.box.innerHTML =
            '<div class="modal-title">🤖 Select Model</div>' +
            '<div class="modal-body"><div class="modal-backup-list">' + listHtml + '</div></div>' +
            '<div class="modal-footer"><button class="modal-btn modal-btn-cancel">Cancel</button></div>';
        
        var selectedId = null;
        var selectedProvider = null;
        var items = modal.box.querySelectorAll('.modal-backup-item');
        items.forEach(function(item) {
            item.onclick = function() {
                items.forEach(function(i) { i.classList.remove('selected'); });
                this.classList.add('selected');
                selectedId = this.getAttribute('data-id');
                selectedProvider = this.getAttribute('data-provider');
                modal.overlay.remove();
                if (activeChatId && chatSessions[activeChatId] && chatSessions[activeChatId].type === 'master') {
                    selectChatModel(selectedId, selectedProvider);
                } else {
                    selectModel(selectedId, selectedProvider);
                }
            };
        });
        modal.box.querySelector('.modal-btn-cancel').onclick = function() { modal.overlay.remove(); };
        modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };
    } catch(e) { await showAlert('Error', e.message); }
}

async function showModels() {
    var modal = createModal();
    modal.box.style.minWidth = '480px';
    modal.box.style.maxWidth = '560px';
    modal.box.innerHTML =
        '<div class="modal-title">🤖 Models<span class="modal-close">✖</span></div>' +
        '<div class="modal-body" style="max-height:60vh;overflow-y:auto;" id="models-body">Loading...</div>' +
        '<div class="modal-footer">' +
        '<button class="modal-btn modal-btn-cancel" id="models-refresh">🔄 Refresh</button>' +
        '<button class="modal-btn modal-btn-cancel" id="models-close">Close</button>' +
        '</div>';

    modal.box.querySelector('.modal-close').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#models-close').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#models-refresh').onclick = async function() {
        await loadModelsList(modal.box);
    };
    modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };

    await loadModelsList(modal.box);
}

/* ═══════════════════════════════════════
   Git Panel
   ═══════════════════════════════════════ */

async function showGitPanel() {
    var modal = createModal();
    modal.box.style.minWidth = '480px';
    modal.box.style.maxWidth = '560px';
    modal.box.innerHTML =
        '<div class="modal-title" style="display:flex;justify-content:space-between;align-items:center;">' +
        '<span>🔀 Git</span><span class="modal-close">✖</span></div>' +
        '<div class="modal-body" style="max-height:55vh;overflow-y:auto;" id="git-body">Loading...</div>' +
        '<div class="modal-footer" id="git-footer"></div>';

    modal.box.querySelector('.modal-close').onclick = function() { modal.overlay.remove(); };
    modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };

    window._gitBox = modal.box;
    await loadGitPanel(modal.box);
}

async function loadGitPanel(box) {
    var body = box.querySelector('#git-body');
    body.innerHTML = 'Loading...';

    var statusData, branchData;
    try {
        statusData = JSON.parse(await pywebview.api.git_status());
        branchData = JSON.parse(await pywebview.api.git_branches());
    } catch(e) {
        body.innerHTML = '<div style="color:#f85149;padding:12px;">Git is not available or this is not a git repository.</div>';
        return;
    }

    var html = '';

    // Branches section
    html += '<div class="git-section-title">▸ Branches</div><div class="git-branch-row">';
    if (branchData.status === 'ok' && branchData.branches) {
        branchData.branches.forEach(function(b) {
            html += '<span class="git-branch-tag' + (b.current ? ' current' : '') + '" onclick="gitSwitchBranch(\'' + escapeHtml(b.name) + '\')">' + escapeHtml(b.name) + '</span>';
        });
    }
    html += '<span class="git-branch-add" onclick="gitNewBranch()" title="New Branch">+</span></div>';

    // Changes section
    html += '<div class="git-section-title">▸ Changes</div>';
    if (statusData.status === 'ok') {
        var files = statusData.files || [];
        if (files.length === 0) {
            html += '<div class="git-clean">✅ Working tree clean</div>';
        } else {
            files.forEach(function(f) {
                var cls = 'git-status-' + f.status[0];
                var icon = f.status[0] === 'M' ? '✏️' : (f.status[0] === 'A' ? '➕' : (f.status[0] === 'D' ? '🗑' : '❓'));
                html += '<div class="git-file-row" onclick="openFile(\'' + escapeHtml(f.file) + '\',\'' + escapeHtml(f.file.split('/').pop()) + '\')"><span class="' + cls + '">' + icon + ' ' + escapeHtml(f.status) + '</span><span class="git-file-name">' + escapeHtml(f.file) + '</span></div>';
            });
        }
    } else {
        html += '<div style="color:#f85149;font-size:12px;">' + escapeHtml(statusData.message || 'Error') + '</div>';
    }

    body.innerHTML = html;

    // Footer with actions
    var footer = box.querySelector('#git-footer');
    footer.innerHTML = '';

    // Refresh button always
    var refreshBtn = document.createElement('button');
    refreshBtn.className = 'modal-btn modal-btn-cancel';
    refreshBtn.textContent = '🔄 Refresh';
    refreshBtn.onclick = function() { loadGitPanel(box); };
    refreshBtn.style.marginRight = '8px';
    footer.appendChild(refreshBtn);

    if (statusData.status === 'ok' && statusData.files && statusData.files.length > 0) {
        // Commit section
        var input = document.createElement('input');
        input.className = 'git-commit-input';
        input.id = 'git-commit-msg';
        input.placeholder = 'Commit message...';
        footer.appendChild(input);
        
        var row = document.createElement('div');
        row.style.cssText = 'display:flex;gap:8px;margin-top:6px;';
        row.innerHTML =
            '<button class="modal-btn modal-btn-confirm" onclick="gitDoCommit()">💾 Commit</button>' +
            '<button class="modal-btn modal-btn-cancel" onclick="gitDoPush()">📤 Push</button>' +
            '<button class="modal-btn modal-btn-cancel" onclick="gitDoPull()">📥 Pull</button>';
        footer.appendChild(row);
    } else {
        var row2 = document.createElement('div');
        row2.style.cssText = 'display:flex;gap:8px;';
        row2.innerHTML =
            '<button class="modal-btn modal-btn-cancel" onclick="gitDoPull()">📥 Pull</button>';
        footer.appendChild(row2);
    }
}

async function gitDoCommit() {
    var msg = document.getElementById('git-commit-msg');
    if (!msg || !msg.value.trim()) { await showAlert('Git', 'Please enter a commit message.'); return; }
    try {
        var r = JSON.parse(await pywebview.api.git_commit(msg.value.trim()));
        if (r.status === 'ok') {
            await showAlert('✅ Git', r.message || 'Committed successfully.');
            if (window._gitBox) loadGitPanel(window._gitBox);
        } else {
            await showAlert('❌ Git Error', r.message);
        }
    } catch(e) { await showAlert('Error', e.message); }
}

async function gitDoPush() {
    try {
        var r = JSON.parse(await pywebview.api.git_push());
        if (r.status === 'ok') {
            await showAlert('✅ Git', r.message || 'Pushed successfully.');
        } else {
            await showAlert('❌ Git Error', r.message);
        }
    } catch(e) { await showAlert('Error', e.message); }
}

async function gitDoPull() {
    try {
        var r = JSON.parse(await pywebview.api.git_pull());
        if (r.status === 'ok') {
            await showAlert('✅ Git', r.message || 'Pulled successfully.');
            if (window._gitBox) loadGitPanel(window._gitBox);
        } else {
            await showAlert('❌ Git Error', r.message);
        }
    } catch(e) { await showAlert('Error', e.message); }
}

async function gitSwitchBranch(name) {
    var ok = await showConfirm('Git', 'Switch to branch "' + name + '"?');
    if (!ok) return;
    try {
        var r = JSON.parse(await pywebview.api.git_checkout(name));
        if (r.status === 'ok') {
            await showAlert('✅ Git', r.message);
            if (window._gitBox) loadGitPanel(window._gitBox);
            loadFileTree();
        } else {
            await showAlert('❌ Git Error', r.message);
        }
    } catch(e) { await showAlert('Error', e.message); }
}

async function gitNewBranch() {
    var name = await showInput('New Branch', 'Branch name:');
    if (!name) return;
    try {
        var r = JSON.parse(await pywebview.api.git_create_branch(name.trim()));
        if (r.status === 'ok') {
            await showAlert('✅ Git', r.message);
            if (window._gitBox) loadGitPanel(window._gitBox);
            loadFileTree();
        } else {
            await showAlert('❌ Git Error', r.message);
        }
    } catch(e) { await showAlert('Error', e.message); }
}

async function loadModelsList(box) {
    var body = box.querySelector('#models-body');
    body.innerHTML = 'Loading...';
    try {
        var data = JSON.parse(await pywebview.api.list_available_models());
        var installed = data.installed || {};
        var available = data.available || [];

        var html = '';
        // Installed
        html += '<div class="model-section-title">✅ Installed</div>';
        var instKeys = Object.keys(installed);
        if (instKeys.length === 0) {
            html += '<div style="color:#8b949e;font-size:11px;padding:6px 0;">No models installed.</div>';
        } else {
            for (var name in installed) {
                var safeId = name.replace(/:/g, '_');
                html += '<div class="model-card" id="model-card-' + safeId + '">' +
                    '<div style="flex:1"><div class="model-name">🟢 ' + escapeHtml(name) + '</div></div>' +
                    '<div class="model-size">' + escapeHtml(installed[name]) + '</div>' +
                    '<button class="model-btn" style="margin-left:8px;" onclick="deleteModel(\'' + escapeHtml(name) + '\')">🗑</button>' +
                    '</div>';
            }
        }

        // Available
        html += '<div class="model-section-title">⬇ Available to Download</div>';
        if (available.length === 0) {
            html += '<div style="color:#8b949e;font-size:11px;padding:6px 0;">All popular models are already installed.</div>';
        } else {
            available.forEach(function(m) {
                html += '<div class="model-card" id="model-card-' + escapeHtml(m.name.replace(/:/g, '_')) + '">' +
                    '<div style="flex:1"><div class="model-name">' + escapeHtml(m.name) + '</div>' +
                    '<div class="model-desc">' + escapeHtml(m.desc) + '</div></div>' +
                    '<div style="text-align:right">' +
                    '<div class="model-size">' + escapeHtml(m.size) + '</div>' +
                    '<button class="model-btn download" onclick="startDownload(\'' + escapeHtml(m.name) + '\')">⬇ Download</button>' +
                    '</div>' +
                    '</div>';
            });
        }

        body.innerHTML = html;
    } catch(e) {
        body.innerHTML = '<div style="color:#f85149;">Error: ' + escapeHtml(e.message) + '</div>';
    }
}

async function startDownload(modelName) {
    if (!window._downloadIntervals) window._downloadIntervals = {};
    if (window._downloadIntervals[modelName]) {
        clearInterval(window._downloadIntervals[modelName]);
    }

    try {
        var r = JSON.parse(await pywebview.api.download_model(modelName));
        if (r.status === 'ok') {
            var card = document.getElementById('model-card-' + modelName.replace(/:/g, '_'));
            if (card) {
                var btn = card.querySelector('.model-btn');
                if (btn) { btn.style.display = 'none'; }
                var progBar = document.createElement('div');
                progBar.className = 'model-download-progress';
                progBar.innerHTML = '<div class="model-download-fill" style="width:0%"></div>';
                card.appendChild(progBar);

                var cancelBtn = document.createElement('button');
                cancelBtn.textContent = '✖ Cancel';
                cancelBtn.className = 'model-btn';
                cancelBtn.style.cssText = 'font-size:10px;margin-top:4px;';
                cancelBtn.onclick = async function() {
                    clearInterval(window._downloadIntervals[modelName]);
                    delete window._downloadIntervals[modelName];
                    progBar.remove();
                    cancelBtn.remove();
                    if (btn) { btn.style.display = 'inline-block'; }
                    await pywebview.api.cancel_download(modelName);
                };
                card.appendChild(cancelBtn);

                var startTime = Date.now();
                var cardText = card.textContent || '';
                var sizeMatch = cardText.match(/(\d+\.?\d*)\s*GB/);
                var estimatedSeconds = 180;
                if (sizeMatch) {
                    var gb = parseFloat(sizeMatch[1]);
                    estimatedSeconds = Math.min(600, Math.max(60, gb * 40));
                }

                window._downloadIntervals[modelName] = setInterval(async function() {
                    try {
                        var p = JSON.parse(await pywebview.api.get_download_progress(modelName));
                        var realProgress = p.progress || 0;
                        var elapsed = (Date.now() - startTime) / 1000;
                        var simulated = Math.min(95, Math.round((elapsed / estimatedSeconds) * 95));
                        var displayProgress = Math.max(simulated, realProgress);

                        var fill = progBar.querySelector('.model-download-fill');
                        if (fill) fill.style.width = displayProgress + '%';

                        if (realProgress >= 100) {
                            clearInterval(window._downloadIntervals[modelName]);
                            delete window._downloadIntervals[modelName];
                            cancelBtn.remove();
                            progBar.remove();
                            if (btn) { btn.textContent = '✅ Done'; btn.style.display = 'inline-block'; btn.className = 'model-btn'; }
                            setTimeout(function() { loadModelsList(document.getElementById('models-body').parentElement); }, 1000);
                        } else if (realProgress < 0) {
                            clearInterval(window._downloadIntervals[modelName]);
                            delete window._downloadIntervals[modelName];
                            cancelBtn.remove();
                            progBar.remove();
                            if (btn) { btn.textContent = '❌ Failed'; btn.style.display = 'inline-block'; btn.className = 'model-btn'; }
                        }
                    } catch(e) {
                        clearInterval(window._downloadIntervals[modelName]);
                        delete window._downloadIntervals[modelName];
                    }
                }, 800);
            }
        } else {
            await showAlert('Error', r.message);
        }
    } catch(e) {
        await showAlert('Error', e.message);
    }
}

async function deleteModel(modelName) {
    var ok = await showConfirm('Delete Model', 'Delete ' + modelName + '? This cannot be undone.');
    if (!ok) return;
    try {
        var r = JSON.parse(await pywebview.api.delete_model(modelName));
        if (r.status === 'ok') {
            await showAlert('Deleted', r.message);
            var box = document.getElementById('models-body');
            if (box) {
                await loadModelsList(box.parentElement);
            }
        } else {
            await showAlert('Error', r.message);
        }
    } catch(e) {
        await showAlert('Error', e.message);
    }
}

/* ═══════════════════════════════════════
   Multi-Chat Management
   ═══════════════════════════════════════ */

function newChat() {
    chatCounter++;
    var id = 'chat_' + chatCounter;
    var name = 'Chat ' + chatCounter;
    chatSessions[id] = { id: id, name: name, type: 'master', parentId: null, messages: [], collapsed: false };
    switchChat(id);
    saveProjectStateOnly();
}

function switchChat(chatId) {
    if (activeChatId && chatSessions[activeChatId]) {
        chatSessions[activeChatId].messages = Array.from(document.getElementById('chat-messages').children);
    }
    activeChatId = chatId;
    var container = document.getElementById('chat-messages');
    container.innerHTML = '';
    var session = chatSessions[chatId];
    if (session && session.messages) {
        session.messages.forEach(function(el) { container.appendChild(el); });
    }
    var modelBtn = document.getElementById('chat-model-btn');
    var delegateBar = document.getElementById('delegate-bar');
    var isMaster = session && session.type === 'master';
    if (isMaster) {
        modelBtn.style.display = 'inline';
    } else {
        modelBtn.style.display = 'none';
    }
    container.querySelectorAll('.delegate-radio').forEach(function(r) {
        r.style.display = isMaster ? 'block' : 'none';
    });
    if (!isMaster) {
        cancelDelegate();
    }
    renderChatTabs();
    container.scrollTop = container.scrollHeight;
}

async function closeConversation(chatId, e) {
    if (e) e.stopPropagation();
    var keys = Object.keys(chatSessions);
    if (keys.length <= 1) return;
    var session = chatSessions[chatId];
    if (!session) return;

    // Build messages array for archiving
    var messages = [];
    var msgList = session.messages || [];
    msgList.forEach(function(el) {
        var isUser = el.classList && el.classList.contains('user');
        var isAi = el.classList && el.classList.contains('ai');
        if (isUser || isAi) {
            messages.push({
                role: isUser ? 'user' : 'ai',
                content: el.textContent || el.innerText || ''
            });
        }
    });

    // Archive conversation
    if (messages.length > 0) {
        try {
            await pywebview.api.save_conversation(
                chatId,
                session.type || 'master',
                JSON.stringify(messages),
                session.taskDescription || ''
            );
        } catch(e) { console.error('Archive error: ' + e.message); }
    }

    // Switch away first, then delete
    if (activeChatId === chatId) {
        var nextId = keys.filter(function(k) { return k !== chatId; })[0];
        switchChat(nextId);
    }
    delete chatSessions[chatId];
    renderChatTabs();
    saveProjectStateOnly();
}

function closeChat(chatId, e) {
    closeConversation(chatId, e);
}

function toggleMasterCollapse(chatId, e) {
    if (e) e.stopPropagation();
    var session = chatSessions[chatId];
    if (!session || session.type !== 'master') return;
    session.collapsed = !session.collapsed;
    renderChatTabs();
}

function renderChatTabs() {
    var container = document.getElementById('chat-tabs');
    if (!container) return;
    container.innerHTML = '';
    
    // Build ordered list: masters followed by their visible workers
    var ordered = [];
    var ids = Object.keys(chatSessions);
    var placed = {};
    
    ids.forEach(function(id) {
        if (placed[id]) return;
        var s = chatSessions[id];
        if (s.type === 'master' || !s.parentId) {
            ordered.push(id);
            placed[id] = true;
            // Add visible workers of this master
            ids.forEach(function(wid) {
                if (placed[wid]) return;
                var ws = chatSessions[wid];
                if (ws.type === 'worker' && ws.parentId === id) {
                    if (!s.collapsed) {
                        ordered.push(wid);
                    }
                    placed[wid] = true;
                }
            });
        }
    });
    // Add any unplaced workers (orphans)
    ids.forEach(function(id) {
        if (!placed[id]) ordered.push(id);
    });
    
    ordered.forEach(function(id) {
        var s = chatSessions[id];
        var tab = document.createElement('span');
        tab.className = 'chat-tab ' + s.type + (id === activeChatId ? ' active' : '');
        
        if (s.type === 'master') {
            var arrow = document.createElement('span');
            arrow.className = 'toggle-arrow';
            arrow.textContent = s.collapsed ? '▸' : '▾';
            arrow.onclick = function(e) { toggleMasterCollapse(id, e); };
            tab.appendChild(arrow);
        }
        
        var dot = document.createElement('span');
        dot.className = 'dot ' + (s.type === 'master' ? 'green' : 'gray');
        tab.appendChild(dot);
        
        var label = document.createElement('span');
        label.textContent = s.name;
        tab.appendChild(label);
        
        var closeBtn = document.createElement('span');
        closeBtn.className = 'close-tab';
        closeBtn.textContent = '✖';
        closeBtn.onclick = function(e) { closeChat(id, e); };
        tab.appendChild(closeBtn);

        // Right-click context menu
        tab.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            e.stopPropagation();
            showChatCtxMenu(e.clientX, e.clientY, id);
        }, true);
        
        tab.onclick = function(e) {
            if (e.target.classList.contains('close-tab') || e.target.classList.contains('toggle-arrow')) return;
            if (e.button !== 0) return;
            switchChat(id);
        };
        container.appendChild(tab);
    });
}

function showChatCtxMenu(x, y, chatId) {
    var old = document.querySelector('.chat-ctx-menu');
    if (old) old.remove();

    var menu = document.createElement('div');
    menu.className = 'menu-dropdown chat-ctx-menu';
    menu.style.cssText = 'display:block;position:fixed;left:' + x + 'px;top:' + y + 'px;z-index:7000;min-width:140px;';

    var renameItem = document.createElement('div');
    renameItem.className = 'menu-dropdown-item';
    renameItem.textContent = '✏️ Rename';
    renameItem.onclick = async function() {
        menu.remove();
        var session = chatSessions[chatId];
        if (!session) return;
        var newName = await showInput('Rename', 'New name:', session.name);
        if (newName) {
            session.name = newName;
            renderChatTabs();
        }
    };
    menu.appendChild(renameItem);

    document.body.appendChild(menu);

    function closeMenu(e) {
        if (!menu.contains(e.target)) {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }
    }
    setTimeout(function() {
        document.addEventListener('click', closeMenu);
    }, 0);
}

/* ═══════════════════════════════════════
   Delegate Selection
   ═══════════════════════════════════════ */

var selectedDelegateMsg = null;
var selectedDelegateRadio = null;

function selectForDelegate(msgDiv, radio) {
    if (selectedDelegateRadio) {
        selectedDelegateRadio.classList.remove('selected');
    }
    if (selectedDelegateMsg === msgDiv) {
        selectedDelegateMsg = null;
        selectedDelegateRadio = null;
        document.getElementById('delegate-bar').style.display = 'none';
        return;
    }
    selectedDelegateMsg = msgDiv;
    selectedDelegateRadio = radio;
    radio.classList.add('selected');
    document.getElementById('delegate-bar').style.display = 'flex';
}

function cancelDelegate() {
    if (selectedDelegateRadio) {
        selectedDelegateRadio.classList.remove('selected');
    }
    selectedDelegateMsg = null;
    selectedDelegateRadio = null;
    document.getElementById('delegate-bar').style.display = 'none';
}

async function confirmDelegate() {
    if (!selectedDelegateMsg || !activeChatId) return;
    var session = chatSessions[activeChatId];
    if (!session || session.type !== 'master') {
        await showAlert('Delegate', 'Only master chats can create workers.');
        cancelDelegate();
        return;
    }
    var text = selectedDelegateMsg.textContent || selectedDelegateMsg.innerText || '';
    var task = await showInput('Delegate to Worker', 'Task description:', text.substring(0, 300));
    if (!task) { cancelDelegate(); return; }
    chatCounter++;
    var workerId = 'chat_' + chatCounter;
    var workerName = 'Worker: ' + task.substring(0, 20);
    chatSessions[workerId] = { id: workerId, name: workerName, type: 'worker', parentId: activeChatId, messages: [] };
    cancelDelegate();
    switchChat(workerId);
    document.getElementById('chat-input').value = task;
}

async function selectModel(id, provider) {
    var oldModel = document.getElementById('status-model').textContent.replace('Model: ', '').trim();
    await pywebview.api.set_model(id, provider);
    document.getElementById('status-model').textContent = 'Model: ' + id;
    if (oldModel && oldModel !== id) {
        var c = document.getElementById('chat-messages');
        var sep = document.createElement('div');
        sep.className = 'chat-separator';
        sep.textContent = 'Switched to ' + id;
        c.appendChild(sep);
        c.scrollTop = c.scrollHeight;
    }
    await showAlert('Model Changed', 'Switched to ' + id);
}

async function selectChatModel(id, provider) {
    if (!activeChatId) return;
    await pywebview.api.set_chat_model(activeChatId, id, provider);
    await showAlert('Model Changed', 'Chat model switched to ' + id);
}

/* ═══════════════════════════════════════
   Chat
   ═══════════════════════════════════════ */

function escapeHtml(t) {
    return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function appendMessage(role, text) {
    var c = document.getElementById('chat-messages');
    var div = document.createElement('div');
    div.className = 'message ' + role;
    if (text.indexOf('```') !== -1) {
        var h = '';
        text.split('```').forEach(function(p, i) {
            if (i % 2 === 1) h += '<pre><code>' + escapeHtml(p) + '</code></pre>';
            else h += escapeHtml(p);
        });
        div.innerHTML = h;
    } else {
        div.textContent = text;
    }
    if (role === 'ai') {
        var radio = document.createElement('div');
        radio.className = 'delegate-radio';
        radio.onclick = function(e) { e.stopPropagation(); selectForDelegate(div, radio); };
        div.appendChild(radio);
    }
    var copyBtn = document.createElement('div');
    copyBtn.textContent = '📋 Copy';
    copyBtn.style.cssText = 'margin-top:6px;font-size:11px;color:#8b949e;cursor:pointer;text-align:right;';
    copyBtn.onclick = function() {
        pywebview.api.copy_to_clipboard(text).then(function() {
            copyBtn.textContent = '✅ Copied!';
            setTimeout(function() { copyBtn.textContent = '📋 Copy'; }, 1500);
        });
    };
    div.appendChild(copyBtn);
    c.appendChild(div);
    c.scrollTop = c.scrollHeight;
}

async function sendMessage() {
    if (window._sendingLock) return;
    var input = document.getElementById('chat-input');
    var msg = input.value.trim();
    if (!msg || !activeChatId) return;
    
    var myChatId = activeChatId;
    window._sendingLock = true;

    // Auto memory recall — use backend history
    var memoryContext = '';
    if (settingsData.memory_mode !== 'manual') {
        try {
            var memStatus = showAiStatus('📚 Reading past conversations...');
            document.getElementById('btn-send').disabled = true;
            var history = JSON.parse(await pywebview.api.get_chat_history(myChatId));
            if (history && history.length > 0) {
                memoryContext = 'Previous conversation with the user:\n';
                history.forEach(function(entry) {
                    memoryContext += 'User: ' + (entry.user || '') + '\nAssistant: ' + (entry.ai || '') + '\n';
                });
            }
            removeAiStatus(memStatus);
        } catch(e) {}
    }

    // Build the actual message sent to AI (with memory context prepended silently)
    var aiMessage = memoryContext ? memoryContext + '\nUser question: ' + msg : msg;

    // Show user message in chat (without memory context)
    appendMessage('user', msg);
    input.value = '';
    input.value = '';
    document.getElementById('btn-send').disabled = true;

    var statusDiv = showAiStatus('🤔 Thinking...');
    var filesChanged = [];

    try {
        var currentMsg = aiMessage;
        for (var round = 0; round < 5; round++) {
            var r = JSON.parse(await pywebview.api.ask_ai(currentMsg, myChatId));
            if (r.status === 'error') {
                if (activeChatId === myChatId) {
                    removeAiStatus(statusDiv);
                    appendMessage('ai', 'Error: ' + (r.response || 'Unknown'));
                }
                break;
            }
            if (r.action === 'tool') {
                var toolLabel = r.tool;
                if (r.tool === 'READ') toolLabel = '📖 Reading ' + (r.path || 'file') + '...';
                else if (r.tool === 'WRITE') { toolLabel = '✏️ Writing ' + (r.path || 'file') + '...'; filesChanged.push(r.path); }
                else if (r.tool === 'CREATE') { toolLabel = '📄 Creating ' + (r.path || 'file') + '...'; filesChanged.push(r.path); }
                else if (r.tool === 'SEARCH') toolLabel = '🔍 Searching: ' + (r.query || '...');
                if (activeChatId === myChatId) updateAiStatus(statusDiv, toolLabel);
                currentMsg = '';
            } else if (r.action === 'done') {
                if (activeChatId === myChatId) {
                    removeAiStatus(statusDiv);
                    if (r.chunks && r.chunks.length > 0) {
                        appendMessageStream('ai', r.chunks, r.response, r.elapsed);
                    } else {
                        appendMessage('ai', r.response + '\n\n⏱️ ' + r.elapsed + 's');
                    }
                } else {
                    removeAiStatus(statusDiv);
                    var cachedDiv = document.createElement('div');
                    cachedDiv.className = 'message ai';
                    cachedDiv.textContent = r.response;
                    var cachedRadio = document.createElement('div');
                    cachedRadio.className = 'delegate-radio';
                    cachedRadio.onclick = function(e) { e.stopPropagation(); selectForDelegate(cachedDiv, cachedRadio); };
                    cachedDiv.appendChild(cachedRadio);
                    var copyBtn = document.createElement('div');
                    copyBtn.textContent = '📋 Copy';
                    copyBtn.style.cssText = 'margin-top:6px;font-size:11px;color:#8b949e;cursor:pointer;text-align:right;';
                    copyBtn.onclick = function() {
                        pywebview.api.copy_to_clipboard(r.response).then(function() {
                            copyBtn.textContent = '✅ Copied!';
                            setTimeout(function() { copyBtn.textContent = '📋 Copy'; }, 1500);
                        });
                    };
                    cachedDiv.appendChild(copyBtn);
                    var timeSpan = document.createElement('div');
                    timeSpan.textContent = '⏱️ ' + r.elapsed + 's';
                    timeSpan.style.cssText = 'margin-top:4px;font-size:10px;color:#484f58;text-align:right;';
                    cachedDiv.appendChild(timeSpan);
                    if (!chatSessions[myChatId].messages) chatSessions[myChatId].messages = [];
                    chatSessions[myChatId].messages.push(cachedDiv);
                }
                if (filesChanged.length > 0) {
                    var cf = await pywebview.api.get_current_file();
                    if (cf && filesChanged.indexOf(cf) !== -1) {
                        var content = await pywebview.api.read_file(cf);
                        if (activeChatId === myChatId) editor.setValue(content);
                    }
                    loadFileTree();
                }
                if (chatSessions[myChatId] && chatSessions[myChatId].type === 'worker') {
                    var parentId = chatSessions[myChatId].parentId;
                    if (parentId && chatSessions[parentId]) {
                        chatSessions[myChatId].resultSummary = r.response.substring(0, 200);
                    }
                }
                break;
            }
        }
    } catch(e) {
        if (activeChatId === myChatId) {
            removeAiStatus(statusDiv);
            appendMessage('ai', 'Error: ' + e.message);
        }
    }
    if (activeChatId === myChatId) {
        document.getElementById('btn-send').disabled = false;
    }
    window._sendingLock = false;
}

function showAiStatus(text) {
    var c = document.getElementById('chat-messages');
    var div = document.createElement('div');
    div.className = 'ai-status';
    div.innerHTML = '<span class="dot"></span>' + escapeHtml(text);
    c.appendChild(div);
    c.scrollTop = c.scrollHeight;
    return div;
}

function updateAiStatus(div, text) {
    if (div) {
        div.innerHTML = '<span class="dot"></span>' + escapeHtml(text);
        document.getElementById('chat-messages').scrollTop = document.getElementById('chat-messages').scrollHeight;
    }
}

function removeAiStatus(div) {
    if (div && div.parentNode) {
        div.parentNode.removeChild(div);
    }
}

function appendMessageStream(role, chunks, fullText, elapsed) {
    var c = document.getElementById('chat-messages');
    var div = document.createElement('div');
    div.className = 'message ' + role;
    var span = document.createElement('span');
    div.appendChild(span);
    c.appendChild(div);
    c.scrollTop = c.scrollHeight;
    var i = 0;
    function showNext() {
        if (i < chunks.length) {
            span.textContent += chunks[i];
            c.scrollTop = c.scrollHeight;
            i++;
            setTimeout(showNext, 15);
        } else {
            span.remove();
            if (fullText.indexOf('```') !== -1) {
                var h = '';
                fullText.split('```').forEach(function(p, j) {
                    if (j % 2 === 1) h += '<pre><code>' + escapeHtml(p) + '</code></pre>';
                    else h += escapeHtml(p);
                });
                div.innerHTML = h;
            } else {
                div.textContent = fullText;
            }
            if (role === 'ai') {
                var radio = document.createElement('div');
                radio.className = 'delegate-radio';
                radio.onclick = function(e) { e.stopPropagation(); selectForDelegate(div, radio); };
                div.appendChild(radio);
            }
            var timeSpan = document.createElement('div');
            timeSpan.textContent = '⏱️ ' + elapsed + 's';
            timeSpan.style.cssText = 'margin-top:4px;font-size:10px;color:#484f58;text-align:right;';
            div.appendChild(timeSpan);
            var copyBtn = document.createElement('div');
            copyBtn.textContent = '📋 Copy';
            copyBtn.style.cssText = 'margin-top:4px;font-size:11px;color:#8b949e;cursor:pointer;text-align:right;';
            copyBtn.onclick = function() {
                pywebview.api.copy_to_clipboard(fullText).then(function() {
                    copyBtn.textContent = '✅ Copied!';
                    setTimeout(function() { copyBtn.textContent = '📋 Copy'; }, 1500);
                });
            };
            div.appendChild(copyBtn);
            c.scrollTop = c.scrollHeight;
        }
    }
    showNext();
}

document.getElementById('btn-send').onclick = sendMessage;
document.getElementById('chat-input').onkeydown = function(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
};

/* ═══════════════════════════════════════
   Terminal & Actions
   ═══════════════════════════════════════ */

async function runCurrentFile() {
    var cf = await pywebview.api.get_current_file();
    if (!cf) { appendTerminal('No file open.'); return; }
    if (!cf.endsWith('.vigo')) { appendTerminal('Only .vigo files can be run.'); return; }
    appendTerminal('▶️ Running: ' + cf + '\n');
    var r = JSON.parse(await pywebview.api.run_vigo_file(cf));
    appendTerminal(r.output + '\n' + (r.status === 'ok' ? '✅ Done.' : '❌ Failed.'));
}

function appendTerminal(text) {
    var t = document.getElementById('terminal');
    t.style.display = 'flex';
    var o = document.getElementById('terminal-output');
    o.textContent += text + '\n';
    o.scrollTop = o.scrollHeight;
}

function toggleTerminal() {
    var t = document.getElementById('terminal');
    t.style.display = t.style.display === 'none' ? 'flex' : 'none';
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'F5') { e.preventDefault(); runCurrentFile(); }
});

async function runTests() {
    appendMessage('ai', 'Running tests...');
    try {
        var r = JSON.parse(await pywebview.api.run_test());
        appendMessage('ai', (r.status === 'ok' ? '✅ Tests passed!\n' + r.stdout : '❌ Tests failed!\n' + r.stdout));
    } catch(e) { appendMessage('ai', 'Error: ' + e.message); }
}

async function showMemory() {
    try {
        var s = JSON.parse(await pywebview.api.mem_snapshot());
        appendMessage('ai', 'Memory: ' + s.total + ' items\nOldest: ' + (s.oldest || 'N/A') + '\nNewest: ' + (s.newest || 'N/A'));
    } catch(e) { appendMessage('ai', 'Error: ' + e.message); }
}

/* Create Project Modal */
function showCreateProjectModal() {
    var modal = createModal();
    modal.box.style.minWidth = '440px';
    modal.box.innerHTML =
        '<div class="modal-title">🆕 Create New Project<span class="modal-close">✖</span></div>' +
        '<div class="modal-body">' +
        '<div class="settings-field"><label>Project Name</label><input id="cp-name" style="width:100%" placeholder="my-app"></div>' +
        '<div class="settings-field"><label>Project Path</label><div style="display:flex;gap:4px;width:100%"><input id="cp-path" style="flex:1" value="F:\\ViGo\\vigo-dev\\Projects"><span onclick="selectCreatePath()" style="cursor:pointer;font-size:16px;padding:4px 6px;">📁</span></div></div>' +
        '<div class="settings-field"><label>Project Type</label>' +
        '<div style="display:flex;gap:16px;padding:4px 0;">' +
        '<label style="color:#c9d1d9;font-size:13px;cursor:pointer;"><input type="radio" name="cp-type" value="vigo" checked> ViGo (.vigo)</label>' +
        '<label style="color:#c9d1d9;font-size:13px;cursor:pointer;"><input type="radio" name="cp-type" value="python"> Python (.py)</label>' +
        '</div></div>' +
        '</div>' +
        '<div class="modal-footer">' +
        '<button class="modal-btn modal-btn-cancel" id="cp-cancel">Cancel</button>' +
        '<button class="modal-btn modal-btn-confirm" id="cp-create">Create Project</button>' +
        '</div>';

    modal.box.querySelector('.modal-close').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#cp-cancel').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#cp-create').onclick = async function() {
        var name = modal.box.querySelector('#cp-name').value.trim();
        var projType = modal.box.querySelector('input[name="cp-type"]:checked').value;
        if (!name) { await showAlert('Error', 'Project name is required.'); return; }
        modal.overlay.remove();
        try {
            var r = JSON.parse(await pywebview.api.create_project(name.trim()));
            if (r.status === 'ok') {
                if (projType === 'python') {
                    var mainPy = r.last_file ? r.last_file.replace('.vigo', '.py') : 'main.py';
                    await pywebview.api.create_file('', mainPy);
                    await pywebview.api.delete_item('main.vigo');
                }
                await loadProjects();
                loadFileTree();
                var firstFile = projType === 'python' ? 'main.py' : 'main.vigo';
                openFile(firstFile, firstFile);
            } else {
                await showAlert('Error', r.message || 'Failed');
            }
        } catch(e) { await showAlert('Error', e.message); }
    };
    modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };
}

async function selectCreatePath() {
    try {
        var folder = await pywebview.api.open_folder_dialog();
        if (folder) {
            document.getElementById('cp-path').value = folder;
        }
    } catch(e) {}
}

/* Open Project Modal */
function showOpenProjectModal() {
    var modal = createModal();
    modal.box.style.minWidth = '480px';
    modal.box.innerHTML =
        '<div class="modal-title">📂 Open Project<span class="modal-close">✖</span></div>' +
        '<div class="modal-body" style="max-height:50vh;overflow-y:auto;">' +
        '<input id="op-search" style="width:100%;margin-bottom:10px;" placeholder="🔍 Search projects...">' +
        '<div id="op-list">Loading...</div>' +
        '</div>' +
        '<div class="modal-footer">' +
        '<button class="modal-btn modal-btn-cancel" id="op-cancel">Cancel</button>' +
        '</div>';

    modal.box.querySelector('.modal-close').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#op-cancel').onclick = function() { modal.overlay.remove(); };
    modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };

    loadOpenProjectList(modal.box);
}

async function loadOpenProjectList(box, filter) {
    var container = box.querySelector('#op-list');
    try {
        var d = JSON.parse(await pywebview.api.list_projects());
        var projects = d.projects || [];
        if (filter) {
            projects = projects.filter(function(p) { return p.name.toLowerCase().indexOf(filter.toLowerCase()) >= 0; });
        }
        var html = '';
        if (projects.length === 0) {
            html = '<div style="color:#484f58;text-align:center;padding:20px;">No projects found.</div>';
        }
        projects.forEach(function(p) {
            html += '<div class="welcome-recent-item" onclick="openProjectFromModal(\'' + escapeHtml(p.name) + '\')" style="padding:10px 12px;">' +
                '<div><div class="welcome-recent-name">📁 ' + escapeHtml(p.name) + '</div>' +
                '<div style="font-size:10px;color:#484f58;">' + escapeHtml(p.path || '') + '</div></div>' +
                '</div>';
        });
        container.innerHTML = html;
    } catch(e) {}
}

async function openProjectFromModal(name) {
    var overlay = document.querySelector('.modal-overlay');
    if (overlay) overlay.remove();
    try {
        var r = JSON.parse(await pywebview.api.open_project(name));
        if (r.status === 'ok') {
            openTabs = [];
            fileContents = {};
            activeTabPath = '';
            editor.setValue('// Welcome to ViGo Dev');
            renderTabs();
            var labelEl = document.getElementById('tab-label');
            if (labelEl) labelEl.textContent = 'Welcome';
            await loadProjects();
            loadFileTree();
            if (r.last_file) openFile(r.last_file, r.last_file.split('/').pop());
        }
    } catch(e) {}
}

document.addEventListener('input', function(e) {
    if (e.target.id === 'op-search') {
        var box = e.target.closest('.modal-box');
        if (box) loadOpenProjectList(box, e.target.value);
    }
});

async function autoSaveCurrentConversation() {
    if (!activeChatId || !chatSessions[activeChatId]) return;
    var session = chatSessions[activeChatId];
    var messages = [];
    (session.messages || []).forEach(function(el) {
        var isUser = el.classList && el.classList.contains('user');
        var isAi = el.classList && el.classList.contains('ai');
        if (isUser || isAi) {
            messages.push({ role: isUser ? 'user' : 'ai', content: el.textContent || el.innerText || '' });
        }
    });
    if (messages.length > 0) {
        try {
            await pywebview.api.save_conversation(activeChatId, session.type || 'master', JSON.stringify(messages), '');
        } catch(e) {}
    }
    try {
        var state = {
            open_chats: Object.keys(chatSessions),
            open_editor_tabs: openTabs.map(function(t) { return t.path; })
        };
        await pywebview.api.save_project_state(JSON.stringify(state));
    } catch(e) {}
}

/* ═══════════════════════════════════════
   Task Manager
   ═══════════════════════════════════════ */

function showTaskManager() {
    var modal = createModal();
    modal.box.style.minWidth = '520px';
    modal.box.style.maxWidth = '600px';
    renderTaskManagerTabs('manual', modal.box);
    modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };
}

function renderTaskManagerTabs(tab, box) {
    box.innerHTML = '';
    var title = document.createElement('div');
    title.className = 'modal-title';
    title.innerHTML = '📋 Task Manager<span class="modal-close">✖</span>';
    title.querySelector('.modal-close').onclick = function() { box.parentElement.remove(); };
    box.appendChild(title);

    var tabs = document.createElement('div');
    tabs.className = 'settings-tabs';
    ['manual', 'auto'].forEach(function(t) {
        var btn = document.createElement('button');
        btn.className = 'settings-tab' + (t === tab ? ' active' : '');
        btn.textContent = t === 'manual' ? 'Manual Mode' : 'Auto Mode';
        btn.onclick = function() { renderTaskManagerTabs(t, box); };
        tabs.appendChild(btn);
    });
    box.appendChild(tabs);

    if (tab === 'manual') {
        renderTaskManager(box);
    } else {
        renderAgentManager(box);
    }
}

var agentMonitorVisible = false;

function toggleAgentMonitor() {
    var monitor = document.getElementById('agent-monitor');
    if (!monitor) {
        monitor = document.createElement('div');
        monitor.id = 'agent-monitor';
        monitor.innerHTML =
            '<div id="agent-monitor-header">' +
            '<span>🟢 Auto Agent Monitor</span>' +
            '<span id="agent-monitor-close">✖</span>' +
            '</div>' +
            '<div id="agent-monitor-body">' +
            '<div style="color:#8b949e;text-align:center;padding:20px;">No agent task running. Launch a project from Task Manager → Auto Mode.</div>' +
            '</div>' +
            '<div id="agent-monitor-footer">' +
            '<button onclick="toggleAgentMonitor()">Close</button>' +
            '</div>';
        document.body.appendChild(monitor);
        monitor.querySelector('#agent-monitor-close').onclick = function() { toggleAgentMonitor(); };
    }
    if (agentMonitorVisible) {
        monitor.style.display = 'none';
        agentMonitorVisible = false;
        var btn = document.getElementById('agent-btn');
        if (btn) btn.style.color = '#484f58';
    } else {
        monitor.style.display = 'flex';
        agentMonitorVisible = true;
        var btn = document.getElementById('agent-btn');
        if (btn) btn.style.color = '#3fb950';
    }
}

function updateAgentMonitor(html) {
    var body = document.getElementById('agent-monitor-body');
    if (body) {
        body.innerHTML = html;
    }
    var monitor = document.getElementById('agent-monitor');
    if (monitor && monitor.style.display === 'none') {
        toggleAgentMonitor();
    }
    var btn = document.getElementById('agent-btn');
    if (btn) {
        btn.style.color = '#3fb950';
        btn.disabled = false;
    }
}

async function renderAgentManager(box) {
    var body = document.createElement('div');
    body.className = 'modal-body';
    body.style.maxHeight = '60vh';
    body.style.overflowY = 'auto';

    try {
        var data = JSON.parse(await pywebview.api.list_project_managers());
        var managers = data.managers || [];
    } catch(e) {
        await showAlert('Error', e.message);
        managers = [];
    }

    if (managers.length === 0) {
        body.innerHTML = '<div class="task-empty" style="padding:20px">No project managers yet. Click "+ Add New Project Manager" below.</div>';
    }

    managers.forEach(function(pm) {
        var card = document.createElement('div');
        card.className = 'task-master-card';
        card.innerHTML =
            '<div class="task-master-header">' +
            '<span class="dot"></span><span class="task-master-name">📋 ' + escapeHtml(pm.name) + '</span>' +
            '<span class="task-master-count">' + (pm.max_masters || 3) + ' Masters / ' + (pm.max_workers_per_master || 2) + ' Workers</span>' +
            '</div>' +
            '<div class="task-step-list" style="padding:8px 14px;color:#8b949e;font-size:11px;">' +
            escapeHtml((pm.system_prompt || '').substring(0, 120)) + '...' +
            '</div>';
        var btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:6px;padding:6px 14px;';
        var launchBtn = document.createElement('button');
        launchBtn.className = 'task-run-btn';
        launchBtn.textContent = '▶ Launch';
        launchBtn.onclick = function() { box.parentElement.remove(); showLaunchModal(pm); };
        btnRow.appendChild(launchBtn);
        var editBtn = document.createElement('button');
        editBtn.className = 'modal-btn modal-btn-cancel';
        editBtn.style.cssText = 'padding:4px 10px;font-size:11px;';
        editBtn.textContent = '✎ Edit';
        editBtn.onclick = function() { box.parentElement.remove(); showEditManagerModal(pm); };
        btnRow.appendChild(editBtn);
        var delBtn = document.createElement('button');
        delBtn.className = 'modal-btn modal-btn-cancel';
        delBtn.style.cssText = 'padding:4px 10px;font-size:11px;';
        delBtn.textContent = '🗑 Delete';
        delBtn.onclick = async function() {
            var ok = await showConfirm('Delete', 'Delete "' + pm.name + '"?');
            if (!ok) return;
            await pywebview.api.delete_project_manager(pm.id);
            box.innerHTML = '';
            renderTaskManagerTabs('auto', box);
        };
        btnRow.appendChild(delBtn);
        card.appendChild(btnRow);
        body.appendChild(card);
    });

    box.appendChild(body);

    var footer = document.createElement('div');
    footer.className = 'modal-footer';
    footer.style.justifyContent = 'space-between';
    var addBtn = document.createElement('button');
    addBtn.className = 'modal-btn modal-btn-confirm';
    addBtn.textContent = '+ Add New Project Manager';
    addBtn.onclick = function() { box.parentElement.remove(); showEditManagerModal(null); };
    footer.appendChild(addBtn);
    var closeBtn = document.createElement('button');
    closeBtn.className = 'modal-btn modal-btn-cancel';
    closeBtn.textContent = 'Close';
    closeBtn.onclick = function() { box.parentElement.remove(); };
    footer.appendChild(closeBtn);
    box.appendChild(footer);
}

function showEditManagerModal(pm) {
    var modal = createModal();
    modal.box.style.minWidth = '500px';
    var isNew = !pm;

    modal.box.innerHTML =
        '<div class="modal-title">' + (isNew ? 'Create' : 'Edit') + ' Project Manager<span class="modal-close">✖</span></div>' +
        '<div class="modal-body" style="max-height:60vh;overflow-y:auto;">' +
        '<div class="settings-field"><label>Preset</label><select id="pm-preset" style="width:200px"><option value="">Custom</option></select></div>' +
        '<div class="settings-field"><label>Name</label><input id="pm-name" value="' + escapeHtml(pm ? pm.name : '') + '" style="width:100%"></div>' +
        '<div class="settings-field"><label>System Prompt</label><textarea id="pm-prompt" rows="8" style="width:100%;background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;padding:8px;font-size:12px;font-family:Consolas,monospace">' + escapeHtml(pm ? pm.system_prompt : '') + '</textarea></div>' +
        '<div class="settings-field"><label>Default Provider</label><input id="pm-provider" value="' + escapeHtml(pm ? pm.default_provider || 'gemma-4b' : 'gemma-4b') + '" style="width:200px"></div>' +
        '<div class="settings-field"><label>Max Masters</label><input id="pm-masters" type="number" value="' + (pm ? pm.max_masters || 3 : 3) + '" min="1" max="10" style="width:100px"></div>' +
        '<div class="settings-field"><label>Max Workers per Master</label><input id="pm-workers" type="number" value="' + (pm ? pm.max_workers_per_master || 2 : 2) + '" min="1" max="10" style="width:100px"></div>' +
        '</div>' +
        '<div class="modal-footer">' +
        '<button class="modal-btn modal-btn-cancel" id="pm-cancel">Cancel</button>' +
        '<button class="modal-btn modal-btn-confirm" id="pm-save">💾 Save</button>' +
        '</div>';

    modal.box.querySelector('.modal-close').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#pm-cancel').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#pm-save').onclick = async function() {
        var name = modal.box.querySelector('#pm-name').value.trim();
        var prompt = modal.box.querySelector('#pm-prompt').value.trim();
        var provider = modal.box.querySelector('#pm-provider').value.trim() || 'gemma-4b';
        var masters = parseInt(modal.box.querySelector('#pm-masters').value) || 3;
        var workers = parseInt(modal.box.querySelector('#pm-workers').value) || 2;
        if (!name) { await showAlert('Error', 'Name is required.'); return; }
        if (!prompt) { await showAlert('Error', 'System prompt is required.'); return; }
        try {
            var r;
            if (isNew) {
                r = JSON.parse(await pywebview.api.create_project_manager(name, prompt, provider, masters, workers, '{}'));
            } else {
                r = JSON.parse(await pywebview.api.update_project_manager(pm.id, name, prompt, provider, masters, workers, null));
            }
            if (r.status === 'ok') {
                modal.overlay.remove();
                var taskModal = createModal();
                taskModal.box.style.minWidth = '520px';
                taskModal.box.style.maxWidth = '600px';
                renderTaskManagerTabs('auto', taskModal.box);
                taskModal.overlay.onclick = function(e) { if (e.target === taskModal.overlay) taskModal.overlay.remove(); };
            } else {
                await showAlert('Error', r.message);
            }
        } catch(e) { await showAlert('Error', e.message); }
    };

    // Load presets into dropdown
    try {
        pywebview.api.list_project_managers().then(function(r) {
            var d = JSON.parse(r);
            var sel = modal.box.querySelector('#pm-preset');
            (d.templates || []).forEach(function(t) {
                sel.innerHTML += '<option value="' + escapeHtml(t.name) + '">' + escapeHtml(t.name) + '</option>';
            });
            sel.onchange = function() {
                var name = this.value;
                if (!name) return;
                var t = d.templates.find(function(x) { return x.name === name; });
                if (t) {
                    modal.box.querySelector('#pm-name').value = t.name;
                    modal.box.querySelector('#pm-prompt').value = t.system_prompt;
                }
            };
        });
    } catch(e) {}

    modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };
}

async function selectProjectPath() {
    try {
        var folder = await pywebview.api.open_folder_dialog();
        if (folder) {
            document.getElementById('launch-path').value = folder;
        }
    } catch(e) {}
}

function showLaunchModal(pm) {
    var modal = createModal();
    modal.box.style.minWidth = '500px';
    modal.box.innerHTML =
        '<div class="modal-title">🚀 Launch: ' + escapeHtml(pm.name) + '<span class="modal-close">✖</span></div>' +
        '<div class="modal-body" style="max-height:60vh;overflow-y:auto;">' +
        '<div class="settings-field"><label>Project Name</label><input id="launch-name" style="width:100%"></div>' +
        '<div class="settings-field"><label>Project Path</label><div style="display:flex;gap:4px;width:100%"><input id="launch-path" style="flex:1" value="F:\\ViGo\\vigo-dev\\Projects"><span onclick="selectProjectPath()" style="cursor:pointer;font-size:16px;padding:4px 6px;">📁</span></div></div>' +
        '<div class="settings-field"><label>Goal</label><textarea id="launch-goal" rows="4" style="width:100%;background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;padding:8px;font-size:12px;font-family:Consolas,monospace"></textarea></div>' +
        '<div class="settings-field"><label>Detailed Plan (optional, paste JSON)</label><textarea id="launch-plan" rows="6" style="width:100%;background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;padding:8px;font-size:12px;font-family:Consolas,monospace"></textarea></div>' +
        '<div style="padding:8px 0;color:#8b949e;font-size:11px;">☑ Export conversation logs when complete</div>' +
        '<div style="padding:4px 0;color:#484f58;font-size:11px;">☐ Auto-validate each step <span style="color:#484f58">[Coming Soon]</span><br>☐ Auto Git commit <span style="color:#484f58">[Coming Soon]</span><br>☐ Auto rollback on failure <span style="color:#484f58">[Coming Soon]</span></div>' +
        '</div>' +
        '<div class="modal-footer">' +
        '<button class="modal-btn modal-btn-cancel" id="launch-cancel">Cancel</button>' +
        '<button class="modal-btn modal-btn-confirm" id="launch-go">🚀 Start Auto Development</button>' +
        '</div>';

    modal.box.querySelector('.modal-close').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#launch-cancel').onclick = function() { modal.overlay.remove(); };
    modal.box.querySelector('#launch-go').onclick = async function() {
        var projectName = modal.box.querySelector('#launch-name').value.trim();
        var goal = modal.box.querySelector('#launch-goal').value.trim();
        var plan = modal.box.querySelector('#launch-plan').value.trim();
        var projectPath = modal.box.querySelector('#launch-path').value.trim();
        if (!projectName || !goal) {
            await showAlert('Error', 'Project name and goal are required.');
            return;
        }

        // Show monitor immediately
        var monitor = document.getElementById('agent-monitor');
        if (!monitor) {
            toggleAgentMonitor();
            monitor = document.getElementById('agent-monitor');
        }
        if (monitor) {
            monitor.style.display = 'flex';
            agentMonitorVisible = true;
            document.getElementById('agent-monitor-body').innerHTML = '<div style="text-align:center;padding:20px;">🤔 Analyzing goal...<br><span style="color:#8b949e;font-size:11px;">' + escapeHtml(goal) + '</span></div>';
            var agentBtn = document.getElementById('agent-btn');
            if (agentBtn) { agentBtn.style.color = '#3fb950'; agentBtn.disabled = false; }
        }
        modal.overlay.remove();

        try {
            var r = JSON.parse(await pywebview.api.launch_agent(pm.id, projectName, goal, plan, projectPath));
            if (r.status !== 'ok') {
                await showAlert('Error', r.message);
                updateAgentMonitor('<div style="text-align:center;padding:20px;color:#f85149;">❌ Failed: ' + escapeHtml(r.message) + '</div>');
                return;
            }
            var masterId = Object.keys(chatSessions).find(function(id) { return chatSessions[id].type === 'master'; });
            if (!masterId) {
                newChat();
                masterId = activeChatId;
            }
            var session = chatSessions[masterId];
            session.taskMode = 'manager';
            session.pipeline = r.pipeline.steps.map(function(s) {
                return { assignee: s.assignee || 'master', desc: s.desc || '' };
            });

            // Auto-create workers with limit
            var workerCount = 0;
            var maxWorkers = pm.max_workers_per_master || 2;
            for (var i = 0; i < session.pipeline.length; i++) {
                var step = session.pipeline[i];
                if (step.assignee && step.assignee !== 'master') {
                    if (workerCount >= maxWorkers) {
                        step.assignee = 'master';
                        continue;
                    }
                    var workerName = step.assignee;
                    var existingWorker = null;
                    Object.keys(chatSessions).forEach(function(k) {
                        if (chatSessions[k].name === workerName && chatSessions[k].parentId === masterId) {
                            existingWorker = k;
                        }
                    });
                    if (existingWorker) {
                        step.assignee = existingWorker;
                    } else {
                        chatCounter++;
                        var workerId = 'chat_' + chatCounter;
                        chatSessions[workerId] = { id: workerId, name: workerName, type: 'worker', parentId: masterId, messages: [], collapsed: false };
                        step.assignee = workerId;
                        workerCount++;
                    }
                }
            }

            // Update monitor with pipeline
            var monitorHtml = '<div style="padding:8px 0;"><strong>Goal:</strong><br>' + escapeHtml(goal) + '</div>';
            monitorHtml += '<div style="padding:8px 0;border-top:1px solid #30363d;"><strong>Pipeline:</strong></div>';
            for (var i = 0; i < session.pipeline.length; i++) {
                var s = session.pipeline[i];
                monitorHtml += '<div class="agent-step running">🔧 ' + escapeHtml(s.desc) + '</div>';
            }
            if (monitor) {
                document.getElementById('agent-monitor-body').innerHTML = monitorHtml;
            }

            // Sync project name and clear old tabs
            document.getElementById('project-name').textContent = projectName;
            document.getElementById('project-name').className = 'active';
            openTabs = [];
            fileContents = {};
            activeTabPath = '';
            editor.setValue('// Welcome to ViGo Dev');
            renderTabs();
            var labelEl = document.getElementById('tab-label');
            if (labelEl) labelEl.textContent = 'Welcome';

            // Sync IDE to target project
            if (r.project_root) {
                try {
                    var projects = JSON.parse(await pywebview.api.list_projects());
                    var targetName = projectName.replace(/ /g, '-');
                    var found = (projects.projects || []).find(function(p) { return p.path === r.project_root; });
                    if (found) {
                        await pywebview.api.open_project(found.name);
                        await loadProjects();
                        loadFileTree();
                    }
                } catch(e) {}
            }

            // Auto-execute the pipeline
            runManagerPipeline(masterId);
        } catch(e) {
            await showAlert('Error', e.message);
        }
    };

    modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };
}

async function renderTaskManager(box) {

    var body = document.createElement('div');
    body.className = 'modal-body';
    body.style.maxHeight = '60vh';
    body.style.overflowY = 'auto';

    var hasMaster = false;
    Object.keys(chatSessions).forEach(function(id) {
        var s = chatSessions[id];
        if (s.type !== 'master') return;
        hasMaster = true;
        if (!s.taskMode) s.taskMode = 'alone';
        var card = document.createElement('div');
        card.className = 'task-master-card';

        // Header
        var header = document.createElement('div');
        header.className = 'task-master-header';
        header.innerHTML = '<span class="dot"></span><span class="task-master-name">' + escapeHtml(s.name) + '</span>';

        // Mode switcher
        var modeSelect = document.createElement('select');
        modeSelect.style.cssText = 'background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;padding:2px 6px;font-size:10px;margin-right:8px;cursor:pointer;';
        modeSelect.innerHTML = '<option value="alone"' + (s.taskMode === 'alone' ? ' selected' : '') + '>Alone</option><option value="manager"' + (s.taskMode === 'manager' ? ' selected' : '') + '>Manager</option>';
        modeSelect.onclick = function(e) { e.stopPropagation(); };
        modeSelect.onchange = function(e) {
            s.taskMode = e.target.value;
            if (s.taskMode === 'manager' && !s.pipeline) {
                s.pipeline = (s.taskSteps || []).map(function(d) { return {assignee: 'master', desc: d}; });
                s.taskSteps = [];
            } else if (s.taskMode === 'alone' && !s.taskSteps) {
                s.taskSteps = (s.pipeline || []).map(function(p) { return p.desc; });
                s.pipeline = [];
            }
            box.innerHTML = '';
            renderTaskManagerTabs('manual', box);
        };
        header.appendChild(modeSelect);

        var countSpan = document.createElement('span');
        countSpan.className = 'task-master-count';
        if (s.taskMode === 'manager') {
            countSpan.textContent = (s.pipeline || []).length + ' step(s)';
        } else {
            countSpan.textContent = (s.taskSteps || []).length + ' step(s)';
        }
        header.appendChild(countSpan);

        var runBtn = document.createElement('button');
        runBtn.className = 'task-run-btn';
        runBtn.textContent = '▶ Run';
        runBtn.onclick = function(e) {
            e.stopPropagation();
            box.parentElement.remove();
            if (s.taskMode === 'manager') {
                runManagerPipeline(id);
            } else {
                runTaskChain(id);
            }
        };
        header.appendChild(runBtn);
        header.onclick = function(e) {
            if (e.target.tagName === 'BUTTON' || e.target.tagName === 'SELECT') return;
            var list = card.querySelector('.task-step-list');
            var add = card.querySelector('.task-add-step');
            var vis = list.style.display === 'none' ? 'block' : 'none';
            list.style.display = vis;
            if (add) add.style.display = vis;
        };
        card.appendChild(header);

        // Step list
        var list = document.createElement('div');
        list.className = 'task-step-list';

        if (s.taskMode === 'manager') {
            // Manager mode: pipeline with assignee
            var pipeline = s.pipeline || [];
            if (pipeline.length === 0) {
                var empty = document.createElement('div');
                empty.className = 'task-empty';
                empty.textContent = 'No steps yet. Click "+ Add Step" below.';
                list.appendChild(empty);
            } else {
                pipeline.forEach(function(step, i) {
                    var item = document.createElement('div');
                    item.className = 'task-step-item';
                    item.innerHTML = '<span class="task-step-num">' + (i + 1) + '.</span>';
                    // Assignee dropdown
                    var assigneeSelect = document.createElement('select');
                    assigneeSelect.style.cssText = 'background:#0d1117;color:#58a6ff;border:1px solid #30363d;border-radius:4px;padding:1px 4px;font-size:10px;margin-right:6px;cursor:pointer;min-width:80px;';
                    var isMaster = step.assignee === 'master' || step.assignee === id;
                    assigneeSelect.innerHTML = '<option value="master"' + (isMaster ? ' selected' : '') + '>Master</option>';
                    Object.keys(chatSessions).forEach(function(wid) {
                        var ws = chatSessions[wid];
                        if (ws.type === 'worker' && ws.parentId === id) {
                            assigneeSelect.innerHTML += '<option value="' + wid + '"' + (step.assignee === wid ? ' selected' : '') + '>' + escapeHtml(ws.name) + '</option>';
                        }
                    });
                    assigneeSelect.onclick = function(e) { e.stopPropagation(); };
                    assigneeSelect.onchange = function(e) {
                        step.assignee = e.target.value;
                    };
                    item.appendChild(assigneeSelect);
                    // Desc
                    var descSpan = document.createElement('span');
                    descSpan.className = 'task-step-desc';
                    descSpan.textContent = step.desc;
                    descSpan.style.cursor = 'pointer';
                    descSpan.ondblclick = async function() {
                        var newDesc = await showInput('Edit Step', 'Modify step description:', step.desc);
                        if (newDesc) {
                            step.desc = newDesc;
                            box.innerHTML = '';
                            renderTaskManagerTabs('manual', box);
                        }
                    };
                    item.appendChild(descSpan);
                    // Remove
                    var removeBtn = document.createElement('span');
                    removeBtn.className = 'task-step-remove';
                    removeBtn.textContent = '✖';
                    removeBtn.onclick = function(e) {
                        e.stopPropagation();
                        s.pipeline.splice(i, 1);
                        box.innerHTML = '';
                        renderTaskManagerTabs('manual', box);
                    };
                    item.appendChild(removeBtn);
                    list.appendChild(item);
                });
            }
            card.appendChild(list);
            var addBtn = document.createElement('span');
            addBtn.className = 'task-add-step';
            addBtn.textContent = '+ Add Step';
            addBtn.onclick = async function(e) {
                e.stopPropagation();
                var desc = await showInput('Add Step', 'Enter task description:');
                if (desc) {
                    if (!s.pipeline) s.pipeline = [];
                    s.pipeline.push({assignee: 'master', desc: desc});
                    box.innerHTML = '';
                    renderTaskManagerTabs('manual', box);
                }
            };
            card.appendChild(addBtn);
        } else {
            // Alone mode: simple steps
            var steps = s.taskSteps || [];
            if (steps.length === 0) {
                var empty2 = document.createElement('div');
                empty2.className = 'task-empty';
                empty2.textContent = 'No steps yet. Click "+ Add Step" below.';
                list.appendChild(empty2);
            } else {
                steps.forEach(function(desc, i) {
                    var item = document.createElement('div');
                    item.className = 'task-step-item';
                    item.innerHTML = '<span class="task-step-num">' + (i + 1) + '.</span><span class="task-step-desc" style="cursor:pointer">' + escapeHtml(desc) + '</span>';
                    item.querySelector('.task-step-desc').ondblclick = async function() {
                        var newDesc = await showInput('Edit Step', 'Modify step description:', desc);
                        if (newDesc) {
                            s.taskSteps[i] = newDesc;
                            box.innerHTML = '';
                            renderTaskManagerTabs('manual', box);
                        }
                    };
                    var removeBtn = document.createElement('span');
                    removeBtn.className = 'task-step-remove';
                    removeBtn.textContent = '✖';
                    removeBtn.onclick = function(e) {
                        e.stopPropagation();
                        s.taskSteps.splice(i, 1);
                        box.innerHTML = '';
                        renderTaskManagerTabs('manual', box);
                    };
                    item.appendChild(removeBtn);
                    list.appendChild(item);
                });
            }
            card.appendChild(list);
            var addBtn2 = document.createElement('span');
            addBtn2.className = 'task-add-step';
            addBtn2.textContent = '+ Add Step';
            addBtn2.onclick = async function(e) {
                e.stopPropagation();
                var desc = await showInput('Add Step', 'Enter task description:');
                if (desc) {
                    if (!s.taskSteps) s.taskSteps = [];
                    s.taskSteps.push(desc);
                    box.innerHTML = '';
                    renderTaskManagerTabs('manual', box);
                }
            };
            card.appendChild(addBtn2);
        }
        body.appendChild(card);
    });

    if (!hasMaster) {
        body.innerHTML = '<div class="task-empty" style="padding:20px">No master chats exist. Create one first.</div>';
    }

    box.appendChild(body);

    var footer = document.createElement('div');
    footer.className = 'modal-footer';
    var closeBtn = document.createElement('button');
    closeBtn.className = 'modal-btn modal-btn-cancel';
    closeBtn.textContent = 'Close';
    closeBtn.onclick = function() { box.parentElement.remove(); };
    footer.appendChild(closeBtn);
    // Template buttons
    var templateRow = document.createElement('div');
    templateRow.style.cssText = 'display:flex;gap:8px;padding:8px 14px;border-top:1px solid #30363d;';

    // Load Template dropdown
    var loadSelect = document.createElement('select');
    loadSelect.style.cssText = 'flex:1;background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;padding:5px 8px;font-size:11px;cursor:pointer;';
    loadSelect.innerHTML = '<option value="">Load Template...</option>';
    var templateList = [];
    try {
        templateList = JSON.parse(await pywebview.api.list_templates());
        templateList.forEach(function(tmpl) {
            loadSelect.innerHTML += '<option value="' + escapeHtml(tmpl.name) + '">' + escapeHtml(tmpl.label || tmpl.name) + '</option>';
        });
    } catch(e) {}
    loadSelect.onchange = async function() {
        var name = loadSelect.value;
        if (!name) return;
        loadSelect.value = '';
        try {
            var tmpl = JSON.parse(await pywebview.api.load_template(name));
            if (tmpl.status === 'error') {
                await showAlert('Error', tmpl.message);
                return;
            }
            var masterIds = Object.keys(chatSessions).filter(function(id) { return chatSessions[id].type === 'master'; });
            if (masterIds.length === 0) {
                await showAlert('Error', 'No master chat exists.');
                return;
            }
            var masterId = masterIds[0];
            if (masterIds.length > 1) {
                var items = masterIds.map(function(id) { return {value: id, label: chatSessions[id].name}; });
                masterId = await showListPicker('Load into which master?', items);
                if (!masterId) return;
            }
            var session = chatSessions[masterId];
            session.taskMode = tmpl.mode || 'alone';
            if (session.taskMode === 'manager') {
                session.pipeline = (tmpl.steps || []).map(function(s) {
                    return {assignee: s.assignee || 'master', desc: s.desc || ''};
                });
                session.taskSteps = [];
            } else {
                session.taskSteps = (tmpl.steps || []).map(function(s) { return s.desc || ''; });
                session.pipeline = [];
            }
            box.innerHTML = '';
            renderTaskManagerTabs('manual', box);
        } catch(e) { await showAlert('Error', e.message); }
    };
    templateRow.appendChild(loadSelect);

    // Delete Template button
    var deleteBtn = document.createElement('button');
    deleteBtn.className = 'modal-btn modal-btn-cancel';
    deleteBtn.style.cssText = 'padding:4px 8px;font-size:11px;white-space:nowrap;';
    deleteBtn.textContent = '✖';
    deleteBtn.title = 'Delete Template';
    deleteBtn.onclick = async function() {
        if (templateList.length === 0) {
            await showAlert('Delete', 'No templates to delete.');
            return;
        }
        var items = templateList.map(function(t) { return {value: t.name, label: t.label || t.name}; });
        var targetName = await showListPicker('Delete which template?', items);
        if (!targetName) return;
        var ok = await showConfirm('Delete Template', 'Delete "' + targetName + '"?');
        if (!ok) return;
        try {
            await pywebview.api.delete_template(targetName);
            // Refresh
            templateList = JSON.parse(await pywebview.api.list_templates());
            loadSelect.innerHTML = '<option value="">Load Template...</option>';
            templateList.forEach(function(tmpl) {
                loadSelect.innerHTML += '<option value="' + escapeHtml(tmpl.name) + '">' + escapeHtml(tmpl.label || tmpl.name) + '</option>';
            });
        } catch(e) { await showAlert('Error', e.message); }
    };
    templateRow.appendChild(deleteBtn);

    // Save Template button
    var saveBtn = document.createElement('button');
    saveBtn.className = 'modal-btn modal-btn-confirm';
    saveBtn.style.cssText = 'padding:4px 10px;font-size:11px;white-space:nowrap;';
    saveBtn.textContent = '💾 Save';
    saveBtn.onclick = async function() {
        var masterIds = Object.keys(chatSessions).filter(function(id) { return chatSessions[id].type === 'master'; });
        if (masterIds.length === 0) {
            await showAlert('Error', 'No master chat exists.');
            return;
        }
        var masterId = masterIds[0];
        if (masterIds.length > 1) {
            var items = masterIds.map(function(id) { return {value: id, label: chatSessions[id].name}; });
            masterId = await showListPicker('Save from which master?', items);
            if (!masterId) return;
        }
        var name = await showInput('Save Template', 'Template name:');
        if (!name) return;
        var session = chatSessions[masterId];
        var template = {
            label: name,
            mode: session.taskMode || 'alone',
            steps: []
        };
        if (session.taskMode === 'manager') {
            template.steps = (session.pipeline || []).map(function(s) {
                return {assignee: s.assignee || 'master', desc: s.desc || ''};
            });
        } else {
            template.steps = (session.taskSteps || []).map(function(d) {
                return {assignee: 'master', desc: d};
            });
        }
        try {
            var r = JSON.parse(await pywebview.api.save_template(name, JSON.stringify(template)));
            if (r.status === 'ok') {
                await showAlert('Saved', 'Template "' + name + '" saved.');
                templateList = JSON.parse(await pywebview.api.list_templates());
                loadSelect.innerHTML = '<option value="">Load Template...</option>';
                templateList.forEach(function(tmpl) {
                    loadSelect.innerHTML += '<option value="' + escapeHtml(tmpl.name) + '">' + escapeHtml(tmpl.label || tmpl.name) + '</option>';
                });
            } else {
                await showAlert('Error', r.message);
            }
        } catch(e) { await showAlert('Error', e.message); }
    };
    templateRow.appendChild(saveBtn);

    body.appendChild(templateRow);
    box.appendChild(footer);
}

async function runTaskChain(chatId) {
    var session = chatSessions[chatId];
    if (!session || !session.taskSteps || session.taskSteps.length === 0) {
        await showAlert('Task', 'No steps defined for this chat.');
        return;
    }
    currentTask = {
        chatId: chatId,
        steps: session.taskSteps.slice(),
        currentIndex: 0,
        stopped: false
    };
    switchChat(chatId);
    showTaskProgress(0, currentTask.steps.length, 'Starting...');

    for (var i = 0; i < currentTask.steps.length; i++) {
        if (currentTask.stopped) break;
        currentTask.currentIndex = i;
        var stepDesc = currentTask.steps[i];
        updateTaskProgress(i + 1, currentTask.steps.length, 'Step ' + (i + 1) + ': ' + stepDesc);
        // Set input and send
        document.getElementById('chat-input').value = stepDesc;
        await executeTaskStep();
        if (currentTask.stopped) break;
    }
    if (!currentTask.stopped) {
        updateTaskProgress(currentTask.steps.length, currentTask.steps.length, 'All steps completed.');
        setTimeout(function() { hideTaskProgress(); }, 3000);
    }
    currentTask = null;
}

async function runManagerPipeline(chatId) {
    var session = chatSessions[chatId];
    if (!session || !session.pipeline || session.pipeline.length === 0) {
        await showAlert('Task', 'No pipeline steps defined for this chat.');
        return;
    }
    var pipeline = session.pipeline;
    currentTask = {
        chatId: chatId,
        steps: pipeline.map(function(s) { return s.desc; }),
        currentIndex: 0,
        stopped: false,
        pipeline: pipeline
    };
    switchChat(chatId);
    showTaskProgress(0, pipeline.length, 'Starting Manager pipeline...');

    var accumulatedContext = '';

    for (var i = 0; i < pipeline.length; i++) {
        if (currentTask.stopped) break;
        currentTask.currentIndex = i;
        var step = pipeline[i];
        var assigneeId = step.assignee === 'master' ? chatId : step.assignee;
        var assigneeName = assigneeId === chatId ? 'Master' : (chatSessions[assigneeId] ? chatSessions[assigneeId].name : 'Worker');

        updateTaskProgress(i + 1, pipeline.length, 'Step ' + (i + 1) + ': [' + assigneeName + '] ' + step.desc);
            // Update Agent Monitor
            var mHtml = '<div style="padding:8px 0;"><strong>Goal:</strong><br>' + escapeHtml(currentTask.steps[0] || '') + '</div>';
            mHtml += '<div style="padding:8px 0;border-top:1px solid #30363d;"><strong>Progress:</strong></div>';
            for (var j = 0; j < pipeline.length; j++) {
                var icon = j < i ? '✅' : (j === i ? '🔧' : '⏳');
                mHtml += '<div class="agent-step ' + (j < i ? 'done' : (j === i ? 'running' : '')) + '">' + icon + ' ' + escapeHtml(pipeline[j].desc) + '</div>';
            }
            updateAgentMonitor(mHtml);

        var contextPrefix = '';
        if (accumulatedContext) {
            contextPrefix = 'Context from previous steps:\n' + accumulatedContext + '\n\nNow execute your step:\n';
        }
        var fullMessage = contextPrefix + step.desc;

        if (assigneeId !== chatId) {
            await pywebview.api.clear_chat_history(assigneeId);
            if (chatSessions[assigneeId]) {
                chatSessions[assigneeId].messages = [];
            }
            switchChat(assigneeId);
        }

        document.getElementById('chat-input').value = fullMessage;
        var aiResponse = await executeTaskStep();

        if (currentTask.stopped) break;

        accumulatedContext += 'Step ' + (i + 1) + ' (' + assigneeName + '): ' + step.desc + '\nResult: ' + aiResponse.substring(0, 500) + '\n\n';

        if (assigneeId !== chatId) {
            var masterSession = chatSessions[chatId];
            if (masterSession) {
                var resultDiv = document.createElement('div');
                resultDiv.className = 'message ai';
                resultDiv.textContent = '↩️ ' + assigneeName + ' completed: ' + aiResponse.substring(0, 300);
                if (!masterSession.messages) masterSession.messages = [];
                masterSession.messages.push(resultDiv);
            }
            switchChat(chatId);
        }
    }

    // Archive each worker's conversation after pipeline
    for (var i = 0; i < pipeline.length; i++) {
        var step = pipeline[i];
        var assigneeId = step.assignee === 'master' ? chatId : step.assignee;
        if (assigneeId !== chatId && chatSessions[assigneeId]) {
            var ws = chatSessions[assigneeId];
            var wmsgs = [];
            (ws.messages || []).forEach(function(el) {
                var isUser = el.classList && el.classList.contains('user');
                var isAi = el.classList && el.classList.contains('ai');
                if (isUser || isAi) {
                    wmsgs.push({ role: isUser ? 'user' : 'ai', content: el.textContent || el.innerText || '' });
                }
            });
            if (wmsgs.length > 0) {
                try {
                    await pywebview.api.save_conversation(assigneeId, 'worker', JSON.stringify(wmsgs), step.desc);
                } catch(e) {}
            }
        }
    }

    if (!currentTask.stopped) {
        updateAgentMonitor('<div style="text-align:center;padding:20px;color:#7ee787;">✅ All steps completed!</div>');
        setTimeout(function() { hideTaskProgress(); }, 3000);
    }
    currentTask = null;
}

async function executeTaskStep() {
    return new Promise(function(resolve) {
        var resolved = false;
        var capturedResponse = '';
        
        // Hook into appendMessage and appendMessageStream to capture AI response
        var origAppendMessage = appendMessage;
        var origAppendMessageStream = appendMessageStream;
        
        appendMessage = function(role, text) {
            if (role === 'ai') capturedResponse = text;
            origAppendMessage(role, text);
        };
        appendMessageStream = function(role, chunks, fullText, elapsed) {
            if (role === 'ai') capturedResponse = fullText;
            origAppendMessageStream(role, chunks, fullText, elapsed);
        };
        
        var checkInterval = setInterval(function() {
            if (resolved) { clearInterval(checkInterval); return; }
            if (currentTask && currentTask.stopped) {
                resolved = true;
                clearInterval(checkInterval);
                appendMessage = origAppendMessage;
                appendMessageStream = origAppendMessageStream;
                resolve('');
                return;
            }
            if (!window._sendingLock && !document.getElementById('btn-send').disabled) {
                setTimeout(function() {
                    if (!resolved) {
                        resolved = true;
                        clearInterval(checkInterval);
                        appendMessage = origAppendMessage;
                        appendMessageStream = origAppendMessageStream;
                        resolve(capturedResponse);
                    }
                }, 500);
            }
        }, 300);
        sendMessage();
    });
}

function showTaskProgress(current, total, title) {
    var bar = document.getElementById('task-progress');
    bar.style.display = 'block';
    bar.innerHTML =
        '<div class="task-progress-header">' +
        '<span class="task-progress-title">' + escapeHtml(title) + '</span>' +
        '<span class="task-progress-stop" onclick="stopTask()">⏹ Stop</span>' +
        '</div>' +
        '<div class="task-progress-bar"><div class="task-progress-fill" style="width:' + (current / total * 100) + '%"></div></div>' +
        '<div class="task-progress-steps" id="task-progress-steps"></div>';
}

function updateTaskProgress(current, total, title) {
    var bar = document.getElementById('task-progress');
    if (bar.style.display === 'none') {
        showTaskProgress(current, total, title);
    }
    bar.querySelector('.task-progress-title').textContent = title;
    bar.querySelector('.task-progress-fill').style.width = (current / total * 100) + '%';
    // Update step list
    var stepsDiv = document.getElementById('task-progress-steps');
    if (stepsDiv && currentTask) {
        stepsDiv.innerHTML = '';
        currentTask.steps.forEach(function(s, i) {
            var icon = i < current ? '✅' : (i === current ? '🔧' : '⏳');
            stepsDiv.innerHTML += '<div class="task-progress-step"><span class="icon">' + icon + '</span>' + escapeHtml(s) + '</div>';
        });
    }
}

function stopTask() {
    if (currentTask) {
        currentTask.stopped = true;
        updateTaskProgress(currentTask.currentIndex, currentTask.steps.length, 'Stopped.');
        setTimeout(function() { hideTaskProgress(); }, 2000);
    }
}

function hideTaskProgress() {
    var bar = document.getElementById('task-progress');
    bar.style.display = 'none';
}

async function updateStatusBar() {
    try {
        var cf = await pywebview.api.get_current_file();
        document.getElementById('status-file').textContent = cf || 'No file open';
    } catch(e) {}
}

/* ═══════════════════════════════════════
   Settings
   ═══════════════════════════════════════ */

var settingsData = {};

async function showSettings() {
    try {
        settingsData = JSON.parse(await pywebview.api.get_settings());
    } catch(e) {
        settingsData = {};
    }
    var modal = createModal();
    renderSettingsTab('ai', modal.box);
    modal.overlay.onclick = function(e) { if (e.target === modal.overlay) modal.overlay.remove(); };
}

function renderSettingsTab(tab, box) {
    box.innerHTML = '';
    // Title
    var title = document.createElement('div');
    title.className = 'modal-title';
    title.innerHTML = '⚙️ Settings<span class="modal-close">✖</span>';
    title.querySelector('.modal-close').onclick = function() { box.parentElement.remove(); };
    box.appendChild(title);
    // Tabs
    var tabs = document.createElement('div');
    tabs.className = 'settings-tabs';
    ['ai', 'editor'].forEach(function(t) {
        var btn = document.createElement('button');
        btn.className = 'settings-tab' + (t === tab ? ' active' : '');
        btn.textContent = t === 'ai' ? 'AI' : 'Editor';
        btn.onclick = function() { renderSettingsTab(t, box); };
        tabs.appendChild(btn);
    });
    box.appendChild(tabs);
    // Body
    var body = document.createElement('div');
    body.className = 'modal-body';
    if (tab === 'ai') {
        body.appendChild(settingInput('Ollama Host', 'ollama_host', settingsData.ollama_host || 'http://localhost:11434'));
        body.appendChild(settingSelect('Memory Mode', 'memory_mode', settingsData.memory_mode || 'auto', ['auto', 'manual']));
        body.appendChild(settingKeybind('F3 Shortcut Key', 'f3_shortcut', settingsData.f3_shortcut || 'F3'));
        body.appendChild(settingNumber('Auto-save Interval (seconds)', 'auto_save_interval', settingsData.auto_save_interval || 60));
        body.appendChild(settingNumber('Timeout (seconds)', 'timeout', settingsData.timeout || 120));
    } else {
        body.appendChild(settingNumber('Font Size', 'font_size', settingsData.font_size || 13));
        body.appendChild(settingSelect('Theme', 'theme', settingsData.theme || 'vs-dark', ['vs', 'vs-dark', 'hc-black']));
        body.appendChild(settingNumber('Tab Size', 'tab_size', settingsData.tab_size || 4));
        body.appendChild(settingToggle('Word Wrap', 'word_wrap', settingsData.word_wrap !== false));
    }
    box.appendChild(body);
    // Footer
    var footer = document.createElement('div');
    footer.className = 'modal-footer';
    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'modal-btn modal-btn-cancel';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.onclick = function() { box.parentElement.remove(); };
    var saveBtn = document.createElement('button');
    saveBtn.className = 'modal-btn modal-btn-confirm';
    saveBtn.textContent = 'Save';
    saveBtn.onclick = async function() {
        // Collect values from inputs
        var inputs = body.querySelectorAll('input, select');
        inputs.forEach(function(inp) {
            if (inp.type === 'checkbox') {
                settingsData[inp.name] = inp.checked;
            } else if (inp.type === 'number') {
                settingsData[inp.name] = parseInt(inp.value) || settingsData[inp.name];
            } else {
                settingsData[inp.name] = inp.value;
            }
        });
        var r = JSON.parse(await pywebview.api.save_settings(JSON.stringify(settingsData)));
        if (r.status === 'ok') {
            applySettings();
            await showAlert('Settings', 'Settings saved successfully.');
        } else {
            await showAlert('Error', r.message);
        }
    };
    footer.appendChild(cancelBtn);
    footer.appendChild(saveBtn);
    box.appendChild(footer);
}

function settingInput(label, name, value) {
    var div = document.createElement('div');
    div.className = 'settings-field';
    div.innerHTML = '<label>' + escapeHtml(label) + '</label><input type="text" name="' + name + '" value="' + escapeHtml(String(value)) + '">';
    return div;
}

function settingNumber(label, name, value) {
    var div = document.createElement('div');
    div.className = 'settings-field';
    var min = name === 'auto_save_interval' ? '20' : '1';
    var max = name === 'auto_save_interval' ? '120' : '999';
    div.innerHTML = '<label>' + escapeHtml(label) + '</label><input type="number" name="' + name + '" value="' + value + '" min="' + min + '" max="' + max + '">';
    return div;
}

function settingSelect(label, name, value, options) {
    var div = document.createElement('div');
    div.className = 'settings-field';
    var html = '<label>' + escapeHtml(label) + '</label><select name="' + name + '">';
    options.forEach(function(o) {
        html += '<option value="' + o + '"' + (o === value ? ' selected' : '') + '>' + o + '</option>';
    });
    html += '</select>';
    div.innerHTML = html;
    return div;
}

function settingToggle(label, name, value) {
    var div = document.createElement('div');
    div.className = 'settings-field';
    div.innerHTML = '<label>' + escapeHtml(label) + '</label>' +
        '<label class="settings-toggle"><input type="checkbox" name="' + name + '"' + (value ? ' checked' : '') + '><span class="slider"></span></label>';
    return div;
}

function settingKeybind(label, name, value) {
    var div = document.createElement('div');
    div.className = 'settings-field';
    div.innerHTML = '<label>' + escapeHtml(label) + '</label>' +
        '<input type="text" name="' + name + '" value="' + escapeHtml(value) + '" readonly style="cursor:pointer;background:#0d1117;color:#58a6ff;border:1px solid #30363d;border-radius:4px;padding:5px 10px;font-size:12px;width:120px;text-align:center;">';
    var input = div.querySelector('input');
    input.onclick = function() {
        input.value = 'Press a key...';
        input.style.color = '#f85149';
        function onKey(e) {
            e.preventDefault();
            e.stopPropagation();
            var key = e.key.toUpperCase();
            if (key === 'CONTROL' || key === 'SHIFT' || key === 'ALT') return;
            if (e.ctrlKey) key = 'CTRL+' + key;
            if (e.shiftKey) key = 'SHIFT+' + key;
            if (e.altKey) key = 'ALT+' + key;
            if (key === 'ESCAPE') key = value;
            input.value = key;
            input.style.color = '#58a6ff';
            document.removeEventListener('keydown', onKey);
        }
        document.addEventListener('keydown', onKey);
    };
    return div;
}

function applySettings() {
    if (editor) {
        editor.updateOptions({
            fontSize: settingsData.font_size || 13,
            theme: settingsData.theme || 'vs-dark',
            tabSize: settingsData.tab_size || 4,
            wordWrap: settingsData.word_wrap !== false ? 'on' : 'off'
        });
    }
    // Apply theme to entire IDE
    var theme = settingsData.theme || 'vs-dark';
    document.body.setAttribute('data-theme', theme);
    var isDark = theme !== 'vs';
    var bg = isDark ? '#0d1117' : '#ffffff';
    var panelBg = isDark ? '#161b22' : '#f6f8fa';
    var textColor = isDark ? '#c9d1d9' : '#24292f';
    var borderColor = isDark ? '#30363d' : '#d0d7de';
    var mutedColor = isDark ? '#8b949e' : '#656d76';
    document.body.style.background = bg;
    document.body.style.color = textColor;
    var panels = document.querySelectorAll('#menubar, #toolbar, #sidebar, #chat-panel, #status-bar, #terminal-header, .panel-header, #editor-tabs, #chat-tabs, #delegate-bar');
    panels.forEach(function(el) {
        el.style.background = panelBg;
        el.style.borderColor = borderColor;
        el.style.color = textColor;
    });
    var mutedEls = document.querySelectorAll('.panel-header, #status-bar, #project-name, .tree-item.dir, .chat-tab, .tab');
    mutedEls.forEach(function(el) {
        el.style.color = mutedColor;
    });
    // Update input/textarea styles
    var inputs = document.querySelectorAll('#chat-input, .modal-body input, .settings-field input, .settings-field select');
    inputs.forEach(function(el) {
        el.style.background = bg;
        el.style.color = textColor;
        el.style.borderColor = borderColor;
    });
    // Restart auto-save timer with new interval
    if (window._autoSaveTimer) clearInterval(window._autoSaveTimer);
    var interval = (settingsData.auto_save_interval || 60) * 1000;
    if (interval < 20000) interval = 20000;
    if (interval > 120000) interval = 120000;
    window._autoSaveTimer = setInterval(autoSaveCurrentConversation, interval);
}

/* ═══════════════════════════════════════
   F3 Code Selection Ask
   ═══════════════════════════════════════ */

var f3Mode = false;
var f3SelectedText = '';
var f3SelectedFile = '';
var f3SelectedLines = '';

document.addEventListener('keydown', function(e) {
    var shortcut = (settingsData.f3_shortcut || 'F3').toUpperCase();
    var key = e.key.toUpperCase();
    if (e.ctrlKey) key = 'CTRL+' + key;
    if (e.shiftKey) key = 'SHIFT+' + key;
    if (e.altKey) key = 'ALT+' + key;
    if (key === shortcut) {
        e.preventDefault();
        e.stopPropagation();
        if (f3Mode) {
            exitF3Mode();
        } else {
            enterF3Mode();
        }
    }
}, true);

function enterF3Mode() {
    f3Mode = true;
    f3SelectedText = '';
    if (editor) {
        editor.updateOptions({ cursorStyle: 'line-thin' });
    }
    var statusEl = document.getElementById('status-file');
    if (statusEl) {
        statusEl.style.color = '#58a6ff';
        statusEl.textContent = '🔵 Selection Mode — Select code, then release to ask AI (Esc to cancel)';
    }
    // Listen for mouseup to detect selection complete
    document.addEventListener('mouseup', onF3MouseUp);
}

function exitF3Mode() {
    f3Mode = false;
    if (editor) {
        editor.updateOptions({ cursorStyle: 'line' });
    }
    var statusEl = document.getElementById('status-file');
    if (statusEl) {
        statusEl.style.color = '';
        var cf = activeTabPath || 'No file open';
        statusEl.textContent = cf;
    }
    document.removeEventListener('mouseup', onF3MouseUp);
    hideF3Card();
}

function onF3MouseUp() {
    if (!f3Mode) return;
    setTimeout(function() {
        if (!f3Mode) return;
        var selection = editor.getSelection();
        if (!selection || selection.isEmpty()) return;
        var model = editor.getModel();
        f3SelectedText = model.getValueInRange(selection);
        f3SelectedFile = activeTabPath || 'unknown';
        var startLine = selection.startLineNumber;
        var endLine = selection.endLineNumber;
        f3SelectedLines = startLine === endLine ? 'Line ' + startLine : 'Lines ' + startLine + '-' + endLine;
        showF3Card();
    }, 100);
}

function showF3Card() {
    var overlay = document.getElementById('f3-overlay');
    var card = document.getElementById('f3-card');
    
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'f3-overlay';
        document.body.appendChild(overlay);
    }
    if (!card) {
        card = document.createElement('div');
        card.id = 'f3-card';
        card.innerHTML =
            '<div id="f3-title"></div>' +
            '<div id="f3-preview"></div>' +
            '<div id="f3-more"></div>' +
            '<textarea id="f3-input" placeholder="What does this code do?" rows="2"></textarea>' +
            '<div id="f3-buttons">' +
            '<button id="f3-btn-cancel">Cancel</button>' +
            '<button id="f3-btn-send">Send</button>' +
            '</div>';
        document.body.appendChild(card);
        
        overlay.onclick = function() { exitF3Mode(); };
        card.querySelector('#f3-btn-cancel').onclick = function() { exitF3Mode(); };
        card.querySelector('#f3-btn-send').onclick = function() { sendF3Message(); };
        card.querySelector('#f3-input').onkeydown = function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendF3Message();
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                exitF3Mode();
            }
        };
    }

    // Fill in code preview
    var lines = f3SelectedText.split('\n');
    var preview = lines.slice(0, 6).join('\n');
    document.getElementById('f3-title').textContent = 'Selected: ' + f3SelectedLines + ' in ' + f3SelectedFile;
    document.getElementById('f3-preview').textContent = preview;
    var more = lines.length > 6 ? '... (' + (lines.length - 6) + ' more lines)' : '';
    document.getElementById('f3-more').textContent = more;
    document.getElementById('f3-input').value = '';
    
    overlay.style.display = 'block';
    card.style.display = 'block';
    document.getElementById('f3-input').focus();
}

function hideF3Card() {
    var overlay = document.getElementById('f3-overlay');
    var card = document.getElementById('f3-card');
    if (overlay) overlay.style.display = 'none';
    if (card) card.style.display = 'none';
}

function sendF3Message() {
    var question = document.getElementById('f3-input').value.trim();
    if (!question) return;
    
    exitF3Mode();
    
    // Build message with code context
    var fullMsg = '[Selected code from ' + f3SelectedFile + ' (' + f3SelectedLines + '):]\n\n' +
                  '```\n' + f3SelectedText + '\n```\n\n' +
                  '---\n\n' +
                  'User question: ' + question;
    
    // Switch to master chat if needed
    if (activeChatId && chatSessions[activeChatId] && chatSessions[activeChatId].type !== 'master') {
        var masterId = Object.keys(chatSessions).find(function(id) { return chatSessions[id].type === 'master'; });
        if (masterId) switchChat(masterId);
    }
    
    // Set input and send
    document.getElementById('chat-input').value = fullMsg;
    sendMessage();
}

/* ═══════════════════════════════════════
   Panel Resizers
   ═══════════════════════════════════════ */

(function() {
    function initResizer(id, targetId, direction, growRight) {
        var resizer = document.getElementById(id);
        var target = document.getElementById(targetId);
        if (!resizer || !target) return;

        var startX, startY, startSize;

        resizer.addEventListener('mousedown', function(e) {
            e.preventDefault();
            if (direction === 'h') {
                startX = e.clientX;
                startSize = target.offsetWidth;
                resizer.classList.add('active');
                document.body.classList.add('resizing');
            } else {
                startY = e.clientY;
                startSize = target.offsetHeight;
                resizer.classList.add('active');
                document.body.classList.add('resizing-v');
            }
        });

        document.addEventListener('mousemove', function(e) {
            if (!resizer.classList.contains('active')) return;
            if (direction === 'h') {
                var delta = e.clientX - startX;
                var newSize = growRight ? startSize + delta : startSize - delta;
                if (newSize < 120) newSize = 120;
                if (newSize > 500) newSize = 500;
                target.style.width = newSize + 'px';
                target.style.minWidth = newSize + 'px';
            } else {
                var delta = e.clientY - startY;
                var newSize = startSize + delta;
                if (newSize < 80) newSize = 80;
                if (newSize > window.innerHeight * 0.6) newSize = window.innerHeight * 0.6;
                target.style.minHeight = newSize + 'px';
                target.style.maxHeight = newSize + 'px';
                target.style.display = 'flex';
            }
            if (editor) editor.layout();
        });

        document.addEventListener('mouseup', function() {
            if (resizer.classList.contains('active')) {
                resizer.classList.remove('active');
                document.body.classList.remove('resizing');
                document.body.classList.remove('resizing-v');
                if (editor) editor.layout();
            }
        });
    }

    waitForPywebview(function() {
        initResizer('resizer-sidebar', 'sidebar', 'h', true);
        initResizer('resizer-chat', 'chat-panel', 'h', false);
        initResizer('resizer-terminal', 'terminal', 'v', true);
    });
})();

/* ═══════════════════════════════════════
   Shutdown Save
   ═══════════════════════════════════════ */

var isShuttingDown = false;

window.addEventListener('beforeunload', async function(e) {
    if (isShuttingDown) return;
    isShuttingDown = true;
    e.preventDefault();
    showAiStatus('💾 Saving...');
    while (window._sendingLock) {
        await new Promise(function(r) { setTimeout(r, 200); });
    }
    await autoSaveCurrentConversation();
    await saveProjectStateOnly();
    try { await pywebview.api.shutdown_save(); } catch(e) {}
    isShuttingDown = false;
    window.close();
});