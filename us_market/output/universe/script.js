(function () {
    const searchInput  = document.getElementById('searchInput');
    const resultCount  = document.getElementById('resultCount');
    const cards        = Array.from(document.querySelectorAll('.card-link'));
    const btnAlpha     = document.getElementById('sortAlpha');
    const btnChange    = document.getElementById('sortChange');
    const grid         = document.getElementById('cardGrid');

    let currentSort = 'alpha';

    function getVisible() {
        return cards.filter(c => !c.classList.contains('hidden'));
    }

    function updateCount() {
        resultCount.innerHTML = '<span>' + getVisible().length + '</span> tickers';
    }

    function applySearch() {
        const q = searchInput.value.trim().toLowerCase();
        cards.forEach(c => {
            const match = !q ||
                c.dataset.ticker.toLowerCase().includes(q) ||
                c.dataset.name.toLowerCase().includes(q) ||
                c.dataset.sector.toLowerCase().includes(q) ||
                c.dataset.industry.toLowerCase().includes(q);
            c.classList.toggle('hidden', !match);
        });
        updateCount();
        applySort(currentSort);
    }

    function applySort(mode) {
        currentSort = mode;
        btnAlpha.classList.toggle('active', mode === 'alpha');
        btnChange.classList.toggle('active', mode === 'change');

        const visible = getVisible();
        visible.sort((a, b) => {
            if (mode === 'alpha') {
                return a.dataset.ticker.localeCompare(b.dataset.ticker);
            } else {
                const ca = parseFloat(a.dataset.change) || -9999;
                const cb = parseFloat(b.dataset.change) || -9999;
                return cb - ca;
            }
        });
        visible.forEach(c => grid.appendChild(c));
    }

    searchInput.addEventListener('input', applySearch);
    btnAlpha.addEventListener('click',  () => applySort('alpha'));
    btnChange.addEventListener('click', () => applySort('change'));

    updateCount();
    applySort('alpha');
})();
