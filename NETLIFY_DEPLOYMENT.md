# Netlify Deployment Instructions

## Quick Start (2 minutes)

### Step 1: Go to Netlify

1. Open [netlify.com](https://netlify.com)
2. Click **"Sign up"** (top right)
3. Sign up with GitHub (recommended) or email

### Step 2: Deploy Your Project

**Option A: Drag & Drop (Easiest)**
1. Click **"Drag and drop your site output here"**
2. **Drag your entire project folder** into the drop area
3. Wait for upload and deployment (~30 seconds)

**Option B: Connect to GitHub**
1. Click **"New site from Git"**
2. Connect your GitHub account
3. Select your `TaxFairnessCoalitionWebsite` repo
4. Click **"Deploy site"**

### Step 3: Get Your URL

After deployment, you'll get a URL like:
```
https://amazing-tesla-123456.netlify.app
```

**Copy this URL** - you need it for the next step.

### Step 4: Update Your Frontend Code

Open `wealth_taxes_squarespace.html` and replace line 1330:

**Change from:**
```javascript
proxyUrl: 'https://YOUR-PROJECT-NAME.netlify.app/.netlify/functions/rss-proxy',
```

**Change to:**
```javascript
proxyUrl: 'https://amazing-tesla-123456.netlify.app/.netlify/functions/rss-proxy',
```
(Use your actual Netlify URL from Step 3)

### Step 5: Test It

**Test the API directly:**
```
https://your-site.netlify.app/.netlify/functions/rss-proxy?bill=HB1850&year=2026
```

You should see XML RSS feed data returned.

**Test your bill tracker:**
1. Open your `wealth_taxes_squarespace.html` page
2. Open browser console (F12 → Console)
3. Look for:
   ```
   ✓ HB1850 fetched successfully
   ✓ SB2468 fetched successfully
   ```

---

## What I Created for Netlify

### 1. Netlify Function
`netlify/functions/rss-proxy.js`
- Same RSS proxy logic as Vercel version
- Uses Netlify's `exports.handler` format
- 10-minute caching
- Full CORS support

### 2. Netlify Configuration
`netlify.toml`
- Configures function directory
- Sets memory and timeout limits
- Adds optional `/api/rss-proxy` redirect
- Security headers

### 3. Updated Frontend
`wealth_taxes_squarespace.html:1330`
- Updated to use Netlify endpoint
- Ready for your actual Netlify URL

---

## Testing Your Netlify Function

### Test URLs:
```bash
# Test HB1850
curl "https://your-site.netlify.app/.netlify/functions/rss-proxy?bill=HB1850&year=2026"

# Test SB349
curl "https://your-site.netlify.app/.netlify/functions/rss-proxy?bill=SB349&year=2026"

# Test with shorter URL (via redirect)
curl "https://your-site.netlify.app/api/rss-proxy?bill=HB1850&year=2026"
```

### Expected Response:
XML RSS feed data (not JSON error).

---

## Monitoring & Logs

### View Function Logs:
1. Go to [app.netlify.com](https://app.netlify.com)
2. Click your site
3. Go to **"Functions"** tab
4. Click on `rss-proxy`
5. View real-time logs and performance

### Check Performance:
- **Response time:** ~50ms for cached, ~500ms for fresh
- **Memory usage:** Should be < 100MB
- **Execution time:** Should be < 3 seconds

---

## Free Tier Limits

You're well within the free tier:
- **125,000 function calls/month** (~1,000 needed)
- **100GB bandwidth/month** (~1GB needed)
- **Unlimited sites**
- **Custom domains** (optional)

**Your usage: ~1% of free tier**

---

## Troubleshooting

### Issue: "Function not found"
**Solution:** Make sure `netlify/functions/rss-proxy.js` exists in your project

### Issue: "404 Not Found"
**Solution:** Check the function logs for deployment errors

### Issue: "500 Internal Error"
**Solution:** Check function logs for runtime errors

### Issue: "CORS error"
**Solution:** The function has CORS headers. Clear browser cache.

### Issue: "Still getting errors"
**Solution:** Check browser console for the exact error message

---

## Advantages of Netlify

✅ **Easier deployment** (drag & drop)
✅ **Better free tier** (125k vs 100k calls)
✅ **Excellent documentation**
✅ **Built-in form handling**
✅ **Automatic HTTPS**
✅ **Instant rollbacks**
✅ **Preview deployments**

---

## Next Steps

1. Deploy to Netlify (2 minutes)
2. Update the `proxyUrl` in your HTML file
3. Test the bill tracker
4. Enjoy reliable RSS feeds! 🎉

---

## Need Help?

- Netlify Docs: https://docs.netlify.com
- Netlify Support: https://www.netlify.com/support
- This project's function: `netlify/functions/rss-proxy.js`
