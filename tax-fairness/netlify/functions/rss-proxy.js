// Netlify Serverless Function for RSS Proxy
// Fetches Hawaii Legislature RSS feeds without CORS issues

exports.handler = async (event) => {
    // Enable CORS for all origins
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/xml; charset=utf-8'
    };
    
    // Handle preflight requests
    if (event.httpMethod === 'OPTIONS') {
        return {
            statusCode: 200,
            headers,
            body: ''
        };
    }
    
    const { bill, year = '2026' } = event.queryStringParameters;
    
    // Validate bill parameter
    if (!bill) {
        return {
            statusCode: 400,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                error: 'Bill parameter required',
                usage: 'Example: /.netlify/functions/rss-proxy?bill=HB1850&year=2026'
            })
        };
    }
    
    // Extract bill type and number (e.g., "HB1850" -> "HB" + "1850")
    const match = bill.match(/^([A-Z]+)(\d+)$/i);
    if (!match) {
        return {
            statusCode: 400,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                error: 'Invalid bill format',
                expected: 'Format should be like HB1850 or SB349'
            })
        };
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
            return {
                statusCode: response.status,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    error: `Failed to fetch RSS from Hawaii Legislature`,
                    status: response.status,
                    bill: `${billType}${billNumber}`,
                    url: rssUrl
                })
            };
        }
        
        const xmlText = await response.text();
        
        // Validate that we got actual RSS XML
        if (!xmlText.includes('<rss') && !xmlText.includes('<item>')) {
            console.error('Invalid RSS response received');
            return {
                statusCode: 500,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    error: 'Invalid RSS response from legislature website'
                })
            };
        }
        
        console.log(`✓ Successfully fetched ${billType}${billNumber}`);
        
        // Cache for 10 minutes (600 seconds)
        // stale-while-revalidate allows serving stale content while fetching fresh data
        headers['Cache-Control'] = 's-maxage=600, stale-while-revalidate=1800';
        
        return {
            statusCode: 200,
            headers,
            body: xmlText
        };
        
    } catch (error) {
        console.error(`Error fetching RSS for ${billType}${billNumber}:`, error.message);
        return {
            statusCode: 500,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                error: 'Failed to fetch RSS feed',
                details: error.message,
                bill: `${billType}${billNumber}`
            })
        };
    }
};
