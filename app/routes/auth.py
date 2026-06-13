from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.role import Role
from app.forms.auth_forms import LoginForm, RegisterForm, ProfileForm

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            user.update_login_info()
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))
        flash("Invalid username or password", "danger")
    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already exists.", "danger")
            return render_template("register.html", form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered.", "danger")
            return render_template("register.html", form=form)
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
        )
        user.set_password(form.password.data)
        default_role = Role.query.filter_by(name="Staff").first()
        if default_role:
            user.role_id = default_role.id
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        if form.password.data:
            current_user.set_password(form.password.data)
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("profile.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        username_or_email = request.form.get("username_or_email")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        if not username_or_email or not new_password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("forgot_password.html")
            
        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("forgot_password.html")
            
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            flash("Password has been reset successfully! Please log in.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("User with that username or email does not exist.", "danger")
            
    return render_template("forgot_password.html")


from app.utils.decorators import permission_required, admin_required

@auth_bp.route("/users")
@login_required
@permission_required("manage_users")
def list_users():
    users = User.query.all()
    return render_template("users.html", users=users)


@auth_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    if request.method == "POST":
        role_id = request.form.get("role_id", type=int)
        user.role_id = role_id if role_id != 0 else None
        user.is_active = "is_active" in request.form
        db.session.commit()
        flash(f"User {user.username} updated.", "success")
        return redirect(url_for("auth.list_users"))
    return render_template("edit_user.html", user=user, roles=roles)


@auth_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if not (current_user.has_permission("manage_users") or (current_user.role and current_user.role.name == "Admin")):
        abort(403)

    if request.method == "POST":
        action = request.form.get("action")
        if action == "delete_all_data":
            confirmation_code = request.form.get("confirmation_code", "").strip()
            if confirmation_code.upper() == "DELETE_ALL_DATA":
                from app.services.admin.data_service import AdminDataService
                try:
                    AdminDataService.delete_all_data_except_users()
                    flash("All business data has been deleted successfully. Users and passwords are preserved.", "success")
                except Exception as e:
                    flash(f"Error deleting data: {str(e)}", "danger")
            else:
                flash("Confirmation code is incorrect.", "danger")
            return redirect(url_for("auth.settings"))
    return render_template("settings.html")
