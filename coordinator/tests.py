from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from coordinator.models import (
    Announcement,
    Community,
    JournalComment,
    JournalPhoto,
    Participation,
    UmugandaProject,
    UmugandaJournal,
    UserProfile,
    Volunteer,
    Testimonial,
)


class HomePageTests(TestCase):
    def test_homepage_shows_clear_actions_and_journal_section(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organise community work.")
        self.assertContains(response, "coordinator/images/umuganda-logo.svg")
        self.assertContains(response, "Find a project")
        self.assertContains(response, "Join as a volunteer")
        self.assertContains(response, "home-hero-image")
        self.assertContains(response, 'id="journal"')
        self.assertContains(response, "People working together")
        self.assertContains(response, "coordinator/images/umuganda1.jpg")
        self.assertContains(response, "coordinator/images/umuganda2.jpg")
        self.assertContains(response, "coordinator/images/umuganda3.jpg")
        self.assertContains(response, "coordinator/images/umuganda4.jpg")
        self.assertContains(response, "journal-archive-grid")
        self.assertContains(response, "announcement-leader-link")
        self.assertContains(response, "Stories of past Umuganda activities will appear here.")
        self.assertNotContains(response, "youtube.com")
        self.assertNotContains(response, "data-video-player")
        self.assertNotContains(response, "Watch on YouTube")

    def test_homepage_shows_two_latest_active_announcements_and_consented_testimonials(self):
        leader = User.objects.create_user(
            username="homeleader",
            password="StrongPass123!",
        )
        announcements = [
            Announcement.objects.create(
                title=f"Notice {index}",
                body="A local update.",
                created_by=leader,
            )
            for index in range(5)
        ]
        Announcement.objects.create(
            title="Expired notice",
            body="This is out of date.",
            created_by=leader,
            expires_at=timezone.localdate() - timedelta(days=1),
        )
        testimonials = [
            Testimonial.objects.create(
                quote=f"Community story {index}",
                attribution=f"Volunteer {index}",
                consent_confirmed=True,
                is_published=True,
            )
            for index in range(4)
        ]
        Testimonial.objects.create(
            quote="Not approved for publication",
            attribution="Private volunteer",
            consent_confirmed=False,
            is_published=True,
        )

        response = self.client.get("/")

        shown_announcements = list(response.context["announcements"])
        shown_testimonials = list(response.context["testimonials"])
        self.assertEqual(len(shown_announcements), 2)
        self.assertEqual(shown_announcements, list(reversed(announcements[-2:])))
        self.assertEqual(len(shown_testimonials), 3)
        self.assertTrue(set(shown_testimonials).issubset(set(testimonials)))
        self.assertContains(response, "Community announcements")
        self.assertContains(response, "Community stories")
        self.assertContains(response, reverse('announcement_list'))


class AnnouncementArchiveTests(TestCase):
    def setUp(self):
        self.leader = User.objects.create_user(
            username='archiveleader',
            password='StrongPass123!',
        )

    def create_announcement(self, title, **kwargs):
        return Announcement.objects.create(
            title=title,
            body=f'{title} details.',
            created_by=self.leader,
            **kwargs,
        )

    def test_archive_paginates_active_published_announcements_newest_first(self):
        announcements = [
            self.create_announcement(f'Archive notice {index}')
            for index in range(12)
        ]
        self.create_announcement(
            'Expired archive notice',
            expires_at=timezone.localdate() - timedelta(days=1),
        )
        self.create_announcement('Unpublished archive notice', is_published=False)

        first_page = self.client.get(reverse('announcement_list'))
        second_page = self.client.get(reverse('announcement_list'), {'page': 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context['page_obj'].paginator.count, 12)
        self.assertEqual(len(first_page.context['announcements']), 10)
        self.assertEqual(first_page.context['announcements'][0], announcements[-1])
        self.assertContains(first_page, 'Older announcements')
        self.assertNotContains(first_page, 'Expired archive notice')
        self.assertNotContains(first_page, 'Unpublished archive notice')
        self.assertEqual(len(second_page.context['announcements']), 2)
        self.assertContains(second_page, 'Newer announcements')

    def test_archive_is_not_added_to_the_main_navigation(self):
        response = self.client.get(reverse('home'))

        self.assertNotContains(response, 'class="nav-link" href="/announcements/"')


class SuperuserBootstrapTests(TestCase):
    @patch.dict('os.environ', {
        'DJANGO_SUPERUSER_USERNAME': 'bootstrap-admin',
        'DJANGO_SUPERUSER_EMAIL': 'bootstrap@example.com',
        'DJANGO_SUPERUSER_PASSWORD': 'test-only-password-123',
    })
    def test_creates_superuser_from_environment_without_overwriting_existing_password(self):
        call_command('create_superuser_from_env')
        user = User.objects.get(username='bootstrap-admin')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password('test-only-password-123'))

        with patch.dict('os.environ', {
            'DJANGO_SUPERUSER_USERNAME': 'bootstrap-admin',
            'DJANGO_SUPERUSER_EMAIL': 'bootstrap@example.com',
            'DJANGO_SUPERUSER_PASSWORD': 'different-test-password-456',
        }):
            call_command('create_superuser_from_env')

        user.refresh_from_db()
        self.assertTrue(user.check_password('test-only-password-123'))
        self.assertFalse(user.check_password('different-test-password-456'))

    def test_rejects_partial_environment_credentials(self):
        with patch.dict('os.environ', {
            'DJANGO_SUPERUSER_USERNAME': 'bootstrap-admin',
            'DJANGO_SUPERUSER_EMAIL': 'bootstrap@example.com',
        }):
            with self.assertRaises(CommandError):
                call_command('create_superuser_from_env')

    def test_skips_when_environment_credentials_are_not_configured(self):
        with patch.dict('os.environ', {}, clear=True):
            call_command('create_superuser_from_env')

        self.assertFalse(User.objects.filter(username='bootstrap-admin').exists())


def uploaded_journal_image(name='journal-cover.png'):
    image_bytes = BytesIO()
    Image.new('RGB', (16, 12), color='green').save(image_bytes, format='PNG')
    return SimpleUploadedFile(
        name,
        image_bytes.getvalue(),
        content_type='image/png',
    )


class JournalPageTests(TestCase):
    def tearDown(self):
        for photo in JournalPhoto.objects.all():
            photo.image.delete(save=False)
        for journal in UmugandaJournal.objects.all():
            journal.cover_image.delete(save=False)
        super().tearDown()

    def create_journal(
        self,
        title='Community pathway restored',
        published=True,
        days_ago=1,
        homepage_photo=None,
    ):
        return UmugandaJournal.objects.create(
            title=title,
            activity_date=timezone.localdate() - timedelta(days=days_ago),
            location='Kacyiru, Kigali',
            organizer='Kacyiru community volunteers',
            summary='Neighbors repaired a shared pathway together.',
            description='Residents cleared the path and improved drainage.',
            cover_image=uploaded_journal_image(f'{title.lower().replace(" ", "-")}.png'),
            homepage_photo=homepage_photo,
            is_published=published,
        )

    def test_homepage_shows_latest_four_published_journals(self):
        journals = [
            self.create_journal(f'Journal {index}', days_ago=index)
            for index in range(5)
        ]
        self.create_journal('Draft journal', published=False)

        response = self.client.get('/')

        shown_journals = list(response.context['journals'])
        self.assertEqual(len(shown_journals), 4)
        self.assertNotIn('Draft journal', [journal.title for journal in shown_journals])
        self.assertEqual(shown_journals[0], journals[0])
        self.assertContains(response, reverse('journal_detail', args=[journals[0].slug]))
        self.assertContains(response, reverse('journal_list'))
        self.assertContains(response, 'See all journals')

    def test_homepage_shows_journal_archive_link_only_above_four(self):
        for index in range(4):
            self.create_journal(f'Journal {index}')

        four_journals = self.client.get('/')
        self.assertNotContains(four_journals, 'class="journal-see-more"')

        self.create_journal('Fifth journal')
        five_journals = self.client.get('/')
        self.assertContains(five_journals, 'class="journal-see-more"')

    def test_journal_archive_lists_all_published_journals_in_pages_of_twelve(self):
        journals = [
            self.create_journal(f'Journal {index}', days_ago=index)
            for index in range(13)
        ]
        self.create_journal('Draft journal', published=False)

        first_page = self.client.get(reverse('journal_list'))
        second_page = self.client.get(reverse('journal_list'), {'page': 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context['page_obj'].paginator.count, 13)
        self.assertEqual(len(first_page.context['journals']), 12)
        self.assertEqual(first_page.context['journals'][0], journals[0])
        self.assertContains(first_page, 'Older journals')
        self.assertNotContains(first_page, 'Draft journal')
        self.assertEqual(len(second_page.context['journals']), 1)
        self.assertEqual(second_page.context['journals'][0], journals[-1])
        self.assertContains(second_page, 'Newer journals')

    def test_published_journal_can_link_an_original_homepage_photo(self):
        journal = self.create_journal(homepage_photo='pathway')

        response = self.client.get('/')

        self.assertContains(response, 'class="journal-archive-link"')
        self.assertContains(response, reverse('journal_detail', args=[journal.slug]))
        self.assertContains(response, 'alt="Community members improving a shared pathway"')
        self.assertContains(response, 'Open one of the activity photos above to read its full story.')

    def test_journal_detail_shows_activity_photos_and_approved_comments(self):
        journal = self.create_journal()
        JournalPhoto.objects.create(
            journal=journal,
            image=uploaded_journal_image('community-work.png'),
            caption='Volunteers clearing the path',
        )
        JournalComment.objects.create(
            journal=journal,
            name='A community member',
            body='Thank you for sharing this.',
            is_approved=True,
        )
        JournalComment.objects.create(
            journal=journal,
            name='Awaiting review',
            body='This should stay private for now.',
        )

        response = self.client.get(reverse('journal_detail', args=[journal.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(journal.cover_image.url).status_code, 200)
        self.assertEqual(
            self.client.get(journal.photos.first().image.url).status_code,
            200,
        )
        self.assertContains(response, 'Residents cleared the path and improved drainage.')
        self.assertContains(response, 'Volunteers clearing the path')
        self.assertContains(response, 'A community member')
        self.assertNotContains(response, 'Awaiting review')
        self.assertContains(response, 'id="comments"')
        self.assertContains(response, reverse('home') + '#journal')

    def test_public_comment_is_held_until_approved(self):
        journal = self.create_journal()
        detail_url = reverse('journal_detail', args=[journal.slug])

        response = self.client.post(detail_url, {
            'name': 'Guest volunteer',
            'body': 'This was a meaningful day.',
        })

        self.assertRedirects(response, f'{detail_url}#comments', fetch_redirect_response=False)
        comment = JournalComment.objects.get(journal=journal)
        self.assertFalse(comment.is_approved)
        self.assertNotContains(self.client.get(detail_url), 'Guest volunteer')

        comment.is_approved = True
        comment.save(update_fields=('is_approved',))
        self.assertContains(self.client.get(detail_url), 'Guest volunteer')

    def test_unpublished_journals_and_their_photos_are_not_public(self):
        journal = self.create_journal(published=False)

        response = self.client.get(reverse('journal_detail', args=[journal.slug]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(journal.cover_image.url).status_code, 404)

    def test_admin_can_manage_journals_and_moderate_comments(self):
        admin_user = User.objects.create_superuser(
            username='journaladmin',
            email='journaladmin@example.com',
            password='StrongPass123!',
        )
        self.client.force_login(admin_user)

        self.assertEqual(self.client.get('/admin/coordinator/umugandajournal/').status_code, 200)
        self.assertEqual(self.client.get('/admin/coordinator/journalcomment/').status_code, 200)
        journal_form = self.client.get('/admin/coordinator/umugandajournal/add/')
        self.assertEqual(journal_form.status_code, 200)
        self.assertContains(journal_form, 'Homepage photo')


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
        self.assertContains(response, "Upcoming Community Projects")
        self.assertNotContains(response, "Upcoming Umuganda Projects")
        self.assertContains(response, "Neighborhood Clean-up")
        self.assertContains(response, "Gisozi Park")

    def test_project_list_paginates_results_and_preserves_filters(self):
        for index in range(12):
            UmugandaProject.objects.create(
                title=f"Additional project {index}",
                description="A community project.",
                location="Gisozi",
                date="2026-10-16",
                start_time="08:00",
                end_time="10:00",
                community=self.community,
                needed_volunteers=10,
                created_by=self.user,
            )

        first_page = self.client.get("/projects/", {"district": "Gasabo"})
        second_page = self.client.get(
            "/projects/",
            {"district": "Gasabo", "page": "2"},
        )

        self.assertEqual(first_page.context["total_projects"], 13)
        self.assertEqual(len(first_page.context["page_obj"].object_list), 12)
        self.assertTrue(first_page.context["page_obj"].has_next())
        self.assertEqual(len(second_page.context["page_obj"].object_list), 1)
        self.assertContains(first_page, "district=Gasabo&amp;page=2")

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


class LeaderAnnouncementTests(TestCase):
    def setUp(self):
        self.leader = User.objects.create_user(
            username="announcementleader",
            password="StrongPass123!",
        )
        self.other_leader = User.objects.create_user(
            username="anotherleader",
            password="StrongPass123!",
        )
        community = Community.objects.create(
            province="kigali",
            district="Gasabo",
            sector="Kacyiru",
            cell="Kagugu",
            village="Kibagabaga",
        )
        for user in (self.leader, self.other_leader):
            UserProfile.objects.create(
                user=user,
                role="leader",
                leader_type="district",
                community=community,
                is_approved=True,
            )

    def test_approved_leader_can_publish_edit_and_delete_announcement(self):
        self.client.force_login(self.leader)
        dashboard = self.client.get("/dashboard/leader/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Share a community announcement")
        create_response = self.client.post(
            "/dashboard/leader/announcements/new/",
            {
                "title": "Community meeting",
                "category": "notice",
                "body": "Residents are invited to the monthly meeting.",
                "area": "Gasabo",
                "expires_at": "",
            },
        )

        self.assertRedirects(create_response, "/dashboard/leader/")
        announcement = Announcement.objects.get(title="Community meeting")
        self.assertEqual(announcement.created_by, self.leader)
        self.assertContains(self.client.get("/"), "Community meeting")

        update_response = self.client.post(
            f"/dashboard/leader/announcements/{announcement.pk}/edit/",
            {
                "title": "Updated community meeting",
                "category": "community",
                "body": "The meeting starts at 9 AM.",
                "area": "Kacyiru",
                "expires_at": "",
            },
        )
        self.assertRedirects(update_response, "/dashboard/leader/")
        announcement.refresh_from_db()
        self.assertEqual(announcement.title, "Updated community meeting")
        self.assertEqual(announcement.area, "Kacyiru")

        delete_response = self.client.post(
            f"/dashboard/leader/announcements/{announcement.pk}/delete/"
        )
        self.assertRedirects(delete_response, "/dashboard/leader/")
        self.assertFalse(Announcement.objects.filter(pk=announcement.pk).exists())

    def test_leader_cannot_manage_other_leaders_announcements(self):
        announcement = Announcement.objects.create(
            title="Owner notice",
            body="An owner's announcement.",
            created_by=self.leader,
        )
        self.client.force_login(self.other_leader)

        edit_response = self.client.get(
            f"/dashboard/leader/announcements/{announcement.pk}/edit/"
        )
        delete_response = self.client.post(
            f"/dashboard/leader/announcements/{announcement.pk}/delete/"
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(Announcement.objects.filter(pk=announcement.pk).exists())

    def test_only_approved_leaders_can_publish_announcements(self):
        profile = UserProfile.objects.get(user=self.leader)
        profile.is_approved = False
        profile.save(update_fields=["is_approved"])
        self.client.force_login(self.leader)

        response = self.client.post(
            "/dashboard/leader/announcements/new/",
            {
                "title": "Unapproved notice",
                "category": "notice",
                "body": "This should not publish.",
                "area": "Gasabo",
                "expires_at": "",
            },
        )

        self.assertRedirects(response, "/")
        self.assertFalse(
            Announcement.objects.filter(title="Unapproved notice").exists()
        )


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
        self.assertEqual(
            self.client.get("/admin/coordinator/announcement/").status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/admin/coordinator/testimonial/").status_code,
            200,
        )


class ProfilePhotoTests(TestCase):
    def test_uploaded_profile_photo_is_saved_and_served_locally(self):
        user = User.objects.create_user(
            username="photovolunteer",
            password="StrongPass123!",
        )
        self.client.force_login(user)
        image_bytes = BytesIO()
        Image.new("RGB", (8, 8), color="green").save(image_bytes, format="PNG")
        upload = SimpleUploadedFile(
            "profile.png",
            image_bytes.getvalue(),
            content_type="image/png",
        )

        response = self.client.post("/profile/edit/", {
            "first_name": "Photo",
            "last_name": "Volunteer",
            "email": "photo@example.com",
            "phone": "123",
            "photo": upload,
        })

        self.assertRedirects(
            response,
            "/dashboard/",
            fetch_redirect_response=False,
        )
        profile = UserProfile.objects.get(user=user)
        try:
            self.assertTrue(profile.photo.name)
            self.assertTrue(profile.photo.storage.exists(profile.photo.name))
            self.assertTrue(profile.photo.url.startswith("/media/"))
        finally:
            profile.photo.delete(save=False)


class AccessibilityTests(TestCase):
    def test_base_page_has_skip_link_and_local_image_sources(self):
        response = self.client.get("/")

        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'id="main-content"')
        self.assertContains(response, 'type="image/webp"')
        self.assertNotContains(response, 'data-slide-toggle')

    def test_leader_signup_field_errors_are_linked_to_invalid_inputs(self):
        response = self.client.post("/leaders/register/", {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'id="id_username_error"')
        self.assertContains(response, 'href="#id_username"')
