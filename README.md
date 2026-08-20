# Eventify — Organizer Portal (Sprint 1–3)

Django + MySQL backend for organizers to log in, manage their own events
(including poster images), and track ticket sales.

## What's implemented

**Sprint 1 — auth & event creation**
- Organizer login (`events:login`) using Django's built-in auth system.
- Every organizer-area view requires login (`LoginRequiredMixin`).
- `EventForm` (ModelForm) validates title, date (no past dates), ticket
  price (>= 0), max tickets (>= 1).
- Events belong to an organizer (`Event.organizer` FK to `User`).

**Sprint 2 — image upload, edit/delete, ownership**
- `poster_image` upload validated for content type (jpeg/png/webp) and
  size (5MB max) in `EventForm.clean_poster_image`.
- Editing an event lets you replace the poster; the old file is deleted
  from storage when replaced.
- Deleting an event removes the DB row **and** the poster file
  (`Event.delete()` override).
- `EventListView` only ever queries `Event.objects.filter(organizer=request.user)`.
- `OwnerRequiredMixin` (used by edit/delete) checks `event.organizer_id
  == request.user.id` and redirects with an error message if another
  organizer tries to touch it — it does not filter the queryset itself,
  so a mismatch produces a friendly redirect rather than a raw 404.

**Sprint 3 — dashboard**
- `bookings` app holds a minimal `Booking` model (event, customer,
  quantity) so sales can be aggregated.
- `Event.tickets_sold`, `tickets_remaining`, `revenue` are computed
  properties; `DashboardView` aggregates per-event and totals across
  all of the organizer's events.

## Project layout

```
eventify/
├── eventify/          # project settings, urls, wsgi/asgi
├── events/            # Event model, form, views, templates
├── bookings/          # Booking model (feeds the dashboard)
├── templates/base.html
├── requirements.txt
├── .env.example
└── azure-pipelines.yml
```

## Local setup

1. **Clone & environment**
   ```bash
   git clone <your-repo-url> eventify
   cd eventify
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **MySQL** — create the database and user:
   ```sql
   CREATE DATABASE eventify_db CHARACTER SET utf8mb4;
   CREATE USER 'eventify_user'@'localhost' IDENTIFIED BY 'change-me';
   GRANT ALL PRIVILEGES ON eventify_db.* TO 'eventify_user'@'localhost';
   ```
   `mysqlclient` needs MySQL's dev headers installed on the OS first
   (`libmysqlclient-dev` on Debian/Ubuntu, or use the MySQL installer's
   dev package on Windows/macOS).

3. **Environment variables**
   ```bash
   cp .env.example .env
   # edit .env with your DB credentials and a real SECRET_KEY
   ```
   For a quick spin without MySQL installed yet, set
   `DJANGO_USE_SQLITE=True` in `.env`.

4. **Migrate & create your first organizer**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Run**
   ```bash
   python manage.py runserver
   ```
   Log in at `/login/`, then use the "+ New Event" button.

## Tests

```bash
python manage.py test
```
Covers: anonymous users get redirected to login; an organizer only sees
their own events; a second organizer cannot open another organizer's
edit/delete URLs; dashboard totals (sold/remaining/revenue) are computed
correctly from bookings.

## Git / GitHub

```bash
git init
git add .
git commit -m "Sprint 1-3: auth, event CRUD with images, sales dashboard"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```
Suggested branching for the sprints as you build them out further:
`feature/sprint1-auth-events`, `feature/sprint2-images-ownership`,
`feature/sprint3-dashboard`, merged into `main` via PRs.

## Azure DevOps

`azure-pipelines.yml` is included at the repo root. In Azure DevOps:
1. Create a new Pipeline → "Azure Repos Git" or "GitHub" → point it at
   this repo → it will detect `azure-pipelines.yml` automatically.
2. The pipeline installs dependencies, runs `manage.py check`, checks
   for missing migrations, and runs the test suite — using SQLite in
   CI so no MySQL server is required in the build agent.
3. For deployment, add a second stage (e.g. deploy to an Azure App
   Service) once you're ready — the current file only covers CI.

## Cursor

Since this is a plain Django project (no special build step), Cursor
should work out of the box — open the `eventify/` folder as the
workspace root so its Python/Django tooling can find `manage.py` and
`requirements.txt`.

## Notes / things to decide next

- `Booking` creation (the attendee-facing purchase flow) isn't part of
  these sprints — the dashboard just reads whatever rows exist in
  `bookings`, so you can seed them via `/admin/` for now.
- Consider adding a `django-storages` backend (e.g. Azure Blob Storage)
  for `MEDIA_ROOT` before deploying, so poster images survive restarts
  on most PaaS hosts.
