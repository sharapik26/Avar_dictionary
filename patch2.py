import sys

with open('webapp/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. State
content = content.replace(
    'currentRandomWord: null,\n    };',
    'currentRandomWord: null,\n        currentTab: \'search\',\n        viewingLetter: false,\n    };'
)

# 2. DOM
content = content.replace(
    'refreshRandom: $(\'refreshRandom\'),\n    };',
    'refreshRandom: $(\'refreshRandom\'),\n        navSearch: $(\'navSearch\'),\n        navAlphabet: $(\'navAlphabet\'),\n        searchContainer: $(\'searchContainer\'),\n        alphabetState: $(\'alphabetState\'),\n        alphabetGrid: $(\'alphabetGrid\'),\n        bottomNav: $(\'bottomNav\'),\n    };'
)

# 3. Telegram BackButton
content = content.replace(
    '''                tg.BackButton.onClick(() => {
                    if (dom.modal.classList.contains('active')) {
                        closeModal();
                    } else {
                        tg.close();
                    }
                });''',
    '''                tg.BackButton.onClick(() => {
                    if (dom.modal.classList.contains('active')) {
                        closeModal();
                    } else if (state.viewingLetter) {
                        state.viewingLetter = false;
                        switchTab('alphabet');
                        tg.BackButton.hide();
                    } else {
                        tg.close();
                    }
                });'''
)

# 4. API & Tabs logic
api_code = """
    async function apiGetAlphabet(dict) {
        const url = `${API_BASE}/api/alphabet?dict=${dict}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }

    async function apiGetWordsByLetter(letter, dict) {
        const url = `${API_BASE}/api/words_by_letter/${encodeURIComponent(letter)}?dict=${dict}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }

    // ══════════════════════════════════════
    // Вкладки и Алфавит
    // ══════════════════════════════════════

    function switchTab(tab) {
        if (state.currentTab === tab) return;
        state.currentTab = tab;

        dom.navSearch.classList.toggle('active', tab === 'search');
        dom.navAlphabet.classList.toggle('active', tab === 'alphabet');

        if (tab === 'search') {
            dom.searchContainer.style.display = 'block';
            dom.alphabetState.style.display = 'none';
            state.viewingLetter = false;
            hideBackButton();
            if (state.query) {
                performSearch(state.query);
            } else {
                showWelcome();
            }
        } else {
            dom.searchContainer.style.display = 'none';
            dom.welcomeState.style.display = 'none';
            dom.emptyState.classList.remove('visible');
            dom.resultsList.innerHTML = '';
            dom.resultsHeader.classList.remove('visible');
            dom.alphabetState.style.display = 'block';
            loadAlphabet();
        }
    }

    async function loadAlphabet() {
        dom.alphabetGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--color-text-muted); padding: 20px;">Загрузка...</div>';
        try {
            const data = await apiGetAlphabet(state.currentDict);
            dom.alphabetGrid.innerHTML = '';
            data.forEach(item => {
                const tile = document.createElement('div');
                tile.className = 'alphabet-tile';
                tile.innerHTML = `<div class="alphabet-tile-letter">${item.letter}</div><div class="alphabet-tile-count">${item.count}</div>`;
                tile.onclick = () => loadWordsByLetter(item.letter);
                dom.alphabetGrid.appendChild(tile);
            });
        } catch (error) {
            dom.alphabetGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #ef4444; padding: 20px;">Ошибка загрузки</div>';
        }
    }

    async function loadWordsByLetter(letter) {
        dom.alphabetState.style.display = 'none';
        showLoading();
        try {
            const data = await apiGetWordsByLetter(letter, state.currentDict);
            state.results = data || [];
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.BackButton.show();
                state.viewingLetter = true;
            }
            showResults(state.results);
            dom.resultsCount.textContent = `Слова на букву «${letter}» (${state.results.length})`;
        } catch (error) {
            showEmpty();
        }
    }
"""
content = content.replace(
    '// ══════════════════════════════════════\n    // Поиск',
    api_code + '\n    // ══════════════════════════════════════\n    // Поиск'
)

# 5. Init listeners
content = content.replace(
    "dom.searchClear.addEventListener('click', clearSearch);",
    "dom.searchClear.addEventListener('click', clearSearch);\n        dom.navSearch.addEventListener('click', () => switchTab('search'));\n        dom.navAlphabet.addEventListener('click', () => switchTab('alphabet'));"
)

with open('webapp/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCHED SUCCESSFULLY")
