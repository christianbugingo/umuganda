from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from coordinator.models import Community, Participation, UmugandaProject, Volunteer


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
