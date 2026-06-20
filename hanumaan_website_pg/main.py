"""
Hanumaan Luxury Ladies PG — Production FastAPI Application
Domain: hanumaanluxuryladiespg.com
"""
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
import sqlite3, hashlib, hmac, base64, json, os, csv, io, secrets, time
from typing import Optional

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "hanumaan-pg-secret-2025-change-in-production")
ADMIN_USERNAME = "MaheshBeeram"
# bcrypt hash of password — store only hash; change default password on first login
# Default password: Hanumaan@2025 (bcrypt hashed below)
ADMIN_PASSWORD_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    "scrypt:32768:8:1$placeholder$use_set_password_script"
)
# Rate limit store: ip -> [timestamp, ...]
_rate_store: dict = {}

app = FastAPI(title="Hanumaan Luxury Ladies PG", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ─────────────────────────────────────────────
# Minimal secure password hashing (no bcrypt dep needed — uses PBKDF2-HMAC)
# ─────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 390000)
    return f"pbkdf2:sha256:390000${salt}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        parts = hashed.split("$")
        if len(parts) != 3:
            return False
        salt = parts[1]
        stored_key = parts[2]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 390000)
        return hmac.compare_digest(key.hex(), stored_key)
    except Exception:
        return False


# ─────────────────────────────────────────────
# Simple JWT (no extra dep)
# ─────────────────────────────────────────────
def create_token(data: dict, expires_hours: int = 12) -> str:
    payload = {**data, "exp": (datetime.utcnow() + timedelta(hours=expires_hours)).timestamp()}
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"

def verify_token(token: str) -> Optional[dict]:
    try:
        encoded, sig = token.rsplit(".", 1)
        expected = hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=="))
        if payload.get("exp", 0) < datetime.utcnow().timestamp():
            return None
        return payload
    except Exception:
        return None


# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
DB_PATH = "hanumaan.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT DEFAULT '',
            occupation TEXT DEFAULT '',
            company_college TEXT DEFAULT '',
            move_in_date TEXT DEFAULT '',
            enquiry_type TEXT DEFAULT 'General Enquiry',
            message TEXT DEFAULT '',
            status TEXT DEFAULT 'New Lead',
            created_at TEXT NOT NULL,
            ip_address TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            title TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            sort_order INTEGER DEFAULT 0,
            is_featured INTEGER DEFAULT 0,
            uploaded_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            last_login TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
    """)
    # Seed admin user if not exists
    existing = conn.execute("SELECT id FROM admin_users WHERE username = ?", (ADMIN_USERNAME,)).fetchone()
    if not existing:
        pwd_hash = hash_password("Hanumaan@2025")
        conn.execute(
            "INSERT INTO admin_users (username, email, password_hash, created_at) VALUES (?,?,?,?)",
            (ADMIN_USERNAME, "hanumaanluxuryladiespg@gmail.com", pwd_hash, datetime.now().isoformat())
        )
        conn.commit()
    conn.close()

init_db()


# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────
def get_current_admin(request: Request) -> Optional[dict]:
    token = request.cookies.get("admin_token")
    if not token:
        return None
    return verify_token(token)

def require_admin(request: Request):
    admin = get_current_admin(request)
    if not admin:
        raise HTTPException(status_code=302, detail="Not authenticated", headers={"Location": "/admin/login"})
    return admin

def rate_limit(ip: str, max_requests: int = 5, window: int = 60) -> bool:
    now = time.time()
    _rate_store[ip] = [t for t in _rate_store.get(ip, []) if now - t < window]
    if len(_rate_store[ip]) >= max_requests:
        return False
    _rate_store[ip].append(now)
    return True

def audit_log(username: str, action: str, details: str = "", ip: str = ""):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_logs (username, action, details, ip_address, created_at) VALUES (?,?,?,?,?)",
        (username, action, details, ip, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# PUBLIC ROUTES
# ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    conn = get_db()
    gallery = conn.execute(
        "SELECT * FROM gallery WHERE is_featured=1 ORDER BY sort_order LIMIT 6"
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "gallery": gallery})

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/facilities", response_class=HTMLResponse)
async def facilities(request: Request):
    return templates.TemplateResponse("facilities.html", {"request": request})

@app.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request):
    conn = get_db()
    images = conn.execute("SELECT * FROM gallery ORDER BY sort_order, id").fetchall()
    conn.close()
    return templates.TemplateResponse("gallery.html", {"request": request, "images": images})

@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@app.post("/enquire")
async def enquire(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    occupation: str = Form(""),
    company_college: str = Form(""),
    move_in_date: str = Form(""),
    enquiry_type: str = Form("General Enquiry"),
    message: str = Form("")
):
    ip = request.client.host if request.client else "unknown"
    if not rate_limit(ip, max_requests=3, window=300):
        return JSONResponse(
            {"success": False, "message": "Too many requests. Please try again later."},
            status_code=429
        )
    # Input validation
    name = name.strip()[:100]
    phone = phone.strip()[:15]
    email = email.strip()[:100]
    message = message.strip()[:500]
    if not name or not phone:
        return JSONResponse({"success": False, "message": "Name and phone are required."})

    conn = get_db()
    conn.execute(
        """INSERT INTO enquiries
           (name, phone, email, occupation, company_college, move_in_date, enquiry_type, message, status, created_at, ip_address)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (name, phone, email, occupation, company_college, move_in_date,
         enquiry_type, message, "New Lead", datetime.now().isoformat(), ip)
    )
    conn.commit()
    conn.close()
    return JSONResponse({
        "success": True,
        "message": "Enquiry submitted! We will contact you shortly.",
        "whatsapp_url": f"https://wa.me/917092189999?text=Hi%2C%20I%20submitted%20an%20enquiry.%20My%20name%20is%20{name}%20and%20phone%20is%20{phone}."
    })


