import dotenv

ALLOWED_EXTENSIONS = set(
    dotenv.dotenv_values().get("ALLOWED_EXTENSIONS", "pdf,png,jpg,jpeg").split(",")
)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
