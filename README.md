# Umuganda - Community Volunteer Coordinator 🇷🇼

A Django-based web application for managing "Umuganda" community volunteer projects and participation in Rwanda. This platform helps coordinators organize community work and track volunteer engagement across the country's geographic hierarchy.

## 📋 Overview

Umuganda (meaning "community work" in Kinyarwanda) is a traditional Rwandan practice of coming together to accomplish a common goal. This digital platform modernizes the coordination of these community activities by providing tools for project management, volunteer registration, and participation tracking.

## 🏗️ Database Structure

The application uses four main models:

- **Community** - Manages Rwanda's geographic hierarchy (Provinces → Districts → Sectors → Villages)
- **UmugandaProject** - Volunteer projects created by coordinators with details like date, location, and description
- **Volunteer** - User profiles automatically created upon registration, linked to their specific community
- **Participation** - Tracks volunteer sign-ups with unique constraints to prevent duplicate registrations

## ✨ Key Features

- **Geographic Organization** - Projects grouped by Rwandan provinces for easy discovery
- **Smart Sign-up System** - Prevents duplicate sign-ups with unique constraints
- **Volunteer Dashboard** - Personal tracking of sign-up history, attendance, and hours contributed
- **Leader Accounts** - Village, cell, sector, district, and province leaders can publish projects in the villages within their managed area
- **Admin Management** - Staff can create projects and mark participant attendance
- **Community-Based** - Volunteers automatically linked to their village community
- **Hours Tracking** - Monitor and report volunteer contribution hours
- **Community Announcements** - Approved leaders can publish local notices, updates,
  and volunteer opportunities separately from project listings

## 🗺️ Geographic Hierarchy

The system follows Rwanda's official administrative structure:
- Province (Intara)
- District (Akarere)
- Sector (Umurenge)
- Cell (Akagari)
- Village (Umudugudu)

## 🚶‍♂️ User Workflow

### For Visitors (Non-logged in users)
1. Browse available projects on `project_list.html` (organized by province)
2. View project details without signing up

### For Registered Volunteers
1. Register/Login to automatically create a Volunteer profile
2. Browse and sign up for projects on `project_detail.html`
3. Access personal dashboard to view:
   - Sign-up history
   - Attendance records
   - Total hours contributed

### For Community Leaders
1. Apply as a village, cell, sector, district, or province leader and enter the location fields up to your leadership level
2. Wait for an administrator to independently verify and approve the application
3. After approval, publish projects for your managed area; projects are listed publicly for volunteers to discover and join

Leader applications are not proof of a real-world leadership role. Before approving one in
the Django admin under **User profiles**, contact the relevant local authority or use an
official appointment/confirmation record. Verify the person's identity through a trusted
channel, and avoid collecting or storing identity documents unless the organization has a
secure, lawful process for handling them. Set **Approved** only after verification; an
unapproved applicant cannot sign in as a leader or open the leader dashboard.
Existing leader accounts are left unapproved by the migration and should be verified before
they regain leader access. Existing volunteer accounts remain usable.

### For Admins/Staff
1. Create and manage Umuganda projects
2. Mark participant attendance
3. Oversee volunteer participation
4. Generate reports on community engagement

## 📄 Main Pages

- **Home** - Landing page with overview
- **Project List** - Browse all projects by province
- **Project Details** - View specific project information
- **Sign Up** - Register for projects
- **Dashboard** - Personal volunteer statistics
- **Register** - New user registration
- **Login** - User authentication
- **Admin Panel** - Django admin interface for management

## 🛠️ Technology Stack

- **Backend**: Django (Python)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTML5, CSS3, Bootstrap
- **Authentication**: Django's built-in auth system

## 📦 Installation

1. Clone the repository
```bash
git clone https://github.com/christianbugingo/umuganda.git
cd umuganda
```

### Run locally

Install the dependencies, create the database tables, and start the development server:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Open `http://localhost:8000/` when running on your computer. If the project is running
in a remote workspace or Codespace, forward port **8000** in the editor and open its
forwarded URL in Safari; `localhost` on your computer does not point to a remote workspace.

### Back up and restore SQLite

Create an integrity-checked, timestamped backup while the app is running:

```bash
python scripts/sqlite_backup.py backup
```

Backups are written to `backups/` (excluded from Git). To keep a copy outside the
computer or deployment filesystem, choose a durable backup location:

```bash
python scripts/sqlite_backup.py backup --backup-dir /path/to/durable/backups
```

For a daily local backup on macOS/Linux, add a scheduled task with `crontab -e`
(replace both paths with absolute paths; use a destination on a separate drive):

```cron
0 2 * * * test -d /Volumes/BackupDrive && cd /absolute/path/to/umuganda && /absolute/path/to/python scripts/sqlite_backup.py backup --backup-dir /Volumes/BackupDrive/umuganda
```

To restore, stop the web server first, then use the backup file path. The command
checks the backup and saves the current database as a `pre-restore-...` backup before
replacing it:

```bash
python scripts/sqlite_backup.py restore /path/to/durable/backups/db-YYYYMMDDTHHMMSSffffffZ.sqlite3
```

