from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.inventory import Inventory
from app.models.stock_ledger import StockLedger
from app.models.product import Product
from app.models.stock_transfer import StockTransfer
from app.models.warehouse import Warehouse, Location
from app.utils.decorators import permission_required
from app.services.inventory.inventory_service import InventoryService
from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, TextAreaField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange

inventory_bp = Blueprint("inventory", __name__, template_folder="../templates/inventory")


class StockAdjustmentForm(FlaskForm):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    warehouse = StringField("Warehouse", default="Main", validators=[DataRequired()])
    location = StringField("Location/Phase", default="Default", validators=[DataRequired()])
    quantity = FloatField("Adjustment Quantity", validators=[DataRequired()])
    reason = TextAreaField("Reason/Notes", validators=[DataRequired()])
    submit = SubmitField("Apply Adjustment")


class StockTransferForm(FlaskForm):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    from_warehouse = StringField("From Warehouse", default="Main", validators=[DataRequired()])
    from_location = StringField("From Location/Phase", default="Default", validators=[DataRequired()])
    quantity = FloatField("Transfer Quantity", validators=[DataRequired(), NumberRange(min=0.01, message="Must transfer positive quantity")])
    to_warehouse = StringField("To Warehouse", validators=[DataRequired()])
    to_location = StringField("To Location/Phase", validators=[DataRequired()])
    source_inventory_id = SelectField("Source Inventory", coerce=int, validators=[], validate_choice=False)
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
        warehouse = form.warehouse.data.strip()
        location = form.location.data.strip()
        
        success, result = InventoryService.adjust_stock(
            product_id=product_id,
            quantity=quantity,
            reason=reason,
            user_id=current_user.id,
            warehouse=warehouse,
            location=location
        )
        if success:
            flash(f"Stock adjusted successfully at {warehouse} ({location}). Reason: {reason}", "success")
            return redirect(url_for("inventory.stock_view"))
        else:
            flash(f"Adjustment failed: {result}", "danger")
            
    # Fetch warehouses and locations from database configuration as source of truth
    whs = Warehouse.query.order_by(Warehouse.name).all()
    warehouse_json_map = {w.name: sorted([l.name for l in w.locations]) for w in whs}

    return render_template("inventory/adjust.html", form=form, warehouse_map=warehouse_json_map)


@inventory_bp.route("/transfer", methods=["GET", "POST"])
@login_required
@permission_required("adjust_inventory")
def stock_transfer():
    form = StockTransferForm()
    
    # Populate product choices
    active_products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    form.product_id.choices = [(p.id, f"{p.name} ({p.sku})") for p in active_products]
    
    # Populate source_inventory_id choices for backward compatibility
    inventories = Inventory.query.join(Product).filter(Product.is_active == True).order_by(Product.name).all()
    form.source_inventory_id.choices = [
        (i.id, f"{i.product.name} ({i.product.sku}) — {i.free_to_use_qty} pcs available at {i.warehouse} ({i.location})")
        for i in inventories if i.free_to_use_qty > 0
    ]
    if not form.source_inventory_id.choices:
        form.source_inventory_id.choices = [(0, "No stock available anywhere")]
    else:
        form.source_inventory_id.choices.insert(0, (0, "Select Source Inventory (optional)"))

    # Check for backward compatibility post
    if request.method == "POST":
        src_inv_id = request.form.get("source_inventory_id")
        if src_inv_id and src_inv_id.isdigit() and int(src_inv_id) > 0:
            inv = Inventory.query.get(int(src_inv_id))
            if inv:
                if not request.form.get("product_id") or not form.product_id.data:
                    form.product_id.data = inv.product_id
                if not request.form.get("from_warehouse") or not form.from_warehouse.data:
                    form.from_warehouse.data = inv.warehouse
                if not request.form.get("from_location") or not form.from_location.data:
                    form.from_location.data = inv.location

    if form.validate_on_submit():
        product_id = form.product_id.data
        quantity = form.quantity.data
        from_wh = form.from_warehouse.data.strip()
        from_loc = form.from_location.data.strip()
        to_wh = form.to_warehouse.data.strip()
        to_loc = form.to_location.data.strip()
        
        # Check source inventory
        inv = Inventory.query.filter_by(
            product_id=product_id,
            warehouse=from_wh,
            location=from_loc
        ).first()
        
        if not inv:
            flash(f"Source inventory record not found at {from_wh} ({from_loc}).", "danger")
            return redirect(url_for("inventory.stock_transfer"))
            
        if inv.free_to_use_qty < quantity:
            flash(f"Insufficient stock: {inv.free_to_use_qty} available at {from_wh} ({from_loc}), {quantity} requested.", "danger")
            return redirect(url_for("inventory.stock_transfer"))
            
        if from_wh == to_wh and from_loc == to_loc:
            flash("Source and destination warehouse/location cannot be identical.", "danger")
            return redirect(url_for("inventory.stock_transfer"))
            
        from app.services.inventory.transfer_service import TransferService
        transfer, err = TransferService.create_transfer(
            product_id=product_id,
            quantity=quantity,
            from_wh=from_wh,
            from_loc=from_loc,
            to_wh=to_wh,
            to_loc=to_loc,
            notes=f"Manually executed stock transfer by {current_user.full_name or current_user.username}",
            user_id=current_user.id
        )
        if transfer:
            success, exec_err = TransferService.execute_transfer(transfer.id, user_id=current_user.id)
            if success:
                flash(f"Executed stock transfer of {quantity} {inv.product.unit_of_measure or 'pcs'} from {from_wh}:{from_loc} to {to_wh}:{to_loc}.", "success")
                return redirect(url_for("inventory.stock_view"))
            else:
                flash(f"Execution failed: {exec_err}", "danger")
        else:
            flash(f"Creation failed: {err}", "danger")
            
    # Fetch warehouses and locations from database configuration as source of truth
    whs = Warehouse.query.order_by(Warehouse.name).all()
    warehouse_json_map = {w.name: sorted([l.name for l in w.locations]) for w in whs}

    # Build product_stock_map: product_id -> list of {warehouse, location, qty}
    product_stock_map = {}
    for i in inventories:
        if i.free_to_use_qty > 0:
            product_stock_map.setdefault(i.product_id, []).append({
                "warehouse": i.warehouse,
                "location": i.location,
                "qty": i.free_to_use_qty
            })

    return render_template(
        "inventory/transfer.html", 
        form=form, 
        warehouse_map=warehouse_json_map,
        product_stock_map=product_stock_map
    )


