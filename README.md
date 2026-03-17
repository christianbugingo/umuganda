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
- **Admin Management** - Staff can create projects and mark participant attendance
- **Community-Based** - Volunteers automatically linked to their village community
- **Hours Tracking** - Monitor and report volunteer contribution hours

## 🗺️ Geographic Hierarchy

The system follows Rwanda's official administrative structure:
- Province (Intara)
- District (Akarere)
- Sector (Umurenge)
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
