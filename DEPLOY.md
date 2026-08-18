# Skyeman — push to GitHub + deploy on Render

A short checklist for getting this project live.

---

## 1. Push to GitHub

```bash
# one-time: create the repo on github.com first, then:
cd /Users/macbook/Desktop/skyeman/skyeman
git init                                   # only if this isn't a repo yet
git add .
git commit -m "Initial commit: Skyeman Inc."
git branch -M main
git remote add origin git@github.com:<your-username>/<your-repo>.git
git push -u origin main
```

Make sure `.env` and `db.sqlite3` are in `.gitignore` (they already are in this project).

---

## 2. Deploy on Render (free tier)

1. Go to <https://dashboard.render.com/> → **New +** → **Blueprint**.
2. Connect your GitHub repo. Render will read `render.yaml` (already included).
3. The blueprint creates:
   - a **Postgres** database (free)
   - a **Web Service** running `gunicorn skyeman_project.wsgi`
4. Set environment variables (Render injects `DATABASE_URL` automatically from the linked DB). You also need to set:
   - `SECRET_KEY` — generate one with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
   - `DEBUG` — set to `False` for production
   - `ALLOWED_HOSTS` — e.g. `skyeman.onrender.com` (no protocol, comma-separated for multiple)
5. Render runs migrations automatically on each deploy via the `build.sh` script.

If you don't want to use the Blueprint, do it manually:

- **Web Service** → Environment: Python 3 → Build: `./build.sh` → Start: `gunicorn skyeman_project.wsgi`
- **Postgres** → copy its internal `DATABASE_URL` into the web service's env.

---

## 3. First-time setup after deploy

```bash
# SSH into the Render shell (or use the one-off "Run command" feature)
python manage.py createsuperuser     # create your admin user
python manage.py seed --reset         # populate demo data
```

Visit:
- Customer site: `https://skyeman.onrender.com/`
- Admin: `https://skyeman.onrender.com/admin/`

---

## Local development reminder

```bash
cd /Users/macbook/Desktop/skyeman/skyeman
source venv/bin/activate
python manage.py runserver
```

The dev server runs at <http://127.0.0.1:8000/>.

---

## Notes

- All payments are **simulated**. No card data is collected or stored.
- The Django admin is at `/admin/`. Default seed creates `admin / admin12345` and `demo / demo12345`.
- The Django 5.0 + Python 3.14 patch in `venv/lib/python3.14/site-packages/django/template/context.py` is needed locally; production runs on Python 3.13 in `render.yaml` so no patch is required there.