@inventory_bp.route("/transfers")
@login_required
@permission_required("view_inventory")
def list_transfers():
    page = request.args.get("page", 1, type=int)
    transfers = StockTransfer.query.order_by(StockTransfer.created_at.desc()).paginate(page=page, per_page=30)
    return render_template("inventory/transfers.html", transfers=transfers)


@inventory_bp.route("/warehouses")
@login_required
@permission_required("view_inventory")
def warehouses_view():
    # Sync database configuration tables with existing inventory records
    InventoryService.sync_warehouses_and_locations()

    # Query all warehouses ordered by name
    all_whs = Warehouse.query.order_by(Warehouse.name).all()

    warehouses_data = []
    for wh in all_whs:
        # Get all inventories for this warehouse name
        items = Inventory.query.filter_by(warehouse=wh.name).all()
        unique_products = len(set(i.product_id for i in items))
        total_on_hand = sum(i.on_hand_qty for i in items)
        
        # Build locations mapping
        locations_data = {}
        # Pre-populate with all defined locations for this warehouse
        for loc in wh.locations:
            locations_data[loc.name] = []
            
        # Group inventory items under locations
        for item in items:
            locations_data.setdefault(item.location, []).append(item)
            
        warehouses_data.append({
            "id": wh.id,
            "name": wh.name,
            "code": wh.code,
            "address": wh.address,
            "is_active": wh.is_active,
            "unique_products": unique_products,
            "total_on_hand": total_on_hand,
            "locations": locations_data
        })

    # Get inter-location replenishment recommendations
    recommendations = InventoryService.get_inter_location_replenishment_recommendations()

    return render_template(
        "inventory/warehouses.html",
        warehouses=warehouses_data,
        recommendations=recommendations
    )


