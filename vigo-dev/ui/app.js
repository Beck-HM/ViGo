// ViGo Dev - Frontend Application Logic

// ═══════════════════════════════════════
//  Monaco Editor Setup
// ═══════════════════════════════════════
alert('JS loaded');
let editor;

require.config({
    paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs' }
});

require(['vs/editor/editor.main'], function () {
    editor = monaco.editor.create(document.getElementById('editor'), {
        value: '// Welcome to ViGo Dev\n// Select a file from the project tree to start editing.\n\nprint("Hello from ViGo Dev!")',
        language: 'python',
        theme: 'vs-dark',
        fontSize: 13,
        minimap: { enabled: false },
        automaticLayout: true,
        scrollBeyondLastLine: false,
        wordWrap: 'on',
    });

    // Load file tree after editor is ready
    loadFileTree();
    loadModels();
    updateStatusBar();
});

// ═══════════════════════════════════════
//  File Tree
// ═══════════════════════════════════════
async function loadFileTree() {
    try {
        const treeData = await pywebview.api.get_file_tree();
        const tree = JSON.parse(treeData);
        renderTree(tree, document.getElementById('file-tree'));
    } catch (e) {
        document.getElementById('file-tree').innerHTML = '<div class="tree-item">Error loading files</div>';
    }
}

function renderTree(items, container, depth = 0) {
    container.innerHTML = '';
    items.forEach(item => {
        const div = document.createElement('div');
        div.className = `tree-item ${item.type} ${item.type === 'file' ? item.ext.replace('.', '') : ''}`;
        div.style.paddingLeft = (14 + depth * 14) + 'px';
        const icon = item.type === 'dir' ? '📁' : '📄';
        div.textContent = `${icon} ${item.name}`;

        if (item.type === 'file') {
            div.onclick = () => openFile(item.path, item.name);
        } else if (item.type === 'dir') {
            div.onclick = function(e) {
                e.stopPropagation();
                const childrenDiv = this.nextElementSibling;
                if (childrenDiv && childrenDiv.classList.contains('tree-children')) {
                    childrenDiv.style.display = childrenDiv.style.display === 'none' ? 'block' : 'none';
                }
            };
            container.appendChild(div);
            if (item.children && item.children.length > 0) {
                const childrenContainer = document.createElement('div');
                childrenContainer.className = 'tree-children';
                renderTree(item.children, childrenContainer, depth + 1);
                container.appendChild(childrenContainer);
            }
            return;
        }
        container.appendChild(div);
    });
}

// ═══════════════════════════════════════
//  File Operations
// ═══════════════════════════════════════
async function openFile(path, name) {
    try {
        const content = await pywebview.api.read_file(path);
        editor.setValue(content);

        // Set language based on extension
        const ext = path.split('.').pop();
        const langMap = { py: 'python', vigo: 'python', js: 'javascript', html: 'html', css: 'css', json: 'json', md: 'markdown', yaml: 'yaml', yml: 'yaml' };
        const lang = langMap[ext] || 'plaintext';
        monaco.editor.setModelLanguage(editor.getModel(), lang);

        document.getElementById('tab-label').textContent = name;
        document.getElementById('status-file').textContent = path;
    } catch (e) {
        console.error('Error opening file:', e);
    }
}

async function saveCurrentFile() {
    const currentFile = await pywebview.api.get_current_file();
    if (!currentFile) return;
    const content = editor.getValue();
    const result = await pywebview.api.save_file(currentFile, content);
    console.log('Save result:', result);
}

// Keyboard shortcut: Ctrl+S
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveCurrentFile();
    }
});

