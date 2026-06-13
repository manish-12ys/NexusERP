from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder
from app.forms.purchase_forms import VendorForm
from app.utils.decorators import permission_required

vendors_bp = Blueprint("vendors", __name__, template_folder="../templates/vendors")


@vendors_bp.route("/")
@login_required
@permission_required("view_purchases")
def list_vendors():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str)
    
    query = Vendor.query
    if search:
        query = query.filter(
            Vendor.name.ilike(f"%{search}%") |
            Vendor.email.ilike(f"%{search}%") |
            Vendor.city.ilike(f"%{search}%")
        )
        
    vendors = query.order_by(Vendor.name).paginate(page=page, per_page=20)
    return render_template("vendors/list.html", vendors=vendors, search=search)


@vendors_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("create_purchases")
def create_vendor():
    form = VendorForm()
    if form.validate_on_submit():
        vendor = Vendor(
            name=form.name.data,
            contact_person=form.contact_person.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            city=form.city.data,
            state=form.state.data,
            pincode=form.pincode.data,
            gst_number=form.gst_number.data,
            payment_terms=form.payment_terms.data,
            lead_time_days=form.lead_time_days.data,
        )
        db.session.add(vendor)
        db.session.commit()
        flash(f"Vendor '{vendor.name}' created.", "success")
        return redirect(url_for("vendors.list_vendors"))
    return render_template("vendors/create.html", form=form)


@vendors_bp.route("/<int:id>")
@login_required
@permission_required("view_purchases")
def view_vendor(id):
    vendor = Vendor.query.get_or_404(id)
    orders = vendor.purchase_orders.order_by(PurchaseOrder.created_at.desc()).all()
    
    total_spent = sum(o.total_amount for o in orders if o.status in ("confirmed", "received", "closed"))
    total_orders = len(orders)
    
    return render_template(
        "vendors/view.html",
        vendor=vendor,
        orders=orders,
        total_spent=total_spent,
        total_orders=total_orders
    )


@vendors_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("create_purchases")
def edit_vendor(id):
    vendor = Vendor.query.get_or_404(id)
    form = VendorForm(obj=vendor)
    if form.validate_on_submit():
        form.populate_obj(vendor)
        db.session.commit()
        flash(f"Vendor '{vendor.name}' updated.", "success")
        return redirect(url_for("vendors.view_vendor", id=vendor.id))
    return render_template("vendors/edit.html", form=form, vendor=vendor)


@vendors_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@permission_required("create_purchases")
def delete_vendor(id):
    vendor = Vendor.query.get_or_404(id)
    if vendor.purchase_orders.count() > 0:
        flash(f"Cannot delete vendor '{vendor.name}' because they have associated purchase orders.", "danger")
    else:
        db.session.delete(vendor)
        db.session.commit()
        flash(f"Vendor '{vendor.name}' deleted successfully.", "success")
    return redirect(url_for("vendors.list_vendors"))