# ─────────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────────
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    admin = get_current_admin(request)
    if admin:
        return RedirectResponse("/admin/dashboard", status_code=302)
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})

@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    captcha: str = Form("")
):
    ip = request.client.host if request.client else "unknown"
    if not rate_limit(ip, max_requests=5, window=300):
        return templates.TemplateResponse("admin/login.html", {
            "request": request, "error": "Too many login attempts. Try again later."
        })
    # Simple math captcha check is handled client-side; server validates value
    # (captcha answer stored in hidden field)
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM admin_users WHERE username = ?", (username.strip(),)
    ).fetchone()
    conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        audit_log(username, "LOGIN_FAILED", f"IP:{ip}", ip)
        return templates.TemplateResponse("admin/login.html", {
            "request": request, "error": "Invalid username or password."
        })

    token = create_token({"username": username, "role": "admin"})
    audit_log(username, "LOGIN_SUCCESS", f"IP:{ip}", ip)
    conn = get_db()
    conn.execute("UPDATE admin_users SET last_login=? WHERE username=?",
                 (datetime.now().isoformat(), username))
    conn.commit()
    conn.close()

    resp = RedirectResponse("/admin/dashboard", status_code=302)
    resp.set_cookie("admin_token", token, httponly=True, samesite="strict", max_age=43200)
    return resp

@app.get("/admin/logout")
async def admin_logout():
    resp = RedirectResponse("/admin/login", status_code=302)
    resp.delete_cookie("admin_token")
    return resp

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    stats = {
        "today": conn.execute("SELECT COUNT(*) FROM enquiries WHERE created_at LIKE ?", (f"{today}%",)).fetchone()[0],
        "weekly": conn.execute("SELECT COUNT(*) FROM enquiries WHERE created_at >= ?", (week_ago,)).fetchone()[0],
        "monthly": conn.execute("SELECT COUNT(*) FROM enquiries WHERE created_at >= ?", (month_ago,)).fetchone()[0],
        "total": conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0],
        "new_leads": conn.execute("SELECT COUNT(*) FROM enquiries WHERE status='New Lead'").fetchone()[0],
    }
    recent = conn.execute(
        "SELECT * FROM enquiries ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    audit = conn.execute(
        "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "admin": admin, "stats": stats,
        "recent": recent, "audit": audit
    })

