import base64
import hashlib
import uuid

password_iterations = 100000
password_key_length = 64
password_hash_name = 'sha256'
password_salt = base64.urlsafe_b64encode(uuid.uuid4().bytes)


def hash_password(password):
    password = password.encode("utf-8")

    return hashlib.pbkdf2_hmac(
        hash_name=password_hash_name,
        password=password,
        salt=password_salt,
        iterations=password_iterations,
        dklen=password_key_length
    )


def hash_prompt(prompt):
    return str(hashlib.md5(prompt.encode("utf-8")))
