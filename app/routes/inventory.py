from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.inventory import Inventory
from app.models.stock_ledger import StockLedger
from app.models.product import Product
from app.utils.decorators import permission_required
from app.services.inventory.inventory_service import InventoryService
from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, TextAreaField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange

inventory_bp = Blueprint("inventory", __name__, template_folder="../templates/inventory")


class StockAdjustmentForm(FlaskForm):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    quantity = FloatField("Adjustment Quantity", validators=[DataRequired()])
    reason = TextAreaField("Reason/Notes", validators=[DataRequired()])
    submit = SubmitField("Apply Adjustment")


class StockTransferForm(FlaskForm):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    quantity = FloatField("Transfer Quantity", validators=[DataRequired(), NumberRange(min=0.01, message="Must transfer positive quantity")])
    to_warehouse = StringField("To Warehouse", validators=[DataRequired()])
    to_location = StringField("To Location", validators=[DataRequired()])
    submit = SubmitField("Execute Transfer")


@inventory_bp.route("/")
@login_required
@permission_required("view_inventory")
def stock_view():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    query = Inventory.query.join(Product)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))
    inventory = query.order_by(Product.name).paginate(page=page, per_page=20)
    
    # Calculate summary counts for dashboard metrics
    total_stock_items = Inventory.query.count()
    low_stock_items = Inventory.query.filter(
        Inventory.on_hand_qty <= Inventory.product.has(Product.safety_stock)
    ).count()
    
    # Calculate total stock value
    total_value = sum(
        (inv.on_hand_qty * inv.product.cost_price)
        for inv in Inventory.query.all()
        if inv.product
    )

    return render_template(
        "inventory/stock.html",
        inventory=inventory,
        search=search,
        total_stock_items=total_stock_items,
        low_stock_items=low_stock_items,
        total_value=total_value
    )


@inventory_bp.route("/ledger")
@login_required
@permission_required("view_inventory")
def ledger_view():
    page = request.args.get("page", 1, type=int)
    product_id = request.args.get("product_id", type=int)
    query = StockLedger.query
    if product_id:
        query = query.filter_by(product_id=product_id)
    entries = query.order_by(StockLedger.created_at.desc()).paginate(
        page=page, per_page=50
    )
    products = Product.query.order_by(Product.name).all()
    return render_template(
        "inventory/ledger.html", entries=entries, products=products
    )


@inventory_bp.route("/low-stock")
@login_required
@permission_required("view_inventory")
def low_stock():
    low_items = (
        db.session.query(Inventory)
        .join(Product)
        .filter(Inventory.on_hand_qty <= Product.safety_stock)
        .all()
    )
    return render_template("inventory/low_stock.html", items=low_items)


@inventory_bp.route("/adjust", methods=["GET", "POST"])
@login_required
@permission_required("adjust_inventory")
def adjust_stock():
    form = StockAdjustmentForm()
    form.product_id.choices = [
        (p.id, f"{p.name} ({p.sku})")
        for p in Product.query.filter_by(is_active=True).order_by(Product.name).all()
    ]
    if form.validate_on_submit():
        product_id = form.product_id.data
        quantity = form.quantity.data
        reason = form.reason.data
        
        success, result = InventoryService.adjust_stock(
            product_id=product_id,
            quantity=quantity,
            reason=reason,
            user_id=current_user.id
        )
        if success:
            flash(f"Stock adjusted successfully. Reason: {reason}", "success")
            return redirect(url_for("inventory.stock_view"))
        else:
            flash(f"Adjustment failed: {result}", "danger")
            
    return render_template("inventory/adjust.html", form=form)


@inventory_bp.route("/transfer", methods=["GET", "POST"])
@login_required
@permission_required("adjust_inventory")
def stock_transfer():
    form = StockTransferForm()
    inventories = Inventory.query.join(Product).filter(Product.is_active == True).order_by(Product.name).all()
    form.product_id.choices = [
        (i.product_id, f"{i.product.name} ({i.product.sku}) - {i.free_to_use_qty} pcs available at {i.warehouse}:{i.location}")
        for i in inventories
    ]
    if form.validate_on_submit():
        product_id = form.product_id.data
        quantity = form.quantity.data
        to_wh = form.to_warehouse.data
        to_loc = form.to_location.data
        
        inv = Inventory.query.filter_by(product_id=product_id).first()
        if not inv:
            flash("Inventory record not found.", "danger")
            return redirect(url_for("inventory.stock_transfer"))
            
        if inv.free_to_use_qty < quantity:
            flash(f"Insufficient stock: {inv.free_to_use_qty} available, {quantity} requested.", "danger")
            return redirect(url_for("inventory.stock_transfer"))
            
        before_qty = inv.on_hand_qty
        from_wh = inv.warehouse
        from_loc = inv.location
        
        # Move entire product warehouse location state
        inv.warehouse = to_wh
        inv.location = to_loc
        db.session.commit()
        
        from app.services.inventory.ledger_service import LedgerService
        notes = f"Transferred from {from_wh}:{from_loc} to {to_wh}:{to_loc} (Qty: {quantity})"
        LedgerService.record_movement(
            product_id=product_id,
            movement_type="transfer",
            quantity=0.0,
            before_qty=before_qty,
            after_qty=before_qty,
            reference_type="transfer",
            notes=notes,
            user_id=current_user.id
        )
        flash(notes, "success")
        return redirect(url_for("inventory.stock_view"))
        
    return render_template("inventory/transfer.html", form=form)
