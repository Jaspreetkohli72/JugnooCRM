# 📘 JugnooCRM: Technical Documentation & User Guide

Welcome to the technical documentation for **JugnooCRM**. This guide is designed to explain how the application works under the hood, in simple terms that anyone can understand. We'll look at the "Brain" (Logic) and the "Memory" (Database) of the system.

---

## 🏗️ High-Level Architecture

Think of JugnooCRM as a smart digital assistant that lives on your computer but keeps its notes in the cloud.

### 1. The Brain: Streamlit (Python)
The application is built using **Python**, a powerful programming language, and **Streamlit**, a framework that turns Python scripts into interactive websites.
- **What it does:** It handles all the logic—calculating estimates, generating PDFs, and drawing charts.
- **Where it lives:** In the `app.py` file. This is the main script that runs the show.

### 2. The Memory: Supabase (Database)
All your data—clients, inventory, settings—is stored in **Supabase**, a secure cloud database.
- **What it does:** It remembers everything even when you close the app.
- **Why it's cool:** It allows you to access your data from anywhere and ensures it's safe.

---

## 🛠️ Key Features & How They Work

### 1. The Dashboard (Client Management)
The Dashboard is your command center. It lists all your clients and lets you manage their details.

**How it works:**
When you open the app, it asks the "Memory" (Supabase) for a list of all clients. It then displays them in a list. When you edit a phone number or status, the "Brain" sends a message to the "Memory" to update that specific record.

**Code Snippet (Simplified):**
```python
# This function asks the database for all clients
def get_clients():
    response = supabase.table("clients").select("*").execute()
    return response

# This part displays the list
clients = get_clients()
for client in clients:
    display_client_details(client)
```

### 2. The Estimator (The Calculator)
This is the heart of the app. It calculates exactly how much to charge a client based on materials, labor, and your desired profit margins.

**How it works:**
1. You select items from your Inventory.
2. You enter the quantity.
3. The app looks up the **Base Rate** (your cost) for each item.
4. It applies your **Margins** (Part %, Labor %, Extra %) to calculate the **Selling Price**.
5. It adds everything up to give you a Grand Total.

**Code Snippet (The Math):**
```python
# How we calculate the selling price
material_cost = item_qty * base_rate
margin_multiplier = 1 + (part_margin / 100)
selling_price = material_cost * margin_multiplier
```

### 3. PDF Generator (The Paperwork)
JugnooCRM can instantly create professional PDFs for Invoices and Estimates.

**How it works:**
The app takes all the data from the Estimator (client name, items, totals) and uses a tool called `FPDF` to draw a PDF document, line by line. It then gives you a file to download.

**Smart Feature:**
- If the client status is **"Closed"** or **"Work Done"**, it creates an **INVOICE**.
- For everyone else, it creates an **ESTIMATE**.

**Code Snippet:**
```python
if is_final_bill:
    pdf.add_header("INVOICE")
    pdf.add_footer("Thank you for your business!")
else:
    pdf.add_header("ESTIMATE")
    pdf.add_footer("Advance Payment Required")
```

### 4. Profit & Loss (The Scorecard)
This tab tells you if you are making money.

**How it works:**
It looks at two things:
1. **Money In:** The "Final Amount Received" you recorded for closed clients.
2. **Money Out:** The cost of materials (from Inventory) and labor.

It subtracts Money Out from Money In to show your **Net Profit**.

---

## 📂 Project Structure

Here is a quick tour of the files in the project folder:

- **`app.py`**: The main application file. Run this to start the app.
- **`utils/helpers.py`**: A helper file containing heavy logic (like complex math and PDF drawing) to keep `app.py` clean.
- **`.streamlit/secrets.toml`**: A secret file containing your database passwords. Never share this!
- **`requirements.txt`**: A list of "ingredients" (libraries) the app needs to run.

---

## 🚀 How to Run the App

1. Open your terminal (Command Prompt).
2. Navigate to the project folder.
3. Type the following command and hit Enter:
   ```bash
   streamlit run app.py
   ```
4. The app will open in your web browser.

---

*Documentation created for JugnooCRM.*
