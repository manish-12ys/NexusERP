from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
import os
import json
from app.extensions import db
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.manufacturing_order import ManufacturingOrder
from app.models.sales_order import SalesOrder
from app.models.purchase_order import PurchaseOrder

copilot_bp = Blueprint("copilot", __name__, template_folder="../templates/copilot")

def gather_erp_context():
    # Gather key metrics for the context
    low_stock = Inventory.query.filter(Inventory.quantity_on_hand < 10).count()
    active_mos = ManufacturingOrder.query.filter(ManufacturingOrder.status == "in_progress").count()
    open_sos = SalesOrder.query.filter(SalesOrder.status == "confirmed").count()
    open_pos = PurchaseOrder.query.filter(PurchaseOrder.status == "confirmed").count()
    
    context = (
        f"You are the NexusERP AI Operations Copilot. You assist factory managers, inventory managers, and sales teams.\n"
        f"Current ERP State:\n"
        f"- Low Stock Items: {low_stock}\n"
        f"- Active Manufacturing Orders: {active_mos}\n"
        f"- Open Sales Orders: {open_sos}\n"
        f"- Open Purchase Orders: {open_pos}\n"
        f"Provide concise, professional business advice based on these metrics."
    )
    return context

@copilot_bp.route("/")
@login_required
def index():
    return render_template("copilot/index.html")

@copilot_bp.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    context = gather_erp_context()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Fallback to mock response
        response_text = f"[Mock AI - No API Key Found]\n\nBased on the current state:\nI recommend checking the {Inventory.query.filter(Inventory.quantity_on_hand < 10).count()} low stock items and fulfilling the {SalesOrder.query.filter(SalesOrder.status == 'confirmed').count()} open sales orders."
        return jsonify({"response": response_text})

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{context}\n\nUser: {user_message}"
        )
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"response": f"[Error connecting to AI]: {str(e)}"}), 500
