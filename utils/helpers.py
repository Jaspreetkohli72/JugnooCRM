import pandas as pd
import math
from fpdf import FPDF
from datetime import datetime

# ---------------------------
# GLOBAL CONSTANTS
# ---------------------------
CONVERSIONS = {'pcs': 1.0, 'each': 1.0, 'm': 1.0, 'cm': 0.01, 'ft': 0.3048, 'in': 0.0254}
P_L_STATUS = ["Work Done", "Closed"]

# --- PROFESSIONAL PDF GENERATOR ---
def create_pdf(client_name, items, labor_days, labor_total, grand_total, advance_amount):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "Jugnoo", ln=True, align='L')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 6, "Smart Automation Solutions", ln=True, align='L')
    pdf.line(10, 28, 200, 28)
    pdf.ln(15)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Estimate For: {client_name}", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%d-%b-%Y')}", ln=True)
    pdf.ln(5)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, "Description", 1, 0, 'L', 1)
    pdf.cell(15, 10, "Qty", 1, 0, 'C', 1)
    pdf.cell(15, 10, "Unit", 1, 0, 'C', 1)
    pdf.cell(60, 10, "Amount (INR)", 1, 1, 'R', 1)
    
    pdf.set_font("Arial", '', 10)
    for item in items:
        pdf.cell(100, 8, str(item.get('Item', '')), 1)
        pdf.cell(15, 8, str(item.get('Qty', 0)), 1, 0, 'C')
        pdf.cell(15, 8, str(item.get('Unit', '')), 1, 0, 'C')
        pdf.cell(60, 8, f"{item.get('Total Price', 0):,.2f}", 1, 1, 'R')
        
    pdf.set_font("Arial", '', 10)
    pdf.cell(130, 8, f"Labor / Installation ({labor_days} Days)", 1, 0, 'R')
    pdf.cell(60, 8, f"{labor_total:,.2f}", 1, 1, 'R')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 10, "Grand Total", 1, 0, 'R')
    pdf.cell(60, 10, f"Rs. {grand_total:,.2f}", 1, 1, 'R')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.multi_cell(0, 5, f"Advance Payment Required: Rs. {advance_amount:,.2f}")
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, "NOTE: This is an estimate only. Final rates may vary based on actual site conditions and market fluctuations. Valid for 7 days.")
    
    return pdf.output(dest='S').encode('latin-1')

