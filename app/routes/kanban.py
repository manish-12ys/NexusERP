from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from app.extensions import db
from app.models.work_order import WorkOrder
from app.utils.decorators import permission_required

kanban_bp = Blueprint("kanban", __name__, template_folder="../templates/manufacturing")

@kanban_bp.route("/")
@login_required
@permission_required("view_manufacturing")
def index():
    work_orders = WorkOrder.query.all()
    # Group by status
    board = {
        "pending": [],
        "in_progress": [],
        "completed": []
    }
    for wo in work_orders:
        if wo.status in board:
            board[wo.status].append(wo)
        else:
            board["pending"].append(wo)
            
    return render_template("manufacturing/kanban.html", board=board)

@kanban_bp.route("/update_status", methods=["POST"])
@login_required
@permission_required("create_manufacturing")
def update_status():
    wo_id = request.form.get("work_order_id", type=int)
    new_status = request.form.get("status")
    
    if wo_id and new_status in ["pending", "in_progress", "completed"]:
        wo = WorkOrder.query.get(wo_id)
        if wo:
            wo.status = new_status
            if new_status == "completed":
                wo.completion_percent = 100
            db.session.commit()
            flash(f"Work Order {wo.id} moved to {new_status.replace('_', ' ').title()}.", "success")
    return redirect(url_for('kanban.index'))
