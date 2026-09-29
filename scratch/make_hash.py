import hashlib
import base64

password = b"ClasyoAdmin2026!"
salt = b"clasyoSuperSalt2026"
iterations = 600000

derived = hashlib.pbkdf2_hmac("sha256", password, salt, iterations)
hash_b64 = base64.b64encode(derived).decode("ascii")

django_hash = f"pbkdf2_sha256${iterations}${salt.decode('ascii')}${hash_b64}"
print("DJANGO_HASH:")
print(django_hash)
