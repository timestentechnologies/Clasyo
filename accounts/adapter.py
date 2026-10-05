import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from allauth.exceptions import ImmediateHttpResponse
from django.core.exceptions import MultipleObjectsReturned
from django.contrib import messages
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Robust social account adapter that dynamically integrates with
    GlobalGoogleAuthConfiguration, prevents crashes, automatically links verified
    Google accounts, and tags user.auth_provider = 'google'.
    """

    def get_app(self, request, provider, client_id=None):
        if provider == 'google':
            try:
                from superadmin.models import GlobalGoogleAuthConfiguration

                auth_cfg = (
                    GlobalGoogleAuthConfiguration.objects
                    .using('default')
                    .first()
                )

                if auth_cfg and auth_cfg.client_id and auth_cfg.client_secret:
                    app = auth_cfg.sync_to_social_app()

                    if app:
                        return app

            except Exception as e:
                logger.warning(
                    f"Could not load GlobalGoogleAuthConfiguration: {e}"
                )

        try:
            return super().get_app(
                request,
                provider=provider,
                client_id=client_id
            )

        except MultipleObjectsReturned:
            apps = self.list_apps(
                request,
                provider=provider,
                client_id=client_id
            )

            return apps[0]

        except Exception as e:
            logger.error(
                f"SocialApp for provider '{provider}' "
                f"could not be loaded from database: {e}"
            )

            raise SocialApp.DoesNotExist(
                f"No active database configuration found for {provider}"
            )

    def pre_social_login(self, request, sociallogin):
        """
        Handle checks and auto-linking when user attempts social login.
        """

        # 1. Check if Google Auth is enabled
        if sociallogin.account.provider == 'google':
            try:
                from superadmin.models import GlobalGoogleAuthConfiguration

                auth_cfg = (
                    GlobalGoogleAuthConfiguration.objects
                    .using('default')
                    .first()
                )

                if auth_cfg and not auth_cfg.is_active:
                    messages.error(
                        request,
                        'Google Sign-In is currently disabled '
                        'by system administrator.'
                    )

                    raise ImmediateHttpResponse(
                        redirect('frontend:home')
                    )

            except ImmediateHttpResponse:
                raise

            except Exception as e:
                logger.warning(
                    f"Error checking google auth active status: {e}"
                )

        # 2. Check if a user with matching email already exists
        email = sociallogin.account.extra_data.get('email')

        if (
            not email
            and hasattr(sociallogin, 'user')
            and sociallogin.user
        ):
            email = sociallogin.user.email

        from accounts.models import User

        existing_user = None

        if email:
            existing_user = (
                User.objects
                .using('default')
                .filter(email__iexact=email)
                .first()
            )

        action = request.session.get(
            'google_auth_action',
            'login'
        )

        # 3. If user intended to LOGIN but account does not exist,
        # reject with a clear error.
        if (
            action == 'login'
            and not existing_user
            and not sociallogin.is_existing
        ):
            messages.error(
                request,
                f"No account exists with Google email "
                f"({email or 'provided'}). Please click "
                f"'Start Free Trial' to register your institution."
            )

            request.session.pop(
                'google_auth_action',
                None
            )

            raise ImmediateHttpResponse(
                redirect('frontend:home')
            )

        # 4. Connect or update an existing user
        if existing_user:
            if not sociallogin.is_existing:
                sociallogin.connect(
                    request,
                    existing_user
                )

            if getattr(
                existing_user,
                'auth_provider',
                ''
            ) != 'both':
                existing_user.auth_provider = (
                    'both'
                    if existing_user.has_usable_password()
                    else 'google'
                )

            existing_user.is_verified = True

            existing_user.save(
                using='default',
                update_fields=[
                    'auth_provider',
                    'is_verified'
                ]
            )

        # 5. New Google user
        else:
            # IMPORTANT:
            # Do not save the new user here.
            #
            # During pre_social_login(), a brand-new social user
            # does not have a primary key yet. Calling:
            #
            #     save(update_fields=[...])
            #
            # would cause:
            #
            #     ValueError:
            #     Cannot force an update in save() with no primary key.
            #
            # allauth will create the user later through save_user().
            if (
                sociallogin.user
                and hasattr(
                    sociallogin.user,
                    'auth_provider'
                )
            ):
                sociallogin.user.auth_provider = 'google'
                sociallogin.user.is_verified = True

        # Clear the action after processing
        request.session.pop(
            'google_auth_action',
            None
        )

    def save_user(self, request, sociallogin, form=None):
        """
        Mark a newly created social user as a Google-authenticated user.
        """

        # allauth creates and saves the user here.
        user = super().save_user(
            request,
            sociallogin,
            form
        )

        user.auth_provider = 'google'
        user.is_verified = True

        if not user.role:
            user.role = 'admin'

        # At this point the user has already been created by allauth,
        # so it has a primary key and update_fields is safe.
        user.save(
            using='default',
            update_fields=[
                'auth_provider',
                'is_verified',
                'role'
            ]
        )

        return user