@inventory_bp.route("/warehouses/create", methods=["POST"])
@login_required
@permission_required("adjust_inventory")
def create_warehouse():
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip()
    address = request.form.get("address", "").strip()
    
    if not name or not code:
        flash("Warehouse name and code are required.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    existing_name = Warehouse.query.filter_by(name=name).first()
    if existing_name:
        flash(f"Warehouse with name '{name}' already exists.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    existing_code = Warehouse.query.filter_by(code=code).first()
    if existing_code:
        flash(f"Warehouse with code '{code}' already exists.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    wh = Warehouse(name=name, code=code, address=address)
    db.session.add(wh)
    db.session.commit()
    
    default_loc = Location(warehouse_id=wh.id, name="Default")
    db.session.add(default_loc)
    db.session.commit()
    
    flash(f"Warehouse '{name}' created successfully with 'Default' location.", "success")
    return redirect(url_for("inventory.warehouses_view"))


@inventory_bp.route("/warehouses/update", methods=["POST"])
@login_required
@permission_required("adjust_inventory")
def update_warehouse():
    warehouse_id = request.form.get("warehouse_id", type=int)
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip()
    address = request.form.get("address", "").strip()
    
    wh = Warehouse.query.get(warehouse_id)
    if not wh:
        flash("Warehouse not found.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    if not name or not code:
        flash("Warehouse name and code are required.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    existing_name = Warehouse.query.filter(Warehouse.id != warehouse_id, Warehouse.name == name).first()
    if existing_name:
        flash(f"Warehouse with name '{name}' already exists.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    existing_code = Warehouse.query.filter(Warehouse.id != warehouse_id, Warehouse.code == code).first()
    if existing_code:
        flash(f"Warehouse with code '{code}' already exists.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    old_name = wh.name
    wh.name = name
    wh.code = code
    wh.address = address
    db.session.commit()
    
    if old_name != name:
        InventoryService.cascade_warehouse_rename(old_name, name)
        flash(f"Warehouse renamed from '{old_name}' to '{name}'. All associated inventories and documents updated.", "success")
    else:
        flash(f"Warehouse '{name}' updated successfully.", "success")
        
    return redirect(url_for("inventory.warehouses_view"))


@inventory_bp.route("/warehouses/location/create", methods=["POST"])
@login_required
@permission_required("adjust_inventory")
def create_location():
    warehouse_id = request.form.get("warehouse_id", type=int)
    name = request.form.get("name", "").strip()
    
    wh = Warehouse.query.get(warehouse_id)
    if not wh:
        flash("Warehouse not found.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    if not name:
        flash("Location/Phase name is required.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    existing = Location.query.filter_by(warehouse_id=warehouse_id, name=name).first()
    if existing:
        flash(f"Location '{name}' already exists in warehouse '{wh.name}'.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    loc = Location(warehouse_id=warehouse_id, name=name)
    db.session.add(loc)
    db.session.commit()
    
    flash(f"Location '{name}' created successfully under warehouse '{wh.name}'.", "success")
    return redirect(url_for("inventory.warehouses_view"))


@inventory_bp.route("/warehouses/location/update", methods=["POST"])
@login_required
@permission_required("adjust_inventory")
def update_location():
    warehouse_id = request.form.get("warehouse_id", type=int)
    old_name = request.form.get("old_name", "").strip()
    new_name = request.form.get("new_name", "").strip()
    
    wh = Warehouse.query.get(warehouse_id)
    if not wh:
        flash("Warehouse not found.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    if not old_name or not new_name:
        flash("Old and new location names are required.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    loc = Location.query.filter_by(warehouse_id=warehouse_id, name=old_name).first()
    if not loc:
        flash(f"Location '{old_name}' not found under warehouse '{wh.name}'.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    if old_name == new_name:
        flash("No changes made as old and new name are identical.", "info")
        return redirect(url_for("inventory.warehouses_view"))
        
    existing = Location.query.filter_by(warehouse_id=warehouse_id, name=new_name).first()
    if existing:
        flash(f"Location '{new_name}' already exists under warehouse '{wh.name}'.", "danger")
        return redirect(url_for("inventory.warehouses_view"))
        
    loc.name = new_name
    db.session.commit()
    
    InventoryService.cascade_location_rename(wh.name, old_name, new_name)
    flash(f"Location renamed from '{old_name}' to '{new_name}' under warehouse '{wh.name}'. All records updated.", "success")
    return redirect(url_for("inventory.warehouses_view"))



@inventory_bp.route("/warehouses/replenish", methods=["POST"])
@login_required
@permission_required("adjust_inventory")
def execute_replenishment():
    product_id = request.form.get("product_id", type=int)
    warehouse = request.form.get("warehouse")
    from_location = request.form.get("from_location")
    to_location = request.form.get("to_location")
    quantity = request.form.get("quantity", type=float)

    if not all([product_id, warehouse, from_location, to_location, quantity]):
        flash("Invalid replenishment request parameters.", "danger")
        return redirect(url_for("inventory.warehouses_view"))

    prod = Product.query.get(product_id)
    if not prod:
        flash("Product not found.", "danger")
        return redirect(url_for("inventory.warehouses_view"))

    # Create and execute the transfer
    from app.services.inventory.transfer_service import TransferService
    transfer, err = TransferService.create_transfer(
        product_id=product_id,
        quantity=quantity,
        from_wh=warehouse,
        from_loc=from_location,
        to_wh=warehouse,
        to_loc=to_location,
        notes=f"Auto-replenishment from {from_location} to {to_location} in warehouse {warehouse}.",
        user_id=current_user.id
    )

    if transfer:
        success, exec_err = TransferService.execute_transfer(transfer.id, user_id=current_user.id)
        if success:
            flash(f"Successfully replenished {quantity} {prod.unit_of_measure or 'units'} of {prod.name} from {from_location} to {to_location} in {warehouse}.", "success")
        else:
            flash(f"Failed to execute replenishment transfer: {exec_err}", "danger")
    else:
        flash(f"Failed to create replenishment transfer: {err}", "danger")

    return redirect(url_for("inventory.warehouses_view"))


