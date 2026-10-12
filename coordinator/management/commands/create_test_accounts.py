from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from coordinator.models import Community, UserProfile, Volunteer


# Passwords are communicated to the site owner separately; only encoded hashes
# are kept in source control. These dedicated test accounts are reset to the
# documented credentials on startup so an earlier partial bootstrap is repaired.
TEST_ACCOUNTS = (
    (
        'test_community_leader',
        'pbkdf2_sha256$1200000$NM5uKFuzlH0jDaGewuHM91$3b+/PW9+wGwf3/G4ewnE8FFmDpc22QbZEilK/akWpxU=',
        'leader',
    ),
    (
        'test_volunteer',
        'pbkdf2_sha256$1200000$Hg5MhvtEfn0cdEK15htRWY$McF+MUuJwoTS6Ond6N0CJBz6QDbUdkL6jVoQbIYvFSI=',
        'volunteer',
    ),
)


class Command(BaseCommand):
    help = 'Create active community leader and volunteer accounts for site testing.'

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        leader, _ = User.objects.get_or_create(
            username=TEST_ACCOUNTS[0][0],
            defaults={
                'first_name': 'Test Community',
                'last_name': 'Leader',
                'email': 'test-community-leader@example.invalid',
                'password': TEST_ACCOUNTS[0][1],
                'is_active': True,
            },
        )
        leader.is_active = True
        leader.password = TEST_ACCOUNTS[0][1]
        leader.save(update_fields=['is_active', 'password'])

        # A dedicated test-only area keeps the leader account from claiming a
        # real community or colliding with a real leader's assignment.
        community, _ = Community.objects.get_or_create(
            province='kigali',
            district='Test District',
            sector='Test Sector',
            cell='Test Cell',
            village='Test Village',
        )
        UserProfile.objects.update_or_create(
            user=leader,
            defaults={
                'role': 'leader',
                'leader_type': 'village',
                'community': community,
                'province': 'kigali',
                'district': 'Test District',
                'sector': 'Test Sector',
                'cell': 'Test Cell',
                'village': 'Test Village',
                'is_approved': True,
            },
        )
        community.leader = leader
        community.save(update_fields=['leader'])

        volunteer, _ = User.objects.get_or_create(
            username=TEST_ACCOUNTS[1][0],
            defaults={
                'first_name': 'Test',
                'last_name': 'Volunteer',
                'email': 'test-volunteer@example.invalid',
                'password': TEST_ACCOUNTS[1][1],
                'is_active': True,
            },
        )
        volunteer.is_active = True
        volunteer.password = TEST_ACCOUNTS[1][1]
        volunteer.save(update_fields=['is_active', 'password'])
        UserProfile.objects.update_or_create(
            user=volunteer,
            defaults={'role': 'volunteer', 'is_approved': False},
        )
        Volunteer.objects.get_or_create(user=volunteer, defaults={'community': community})

        self.stdout.write('Test community leader and volunteer accounts are ready.')
