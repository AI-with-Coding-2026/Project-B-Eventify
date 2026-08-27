/**
 * Admin Data Grid — shared sorting, search & filter controller.
 *
 * Auto-initialises on any page that contains elements matching:
 *   [data-datagrid]           — a <table> element
 *   [data-datagrid-search]    — a text/search <input> scoped to a grid
 *   [data-datagrid-filter]    — a <select> for column-value filtering
 *   [data-datagrid-count]     — an element whose text is updated with the visible row count
 *   [data-sort]               — a <button> inside <th> to make that column sortable
 */
(function () {
    'use strict';

    /* ── Sorting ───────────────────────────────────────────────── */

    function initSorting(table) {
        var buttons = table.querySelectorAll('thead [data-sort]');

        buttons.forEach(function (btn) {
            btn.style.cursor = 'pointer';
            btn.style.userSelect = 'none';

            // Add single full-arrow sort indicator span (default: descending icon ↓)
            var indicator = document.createElement('span');
            indicator.className = 'sort-indicator';
            indicator.style.marginLeft = '4px';
            indicator.style.opacity = '0.35';
            indicator.style.fontSize = '0.85em';
            indicator.textContent = '↓';
            btn.appendChild(indicator);

            btn.addEventListener('click', function () {
                var colIndex = Number(btn.dataset.sort);
                var currentDir = table.dataset.sortCol === String(colIndex)
                    ? table.dataset.sortDir
                    : null;
                // When clicked for the first time, sort ascending (↑); subsequent clicks toggle
                var direction = currentDir === 'asc' ? 'desc' : 'asc';
                var tbody = table.tBodies[0];
                if (!tbody) return;

                var rows = Array.from(tbody.rows);

                rows.sort(function (a, b) {
                    var aText = (a.cells[colIndex] || {textContent: ''}).textContent.trim().toLowerCase();
                    var bText = (b.cells[colIndex] || {textContent: ''}).textContent.trim().toLowerCase();

                    // Try numeric comparison first
                    var aNum = parseFloat(aText.replace(/[^0-9.\-]/g, ''));
                    var bNum = parseFloat(bText.replace(/[^0-9.\-]/g, ''));

                    var cmp;
                    if (!isNaN(aNum) && !isNaN(bNum)) {
                        cmp = aNum - bNum;
                    } else {
                        cmp = aText.localeCompare(bText);
                    }

                    return direction === 'asc' ? cmp : -cmp;
                });

                rows.forEach(function (row) { tbody.appendChild(row); });

                // Update state
                table.dataset.sortCol = String(colIndex);
                table.dataset.sortDir = direction;

                // Update all indicators in this table
                buttons.forEach(function (b) {
                    var ind = b.querySelector('.sort-indicator');
                    if (!ind) return;

                    if (Number(b.dataset.sort) === colIndex) {
                        ind.style.opacity = '1';
                        ind.textContent = direction === 'asc' ? '↑' : '↓';
                    } else {
                        ind.style.opacity = '0.35';
                        ind.textContent = '↓';
                    }
                });
            });
        });
    }

    /* ── Search ─────────────────────────────────────────────────── */

    function initSearch(wrapper) {
        var searchInput = wrapper.querySelector('[data-datagrid-search]');
        var searchColumn = wrapper.querySelector('[data-datagrid-search-column]');
        var tables = wrapper.querySelectorAll('[data-datagrid]');

        if (!searchInput || tables.length === 0) return;

        function applySearch() {
            var query = searchInput.value.toLowerCase().trim();
            var columnIndex = searchColumn ? Number(searchColumn.value) : -1;

            tables.forEach(function (table) {
                var tbody = table.tBodies[0];
                if (!tbody) return;

                var visibleCount = 0;
                Array.from(tbody.rows).forEach(function (row) {
                    var text = columnIndex >= 0
                        ? (row.cells[columnIndex] || {textContent: ''}).textContent.toLowerCase()
                        : row.textContent.toLowerCase();
                    var matches = !query || text.indexOf(query) !== -1;
                    row.style.display = matches ? '' : 'none';
                    if (matches) visibleCount++;
                });

                // Update row count if present
                var countEl = wrapper.querySelector('[data-datagrid-count]');
                if (countEl) {
                    var totalRows = tbody.rows.length;
                    if (query) {
                        countEl.textContent = visibleCount + ' of ' + totalRows;
                    } else {
                        countEl.textContent = totalRows;
                    }
                }
            });
        }

        searchInput.addEventListener('input', applySearch);
        if (searchColumn) searchColumn.addEventListener('change', applySearch);
    }

    /* ── Column-Value Filter ───────────────────────────────────── */

    function initFilter(wrapper) {
        var filterSelect = wrapper.querySelector('[data-datagrid-filter]');
        var tables = wrapper.querySelectorAll('[data-datagrid]');

        if (!filterSelect || tables.length === 0) return;

        var filterCol = parseInt(filterSelect.dataset.datagridFilter, 10);

        filterSelect.addEventListener('change', function () {
            var filterValue = filterSelect.value.toLowerCase().trim();

            tables.forEach(function (table) {
                var tbody = table.tBodies[0];
                if (!tbody) return;

                Array.from(tbody.rows).forEach(function (row) {
                    if (!filterValue || filterValue === 'all') {
                        row.style.display = '';
                        return;
                    }
                    var cellText = (row.cells[filterCol] || {textContent: ''}).textContent.toLowerCase().trim();
                    row.style.display = cellText.indexOf(filterValue) !== -1 ? '' : 'none';
                });
            });
        });
    }

    /* ── Initialise ────────────────────────────────────────────── */

    function init() {
        // Initialise sorting on every data-grid table (skip tables with data-no-init)
        document.querySelectorAll('[data-datagrid]:not([data-no-init])').forEach(initSorting);

        // Initialise search & filter on wrappers
        document.querySelectorAll('[data-datagrid-wrapper]').forEach(function (wrapper) {
            initSearch(wrapper);
            initFilter(wrapper);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
