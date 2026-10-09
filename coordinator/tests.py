from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from coordinator.models import (
    Community,
    Participation,
    UmugandaProject,
    UserProfile,
    Volunteer,
)


class HomePageTests(TestCase):
    def test_homepage_shows_date_logo_and_slideshow(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Small acts.")
        self.assertContains(response, timezone.localdate().strftime("%A, %B"))
        self.assertContains(response, "coordinator/images/umuganda-logo.svg")
        self.assertContains(response, 'data-slideshow')
        self.assertContains(response, 'data-slide-next')
        self.assertContains(response, "coordinator/images/umuganda4.jpg")


class ProjectPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="coordinator",
            password="test-password",
        )
        self.community = Community.objects.create(
            province="kigali",
            district="Gasabo",
            sector="Kacyiru",
            cell="Kigali",
            village="Gisozi",
            leader=self.user,
        )
        self.project = UmugandaProject.objects.create(
            title="Neighborhood Clean-up",
            description="Clean the community park.",
            location="Gisozi Park",
            date="2026-10-15",
            start_time="08:00:00",
            end_time="10:00:00",
            community=self.community,
            needed_volunteers=10,
            status="planned",
            created_by=self.user,
        )

    def test_project_list_displays_planned_projects(self):
        response = Client(HTTP_HOST="testserver").get("/projects/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Neighborhood Clean-up")
        self.assertContains(response, "Gisozi Park")

    def test_past_projects_disappear_from_public_pages_and_cannot_be_joined(self):
        self.project.date = timezone.localdate() - timedelta(days=1)
        self.project.save(update_fields=["date"])

        volunteer = User.objects.create_user(
            username="pastprojectvolunteer",
            password="StrongPass123!",
        )
        self.client.force_login(volunteer)
        listing = self.client.get("/projects/")
        detail = self.client.get(f"/projects/{self.project.pk}/")
        signup = self.client.post(f"/projects/{self.project.pk}/signup/")

        self.assertEqual(listing.context["total_projects"], 0)
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(signup.status_code, 404)

    def test_project_list_filters_by_full_community_hierarchy(self):
        other_community = Community.objects.create(
            province="kigali",
            district="Nyarugenge",
            sector="Nyamirambo",
            cell="Cyivugiza",
            village="Rugarama",
        )
        UmugandaProject.objects.create(
            title="Other community project",
            description="A project elsewhere.",
            location="Rugarama",
            date="2026-10-16",
            start_time="08:00:00",
            end_time="10:00:00",
            community=other_community,
            needed_volunteers=10,
            created_by=self.user,
        )

        response = self.client.get("/projects/", {
            "province": "kigali",
            "district": "Gasabo",
            "sector": "Kacyiru",
            "cell": "Kigali",
            "village": "Gisozi",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_projects"], 1)
        self.assertContains(response, "Neighborhood Clean-up")
        self.assertNotContains(response, "Other community project")

    def test_location_dropdowns_cascade_from_selected_parent(self):
        Community.objects.create(
            province="south",
            district="Huye",
            sector="Tumba",
            cell="Matyazo",
            village="Rango",
        )

        response = self.client.get("/projects/", {"province": "kigali"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["available_districts"]), ["Gasabo"])
        self.assertEqual(list(response.context["available_sectors"]), ["Kacyiru"])
        self.assertEqual(list(response.context["available_cells"]), ["Kigali"])
        self.assertEqual(list(response.context["available_villages"]), ["Gisozi"])

    def test_project_detail_displays_project_details(self):
        client = Client(HTTP_HOST="testserver")
        client.force_login(self.user)
        response = client.get(f"/projects/{self.project.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.title)
        self.assertContains(response, "Project location:")
        self.assertContains(response, "Gisozi Park")
        self.assertContains(response, "Sign Up as Volunteer")

    def test_volunteer_can_sign_up_once_for_a_project(self):
        volunteer_user = User.objects.create_user(
            username="projectvolunteer",
            password="StrongPass123!",
        )
        client = Client(HTTP_HOST="testserver")
        client.force_login(volunteer_user)

        first_response = client.post(f"/projects/{self.project.pk}/signup/")
        second_response = client.post(f"/projects/{self.project.pk}/signup/")

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(
            Participation.objects.filter(
                volunteer__user=volunteer_user,
                project=self.project,
            ).count(),
            1,
        )
        detail_response = client.get(f"/projects/{self.project.pk}/")
        self.assertContains(
            detail_response,
            "You are already registered as a volunteer",
        )


class RegistrationTests(TestCase):
    def setUp(self):
        self.community = Community.objects.create(
            province="kigali",
            district="Gasabo",
            sector="Kacyiru",
            cell="Kagugu",
            village="Kibagabaga",
        )

    def test_volunteer_registration_creates_account_and_profile(self):
        response = self.client.post("/register/", {
            "username": "newvolunteer",
            "email": "volunteer@example.com",
            "phone": "+250788000001",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertRedirects(
            response,
            "/dashboard/",
            fetch_redirect_response=False,
        )
        user = User.objects.get(username="newvolunteer")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertTrue(Volunteer.objects.filter(
            user=user,
            phone="+250788000001",
        ).exists())
        self.assertEqual(
            UserProfile.objects.get(user=user).role,
            "volunteer",
        )
        self.assertEqual(self.client.get("/dashboard/volunteer/").status_code, 200)

    def test_district_leader_enters_and_saves_only_their_area(self):
        other_district_community = Community.objects.create(
            province="kigali",
            district="Nyarugenge",
            sector="Nyamirambo",
            cell="Cyivugiza",
            village="Rugarama",
        )
        response = self.client.post("/leaders/register/", {
            "username": "districtleader",
            "first_name": "District",
            "last_name": "Leader",
            "email": "leader@example.com",
            "phone": "+250788000002",
            "leader_type": "district",
            "province": "kigali",
            "district": "Gasabo",
            "sector": "Should be discarded",
            "cell": "Should be discarded",
            "village": "Should be discarded",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertRedirects(response, "/leaders/login/")
        user = User.objects.get(username="districtleader")
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.leader_type, "district")
        self.assertEqual(profile.province, "kigali")
        self.assertEqual(profile.district, "Gasabo")
        self.assertEqual(profile.sector, "")
        self.assertEqual(profile.cell, "")
        self.assertEqual(profile.village, "")
        self.assertFalse(profile.is_approved)
        project_list = self.client.get("/projects/")
        self.assertIn("Gasabo", project_list.context["available_districts"])
        self.assertIn(self.community, profile.managed_communities())
        self.assertFalse(
            profile.managed_communities().filter(
                pk=other_district_community.pk
            ).exists()
        )
        self.assertNotIn(
            other_district_community,
            profile.managed_communities(),
        )
        login_response = self.client.post("/leaders/login/", {
            "username": "districtleader",
            "password": "StrongPass123!",
        })
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, "awaiting administrator approval")

        profile.is_approved = True
        profile.save(update_fields=["is_approved"])
        approved_login = self.client.post("/leaders/login/", {
            "username": "districtleader",
            "password": "StrongPass123!",
        })
        self.assertRedirects(
            approved_login,
            "/dashboard/leader/",
            fetch_redirect_response=False,
        )
        dashboard_response = self.client.get("/dashboard/leader/")
        self.assertEqual(dashboard_response.status_code, 200)
        project_response = self.client.post("/dashboard/leader/", {
            "title": "Gasabo district-wide work",
            "description": "A project for residents throughout Gasabo.",
            "location": "Gasabo district",
            "date": "2026-11-01",
            "start_time": "08:00",
            "end_time": "10:00",
            "community": profile.community.pk,
            "needed_volunteers": 100,
        })
        self.assertRedirects(project_response, "/dashboard/leader/")
        project = UmugandaProject.objects.get(title="Gasabo district-wide work")
        self.assertEqual(project.community, profile.community)

    def test_province_leader_can_register_without_child_area_records(self):
        response = self.client.post("/leaders/register/", {
            "username": "provinceleader",
            "email": "province@example.com",
            "phone": "+250788000003",
            "leader_type": "province",
            "province": "south",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertRedirects(response, "/leaders/login/")
        profile = UserProfile.objects.get(user__username="provinceleader")
        self.assertEqual(profile.province, "south")
        self.assertEqual(profile.district, "")
        self.assertEqual(profile.community.full_address(), "Southern Province")
        self.assertEqual(
            set(profile.managed_communities()),
            {profile.community},
        )

    def test_leader_signup_suggests_known_areas_and_allows_new_entries(self):
        response = self.client.get("/leaders/register/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'list="district-location-options"')
        self.assertContains(response, '<option value="Gasabo">', html=True)
        self.assertContains(response, "you can type a new area")

        response = self.client.post("/leaders/register/", {
            "username": "newdistrictleader",
            "email": "newdistrict@example.com",
            "phone": "+250788000004",
            "leader_type": "district",
            "province": "east",
            "district": "New district",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertRedirects(response, "/leaders/login/")
        filter_response = self.client.get("/projects/", {"province": "east"})
        self.assertIn(
            "New district",
            filter_response.context["available_districts"],
        )

    def test_leader_can_publish_project_within_managed_district(self):
        second_district_community = Community.objects.create(
            province="kigali",
            district="Gasabo",
            sector="Remera",
            cell="Rukiri",
            village="Nyabisindu",
        )
        user = User.objects.create_user(
            username="districtleader",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=user,
            role="leader",
            leader_type="district",
            community=self.community,
            is_approved=True,
        )
        self.client.force_login(user)

        response = self.client.post("/dashboard/leader/", {
            "title": "District clean-up",
            "description": "Clean public spaces across the district.",
            "location": "Nyabisindu public area",
            "date": "2026-10-31",
            "start_time": "08:00",
            "end_time": "10:00",
            "community": second_district_community.pk,
            "needed_volunteers": 20,
        })

        self.assertRedirects(response, "/dashboard/leader/")
        project = UmugandaProject.objects.get(title="District clean-up")
        self.assertEqual(project.community, second_district_community)
        self.assertEqual(project.created_by, user)


    def test_leader_can_edit_and_delete_their_own_project(self):
        user = User.objects.create_user(
            username="projectleader",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=user,
            role="leader",
            leader_type="district",
            community=self.community,
            is_approved=True,
        )
        project = UmugandaProject.objects.create(
            title="Original project",
            description="Original description",
            location="Original location",
            date=timezone.localdate() + timedelta(days=10),
            start_time="08:00",
            end_time="10:00",
            community=self.community,
            needed_volunteers=10,
            created_by=user,
        )
        self.client.force_login(user)

        edit_page = self.client.get(f"/dashboard/leader/projects/{project.pk}/edit/")
        self.assertEqual(edit_page.status_code, 200)
        update_response = self.client.post(
            f"/dashboard/leader/projects/{project.pk}/edit/",
            {
                "title": "Updated project",
                "description": "Updated description",
                "location": "Updated location",
                "date": (timezone.localdate() + timedelta(days=12)).isoformat(),
                "start_time": "09:00",
                "end_time": "11:00",
                "community": self.community.pk,
                "needed_volunteers": 20,
            },
        )
        self.assertRedirects(update_response, "/dashboard/leader/")
        project.refresh_from_db()
        self.assertEqual(project.title, "Updated project")
        self.assertEqual(project.needed_volunteers, 20)

        delete_response = self.client.post(
            f"/dashboard/leader/projects/{project.pk}/delete/"
        )
        self.assertRedirects(delete_response, "/dashboard/leader/")
        self.assertFalse(UmugandaProject.objects.filter(pk=project.pk).exists())

    def test_leader_cannot_edit_or_delete_another_leaders_project(self):
        owner = User.objects.create_user(
            username="owner",
            password="StrongPass123!",
        )
        other_leader = User.objects.create_user(
            username="otherleader",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=other_leader,
            role="leader",
            leader_type="district",
            community=self.community,
            is_approved=True,
        )
        project = UmugandaProject.objects.create(
            title="Owner's project",
            description="Project description",
            location="Gasabo",
            date=timezone.localdate() + timedelta(days=10),
            start_time="08:00",
            end_time="10:00",
            community=self.community,
            needed_volunteers=10,
            created_by=owner,
        )
        self.client.force_login(other_leader)

        edit_response = self.client.get(
            f"/dashboard/leader/projects/{project.pk}/edit/"
        )
        delete_response = self.client.post(
            f"/dashboard/leader/projects/{project.pk}/delete/"
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(UmugandaProject.objects.filter(pk=project.pk).exists())


class AdminAccountEditingTests(TestCase):
    def test_admin_can_open_user_editor_from_volunteer_and_profile_records(self):
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
        )
        member = User.objects.create_user(
            username="member",
            password="StrongPass123!",
        )
        Volunteer.objects.create(user=member, phone="123")
        UserProfile.objects.create(
            user=member,
            role="volunteer",
            phone="123",
            is_approved=True,
        )
        self.client.force_login(admin_user)
        user_edit_url = f"/admin/auth/user/{member.pk}/change/"

        volunteer_list = self.client.get("/admin/coordinator/volunteer/")
        profile_list = self.client.get("/admin/coordinator/userprofile/")
        user_edit = self.client.get(user_edit_url)

        self.assertEqual(volunteer_list.status_code, 200)
        self.assertContains(volunteer_list, user_edit_url)
        self.assertEqual(profile_list.status_code, 200)
        self.assertContains(profile_list, user_edit_url)
        self.assertEqual(user_edit.status_code, 200)
        self.assertContains(user_edit, 'name="email"')
        self.assertContains(user_edit, 'name="userprofile-0-phone"')
        self.assertContains(user_edit, 'name="volunteer-0-phone"')
