# Monthly Sales Analysis

A sales dashboard that runs entirely in the browser (HTML, CSS, JavaScript and Chart.js). No server or install needed.

**Submitted by:** Saiprasad Lawangare | Roll No. 19079 | TYBSc IT | SIWS College | 2026-2027

## How it works
1. **Create account / Sign in** with a company name, username and password.
2. **Add sales lines** (date, product, quantity, unit price). Revenue is quantity x unit price.
3. **Show dashboard**: total revenue, orders, units sold, average order value, monthly revenue chart, month-on-month change, top products and searchable sales history.

Accounts and sales data are saved in the browser's local storage on the device where they were created. Passwords are hashed with PBKDF2, but because there is no server this is a demonstration login, not production security.

## Run locally
Open `index.html` in a browser (internet needed for Chart.js and fonts).

## Publish a public link with GitHub Pages
1. Create a new GitHub repository and upload these files (`index.html`, `style.css`, `script.js`, `README.md`).
2. Repository **Settings > Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, branch `main`, folder `/ (root)`, then **Save**.
4. After a minute the site is live at `https://<your-username>.github.io/<repository-name>/`.

## Files
| File | Purpose |
|---|---|
| `index.html` | Page structure: sign-in, sales entry and dashboard screens |
| `style.css` | Styling, light and dark themes |
| `script.js` | Account storage, validation, analytics and charts |
