from django.conf import settings
from django.db import migrations


LEADER = (
    "test_lead",
    "pbkdf2_sha256$1200000$Ax9QlhxIVKrn8Fm0CD0YMB$vetX+2H11zh60LPPFVR3KXSBwZ9b3Oi930sHdRSwMGU=",
)
VOLUNTEER = (
    "test_vol",
    "pbkdf2_sha256$1200000$cktOEUhybbdDxHfXMSuow1$AZRCE7nse5Z0Om+t9O5eAN+JS6wHC/LbqvSV7kPyQJg=",
)


def create_test_accounts(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Community = apps.get_model("coordinator", "Community")
    UserProfile = apps.get_model("coordinator", "UserProfile")
    VolunteerProfile = apps.get_model("coordinator", "Volunteer")

    User.objects.filter(
        username__in=("test_community_leader", "test_volunteer"),
    ).update(is_active=False)

    leader, _ = User.objects.get_or_create(
        username=LEADER[0],
        defaults={
            "first_name": "Test Community",
            "last_name": "Leader",
            "email": "test-community-leader@example.invalid",
            "password": LEADER[1],
            "is_active": True,
        },
    )
    leader.password = LEADER[1]
    leader.is_active = True
    leader.save(update_fields=("password", "is_active"))

    community, _ = Community.objects.get_or_create(
        province="kigali",
        district="Test District",
        sector="Test Sector",
        cell="Test Cell",
        village="Test Village",
    )
    UserProfile.objects.update_or_create(
        user=leader,
        defaults={
            "role": "leader",
            "leader_type": "village",
            "community": community,
            "province": "kigali",
            "district": "Test District",
            "sector": "Test Sector",
            "cell": "Test Cell",
            "village": "Test Village",
            "is_approved": True,
        },
    )
    community.leader = leader
    community.save(update_fields=("leader",))

    volunteer, _ = User.objects.get_or_create(
        username=VOLUNTEER[0],
        defaults={
            "first_name": "Test",
            "last_name": "Volunteer",
            "email": "test-volunteer@example.invalid",
            "password": VOLUNTEER[1],
            "is_active": True,
        },
    )
    volunteer.password = VOLUNTEER[1]
    volunteer.is_active = True
    volunteer.save(update_fields=("password", "is_active"))
    UserProfile.objects.update_or_create(
        user=volunteer,
        defaults={"role": "volunteer", "is_approved": False},
    )
    VolunteerProfile.objects.get_or_create(
        user=volunteer,
        defaults={"community": community},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("coordinator", "0010_umugandajournal_homepage_photo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_test_accounts, migrations.RunPython.noop),
    ]
