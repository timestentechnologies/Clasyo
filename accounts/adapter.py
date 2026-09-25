import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from django.core.exceptions import MultipleObjectsReturned
from django.contrib.sites.models import Site
from decouple import config

logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Robust social account adapter that prevents templates from crashing
    with SocialApp.DoesNotExist when a new database is deployed.
    """

    def get_app(self, request, provider, client_id=None):
        try:
            return super().get_app(request, provider=provider, client_id=client_id)
        except MultipleObjectsReturned:
            apps = self.list_apps(request, provider=provider, client_id=client_id)
            return apps[0]
        except (SocialApp.DoesNotExist, Exception):
            client_id_val = config(
                'GOOGLE_CLIENT_ID',
                default='172325405905909-ktr45ssgqk8rev730pjv0qbgimr8q54j.apps.googleusercontent.com'
            )
            secret_val = config('GOOGLE_CLIENT_SECRET', default='placeholder-secret')
            try:
                app, _ = SocialApp.objects.using('default').get_or_create(
                    provider=provider,
                    defaults={
                        'name': f'{provider.title()} Web Client',
                        'client_id': client_id_val,
                        'secret': secret_val,
                    }
                )
                current_site = Site.objects.using('default').first()
                if current_site and not app.sites.filter(id=current_site.id).exists():
                    app.sites.add(current_site)
                return app
            except Exception as e:
                logger.warning(f"Could not persist fallback SocialApp: {e}")
                return SocialApp(
                    provider=provider,
                    name=f'{provider.title()} Web Client',
                    client_id=client_id_val,
                    secret=secret_val,
                )