// ═══════════════════════════════════════
//  Model Management
// ═══════════════════════════════════════
async function loadModels() {
    try {
        const models = JSON.parse(await pywebview.api.list_models());
        const select = document.getElementById('model-select');
        select.innerHTML = '';

        if (models.length === 0) {
            select.innerHTML = '<option value="">No models found</option>';
            return;
        }

        // Group by source
        const localModels = models.filter(m => m.source === 'local');
        const cloudModels = models.filter(m => m.source === 'cloud');

        if (localModels.length > 0) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = '🖥️ Local (Ollama)';
            localModels.forEach(m => {
                const opt = document.createElement('option');
                opt.value = JSON.stringify({ id: m.id, provider: m.provider });
                opt.textContent = m.name || m.id;
                optgroup.appendChild(opt);
            });
            select.appendChild(optgroup);
        }

        if (cloudModels.length > 0) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = '☁️ Cloud';
            cloudModels.forEach(m => {
                const opt = document.createElement('option');
                opt.value = JSON.stringify({ id: m.id, provider: m.provider });
                opt.textContent = m.name || m.id;
                optgroup.appendChild(opt);
            });
            select.appendChild(optgroup);
        }

        select.onchange = onModelChange;
        updateStatusBar();
    } catch (e) {
        console.error('Error loading models:', e);
    }
}

async function onModelChange() {
    const select = document.getElementById('model-select');
    const value = select.value;
    if (!value) return;
    try {
        const { id, provider } = JSON.parse(value);
        await pywebview.api.set_model(id, provider);
        updateStatusBar();
    } catch (e) {
        console.error('Error setting model:', e);
    }
}

// ═══════════════════════════════════════
//  Chat
// ═══════════════════════════════════════
document.getElementById('btn-send').addEventListener('click', sendMessage);
document.getElementById('chat-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    appendMessage('user', message);
    input.value = '';
    document.getElementById('btn-send').disabled = true;

    try {
        const response = JSON.parse(await pywebview.api.ask_ai(message));
        if (response.status === 'ok') {
            appendMessage('ai', response.response);
            // Auto-save to memory
            pywebview.api.mem_save('chat_' + Date.now(), 'User: ' + message + '\nAI: ' + response.response);
        } else {
            appendMessage('ai', '❌ Error: ' + (response.response || 'Unknown error'));
        }
    } catch (e) {
        appendMessage('ai', '❌ Error connecting to AI: ' + e.message);
    }

    document.getElementById('btn-send').disabled = false;
}

function appendMessage(role, text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message ' + role;

    // Simple code block detection
    if (text.includes('```')) {
        const parts = text.split('```');
        let html = '';
        parts.forEach((part, i) => {
            if (i % 2 === 1) {
                // Code block
                const lines = part.split('\n');
                const code = lines.slice(lines[0] ? 1 : 0).join('\n') || part;
                html += '<pre><code>' + escapeHtml(code) + '</code></pre>';
            } else {
                html += escapeHtml(part);
            }
        });
        div.innerHTML = html;
    } else {
        div.textContent = text;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ═══════════════════════════════════════
//  Toolbar Buttons
// ═══════════════════════════════════════
document.getElementById('btn-test').addEventListener('click', async function() {
    appendMessage('ai', '🧪 Running regression tests...');
    try {
        const result = JSON.parse(await pywebview.api.run_test());
        appendMessage('ai', result.status === 'ok' ? '✅ Tests passed!\n' + result.stdout : '❌ Tests failed!\n' + result.stdout);
    } catch (e) {
        appendMessage('ai', '❌ Error running tests: ' + e.message);
    }
});

document.getElementById('btn-snapshot').addEventListener('click', async function() {
    try {
        const snap = JSON.parse(await pywebview.api.mem_snapshot());
        appendMessage('ai', '🧠 Memory Snapshot:\n' +
            'Total memories: ' + snap.total + '\n' +
            'Oldest: ' + (snap.oldest || 'N/A') + '\n' +
            'Newest: ' + (snap.newest || 'N/A') + '\n' +
            'ChromaDB: ' + (snap.chromadb ? 'Active' : 'Off'));
    } catch (e) {
        appendMessage('ai', '❌ Error: ' + e.message);
    }
});

// ═══════════════════════════════════════
//  Status Bar
// ═══════════════════════════════════════
async function updateStatusBar() {
    try {
        const currentFile = await pywebview.api.get_current_file();
        document.getElementById('status-file').textContent = currentFile || 'No file open';

        const select = document.getElementById('model-select');
        if (select.value) {
            const { id } = JSON.parse(select.value);
            document.getElementById('status-model').textContent = 'Model: ' + id;
        }
    } catch (e) {
        // API not ready yet
    }
}