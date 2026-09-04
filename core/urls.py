from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from sga.api.seguridad import (
    CambiarPasswordView,
    LoginView,
    LogoutView,
    MFAVerificarView,
    RecuperarPasswordConfirmarView,
    RecuperarPasswordSolicitudView,
    RecuperarPasswordValidarView,
    TokenRefreshSeguroView,
)

urlpatterns = [
    path("api/auth/token/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshSeguroView.as_view(), name="token_refresh"),
    path("api/auth/mfa/verify/", MFAVerificarView.as_view(), name="mfa_verify"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/password/change/", CambiarPasswordView.as_view(), name="password_change"),
    path(
        "api/auth/password-reset/request/",
        RecuperarPasswordSolicitudView.as_view(),
        name="password_reset_request",
    ),
    path(
        "api/auth/password-reset/validate/",
        RecuperarPasswordValidarView.as_view(),
        name="password_reset_validate",
    ),
    path(
        "api/auth/password-reset/confirm/",
        RecuperarPasswordConfirmarView.as_view(),
        name="password_reset_confirm",
    ),
    path("api/", include("sga.urls")),
]

if settings.DJANGO_ADMIN_ENABLED:
    urlpatterns.insert(0, path("admin/", admin.site.urls))

if settings.API_DOCS_ENABLED:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
