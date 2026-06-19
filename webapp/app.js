/**
 * МагӀарул мацӀ — Аварский словарь
 * Telegram Mini App — Логика приложения
 */

(function () {
    'use strict';

    // ══════════════════════════════════════
    // Конфигурация
    // ══════════════════════════════════════

    const API_BASE = window.location.origin;
    const DEBOUNCE_MS = 300;
    const MAX_RESULTS = 50;

    // ══════════════════════════════════════
    // Состояние приложения
    // ══════════════════════════════════════

    const state = {
        currentDict: 'av-ru',
        query: '',
        results: [],
        isLoading: false,
        currentRandomWord: null,
        currentTab: 'search',
        viewingLetter: false,
    };

    // ══════════════════════════════════════
    // DOM элементы
    // ══════════════════════════════════════

    const $ = (id) => document.getElementById(id);

    const dom = {
        searchInput: $('searchInput'),
        searchClear: $('searchClear'),
        resultsList: $('resultsList'),
        resultsHeader: $('resultsHeader'),
        resultsCount: $('resultsCount'),
        loadingIndicator: $('loadingIndicator'),
        welcomeState: $('welcomeState'),
        emptyState: $('emptyState'),
        btnAvRu: $('btnAvRu'),
        btnRuAv: $('btnRuAv'),
        statsBadge: $('statsBadge'),
        modalOverlay: $('modalOverlay'),
        modal: $('modal'),
        modalContent: $('modalContent'),
        randomWordCard: $('randomWordCard'),
        randomWord: $('randomWord'),
        randomPos: $('randomPos'),
        randomTranslation: $('randomTranslation'),
        randomExample: $('randomExample'),
        randomExAv: $('randomExAv'),
        randomExRu: $('randomExRu'),
        refreshRandom: $('refreshRandom'),
        navSearch: $('navSearch'),
        navAlphabet: $('navAlphabet'),
        searchContainer: $('searchContainer'),
        alphabetState: $('alphabetState'),
        alphabetGrid: $('alphabetGrid'),
        bottomNav: $('bottomNav'),
    };

    // ══════════════════════════════════════
    // Telegram WebApp интеграция
    // ══════════════════════════════════════

    function initTelegram() {
        try {
            if (window.Telegram && window.Telegram.WebApp) {
                const tg = window.Telegram.WebApp;
                tg.ready();
                tg.expand();

                // Адаптация к теме Telegram
                if (tg.colorScheme === 'light') {
                    document.documentElement.style.setProperty('--color-bg-primary', '#f0f2f5');
                    document.documentElement.style.setProperty('--color-bg-secondary', '#ffffff');
                    document.documentElement.style.setProperty('--color-bg-card', 'rgba(255, 255, 255, 0.9)');
                    document.documentElement.style.setProperty('--color-bg-card-hover', 'rgba(240, 242, 245, 0.95)');
                    document.documentElement.style.setProperty('--color-bg-glass', 'rgba(0, 0, 0, 0.03)');
                    document.documentElement.style.setProperty('--color-bg-glass-strong', 'rgba(0, 0, 0, 0.06)');
                    document.documentElement.style.setProperty('--color-text-primary', '#1a1a2e');
                    document.documentElement.style.setProperty('--color-text-secondary', '#4a5568');
                    document.documentElement.style.setProperty('--color-text-muted', '#718096');
                    document.documentElement.style.setProperty('--border-subtle', 'rgba(0, 0, 0, 0.08)');
                    document.documentElement.style.setProperty('--color-surface', '#e2e8f0');
                }

                // Настройка кнопки "Назад"
                tg.BackButton.onClick(() => {
                    if (dom.modal.classList.contains('active')) {
                        closeModal();
                    } else if (state.viewingLetter) {
                        state.viewingLetter = false;
                        switchTab('alphabet');
                        tg.BackButton.hide();
                    } else {
                        tg.close();
                    }
                });
            }
        } catch (e) {
            console.log('Telegram WebApp SDK не доступен (работаем в браузере)');
        }
    }

    // ══════════════════════════════════════
    // API запросы
    // ══════════════════════════════════════

    async function apiSearch(query, dict, limit = MAX_RESULTS) {
        const url = `${API_BASE}/api/search?q=${encodeURIComponent(query)}&dict=${dict}&limit=${limit}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }

    async function apiGetWord(word, dict) {
        const url = `${API_BASE}/api/word/${encodeURIComponent(word)}?dict=${dict}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }

    async function apiGetRandom(dict = 'av-ru') {
        const url = `${API_BASE}/api/random?dict=${dict}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }

    async function apiGetStats() {
        const url = `${API_BASE}/api/stats`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }

    
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

    // ══════════════════════════════════════
    // Поиск
    // ══════════════════════════════════════

    let searchTimeout = null;

    function onSearchInput() {
        const query = dom.searchInput.value.trim();
        state.query = query;

        // Показать/скрыть кнопку очистки
        dom.searchClear.classList.toggle('visible', query.length > 0);

        // Отменить предыдущий таймер
        if (searchTimeout) clearTimeout(searchTimeout);

        if (!query) {
            showWelcome();
            return;
        }

        // Показать загрузку
        showLoading();

        // Debounce
        searchTimeout = setTimeout(() => performSearch(query), DEBOUNCE_MS);
    }

    async function performSearch(query) {
        if (query !== state.query) return; // Запрос устарел

        state.isLoading = true;

        try {
            const data = await apiSearch(query, state.currentDict);
            
            // Проверяем, что запрос ещё актуален
            if (query !== state.query) return;

            state.results = data.results || [];

            if (state.results.length === 0) {
                showEmpty();
            } else {
                showResults(state.results);
            }
        } catch (error) {
            console.error('Ошибка поиска:', error);
            showEmpty();
        } finally {
            state.isLoading = false;
        }
    }

    function clearSearch() {
        dom.searchInput.value = '';
        state.query = '';
        dom.searchClear.classList.remove('visible');
        showWelcome();
        dom.searchInput.focus();
    }

    // ══════════════════════════════════════
    // Переключение направления
    // ══════════════════════════════════════

    function switchDirection(dict) {
        if (state.currentDict === dict) return;

        state.currentDict = dict;

        // Обновить кнопки
        dom.btnAvRu.classList.toggle('active', dict === 'av-ru');
        dom.btnRuAv.classList.toggle('active', dict === 'ru-av');

        // Обновить placeholder
        dom.searchInput.placeholder = dict === 'av-ru'
            ? 'Введите слово на аварском...'
            : 'Введите слово на русском...';

        // Повторить поиск если есть запрос
        if (state.query) {
            showLoading();
            performSearch(state.query);
        }
    }

    // ══════════════════════════════════════
    // Отображение состояний
    // ══════════════════════════════════════

    function showWelcome() {
        dom.welcomeState.style.display = 'flex';
        dom.resultsList.innerHTML = '';
        dom.resultsHeader.classList.remove('visible');
        dom.emptyState.classList.remove('visible');
        dom.loadingIndicator.classList.remove('visible');
        hideBackButton();
    }

    function showLoading() {
        dom.welcomeState.style.display = 'none';
        dom.resultsList.innerHTML = '';
        dom.resultsHeader.classList.remove('visible');
        dom.emptyState.classList.remove('visible');
        dom.loadingIndicator.classList.add('visible');
    }

    function showEmpty() {
        dom.welcomeState.style.display = 'none';
        dom.resultsList.innerHTML = '';
        dom.resultsHeader.classList.remove('visible');
        dom.loadingIndicator.classList.remove('visible');
        dom.emptyState.classList.add('visible');
    }

    function showResults(results) {
        dom.welcomeState.style.display = 'none';
        dom.loadingIndicator.classList.remove('visible');
        dom.emptyState.classList.remove('visible');

        // Обновить счётчик
        dom.resultsCount.textContent = `${results.length} ${pluralize(results.length, 'результат', 'результата', 'результатов')}`;
        dom.resultsHeader.classList.add('visible');

        // Рендер результатов
        dom.resultsList.innerHTML = '';
        const fragment = document.createDocumentFragment();

        results.forEach((item, index) => {
            const card = createWordCard(item, index);
            fragment.appendChild(card);
        });

        dom.resultsList.appendChild(fragment);
    }

    // ══════════════════════════════════════
    // Создание карточек
    // ══════════════════════════════════════

    function createWordCard(item, index) {
        const card = document.createElement('div');
        card.className = 'word-card';
        card.style.animationDelay = `${index * 0.04}s`;

        let html = `
            <div class="word-card-top">
                <span class="word-text">${escapeHtml(item.word)}</span>
                ${item.pos ? `<span class="word-pos">${escapeHtml(item.pos)}</span>` : ''}
            </div>
        `;

        if (item.translation) {
            html += `<div class="word-translation">${escapeHtml(item.translation)}</div>`;
        }

        if (item.has_examples) {
            html += `<div class="word-example-indicator">💬 есть примеры</div>`;
        }

        card.innerHTML = html;

        card.addEventListener('click', () => openWordDetail(item.word));

        return card;
    }

    // ══════════════════════════════════════
    // Детали слова (модальное окно)
    // ══════════════════════════════════════

    async function openWordDetail(word) {
        try {
            const data = await apiGetWord(word, state.currentDict);
            const entries = data.entries || [];

            if (entries.length === 0) return;

            dom.modalContent.innerHTML = renderWordDetail(entries);
            openModal();

            // Привязать обработчики see_also ссылок
            dom.modalContent.querySelectorAll('.see-also-link').forEach(link => {
                link.addEventListener('click', () => {
                    const target = link.dataset.word;
                    if (target) {
                        closeModal();
                        setTimeout(() => openWordDetail(target), 300);
                    }
                });
            });

        } catch (error) {
            console.error('Ошибка загрузки слова:', error);
        }
    }

    function renderWordDetail(entries) {
        let html = '';

        entries.forEach((entry, entryIdx) => {
            const word = entry.word || '?';
            const pos = entry.pos || '';
            const form = entry.form || '';
            const senses = entry.senses || [];
            const forms = entry.forms || [];
            const seeAlso = entry.see_also || [];

            // Header
            html += `<div class="modal-word-header">`;
            html += `<div class="modal-word">${escapeHtml(word)}</div>`;
            html += `<div class="modal-word-meta">`;
            if (pos) html += `<span class="modal-pos-badge">${escapeHtml(pos)}</span>`;
            if (form && form !== '—') html += `<span class="modal-form-badge">${escapeHtml(form)}</span>`;
            html += `</div>`;
            html += `</div>`;

            // Senses
            const meaningfulSenses = senses.filter(s => s.text || (s.examples && s.examples.length > 0));
            
            meaningfulSenses.forEach((sense, senseIdx) => {
                html += `<div class="sense-block">`;

                const text = sense.text || '';
                const comment = sense.comment || '';
                const labels = sense.labels || [];
                const examples = sense.examples || [];

                if (text) {
                    html += `<div class="sense-header">`;
                    if (meaningfulSenses.length > 1) {
                        html += `<span class="sense-number">${senseIdx + 1}</span>`;
                    }
                    html += `<span class="sense-text">${escapeHtml(text)}</span>`;
                    html += `</div>`;
                }

                if (comment) {
                    html += `<div class="sense-comment">💬 ${escapeHtml(comment)}</div>`;
                }

                if (labels.length > 0) {
                    html += `<div class="sense-labels">`;
                    labels.forEach(label => {
                        html += `<span class="sense-label">${escapeHtml(label)}</span>`;
                    });
                    html += `</div>`;
                }

                if (examples.length > 0) {
                    html += `<div class="examples-block">`;
                    examples.forEach(ex => {
                        html += `<div class="example-item">`;
                        if (ex.av) html += `<div class="example-av">${escapeHtml(ex.av)}</div>`;
                        if (ex.ru) html += `<div class="example-ru">${escapeHtml(ex.ru)}</div>`;
                        if (ex.labels && ex.labels.length) {
                            html += `<div class="example-label">${escapeHtml(ex.labels.join(', '))}</div>`;
                        }
                        html += `</div>`;
                    });
                    html += `</div>`;
                }

                html += `</div>`;
            });

            // Forms
            if (forms.length > 1) {
                html += `<div class="forms-section">`;
                html += `<div class="forms-title">📝 Формы слова</div>`;
                html += `<div class="forms-grid">`;
                forms.forEach(f => {
                    html += `<span class="form-chip">${escapeHtml(f)}</span>`;
                });
                html += `</div></div>`;
            }

            // See also
            if (seeAlso.length > 0) {
                html += `<div class="see-also-section">`;
                html += `<div class="see-also-title">🔗 См. также</div>`;
                seeAlso.forEach(ref => {
                    const target = ref.target || '';
                    const kind = ref.kind || '';
                    if (target) {
                        html += `<span class="see-also-link" data-word="${escapeHtml(target)}">${escapeHtml(target)}</span>`;
                    }
                });
                html += `</div>`;
            }

            // Separator between multiple entries
            if (entryIdx < entries.length - 1) {
                html += `<hr style="border: none; border-top: 1px solid var(--border-subtle); margin: 20px 0;">`;
            }
        });

        return html;
    }

    // ══════════════════════════════════════
    // Modal управление
    // ══════════════════════════════════════

    function openModal() {
        dom.modalOverlay.classList.add('active');
        dom.modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        showBackButton();
    }

    function closeModal() {
        dom.modalOverlay.classList.remove('active');
        dom.modal.classList.remove('active');
        document.body.style.overflow = '';
        if (!state.query) hideBackButton();
    }

    function showBackButton() {
        try {
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.BackButton.show();
            }
        } catch (e) {}
    }

    function hideBackButton() {
        try {
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.BackButton.hide();
            }
        } catch (e) {}
    }

    // ══════════════════════════════════════
    // Случайное слово
    // ══════════════════════════════════════

    async function loadRandomWord() {
        try {
            const data = await apiGetRandom('av-ru');
            const entry = data.entry;
            if (!entry) return;

            state.currentRandomWord = entry;

            dom.randomWord.textContent = entry.word || '—';
            dom.randomPos.textContent = entry.pos || '';

            // Перевод
            const senses = entry.senses || [];
            const translations = senses
                .map(s => s.text)
                .filter(Boolean)
                .slice(0, 2);
            dom.randomTranslation.textContent = translations.join('; ') || 'перевод не найден';

            // Пример
            let foundExample = null;
            for (const sense of senses) {
                if (sense.examples && sense.examples.length > 0) {
                    foundExample = sense.examples[0];
                    break;
                }
            }

            if (foundExample) {
                dom.randomExample.style.display = 'block';
                dom.randomExAv.textContent = foundExample.av || '';
                dom.randomExRu.textContent = foundExample.ru || '';
            } else {
                dom.randomExample.style.display = 'none';
            }

        } catch (error) {
            console.error('Ошибка загрузки случайного слова:', error);
            dom.randomWord.textContent = '—';
            dom.randomTranslation.textContent = 'Не удалось загрузить';
        }
    }

    // ══════════════════════════════════════
    // Статистика
    // ══════════════════════════════════════

    async function loadStats() {
        try {
            const stats = await apiGetStats();
            const avRu = stats['av-ru'];
            const ruAv = stats['ru-av'];

            if (avRu && ruAv) {
                const total = (avRu.total_entries || 0) + (ruAv.total_entries || 0);
                dom.statsBadge.textContent = `${total.toLocaleString('ru-RU')} статей`;
            }
        } catch (error) {
            dom.statsBadge.textContent = 'словарь';
        }
    }

    // ══════════════════════════════════════
    // Утилиты
    // ══════════════════════════════════════

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function pluralize(n, one, few, many) {
        const abs = Math.abs(n) % 100;
        const lastDigit = abs % 10;
        if (abs > 10 && abs < 20) return many;
        if (lastDigit > 1 && lastDigit < 5) return few;
        if (lastDigit === 1) return one;
        return many;
    }

    // ══════════════════════════════════════
    // Touch gestures для модального окна
    // ══════════════════════════════════════

    let touchStartY = 0;
    let touchDeltaY = 0;

    function initModalGestures() {
        const modal = dom.modal;

        modal.addEventListener('touchstart', (e) => {
            if (dom.modalContent.scrollTop <= 0) {
                touchStartY = e.touches[0].clientY;
            }
        }, { passive: true });

        modal.addEventListener('touchmove', (e) => {
            if (dom.modalContent.scrollTop <= 0) {
                touchDeltaY = e.touches[0].clientY - touchStartY;
                if (touchDeltaY > 0) {
                    modal.style.transform = `translateY(${touchDeltaY}px)`;
                    modal.style.transition = 'none';
                }
            }
        }, { passive: true });

        modal.addEventListener('touchend', () => {
            modal.style.transition = '';
            if (touchDeltaY > 100) {
                closeModal();
            } else {
                modal.style.transform = '';
            }
            touchDeltaY = 0;
            touchStartY = 0;
        });
    }

    // ══════════════════════════════════════
    // Инициализация
    // ══════════════════════════════════════

    function init() {
        // Telegram
        initTelegram();

        // Обработчики поиска
        dom.searchInput.addEventListener('input', onSearchInput);
        dom.searchClear.addEventListener('click', clearSearch);
        dom.navSearch.addEventListener('click', () => switchTab('search'));
        dom.navAlphabet.addEventListener('click', () => switchTab('alphabet'));

        // Переключатель направления
        dom.btnAvRu.addEventListener('click', () => switchDirection('av-ru'));
        dom.btnRuAv.addEventListener('click', () => switchDirection('ru-av'));

        // Модальное окно
        dom.modalOverlay.addEventListener('click', closeModal);
        initModalGestures();

        // Клавиша Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && dom.modal.classList.contains('active')) {
                closeModal();
            }
        });

        // Случайное слово
        dom.refreshRandom.addEventListener('click', loadRandomWord);
        dom.randomWordCard.addEventListener('click', () => {
            if (state.currentRandomWord) {
                openWordDetail(state.currentRandomWord.word);
            }
        });

        // Загрузка данных
        loadStats();
        loadRandomWord();

        // Показать приветствие
        showWelcome();

        console.log('📖 МагӀарул мацӀ — Аварский словарь загружен!');
    }

    // Запуск при готовности DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
