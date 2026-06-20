# Hanumaan Luxury Ladies PG — Production Web Application

**Domain:** hanumaanpg.in  
**Business:** No:10, Gangai Street, Bharathi Nagar, Tharamani, Chennai – 600113  
**Phone/WhatsApp:** +91 70921 89999  
**Email:** hanumaanluxuryladiespg@gmail.com

---

## Tech Stack
- **Backend:** FastAPI (Python)
- **Database:** SQLite (production: swap to PostgreSQL)
- **Templates:** Jinja2
- **Auth:** PBKDF2-HMAC password hashing + JWT tokens + HttpOnly cookies

---

## Quick Start (Local Development)

```bash
# 1. Install Python 3.11+
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 4. Open browser → http://localhost:8000
# 5. Admin panel → http://localhost:8000/admin/login
```

---

## Admin Portal

**URL:** `https://hanumaanpg.in/admin/login`

**Default Credentials:**
- Username: `MaheshBeeram`
- Password: `Hanumaan@2025`

⚠️ **IMPORTANT: Change the password immediately after first login!**
Go to: Admin → Settings → Change Password

---

## Admin Features

| Feature | Description |
|---------|-------------|
| Dashboard | Today/weekly/monthly enquiry stats |
| Enquiry Management | View, search, filter, update status, export CSV |
| Gallery Management | Upload/delete images, mark featured |
| Reports | Charts for daily trends, status breakdown |
| Settings | Change password, account info |
| Audit Logs | All admin actions are logged |

### Enquiry Lead Statuses
New Lead → Contacted → Visit Scheduled → Interested → Booked → Rejected

---

## Production Deployment (VPS / Ubuntu)

```bash
# 1. Upload all files to your server
# 2. Install Python & pip
sudo apt update && sudo apt install python3-pip python3-venv -y

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run with gunicorn (production)
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 5. Set up Nginx reverse proxy
# 6. Get SSL certificate with Certbot
```

### Nginx Config
```nginx
server {
    listen 80;
    server_name hanumaanpg.in www.hanumaanpg.in;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /static {
        alias /var/www/hanumaan_pg/static;
        expires 30d;
    }
}
```

### Systemd Service
```ini
[Unit]
Description=Hanumaan PG Web App
After=network.target

[Service]
WorkingDirectory=/var/www/hanumaan_pg
ExecStart=/var/www/hanumaan_pg/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

---

## Vercel Deployment (Serverless)

1. Install Vercel CLI: `npm i -g vercel`
2. Create `vercel.json` (included)
3. Run: `vercel deploy`

---

## Environment Variables (Production)

```bash
SECRET_KEY=your-very-long-random-secret-key-here
ADMIN_PASSWORD_HASH=  # Will be auto-generated on first run
```

---

## Security Features Implemented
- ✅ PBKDF2-HMAC-SHA256 password hashing (390,000 iterations)
- ✅ JWT tokens with HMAC-SHA256 signing
- ✅ HttpOnly secure cookies
- ✅ Rate limiting on login (5 attempts / 5 min) and enquiry form
- ✅ Math CAPTCHA on admin login
- ✅ Input validation & sanitization
- ✅ SQL injection prevention (parameterized queries)
- ✅ Admin audit logging
- ✅ CSRF protection via SameSite cookie
- ✅ XSS protection via Jinja2 auto-escaping
- ✅ robots.txt blocks admin from indexing

---

## Database Schema

```sql
-- enquiries table
CREATE TABLE enquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, phone TEXT NOT NULL,
    email TEXT, occupation TEXT, company_college TEXT,
    move_in_date TEXT, enquiry_type TEXT, message TEXT,
    status TEXT DEFAULT 'New Lead',
    created_at TEXT NOT NULL, ip_address TEXT
);

-- gallery table  
CREATE TABLE gallery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL, title TEXT,
    category TEXT, sort_order INTEGER,
    is_featured INTEGER DEFAULT 0,
    uploaded_at TEXT NOT NULL
);

-- admin_users table
CREATE TABLE admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL, email TEXT,
    password_hash TEXT NOT NULL,
    last_login TEXT, created_at TEXT
);

-- audit_logs table
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT, action TEXT, details TEXT,
    ip_address TEXT, created_at TEXT
);
```

---

## Backup Strategy
```bash
# Daily SQLite backup (add to cron)
cp hanumaan.db backups/hanumaan_$(date +%Y%m%d).db

# Cron job (daily at 2 AM)
0 2 * * * cp /var/www/hanumaan_pg/hanumaan.db /backups/hanumaan_$(date +\%Y\%m\%d).db
```

---

## Support
📞 +91 70921 89999  
✉ hanumaanluxuryladiespg@gmail.com  
🌐 hanumaanpg.in
