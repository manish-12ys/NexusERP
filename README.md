# NexusERP

> **Intelligent Demand-to-Delivery Manufacturing Operating System** built for discrete and furniture manufacturing operations.

NexusERP is a modern Flask-based enterprise resource planning platform engineered specifically to solve the coordination and visibility gaps commonly found in factory operations. The default demo data is modeled around **Shiv Furniture**, resolving core coordination friction points across sales, inventory, purchasing, and production.

---

## 🚀 Key Features

*   **Factory Control Center**: A unified management dashboard providing real-time visibility into open orders, inventory valuations, active shortages, delayed operations, and manufacturing progress.
*   **Unified Product & Inventory Hub**: Clean tracking of product master records across components (raw materials), work-in-progress (semi-finished), and end products (finished goods), using precise inventory states (`On-Hand`, `Reserved`, and `Free to Use`).
*   **Smart Sales & Reservation**: Sales order workflow enforcing automatic inventory reservation upon confirmation, combined with a **Delivery Risk Predictor** (`Low`, `Medium`, `High` risk metrics) to prevent overpromising delivery times.
*   **Point of Sale (POS) Terminal**: An interactive retail checkout system supporting cashier session management (opening/closing cash balances), real-time inventory validation, tax calculation, and instant receipt generation.
*   **Procurement Automation (Smart Purchasing)**: An auto-replenishment engine evaluating Make-to-Stock (MTS) and Make-to-Order (MTO) rules, identifying material shortages, suggesting optimal suppliers, and creating Purchase/Manufacturing Orders.
*   **Bill of Materials (Product Recipes)**: A multi-level costing and recipe structure defining the component list and sequence of operations (e.g., cutting, assembly, painting, packaging) required for each end product.
*   **Kanban Production Board**: A visual shop-floor pipeline mapping manufacturing orders to work centers and tracking real-time status transitions.
*   **Operational Audit Trail**: Comprehensive traceability tracking user actions, entity creation, edits, and state transitions with historical value changes.
*   **AI Operations Copilot**: An intelligent assistant integrated with Google Gemini to query factory status, identify bottlenecks, and suggest next actions in natural language.

---

## 🛠️ Technology Stack

| Layer | Technologies | Key Details |
| :--- | :--- | :--- |
| **Backend** | Python 3.14, Flask 3.1 | Modular design inspired by Odoo module architecture |
| **Database** | SQLAlchemy ORM, Flask-Migrate, SQLite | SQLite database localized in `instance/` for local dev |
| **Security & Auth**| Flask-Login, Flask-Bcrypt | Role-Based Access Control (RBAC) with permission matrix |
| **Forms & Validation**| Flask-WTF, WTForms | Strict form validation, CSRF protection |
| **Frontend UI** | Jinja Templates, Bootstrap 5.3 | Responsive custom dashboard styling |
| **Charts** | Chart.js | Interactive real-time metrics visualizations |
| **AI Integration** | Google Gemini SDK (`google-genai`) | Intelligent contextual business analytics |
| **Testing** | Pytest | Isolated test database and mock configurations |
| **Packaging** | `pyproject.toml`, `uv` lockfile | Modern Python packaging and dependency management |

---

## 📂 Repository Structure

```text
NexusERP/
├── app/
│   ├── models/        # SQLAlchemy database models & schemas
│   ├── routes/        # Flask Blueprints managing endpoint routes
│   ├── services/      # Modular business logic engines (Auth, Inventory, AI, etc.)
│   ├── forms/         # WTForms validation classes
│   ├── templates/     # UI HTML pages & layouts (Jinja templates)
│   ├── static/        # Assets: CSS stylesheets, JS logic, diagrams
│   ├── utils/         # Helper functions, decorators, and system constants
│   └── seed/          # Database seeding scripts and demo catalog
├── migrations/        # Database migration schemas (Alembic)
├── tests/             # Comprehensive Pytest suites
├── instance/          # Local SQLite storage path (excluded from Git)
├── app.py             # Entrypoint script for development environment
├── config.py          # Configuration environments (Development, Testing)
├── pyproject.toml     # Poetry/uv package definitions
└── requirements.txt   # Backup pip dependencies list
```

---

## ⚡ Quick Start Guide

### 1. Install `uv` and Set Up Environment

This project recommends [uv](https://github.com/astral-sh/uv), an extremely fast Python package installer and resolver.

#### Install `uv`

*   **macOS / Linux**:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
*   **Windows (PowerShell - Run as Administrator)**:
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
*   **Alternative (via pip)**:
    ```bash
    pip install uv
    ```

#### Set Up Environment

Initialize the virtual environment and install dependencies:

Using **`uv`** (Recommended):
```bash
uv sync
```

Using standard **`pip`**:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:
```env
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///instance/nexuserp.db
GEMINI_API_KEY=your_gemini_api_key_here
```
> [!NOTE]
> If `GEMINI_API_KEY` is omitted, the AI Operations Copilot runs in mock response mode for offline testing.

### 3. Initialize and Seed the Database

Prepare the database schemas and populate the Shiv Furniture demo dataset:
```bash
# Using uv
uv run python app/seed/reset_db.py

# Using standard virtual environment
python app/seed/reset_db.py
```

### 4. Start the Application

Run the development server:
```bash
# Using uv
uv run flask --app app.py run

# Using standard virtual environment
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### 5. Running Tests

Run the test suite to verify code logic:
```bash
# Using uv
uv run pytest

# Using standard virtual environment
pytest
```

---

## 🔑 Demo Login Credentials

The following pre-configured user credentials represent specific business roles within the Shiv Furniture factory:

| Username | Password | Business Role | Best Workflows to Demo |
| :--- | :--- | :--- | :--- |
| `admin` | `admin123` | **System Administrator** | User management, permissions, configuration, full system access |
| `owner` | `owner123` | **Business Owner** | Dashboard metrics, profit analytics, business health score, AI Copilot |
| `inventory` | `inventory123` | **Inventory Manager** | Product configuration, stock ledger, stock adjustments, reorder rules |
| `sales` | `sales123` | **Sales Representative** | Customer directory, Sales Order creation, Delivery Risk Predictor checks |
| `purchase` | `purchase123` | **Purchasing Agent** | Supplier management, Purchase Orders, Goods Receipt validation |
| `manufacturing`| `manufacturing123`| **Production Manager** | Product Recipes (BOM), Production Orders, Kanban Board |
| `cashier` | `cashier123` | **POS Cashier** | Retail sales terminal checkout |

---

## 🔗 Core Operational URLs

| Area | Route | Role Required |
| :--- | :--- | :--- |
| **Landing & Login** | `/` or `/auth/login` | Public |
| **Control Dashboard** | `/dashboard/` | Business Owner, Admin |
| **Products Catalog** | `/products/` | Inventory Manager, Sales |
| **Inventory Stock** | `/inventory/` | Inventory Manager |
| **Sales Orders** | `/sales/` | Sales Representative |
| **Smart Purchasing** | `/procurement/` | Purchasing Agent, Inventory Manager |
| **POS Terminal** | `/pos/` | POS Cashier |
| **Kanban Board** | `/kanban/` | Production Manager |
| **AI Copilot** | `/copilot/` | Business Owner, Admin |
| **Audit Logs** | `/audit/` | System Administrator, Business Owner |
