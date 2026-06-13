from flask import Blueprint, render_template

landing_bp = Blueprint("landing", __name__, template_folder="../templates/landing")


@landing_bp.route("/")
def index():
    return render_template("landing.html")