The SQLite database does not contain uploaded profile-photo files. Back up the
`media/` directory as well. Render's filesystem is ephemeral on free services, so
the database and uploads are lost when the service spins down, restarts, or redeploys.
Use a free deployment only for a disposable preview. The Render Blueprint below
configures a paid service with persistent storage for data you need to keep. The app
remains on SQLite; keep it on one Render instance and do not enable multiple instances.

##### Create a preview admin without Render Shell

Render Shell is unavailable on the Free plan. To create a disposable test admin,
set these environment variables for the web service in the Render Dashboard:

- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD` (enter it as a secret; never commit it)

After deploying this version, the start command runs
`python manage.py create_superuser_from_env` after migrations. It creates the named
superuser only when no account with that username exists; it does not print or reset
the password. Remove the three environment variables after creating the test admin.
If the Free service loses its SQLite database on a restart or spin-down, set the
variables again to recreate the admin. Use only throwaway accounts and test data on
this ephemeral service; do not enter real volunteer or leader information.

#### Persistent data on Render

The Render Blueprint in `render.yaml` attaches a 1 GB persistent disk at `/var/data`
and configures the database and uploaded media to live there. Persistent disks require
a paid Render web-service plan and incur charges; the Blueprint selects the Starter
plan. Review the plan and disk cost in Render before applying the Blueprint. Keep this
SQLite-backed service at one instance and do not enable multiple instances.

**Before applying this change to an existing service, export its current database and
uploads.** The existing database on Render's ephemeral filesystem will not
automatically move onto the disk. If the site contains data you need, use the Render
Shell to create a SQLite backup and copy it off Render, and archive
`/opt/render/project/src/media/` if it exists. After the persistent disk is attached,
copy the saved database to `/var/data/db.sqlite3` and uploads to `/var/data/media/`
before relying on the new deployment. If the ephemeral database has already been
lost, the new disk will start with an empty database and registrations must be made
again.

#### Render recovery plan

Render automatically snapshots persistent disks about once every 24 hours and keeps
snapshots for at least seven days. To recover from disk corruption or data loss, use
the service's **Disks** page in the Render Dashboard and restore a snapshot from
before the problem. A snapshot restore reverts the entire disk, including later
database and upload changes; it is not a per-file restore. See
[Render persistent-disk snapshots](https://render.com/docs/disks#disk-snapshots).

For a SQLite-consistent logical backup, run this from the Render Shell periodically
and before risky changes:

```bash
python scripts/sqlite_backup.py backup --backup-dir /var/data/backups
```

The backup command runs SQLite's online backup API and checks database integrity.
Copy important backups off the Render disk as well: a disk snapshot protects against
some failures, but a backup kept only on the same disk is not independent. The
`media/` folder is included in Render disk snapshots but not in the SQLite backup
file. To export photos from the Render Shell, archive them separately and copy both
the database backup and media archive off the service. Test a restore periodically;
the restore command makes a safety copy and must only be run with the app stopped.

### Uploaded profile photos

Locally, uploaded photos are stored under `media/` and served at `/media/` while
`DEBUG` is enabled. In production, persist them using `DJANGO_MEDIA_ROOT` as described
above. The current production setup does not yet serve uploaded media URLs; configure
a production media-serving layer (or private object storage) before expecting profile
photos to display on the hosted site.

### Community announcements and testimonials

Approved leaders can create, update, and delete their own community announcements
from the leader dashboard. Announcements are stored in SQLite, appear in a visually
separate homepage section, and can have an optional expiry date. Staff can also review
and unpublish announcements in the Django admin under **Community announcements**.

Authentic testimonials are managed by staff in the admin under **Testimonials**.
Add a quote and attribution only after the contributor has agreed to publication, mark
**Consent confirmed**, then mark **Is published**. The homepage randomly rotates up to
three from the most recently added consented, published testimonials; no sample or
fabricated testimonials are displayed when there are no approved entries.

### Umuganda journals

Staff can add past activities in Django admin under **Umuganda journals**. Enter the
activity title, date, location, organizer (optional), a short summary, the full story,
and a cover photo. Add supporting pictures in the **Journal photos** inline section;
captions are optional. Optionally select one **Homepage photo** to make the matching
existing activity photo link to this full story. Each homepage photo can be assigned
to only one journal. Save the entry as a draft while reviewing it, then select
**Is published** to make it visible. Published stories without a homepage-photo
assignment appear in a separate journal-card section. Every story page includes the
activity details, photos, related journals, and comments. The homepage shows up to
four recent journal cards and links to the full `/journals/` archive when there are
more than four published entries. The archive shows twelve entries per page.

Public comments do not require an account or collect email addresses. New comments are
held for review. Staff can approve them under **Journal comments** in Django admin;
only approved comments appear publicly.

Journal photos are served from `/media/journals/`. On Render, set
`DJANGO_MEDIA_ROOT` to the media directory on a persistent disk before uploading
stories. SQLite and media on the current free, ephemeral deployment can disappear
after a restart or redeploy; see **Keep SQLite and uploads on a Render persistent
disk** above. Uploaded profile-photo URLs still need a separate production media
serving setup.
