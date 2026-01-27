/**
 * Hawaii Bill Tracker Widget
 * Auto-updating RSS feed tracker for Hawaii Legislature bills
 * 
 * Usage:
 * 1. Add data attributes to your tracker element:
 *    <div class="tfc-bill-tracker" 
 *         data-tracker-id="freezing-act-46"
 *         data-hb="476,477" 
 *         data-sb="123">
 *    </div>
 * 
 * 2. Initialize: BillTrackerWidget.initAll()
 * 
 * 3. Or configure manually:
 *    BillTrackerWidget.init({
 *      trackerId: 'freezing-act-46',
 *      hbNumbers: ['476'],
 *      sbNumbers: ['123'],
 *      year: '2026',
 *      refreshInterval: 3600000
 *    });
 */

const BillTrackerWidget = (function() {
    'use strict';

    // Configuration
    const CONFIG = {
        corsProxy: 'https://api.allorigins.win/raw?url=',
        baseUrl: 'https://www.capitol.hawaii.gov/sessions/session',
        defaultYear: '2026',
        refreshInterval: 3600000, // 1 hour in milliseconds
        cachePrefix: 'btw_cache_',
        cacheDuration: 1800000, // 30 minutes cache
        maxRetries: 3,
        retryDelay: 5000
    };

    // Store for all tracker instances
    const trackers = {};

    /**
     * Build RSS feed URL for a bill
     * Format: https://www.capitol.hawaii.gov/sessions/session2026/rss/HB2010.xml
     */
    function buildRssUrl(billType, billNumber, year) {
        year = year || CONFIG.defaultYear;
        return `${CONFIG.baseUrl}${year}/rss/${billType.toUpperCase()}${billNumber}.xml`;
    }

    /**
     * Fetch RSS feed with CORS proxy and caching
     */
    async function fetchRSS(billType, billNumber, year, retryCount = 0) {
        const cacheKey = `${CONFIG.cachePrefix}${billType}_${billNumber}_${year}`;
        
        // Check cache first
        const cached = getFromCache(cacheKey);
        if (cached) {
            console.log(`[BillTracker] Using cached data for ${billType}${billNumber}`);
            return cached;
        }

        const rssUrl = buildRssUrl(billType, billNumber, year);
        const proxyUrl = CONFIG.corsProxy + encodeURIComponent(rssUrl);

        try {
            console.log(`[BillTracker] Fetching ${billType}${billNumber} from ${rssUrl}`);
            const response = await fetch(proxyUrl);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const xmlText = await response.text();
            
            // Validate XML
            if (!xmlText.includes('<rss') && !xmlText.includes('<item>')) {
                throw new Error('Invalid RSS response');
            }
            
            // Cache the result
            saveToCache(cacheKey, xmlText);
            
            return xmlText;
        } catch (error) {
            console.warn(`[BillTracker] Fetch failed for ${billType}${billNumber}:`, error.message);
            
            // Retry logic
            if (retryCount < CONFIG.maxRetries) {
                console.log(`[BillTracker] Retrying in ${CONFIG.retryDelay/1000}s... (${retryCount + 1}/${CONFIG.maxRetries})`);
                await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelay));
                return fetchRSS(billType, billNumber, year, retryCount + 1);
            }
            
            return null;
        }
    }

    /**
     * Cache management
     */
    function getFromCache(key) {
        try {
            const item = localStorage.getItem(key);
            if (!item) return null;
            
            const { data, timestamp } = JSON.parse(item);
            
            // Check if cache is still valid
            if (Date.now() - timestamp < CONFIG.cacheDuration) {
                return data;
            }
            
            // Cache expired
            localStorage.removeItem(key);
            return null;
        } catch (e) {
            return null;
        }
    }

    function saveToCache(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify({
                data: data,
                timestamp: Date.now()
            }));
        } catch (e) {
            console.warn('[BillTracker] Cache save failed:', e.message);
        }
    }

    function clearCache() {
        const keys = Object.keys(localStorage).filter(k => k.startsWith(CONFIG.cachePrefix));
        keys.forEach(k => localStorage.removeItem(k));
        console.log(`[BillTracker] Cleared ${keys.length} cached items`);
    }

    /**
     * Parse RSS XML into structured data
     */
    function parseRSS(xmlText) {
        if (!xmlText) return [];

        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, "text/xml");
        
        // Check for parse errors
        const parseError = xmlDoc.querySelector('parsererror');
        if (parseError) {
            console.warn('[BillTracker] XML parse error');
            return [];
        }

        const items = xmlDoc.getElementsByTagName("item");
        const updates = [];

        for (let i = 0; i < items.length; i++) {
            const titleEl = items[i].getElementsByTagName("title")[0];
            const pubDateEl = items[i].getElementsByTagName("pubDate")[0];
            const linkEl = items[i].getElementsByTagName("link")[0];

            if (!titleEl || !pubDateEl) continue;

            const title = titleEl.textContent;
            const pubDate = pubDateEl.textContent;
            const link = linkEl ? linkEl.textContent : '';

            // Parse description from title (format: "Date Bill: Description")
            let description = title;
            const parts = title.split(': ');
            if (parts.length > 1) {
                description = parts.slice(1).join(': ');
            }

            updates.push({
                title: title,
                description: description,
                date: new Date(pubDate).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                }),
                rawDate: new Date(pubDate),
                link: link
            });
        }

        // Sort by date descending (newest first)
        updates.sort((a, b) => b.rawDate - a.rawDate);

        return updates;
    }

    /**
     * Determine status badge from description
     */
    function getStatusBadge(description) {
        const desc = description.toLowerCase();
        
        if (desc.includes('signed by governor') || desc.includes('became law')) return { text: 'Enacted', class: 'enacted' };
        if (desc.includes('passed third reading') && desc.includes('transmitted')) return { text: 'Passed Chamber', class: 'passed' };
        if (desc.includes('passed third reading')) return { text: 'Passed', class: 'passed' };
        if (desc.includes('passed second reading')) return { text: 'Second Reading', class: 'progress' };
        if (desc.includes('passed first reading')) return { text: 'First Reading', class: 'progress' };
        if (desc.includes('carried over')) return { text: 'Carried Over', class: 'deferred' };
        if (desc.includes('deferred')) return { text: 'Deferred', class: 'deferred' };
        if (desc.includes('hearing')) return { text: 'Hearing', class: 'hearing' };
        if (desc.includes('referred to')) return { text: 'Referred', class: 'referred' };
        if (desc.includes('recommitted')) return { text: 'Recommitted', class: 'referred' };
        if (desc.includes('reported from')) return { text: 'Reported', class: 'progress' };
        if (desc.includes('introduced')) return { text: 'Introduced', class: 'new' };
        
        return { text: 'Update', class: 'update' };
    }

    /**
     * Generate tracker HTML
     */
    function generateTrackerHTML(trackerId, hbNumbers, sbNumbers, year) {
        year = year || CONFIG.defaultYear;
        
        // Generate hyperlinked bill numbers for HB
        const hbList = hbNumbers.length > 0 
            ? hbNumbers.map(num => `<a href="https://www.capitol.hawaii.gov/session/measure_indiv.aspx?billtype=HB&billnumber=${num}&year=${year}" target="_blank" onclick="event.stopPropagation()">${num}</a>`).join(', ')
            : '--';
        
        // Generate hyperlinked bill numbers for SB
        const sbList = sbNumbers.length > 0 
            ? sbNumbers.map(num => `<a href="https://www.capitol.hawaii.gov/session/measure_indiv.aspx?billtype=SB&billnumber=${num}&year=${year}" target="_blank" onclick="event.stopPropagation()">${num}</a>`).join(', ')
            : '--';
        
        return `
            <div class="tfc-bill-columns">
                <div class="tfc-bill-col ${hbNumbers.length > 0 ? 'active' : ''}" 
                     data-bill-type="hb" 
                     onclick="BillTrackerWidget.switchFeed('${trackerId}', 'hb')">
                    <h4>House Bill${hbNumbers.length > 1 ? 's' : ''}</h4>
                    <div class="tfc-bill-number">HB <span class="hb-numbers">${hbList}</span></div>
                </div>
                <div class="tfc-bill-col ${hbNumbers.length === 0 && sbNumbers.length > 0 ? 'active' : ''}" 
                     data-bill-type="sb" 
                     onclick="BillTrackerWidget.switchFeed('${trackerId}', 'sb')">
                    <h4>Senate Bill${sbNumbers.length > 1 ? 's' : ''}</h4>
                    <div class="tfc-bill-number">SB <span class="sb-numbers">${sbList}</span></div>
                </div>
            </div>

            <div class="tfc-status-section" id="${trackerId}-status">
                <div class="tfc-status-header" onclick="BillTrackerWidget.toggleHistory('${trackerId}')">
                    <span class="tfc-status-title">Latest Status <span class="tfc-status-badge" id="${trackerId}-badge">Loading...</span></span>
                    <span class="tfc-status-toggle">History</span>
                </div>
                <div class="tfc-latest-update" id="${trackerId}-latest">
                    <span class="tfc-loading">Loading bill status...</span>
                </div>
                <div class="tfc-status-history" id="${trackerId}-history"></div>
            </div>
            
            <div class="tfc-tracker-meta">
                <span class="tfc-last-updated" id="${trackerId}-updated"></span>
                <button class="tfc-refresh-btn" onclick="BillTrackerWidget.refresh('${trackerId}')" title="Refresh">
                    &#8635;
                </button>
            </div>
        `;
    }

    /**
     * Update tracker UI with feed data
     */
    function updateTrackerUI(trackerId, updates, billType) {
        const latestEl = document.getElementById(`${trackerId}-latest`);
        const badgeEl = document.getElementById(`${trackerId}-badge`);
        const historyEl = document.getElementById(`${trackerId}-history`);
        const updatedEl = document.getElementById(`${trackerId}-updated`);

        if (!latestEl) {
            console.warn(`[BillTracker] Element not found: ${trackerId}-latest`);
            return;
        }

        if (!updates || updates.length === 0) {
            latestEl.innerHTML = '<span style="color: #718096;">No status updates available</span>';
            if (badgeEl) badgeEl.textContent = 'N/A';
            return;
        }

        const latest = updates[0];
        const badge = getStatusBadge(latest.description);

        // Update latest status
        latestEl.innerHTML = `
            <span class="tfc-status-date">${latest.date}</span>
            ${latest.description}
        `;

        // Update badge
        if (badgeEl) {
            badgeEl.textContent = badge.text;
            badgeEl.className = `tfc-status-badge tfc-badge-${badge.class}`;
        }

        // Update history
        if (historyEl) {
            historyEl.innerHTML = '';
            
            for (let i = 1; i < updates.length; i++) {
                const update = updates[i];
                const div = document.createElement('div');
                div.className = 'tfc-history-item';
                div.innerHTML = `
                    <span class="tfc-status-date">${update.date}</span>
                    ${update.description}
                `;
                historyEl.appendChild(div);
            }
        }

        // Update timestamp
        if (updatedEl) {
            updatedEl.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
        }
    }

    /**
     * Tracker instance class
     */
    class Tracker {
        constructor(config) {
            this.id = config.trackerId;
            this.element = config.element;
            this.hbNumbers = config.hbNumbers || [];
            this.sbNumbers = config.sbNumbers || [];
            this.year = config.year || CONFIG.defaultYear;
            this.refreshInterval = config.refreshInterval || CONFIG.refreshInterval;
            this.currentType = this.hbNumbers.length > 0 ? 'hb' : 'sb';
            this.feeds = { hb: {}, sb: {} };
            this.intervalId = null;
        }

        async init() {
            // Generate HTML structure
            this.element.innerHTML = generateTrackerHTML(
                this.id, 
                this.hbNumbers, 
                this.sbNumbers,
                this.year
            );

            // Load initial data
            await this.loadFeeds();

            // Set up auto-refresh
            this.startAutoRefresh();

            console.log(`[BillTracker] Initialized tracker: ${this.id}`);
        }

        async loadFeeds() {
            // Load HB feeds
            for (const billNum of this.hbNumbers) {
                const xmlText = await fetchRSS('HB', billNum, this.year);
                this.feeds.hb[billNum] = parseRSS(xmlText);
            }

            // Load SB feeds
            for (const billNum of this.sbNumbers) {
                const xmlText = await fetchRSS('SB', billNum, this.year);
                this.feeds.sb[billNum] = parseRSS(xmlText);
            }

            // Update UI with current type
            this.updateDisplay();
        }

        updateDisplay() {
            const numbers = this.currentType === 'hb' ? this.hbNumbers : this.sbNumbers;
            
            if (numbers.length === 0) {
                updateTrackerUI(this.id, [], this.currentType);
                return;
            }

            // Combine all updates for this type and sort by date
            let allUpdates = [];
            for (const billNum of numbers) {
                const updates = this.feeds[this.currentType][billNum] || [];
                allUpdates = allUpdates.concat(updates);
            }

            // Sort combined updates by date
            allUpdates.sort((a, b) => b.rawDate - a.rawDate);

            updateTrackerUI(this.id, allUpdates, this.currentType);
        }

        switchFeed(billType) {
            this.currentType = billType;

            // Update active state in UI
            const cols = this.element.querySelectorAll('.tfc-bill-col');
            cols.forEach(col => {
                col.classList.remove('active');
                if (col.dataset.billType === billType) {
                    col.classList.add('active');
                }
            });

            this.updateDisplay();
        }

        toggleHistory() {
            const section = document.getElementById(`${this.id}-status`);
            if (section) {
                section.classList.toggle('expanded');
            }
        }

        async refresh() {
            console.log(`[BillTracker] Refreshing tracker: ${this.id}`);
            
            // Clear cache for this tracker's bills
            for (const billNum of this.hbNumbers) {
                const key = `${CONFIG.cachePrefix}HB_${billNum}_${this.year}`;
                localStorage.removeItem(key);
            }
            for (const billNum of this.sbNumbers) {
                const key = `${CONFIG.cachePrefix}SB_${billNum}_${this.year}`;
                localStorage.removeItem(key);
            }

            // Reload feeds
            await this.loadFeeds();
        }

        startAutoRefresh() {
            if (this.intervalId) {
                clearInterval(this.intervalId);
            }
            
            this.intervalId = setInterval(() => {
                console.log(`[BillTracker] Auto-refreshing tracker: ${this.id}`);
                this.refresh();
            }, this.refreshInterval);
        }

        stopAutoRefresh() {
            if (this.intervalId) {
                clearInterval(this.intervalId);
                this.intervalId = null;
            }
        }

        destroy() {
            this.stopAutoRefresh();
            delete trackers[this.id];
        }
    }

    /**
     * Public API
     */
    return {
        /**
         * Initialize a single tracker
         */
        init: function(config) {
            const tracker = new Tracker(config);
            trackers[config.trackerId] = tracker;
            tracker.init();
            return tracker;
        },

        /**
         * Initialize all trackers on the page
         * Looks for elements with data-tracker-id attribute
         */
        initAll: function() {
            const elements = document.querySelectorAll('[data-tracker-id]');
            
            elements.forEach(element => {
                const trackerId = element.dataset.trackerId;
                const hbNumbers = element.dataset.hb ? element.dataset.hb.split(',').map(n => n.trim()).filter(n => n) : [];
                const sbNumbers = element.dataset.sb ? element.dataset.sb.split(',').map(n => n.trim()).filter(n => n) : [];
                const year = element.dataset.year || CONFIG.defaultYear;

                this.init({
                    trackerId: trackerId,
                    element: element,
                    hbNumbers: hbNumbers,
                    sbNumbers: sbNumbers,
                    year: year
                });
            });

            console.log(`[BillTracker] Initialized ${elements.length} tracker(s)`);
        },

        /**
         * Switch feed type for a tracker
         */
        switchFeed: function(trackerId, billType) {
            const tracker = trackers[trackerId];
            if (tracker) {
                tracker.switchFeed(billType);
            }
        },

        /**
         * Toggle history for a tracker
         */
        toggleHistory: function(trackerId) {
            const tracker = trackers[trackerId];
            if (tracker) {
                tracker.toggleHistory();
            }
        },

        /**
         * Refresh a specific tracker
         */
        refresh: function(trackerId) {
            const tracker = trackers[trackerId];
            if (tracker) {
                tracker.refresh();
            }
        },

        /**
         * Reinitialize a tracker with new bill numbers from DOM attributes
         */
        reinit: function(trackerId) {
            const existingTracker = trackers[trackerId];
            if (existingTracker) {
                existingTracker.destroy();
            }

            const element = document.querySelector(`[data-tracker-id="${trackerId}"]`);
            if (!element) {
                console.warn(`[BillTracker] Element not found for tracker: ${trackerId}`);
                return;
            }

            const hbNumbers = element.dataset.hb ? element.dataset.hb.split(',').map(n => n.trim()).filter(n => n) : [];
            const sbNumbers = element.dataset.sb ? element.dataset.sb.split(',').map(n => n.trim()).filter(n => n) : [];
            const year = element.dataset.year || CONFIG.defaultYear;

            this.init({
                trackerId: trackerId,
                element: element,
                hbNumbers: hbNumbers,
                sbNumbers: sbNumbers,
                year: year
            });

            console.log(`[BillTracker] Reinitialized tracker: ${trackerId} with HB: ${hbNumbers.join(',')} SB: ${sbNumbers.join(',')}`);
        },

        /**
         * Refresh all trackers
         */
        refreshAll: function() {
            Object.values(trackers).forEach(tracker => tracker.refresh());
        },

        /**
         * Clear all cached data
         */
        clearCache: clearCache,

        /**
         * Get tracker instance
         */
        getTracker: function(trackerId) {
            return trackers[trackerId];
        },

        /**
         * Update configuration
         */
        configure: function(options) {
            Object.assign(CONFIG, options);
        },

        /**
         * Get current configuration
         */
        getConfig: function() {
            return { ...CONFIG };
        }
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => BillTrackerWidget.initAll());
} else {
    BillTrackerWidget.initAll();
}
