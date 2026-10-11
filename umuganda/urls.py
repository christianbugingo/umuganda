from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from coordinator import views as coordinator_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'media/journals/<path:file_path>',
        coordinator_views.serve_journal_media,
        name='journal_media',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [path('', include('coordinator.urls'))]