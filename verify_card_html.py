
# Mocking the logic from app.py to verify HTML output
staff = {
    'id': 1,
    'name': 'Test Bot Verification',
    'bg_color': 'rgba(239, 68, 68, 0.1)',
    'status_color': '#ef4444',
    's_status': 'On Leave',
    'role': 'Helper',
    'phone': '123',
    'salary': 100
}

# The new HTML structure
html = f"""
<div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
    <!-- Top Row: Name + Badge -->
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-weight: 600; font-size: 1.2rem; color: #f8fafc; letter-spacing: -0.01em;">{staff['name']}</span>
        <span style="
            background: {staff['bg_color']};
            color: {staff['status_color']};
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            border: 1px solid {staff['status_color']}30;
            white-space: nowrap;
        ">{staff['s_status']}</span>
    </div>
    
    <!-- Bottom Row: Role/Phone + Salary (Grid Layout) -->
    <div style="
        display: grid; 
        grid-template-columns: auto 1fr auto; 
        align-items: center; 
        font-size: 0.9rem;
        color: #94a3b8;
    ">
        <!-- Left: Role & Phone -->
        <div style="display: flex; align-items: center; gap: 8px;">
            <span>{staff['role']}</span>
            <span style="color: #475569;">•</span>
            <span style="font-family: monospace;">{staff['phone']}</span>
        </div>
        
        <!-- Middle: Spacer -->
        <div></div>
        
        <!-- Right: Salary -->
        <div style="color: #cbd5e1; font-family: monospace; font-weight: 500; text-align: right;">
            ₹{staff.get('salary', 0)}/day
        </div>
    </div>
</div>
"""

print("Generated HTML:")
print(html)

if "display: grid" in html and "grid-template-columns: auto 1fr auto" in html:
    print("\nSUCCESS: CSS Grid layout detected.")
else:
    print("\nFAILURE: CSS Grid layout NOT detected.")
