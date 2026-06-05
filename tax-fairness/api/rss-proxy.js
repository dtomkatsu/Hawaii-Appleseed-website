// Vercel Serverless Function for RSS Proxy
// Fetches Hawaii Legislature RSS feeds without CORS issues

export default async function handler(req, res) {
    // Enable CORS for all origins
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    // Handle preflight requests
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    const { bill, year = '2026' } = req.query;
    
    // Validate bill parameter
    if (!bill) {
        return res.status(400).json({ 
            error: 'Bill parameter required',
            usage: 'Example: /api/rss-proxy?bill=HB1850&year=2026'
        });
    }
    
    // Extract bill type and number (e.g., "HB1850" -> "HB" + "1850")
    const match = bill.match(/^([A-Z]+)(\d+)$/i);
    if (!match) {
        return res.status(400).json({ 
            error: 'Invalid bill format',
            expected: 'Format should be like HB1850 or SB349'
        });
    }
    
    const [, billType, billNumber] = match;
    const rssUrl = `https://www.capitol.hawaii.gov/sessions/session${year}/rss/${billType.toUpperCase()}${billNumber}.xml`;
    
    console.log(`Fetching RSS for ${billType}${billNumber} (${year})`);
    
    try {
        const response = await fetch(rssUrl, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (compatible; TaxFairnessCoalition/1.0)'
            }
        });
        
        if (!response.ok) {
            console.error(`RSS fetch failed: ${response.status} ${response.statusText}`);
            return res.status(response.status).json({ 
                error: `Failed to fetch RSS from Hawaii Legislature`,
                status: response.status,
                bill: `${billType}${billNumber}`,
                url: rssUrl
            });
        }
        
        const xmlText = await response.text();
        
        // Validate that we got actual RSS XML
        if (!xmlText.includes('<rss') && !xmlText.includes('<item>')) {
            console.error('Invalid RSS response received');
            return res.status(500).json({ 
                error: 'Invalid RSS response from legislature website'
            });
        }
        
        console.log(`✓ Successfully fetched ${billType}${billNumber}`);
        
        // Cache for 10 minutes (600 seconds)
        // stale-while-revalidate allows serving stale content while fetching fresh data
        res.setHeader('Cache-Control', 's-maxage=600, stale-while-revalidate=1800');
        res.setHeader('Content-Type', 'application/xml; charset=utf-8');
        
        return res.status(200).send(xmlText);
        
    } catch (error) {
        console.error(`Error fetching RSS for ${billType}${billNumber}:`, error);
        return res.status(500).json({ 
            error: 'Failed to fetch RSS feed',
            details: error.message,
            bill: `${billType}${billNumber}`
        });
    }
}
