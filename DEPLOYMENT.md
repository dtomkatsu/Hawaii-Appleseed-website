# Vercel Deployment Instructions

## Quick Start (5 minutes)

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Deploy Your Project

```bash
cd /Users/dtomkatsu/CascadeProjects/TaxFairnessCoalitionWebsite
vercel
```

**Follow the prompts:**
- "Set up and deploy?" → **Yes**
- "Which scope?" → Choose your account
- "Link to existing project?" → **No**
- "What's your project's name?" → `tax-fairness-coalition` (or your choice)
- "In which directory is your code located?" → `.` (press Enter)

**That's it!** Vercel will deploy and give you a URL like:
```
https://tax-fairness-coalition.vercel.app
```

### Step 3: Update Your Frontend Code

Open `wealth_taxes_squarespace.html` and replace line 1330:

**Change from:**
```javascript
proxyUrl: 'https://YOUR-PROJECT-NAME.vercel.app/api/rss-proxy',
```

**Change to:**
```javascript
proxyUrl: 'https://tax-fairness-coalition.vercel.app/api/rss-proxy',
```
(Use your actual Vercel URL from Step 2)

### Step 4: Test It

Open your browser console and check for:
```
✓ HB1850 fetched successfully
✓ SB2468 fetched successfully
```

---

## Alternative: Deploy via Vercel Dashboard

### Step 1: Create Account
1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub (recommended) or email

### Step 2: Import Project
1. Click **"Add New Project"**
2. Choose **"Import Git Repository"** or **"Upload Files"**
3. If using Git: Connect your GitHub and select your repo
4. If uploading: Drag your project folder

### Step 3: Configure & Deploy
1. Project name: `tax-fairness-coalition`
2. Framework Preset: **Other** (leave as is)
3. Root Directory: `.` (default)
4. Click **"Deploy"**

### Step 4: Get Your URL
After deployment (~30 seconds), you'll see:
```
https://tax-fairness-coalition.vercel.app
```

Copy this URL and update line 1330 in `wealth_taxes_squarespace.html`

---

## Testing Your Serverless Function

### Test the API directly:
```bash
# Test HB1850
curl "https://YOUR-URL.vercel.app/api/rss-proxy?bill=HB1850&year=2026"

# Test SB349
curl "https://YOUR-URL.vercel.app/api/rss-proxy?bill=SB349&year=2026"
```

You should see XML RSS feed data returned.

---

## Troubleshooting

### Issue: "Function not found"
**Solution:** Make sure the `api/` folder is in your project root

### Issue: "CORS error"
**Solution:** The function already has CORS headers. Clear your browser cache.

### Issue: "Timeout"
**Solution:** The function has a 10-second timeout. This is plenty for Hawaii Legislature RSS feeds.

### Issue: "Still getting errors"
**Solution:** Check browser console for the actual error. The function logs detailed errors.

---

## Monitoring & Logs

### View Function Logs:
1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click your project
3. Go to **"Functions"** tab
4. Click on `api/rss-proxy.js`
5. View real-time logs

### Check Performance:
- **Cache hit rate:** Should be high after initial loads
- **Response time:** ~50ms for cached, ~500ms for fresh fetches
- **Error rate:** Should be near 0%

---

## Free Tier Limits

You're well within the free tier:
- **100GB bandwidth/month** (~1 million requests)
- **100GB-hours compute time**
- **Unlimited projects**

Your expected usage: ~1,000 requests/month = **0.1% of free tier**

---

## Next Steps

1. Deploy to Vercel (5 minutes)
2. Update the `proxyUrl` in your HTML file
3. Test the bill tracker
4. Enjoy 99.9% uptime! 🎉

---

## Need Help?

- Vercel Docs: https://vercel.com/docs
- Vercel Support: https://vercel.com/support
- This project's function: `/api/rss-proxy.js`
