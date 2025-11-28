# 🏗️ Jugnoo CRM

A specialized Construction & Automation CRM built for **Navneet Steel Fabricators**. This application manages clients, estimates, inventory, and supplier costs in real-time.

**📘 [Read the Technical Documentation & User Guide](project_documentation.md)**

## 🌟 Key Features

### 1. 📋 Dashboard & Project Management
- Track all active sites and their status (Order Received, Work in Progress, Done).
- **Geolocation**: One-click GPS capture to save site locations. Open directly in Google Maps.
- **Profit Analytics**: Real-time breakdown of Material Cost vs. Selling Price to calculate exact Net Profit per project.

### 2. 🧮 Smart Estimator
- Create estimates using your Inventory database.
- **Custom Margins**: Apply global defaults or specific margins (Part/Labor/Extra) for difficult clients.
- **PDF Generation**: Instantly generate professional **Client Invoices** (for closed jobs) or **Estimates** (for ongoing work).

### 3. 🚚 Supplier & Inventory "JIT" System
- **Live Costing**: Record purchases from suppliers.
- **Auto-Update**: When you buy an item at a new rate, the system automatically updates your global Inventory price, ensuring future estimates use current market rates.
- **History**: Track spending and purchase logs.

### 4. 📈 Profit & Loss (P&L)
- **Business Health**: View total revenue, expenses, and net profit.
- **Visualizations**: Interactive charts for monthly trends and cost breakdowns.

### 5. ⚙️ Admin Control
- **Inventory Manager**: Bulk edit item rates and units.
- **Global Settings**: Set default labor costs and profit margins.

## 🚀 Getting Started

1. **Setup Secrets**: Ensure `.streamlit/secrets.toml` contains your Supabase credentials (`SUPABASE_URL` and `SUPABASE_KEY`).
2.  **Run App**:
    ```bash
    streamlit run app.py
    ```
3. Login: Use your configured username/password.
