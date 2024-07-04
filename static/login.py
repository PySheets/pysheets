import constants
import ltk
import re
import state

local_storage = ltk.window.localStorage

def setup():
    ltk.find("#login-email").val(local_storage.getItem(constants.DATA_KEY_EMAIL))

    def get_data():
        return (
            {
                constants.DATA_KEY_EMAIL: ltk.find("#login-email").val(),
                constants.DATA_KEY_PASSWORD: ltk.find("#login-password").val(),
                constants.DATA_KEY_CODE: ltk.find("#login-code").val(),
            },
        )

    def handle_login(data):
        if data and not data.get(constants.DATA_KEY_STATUS) == "error":
            state.login(ltk.find("#login-email").val(), data[constants.DATA_KEY_TOKEN])
            ltk.find("#login-container").css("display", "none")
            ltk.window.location.reload()
        else:
            error("Email and password do not match our records.")
            ltk.find("#login-password-reset").css("display", "block").on("click", ltk.proxy(reset_password))


    def confirm_registration(event):
        ltk.find("#login-confirm").css("display", "none")
        ltk.find(event.target).attr('disabled', True)
        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]):
            error("The email looks invalid. Please enter a valid email.")
        elif invalid_password(data[0][constants.DATA_KEY_PASSWORD]):
            error(f"The password is too short. PySheets has a {constants.MIN_PASSWORD_LENGTH} character minimum.")
        elif invalid_code(data[0][constants.DATA_KEY_CODE]):
            error(f"This is not a valid 6-digit code. Check your email.")
        else:
            ltk.post("/confirm", data, ltk.proxy(handle_login))


    def login(event):
        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]) or invalid_password(data[0][constants.DATA_KEY_PASSWORD]):
            error("Please enter valid email/password.")
        else:
            ltk.post(f"/login", get_data(), ltk.proxy(handle_login))

    def invalid_email(email):
        return not re.match(r"^\S+@\S+\.\S+$", email)

    def invalid_password(password):
        return len(password) < constants.MIN_PASSWORD_LENGTH

    def invalid_code(code):
        return not re.match(r"^[1-9][1-9][1-9][1-9][1-9][1-9]$", code)

    def error(message):
        if not message:
            ltk.find("#login-message").css("display", "none").text(message)
        else:
            ltk.find("#login-message").css("display", "block").text(message)

    def enable_register(event):
        ltk.find("#login-title").text("Register a PySheets Account")
        ltk.find("#login-register-link").css("display", "none")
        ltk.find("#login-signin-link").css("display", "block")
        ltk.find("#login-login").css("display", "none")
        ltk.find("#login-register").css("display", "block").on("click", ltk.proxy(register))

    def enable_signin(event):
        error("")
        ltk.find("#login-title").text("Sign In to PySheets")
        ltk.find("#login-signin-link").css("display", "none")
        ltk.find("#login-register-link").css("display", "block")
        ltk.find("#login-login").css("display", "block")
        ltk.find("#login-register").css("display", "none")

    def register(event):
        def handle_register(data):
            if not data or data.get(constants.DATA_KEY_STATUS) == "error":
                error("Could not register with that email. Try signing in.")
            else:
                ltk.find("#login-code").css("display", "block")
                ltk.find("#login-login").css("display", "none")
                error("Please check your email and enter the confirmation code.")
                ltk.find("#login-confirm").css("display", "block").on("click", ltk.proxy(confirm_registration))

        ltk.find("#login-register").css("display", "none")
        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]):
            error("The email looks invalid. PySheets needs a valid email.")
        elif invalid_password(data[0][constants.DATA_KEY_PASSWORD]):
            error(f"The password is too short. PySheets has a {constants.MIN_PASSWORD_LENGTH} character minimum.")
        else:
            ltk.post("/register", data, ltk.proxy(handle_register))

    def reset_password_with_code(event):
        error("checking details...")
        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]):
            error("The email looks invalid. Please enter a valid email.")
        elif invalid_password(data[0][constants.DATA_KEY_PASSWORD]):
            error(f"The password is too short. PySheets has a {constants.MIN_PASSWORD_LENGTH} character minimum.")
        elif invalid_code(data[0][constants.DATA_KEY_CODE]):
            error(f"This is not a valid 6-digit code. Check your email.")
        else:
            ltk.post("/reset_code", data, ltk.proxy(handle_login))

    def reset_password(event):
        def handle_reset_password(event):
            error("")
            ltk.find("#login-code").css("display", "block")
            ltk.find("#login-login").css("display", "none")
            ltk.find("#login-password").val("")
            ltk.find("#login-reset").css("display", "block")
            ltk.find("#login-title").text("Change Password")

        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]):
            error("The email looks invalid. Please enter a valid email.")
        else:
            error("Resetting password...")
            ltk.find("#login-password-reset").css("display", "none")
            ltk.post("/reset", get_data(), ltk.proxy(handle_reset_password))

    ltk.find("#login-register-link").on("click", ltk.proxy(enable_register))
    ltk.find("#login-signin-link").on("click", ltk.proxy(enable_signin))
    ltk.find("#login-reset").on("click", ltk.proxy(reset_password_with_code))
    ltk.find("#login-login").on("click", ltk.proxy(login))

    if not local_storage.getItem(constants.DATA_KEY_EMAIL):
        enable_register(None)