def create_internal_pdf(client_name, items, labor_days, labor_cost, labor_charged, grand_total, total_profit):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "INTERNAL PROFIT REPORT (CONFIDENTIAL)", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Client: {client_name} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(5)

    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(70, 8, "Item Description", 1, 0, 'L', 1)
    pdf.cell(15, 8, "Qty", 1, 0, 'C', 1)
    pdf.cell(35, 8, "Base Rate", 1, 0, 'R', 1)
    pdf.cell(35, 8, "Sold At", 1, 0, 'R', 1)
    pdf.cell(35, 8, "Profit", 1, 1, 'R', 1)

    pdf.set_font("Arial", '', 9)
    for item in items:
        qty = float(item.get('Qty', 0))
        base = float(item.get('Base Rate', 0))
        total_sell = float(item.get('Total Price', 0))
        unit_sell = total_sell / qty if qty > 0 else 0
        row_profit = total_sell - (base * qty)
        
        pdf.cell(70, 8, str(item.get('Item', ''))[:35], 1)
        pdf.cell(15, 8, str(qty), 1, 0, 'C')
        pdf.cell(35, 8, f"{base:,.2f}", 1, 0, 'R')
        pdf.cell(35, 8, f"{unit_sell:,.2f}", 1, 0, 'R')
        pdf.set_text_color(0, 150, 0); pdf.cell(35, 8, f"{row_profit:,.2f}", 1, 1, 'R'); pdf.set_text_color(0, 0, 0)

    labor_profit = labor_charged - labor_cost
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(120, 8, f"Labor ({labor_days} Days)", 1, 0, 'R')
    pdf.cell(35, 8, f"Cost: {labor_cost:,.2f}", 1, 0, 'R')
    pdf.cell(35, 8, f"Chrg: {labor_charged:,.2f}", 1, 1, 'R')

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(120, 10, "TOTAL REVENUE:", 1, 0, 'R')
    pdf.cell(70, 10, f"Rs. {grand_total:,.2f}", 1, 1, 'R')
    pdf.cell(120, 10, "NET PROFIT:", 1, 0, 'R')
    pdf.set_text_color(0, 150, 0); pdf.cell(70, 10, f"Rs. {total_profit:,.2f}", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')


def calculate_estimate_details(edf_items_list, days, margins, global_settings):
    # edf_items_list is a list of dictionaries, representing the items in the estimate
    # CONVERSIONS is a global variable
    # mm calculation
    mm = 1 + (margins.get('part_margin', 0)/100) + (margins.get('labor_margin', 0)/100) + (margins.get('extra_margin', 0)/100)

    def calc_total_item(row):
        try:
            qty = float(row.get('Qty', 0))
            base = float(row.get('Base Rate', 0))
            unit = CONVERSIONS.get(row.get('Unit', 'pcs'), 1.0) # Use CONVERSIONS here as well
            factor = CONVERSIONS.get(unit, 1.0)
            
            if unit in ['m', 'cm', 'ft', 'in']:
                return base * (qty * factor) * mm
            else:
                return base * qty * mm
        except (ValueError, TypeError):
            return 0.0

    edf_details_df = pd.DataFrame(edf_items_list)
    if not edf_details_df.empty:
        edf_details_df['Total Price'] = edf_details_df.apply(calc_total_item, axis=1)
        edf_details_df['Unit Price'] = edf_details_df['Total Price'] / edf_details_df['Qty'].replace(0, 1)
        
        mat_sell = edf_details_df['Total Price'].sum()
    else:
        mat_sell = 0.0

    daily_labor_cost = float(global_settings.get('daily_labor_cost', 1000.0))
    labor_actual_cost = float(days) * daily_labor_cost

    def calculate_item_base_cost(row):
        qty = float(row.get('Qty', 0))
        base_rate = float(row.get('Base Rate', 0))
        unit = CONVERSIONS.get(row.get('Unit', 'pcs'), 1.0) # Use CONVERSIONS here as well
        factor = CONVERSIONS.get(unit, 1.0)
        return base_rate * qty * factor
    
    total_material_base_cost = edf_details_df.apply(calculate_item_base_cost, axis=1).sum() if not edf_details_df.empty else 0.0
    total_base_cost = total_material_base_cost + labor_actual_cost
    
    raw_grand_total = mat_sell + labor_actual_cost
    rounded_grand_total = math.ceil(raw_grand_total / 100) * 100
    total_profit = rounded_grand_total - total_base_cost
    advance_amount = math.ceil((total_base_cost + (total_profit * 0.10)) / 100) * 100
    disp_lt = labor_actual_cost + (rounded_grand_total - raw_grand_total)

    return {
        "mat_sell": mat_sell,
        "labor_actual_cost": labor_actual_cost, # Base labor cost
        "rounded_grand_total": rounded_grand_total,
        "total_profit": total_profit,
        "advance_amount": advance_amount,
        "disp_lt": disp_lt, # Displayed labor total (includes rounding diff)
        "edf_details_df": edf_details_df # Return the updated dataframe as well
    }

def calculate_profit_row(row):
    qty = float(row.get('Qty', 0))
    base_rate = float(row.get('Base Rate', 0))
    unit = row.get('Unit', 'pcs')
    total_sell = float(row.get('Total Sell Price', 0))
    factor = CONVERSIONS.get(unit, 1.0)
    total_cost = base_rate * qty * factor
    return total_sell - total_cost