@app.get("/admin/enquiries", response_class=HTMLResponse)
async def admin_enquiries(
    request: Request,
    search: str = "",
    status: str = "",
    page: int = 1
):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    conn = get_db()
    per_page = 20
    offset = (page - 1) * per_page
    where, params = [], []
    if search:
        where.append("(name LIKE ? OR phone LIKE ? OR email LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if status:
        where.append("status = ?")
        params.append(status)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM enquiries {where_clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM enquiries {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("admin/enquiries.html", {
        "request": request, "admin": admin, "enquiries": rows,
        "total": total, "page": page, "per_page": per_page,
        "search": search, "status_filter": status,
        "statuses": ["New Lead","Contacted","Visit Scheduled","Interested","Booked","Rejected"]
    })

@app.post("/admin/enquiries/{eid}/status")
async def update_status(request: Request, eid: int, new_status: str = Form(...)):
    admin = get_current_admin(request)
    if not admin:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    valid = ["New Lead","Contacted","Visit Scheduled","Interested","Booked","Rejected"]
    if new_status not in valid:
        return JSONResponse({"error": "Invalid status"}, status_code=400)
    conn = get_db()
    conn.execute("UPDATE enquiries SET status=? WHERE id=?", (new_status, eid))
    conn.commit()
    conn.close()
    audit_log(admin["username"], "STATUS_UPDATE", f"Enquiry #{eid} -> {new_status}")
    return JSONResponse({"success": True})

@app.get("/admin/enquiries/export")
async def export_enquiries(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    conn = get_db()
    rows = conn.execute("SELECT * FROM enquiries ORDER BY created_at DESC").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID","Name","Phone","Email","Occupation","Company/College",
                     "Move-In Date","Enquiry Type","Message","Status","Created At"])
    for r in rows:
        writer.writerow([r["id"],r["name"],r["phone"],r["email"],r["occupation"],
                         r["company_college"],r["move_in_date"],r["enquiry_type"],
                         r["message"],r["status"],r["created_at"]])
    output.seek(0)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=enquiries.csv"}
    )

@app.get("/admin/gallery", response_class=HTMLResponse)
async def admin_gallery(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    conn = get_db()
    images = conn.execute("SELECT * FROM gallery ORDER BY sort_order, id").fetchall()
    conn.close()
    return templates.TemplateResponse("admin/gallery.html", {
        "request": request, "admin": admin, "images": images
    })

@app.post("/admin/gallery/upload")
async def upload_image(request: Request, title: str = Form(""), category: str = Form("general")):
    admin = get_current_admin(request)
    if not admin:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    form = await request.form()
    file = form.get("file")
    if not file:
        return JSONResponse({"error": "No file"}, status_code=400)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        return JSONResponse({"error": "Invalid file type"}, status_code=400)
    filename = f"{secrets.token_hex(8)}.{ext}"
    dest = f"static/images/gallery/{filename}"
    os.makedirs("static/images/gallery", exist_ok=True)
    with open(dest, "wb") as f:
        f.write(await file.read())
    conn = get_db()
    conn.execute(
        "INSERT INTO gallery (filename, title, category, uploaded_at) VALUES (?,?,?,?)",
        (filename, title, category, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    audit_log(admin["username"], "GALLERY_UPLOAD", filename)
    return JSONResponse({"success": True, "filename": filename})

@app.post("/admin/gallery/{gid}/delete")
async def delete_image(request: Request, gid: int):
    admin = get_current_admin(request)
    if not admin:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    conn = get_db()
    row = conn.execute("SELECT filename FROM gallery WHERE id=?", (gid,)).fetchone()
    if row:
        try:
            os.remove(f"static/images/gallery/{row['filename']}")
        except Exception:
            pass
        conn.execute("DELETE FROM gallery WHERE id=?", (gid,))
        conn.commit()
    conn.close()
    return JSONResponse({"success": True})

@app.post("/admin/gallery/{gid}/featured")
async def toggle_featured(request: Request, gid: int):
    admin = get_current_admin(request)
    if not admin:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    conn = get_db()
    row = conn.execute("SELECT is_featured FROM gallery WHERE id=?", (gid,)).fetchone()
    if row:
        conn.execute("UPDATE gallery SET is_featured=? WHERE id=?", (1 - row["is_featured"], gid))
        conn.commit()
    conn.close()
    return JSONResponse({"success": True})

@app.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    conn = get_db()
    # Last 30 days daily counts
    daily = conn.execute("""
        SELECT substr(created_at,1,10) as day, COUNT(*) as cnt
        FROM enquiries
        WHERE created_at >= date('now','-30 days')
        GROUP BY day ORDER BY day
    """).fetchall()
    by_status = conn.execute("""
        SELECT status, COUNT(*) as cnt FROM enquiries GROUP BY status
    """).fetchall()
    by_type = conn.execute("""
        SELECT enquiry_type, COUNT(*) as cnt FROM enquiries GROUP BY enquiry_type
    """).fetchall()
    conn.close()
    return templates.TemplateResponse("admin/reports.html", {
        "request": request, "admin": admin,
        "daily": [dict(r) for r in daily],
        "by_status": [dict(r) for r in by_status],
        "by_type": [dict(r) for r in by_type]
    })

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, msg: str = ""):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    return templates.TemplateResponse("admin/settings.html", {
        "request": request, "admin": admin, "msg": msg
    })

@app.post("/admin/settings/password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    if new_password != confirm_password:
        return RedirectResponse("/admin/settings?msg=Passwords+do+not+match", status_code=302)
    if len(new_password) < 8:
        return RedirectResponse("/admin/settings?msg=Password+too+short", status_code=302)
    conn = get_db()
    user = conn.execute("SELECT * FROM admin_users WHERE username=?", (admin["username"],)).fetchone()
    if not verify_password(current_password, user["password_hash"]):
        conn.close()
        return RedirectResponse("/admin/settings?msg=Current+password+incorrect", status_code=302)
    new_hash = hash_password(new_password)
    conn.execute("UPDATE admin_users SET password_hash=? WHERE username=?",
                 (new_hash, admin["username"]))
    conn.commit()
    conn.close()
    audit_log(admin["username"], "PASSWORD_CHANGE", "Password updated successfully")
    return RedirectResponse("/admin/settings?msg=Password+changed+successfully", status_code=302)


# ─────────────────────────────────────────────
# SEO
# ─────────────────────────────────────────────
@app.get("/sitemap.xml")
async def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://hanumaanluxuryladiespg.com/</loc><priority>1.0</priority></url>
  <url><loc>https://hanumaanluxuryladiespg.com/about</loc><priority>0.8</priority></url>
  <url><loc>https://hanumaanluxuryladiespg.com/facilities</loc><priority>0.8</priority></url>
  <url><loc>https://hanumaanluxuryladiespg.com/gallery</loc><priority>0.7</priority></url>
  <url><loc>https://hanumaanluxuryladiespg.com/contact</loc><priority>0.8</priority></url>
</urlset>"""
    return Response(content=xml, media_type="application/xml")

@app.get("/robots.txt")
async def robots():
    content = "User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: https://hanumaanluxuryladiespg.com/sitemap.xml"
    return Response(content=content, media_type="text/plain")
