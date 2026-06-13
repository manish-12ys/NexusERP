from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.customer import Customer
from app.models.sales_order import SalesOrder
from app.forms.sales_forms import CustomerForm
from app.utils.decorators import permission_required

customers_bp = Blueprint("customers", __name__, template_folder="../templates/customers")


@customers_bp.route("/")
@login_required
@permission_required("view_sales")
def list_customers():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str)
    
    query = Customer.query
    if search:
        query = query.filter(
            Customer.name.ilike(f"%{search}%") |
            Customer.email.ilike(f"%{search}%") |
            Customer.city.ilike(f"%{search}%")
        )
        
    customers = query.order_by(Customer.name).paginate(page=page, per_page=20)
    return render_template("customers/list.html", customers=customers, search=search)


@customers_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("create_sales")
def create_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(
            name=form.name.data,
            contact_person=form.contact_person.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            city=form.city.data,
            state=form.state.data,
            pincode=form.pincode.data,
            gst_number=form.gst_number.data,
            credit_limit=form.credit_limit.data,
        )
        db.session.add(customer)
        db.session.commit()
        flash(f"Customer '{customer.name}' created.", "success")
        return redirect(url_for("customers.list_customers"))
    return render_template("customers/create.html", form=form)


@customers_bp.route("/<int:id>")
@login_required
@permission_required("view_sales")
def view_customer(id):
    customer = Customer.query.get_or_404(id)
    orders = customer.sales_orders.order_by(SalesOrder.created_at.desc()).all()
    
    total_spent = sum(o.total_amount for o in orders if o.status in ("confirmed", "delivered", "closed"))
    total_orders = len(orders)
    
    return render_template(
        "customers/view.html",
        customer=customer,
        orders=orders,
        total_spent=total_spent,
        total_orders=total_orders
    )


@customers_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("create_sales")
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        form.populate_obj(customer)
        db.session.commit()
        flash(f"Customer '{customer.name}' updated.", "success")
        return redirect(url_for("customers.view_customer", id=customer.id))
    return render_template("customers/edit.html", form=form, customer=customer)


@customers_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@permission_required("create_sales")
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    if customer.sales_orders.count() > 0:
        flash(f"Cannot delete customer '{customer.name}' because they have associated sales orders.", "danger")
    else:
        db.session.delete(customer)
        db.session.commit()
        flash(f"Customer '{customer.name}' deleted successfully.", "success")
    return redirect(url_for("customers.list_customers"))
