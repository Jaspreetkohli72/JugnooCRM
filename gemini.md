# Jugnoo CRM - Technical Documentation

## 1. Tech Stack
- **Frontend**: Streamlit (Dark Mode)
- **Backend**: Supabase (PostgreSQL)
- **Key Libraries**: `pandas`, `fpdf`, `extra_streamlit_components` (Cookie Auth), `streamlit_js_eval` (Geolocation).

## 2. Database Schema
- **`users`**: `username` (PK), `password`, `recovery_key`.
- **`clients`**: `id` (PK), `name`, `phone`, `address`, `location` (Maps Link), `status`, `start_date`, `internal_estimate` (JSONB), `created_at`.
- **`inventory`**: `id` (PK), `item_name`, `base_rate`, `unit` (pcs, m, ft, cm, in).
- **`suppliers`**: `id` (PK), `name`, `contact_person`, `phone`.
- **`purchase_log`**: `id` (PK), `supplier_id` (FK), `item_name`, `qty`, `rate`, `total_cost`, `created_at`.
- **`settings`**: `id`, `part_margin`, `labor_margin`, `extra_margin`, `daily_labor_cost`.

## 3. Application Architecture (`app.py`)
- **Tab 1: Dashboard**:
    - Lists active clients.
    - "Manage Client": Update status/details, Open Maps, "Danger Zone" deletion.
    - **Profit Analysis**: Displays Material Cost vs. Sale Price and calculated Net Profit in a table (No PDF for internal report).
- **Tab 2: New Client**:
    - Form to add clients. Includes `get_geolocation` button to auto-paste Maps links.
- **Tab 3: Estimator**:
    - Builds estimates using Inventory items.
    - Supports custom margin overrides per client.
    - Generates Client PDF Invoices.
- **Tab 4: Suppliers**:
    - **Top**: Split layout. Left = Record Purchase (Interactive inputs, no Form), Right = Add New Supplier.
    - **Middle**: Editable dataframe of Existing Suppliers (Full Width).
    - **Bottom**: Recent Purchase History merged with Supplier Names.
    - **Logic**: Recording a purchase optionally updates the global Inventory `base_rate`.
- **Tab 5: Settings**:
    - Global margin defaults.
    - Editable Inventory table (Upsert logic).

## 4. Critical Rules
- **Interactive Inputs**: Do not put dependent inputs (like Item Price lookups) inside `st.form`.
- **Layout**: Wide tables (Inventory, Suppliers) must be outside of columns to prevent squashing.
- **Auth**: Uses `CookieManager` for 7-day persistent login.