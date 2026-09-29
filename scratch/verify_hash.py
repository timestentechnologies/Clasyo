from django.conf import settings

if not settings.configured:
    settings.configure()

from django.contrib.auth.hashers import check_password

h = "pbkdf2_sha256$600000$clasyoSuperSalt2026$Xofgr/Orv7ZOcsw83UPmTELMlJSB6xsq/wDEAvenjgM="
valid = check_password("ClasyoAdmin2026!", h)
print(f"VERIFICATION RESULT: {valid}")
