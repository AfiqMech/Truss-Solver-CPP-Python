import streamlit as st
import subprocess
import os
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURATION & PREMIUM DESIGN ---
st.set_page_config(page_title="Truss Solver", layout="wide", initial_sidebar_state="expanded")

# --- SESSION STATE INIT ---
defaults = {
    "e_val": 200.0, "y_val": 250.0, "data_key": 0, "material_preset": "Steel",
    "node_data": pd.DataFrame([
        {"Joint #": 1, "X (m)": 0.0, "Y (m)": 0.0, "Support Type": "Pinned Support"},
        {"Joint #": 2, "X (m)": 4.0, "Y (m)": 0.0, "Support Type": "Free Joint"},
        {"Joint #": 3, "X (m)": 8.0, "Y (m)": 0.0, "Support Type": "Roller Support"},
        {"Joint #": 4, "X (m)": 4.0, "Y (m)": 4.0, "Support Type": "Free Joint"}
    ]),
    "beam_data": pd.DataFrame([
        {"Beam #": 1, "From Joint": 1, "To Joint": 2}, {"Beam #": 2, "From Joint": 2, "To Joint": 3},
        {"Beam #": 3, "From Joint": 1, "To Joint": 4}, {"Beam #": 4, "From Joint": 2, "To Joint": 4},
        {"Beam #": 5, "From Joint": 4, "To Joint": 3}
    ]),
    "load_data": pd.DataFrame([{"Target Joint": 2, "Weight (kN)": 50.0, "Push Angle": 270.0}])
}
for k,v in defaults.items(): 
    if k not in st.session_state: st.session_state[k] = v

# ==========================================
# 1. VISUALIZATION FUNCTION
# ==========================================
def draw_bridge(input_file_path, output_file_path=None, deformation_scale=0.0, visualization_scale_multiplier=0.6):
    """
    Reads the truss structure from JSON input/output files and renders an interactive
    Plotly figure. It visualizes beams, joints, supports, and force arrows (Tension,
    Compression, Load, Reaction).
    
    Args:
        input_file_path (str): Path to the input JSON definition.
        output_file_path (str): Path to the analysis results JSON (optional).
        deformation_scale (float): Scale factor for displaying deformation (unused currently).
        visualization_scale_multiplier (float): Global scale multiplier for arrow/icon sizes.
        
    Returns:
        go.Figure: The Plotly figure object, or None if input reading fails.
    """
    if not os.path.exists(input_file_path): return None
    
    try:
        with open(input_file_path, 'r') as file: bridge_data = json.load(file)
    except: return None
    
    simulation_results = {}
    node_results = {}
    
    if output_file_path and os.path.exists(output_file_path):
        try:
            with open(output_file_path, 'r') as file:
                results_data = json.load(file)
                for element in results_data.get('elements', []): simulation_results[element['id']] = element
                for node in results_data.get('nodes', []): node_results[node['id']] = node
        except: pass

    all_nodes = {node['id']: node for node in bridge_data.get('nodes', [])}
    all_elements = bridge_data.get('elements', [])

    fig = go.Figure()
    
    # Auto-Brain 2.0: Density-Sensing Scaling
    complexity_factor = max(0.35, (12.0 / max(12.0, len(all_elements)))**0.5)
    
    # Calculate recommended height based on aspect ratio
    x_coords = [n['x'] for n in all_nodes.values()]
    y_coords = [n['y'] for n in all_nodes.values()]
    dx = max(x_coords) - min(x_coords) if x_coords else 10
    dy = max(y_coords) - min(y_coords) if y_coords else 5
    aspect_ratio = dy / dx if dx > 0 else 1
    rec_h = max(500, min(900, 500 + int(aspect_ratio * 300)))

    min_len = 2.0 
    if all_elements:
        lengths = [np.sqrt((all_nodes[e['start']]['x']-all_nodes[e['end']]['x'])**2 + 
                          (all_nodes[e['start']]['y']-all_nodes[e['end']]['y'])**2) 
                   for e in all_elements if e['start'] in all_nodes and e['end'] in all_nodes]
        if lengths: min_len = min(l for l in lengths if l > 0)
    
    # Auto-Brain: Automatically pick safe multiplier based on complexity
    auto_mult = 0.55 if len(all_elements) > 20 else (0.75 if len(all_elements) < 8 else 0.65)
    visual_scale = max(0.1, min(min_len * 0.3, 0.6)) * complexity_factor * auto_mult

    # Helper: Add Arrow Trace with Adaptive Border
    def add_trace_arrow(fig, start_x, start_y, end_x, end_y, color, name, group, text=None, text_offset=0.45):
        h_sz = 0.48 * visual_scale 
        angle = np.arctan2(end_y - start_y, end_x - start_x)
        sh_len = 0.7 * h_sz
        sx_e, sy_e = end_x - sh_len * np.cos(angle), end_y - sh_len * np.sin(angle)
        
        bw = 0.08 * h_sz
        bx_s, by_s = start_x + bw*np.cos(angle), start_y + bw*np.sin(angle)
        bx_e, by_e = sx_e - bw*np.cos(angle), sy_e - bw*np.sin(angle)
        cx_s, cy_s, cx_e, cy_e = bx_s, by_s, bx_e, by_e

        a1, a2 = angle + np.pi*1.11, angle - np.pi*1.11
        hx = [end_x, end_x + h_sz*np.cos(a1), end_x + h_sz*np.cos(a2), end_x, None]
        hy = [end_y, end_y + h_sz*np.sin(a1), end_y + h_sz*np.sin(a2), end_y, None]
        
        w_dark = max(6, 8 * complexity_factor)
        w_white = max(4, 6 * complexity_factor)
        w_color = max(2, 4 * complexity_factor)
        dark_c = '#0f172a' # High-contrast shadow
        
        # Layer 1: Dark Shadow (pops on light backgrounds)
        fig.add_trace(go.Scatter(x=[bx_s, bx_e, None], y=[by_s, by_e, None], mode='lines', line=dict(color=dark_c, width=w_dark), legendgroup=group, showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=hx, y=hy, mode='lines', fill='toself', fillcolor=dark_c, line=dict(color=dark_c, width=2.5), legendgroup=group, showlegend=False, hoverinfo='skip'))
        
        # Layer 2: White Glow (pops on dark backgrounds)
        fig.add_trace(go.Scatter(x=[bx_s, bx_e, None], y=[by_s, by_e, None], mode='lines', line=dict(color='white', width=w_white), legendgroup=group, showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=hx, y=hy, mode='lines', fill='toself', fillcolor='white', line=dict(color='white', width=1.5), legendgroup=group, showlegend=False, hoverinfo='skip'))
        
        # Layer 3: Vibrant Center
        fig.add_trace(go.Scatter(x=[cx_s, cx_e, None], y=[cy_s, cy_e, None], mode='lines', line=dict(color=color, width=w_color), legendgroup=group, showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=hx, y=hy, mode='lines', fill='toself', fillcolor=color, line=dict(color=color, width=0.8), legendgroup=group, showlegend=False, hoverinfo='skip'))
        
        if text:
            dirs = np.array([np.cos(angle), np.sin(angle)])
            off = text_offset * visual_scale
            lx, ly = (np.array([end_x, end_y]) + dirs * off) if "Force" in name else (np.array([start_x, start_y]) - dirs * off)
            if "Reaction" in name: lx, ly = np.array([start_x, start_y]) - dirs * off
            
            # Smart Labels 2.0: Badge Logic (Dynamic Width + High Contrast)
            fig.add_annotation(
                x=lx, y=ly, text=text, showarrow=False,
                font=dict(color='white', size=min(10, 8.0+2.5*complexity_factor), weight='bold'),
                bgcolor=color, bordercolor=dark_c, borderwidth=1.5, borderpad=3, opacity=0.98
            )

    # 1. Beams
    for element in all_elements:
        if element['start'] not in all_nodes or element['end'] not in all_nodes: continue
        
        node_start = all_nodes[element['start']]
        node_end = all_nodes[element['end']]
        
        start_x, start_y = node_start['x'], node_start['y']
        end_x, end_y = node_end['x'], node_end['y']
        
        # Style based on safety factor
        beam_color, beam_width = '#3b82f6', 4
        hover_text = f"Beam #{element['id']}"
        
        safety_factor = 999.0
        
        if element['id'] in simulation_results:
            beam_result = simulation_results[element['id']]
            safety_factor = beam_result['safety']
            force_magnitude = beam_result['force']
            hover_text += f"<br>Force: {force_magnitude:.2f} kN<br>Safety: {safety_factor:.2f}"
            
            if safety_factor < 1.0: 
                beam_color, beam_width = '#ef4444', 6 # Red
            elif safety_factor < 2.0: 
                beam_color, beam_width = '#f59e0b', 5 # Orange
            else: 
                beam_color, beam_width = '#10b981', 6 # Green
        
        # Determine Legend Group (Draft/Safe/Caution/Unsafe)
        is_draft = element['id'] not in simulation_results
        if is_draft:
            legend_group_name = "Beam (Draft)"
        else:
            if safety_factor < 1.0: legend_group_name = "Beam (Unsafe)"
            elif safety_factor < 2.0: legend_group_name = "Beam (Caution)"
            else: legend_group_name = "Beam (Safe)"
        
        # Manage Legend Entries (Show only once per group)
        show_legend_item = False
        simulation_results.setdefault('_legend_set', set())
        if legend_group_name not in simulation_results['_legend_set']:
            show_legend_item = True
            simulation_results['_legend_set'].add(legend_group_name)

        # Draw Beam Line
        fig.add_trace(go.Scatter(
            x=[start_x, end_x, None], 
            y=[start_y, end_y, None], 
            mode='lines', 
            line=dict(color=beam_color, width=beam_width),
            hoverinfo='text', 
            text=hover_text, 
            name=legend_group_name, 
            legendgroup=legend_group_name, 
            showlegend=show_legend_item
        ))
        
        # Internal Forces Arrows (Visualization)
        if element['id'] in simulation_results and abs(simulation_results[element['id']]['force']) > 0.1:
            force_value = simulation_results[element['id']]['force']
            is_compression = force_value <= 0
            
            arrow_color = '#22d3ee' # Electric Cyan for Tension
            legend_group_arrow = 'Tension Force'
            
            if is_compression:
                arrow_color = '#fb923c' # Orange for Compression
                legend_group_arrow = 'Compression Force'
            
            length_of_beam = np.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
            midpoint_x = (start_x + end_x) / 2
            midpoint_y = (start_y + end_y) / 2
            
            slope_x = (end_x - start_x) / length_of_beam
            slope_y = (end_y - start_y) / length_of_beam
            
            # Geometry Logic for Arrow Placement
            # Smart Scaling 2.0: Space-Proportional Gaps
            arrow_length = min(visual_scale * 1.5, length_of_beam * 0.35)
            inner_gap_distance = min(visual_scale * 0.6, length_of_beam * 0.1)
            outer_gap_distance = inner_gap_distance + arrow_length
            
            # Determine direction (Compression points OUT, Tension points IN relative to center?)
            # Wait, original logic:
            # is_comp: tail=outer, tip=inner (Points IN towards center) -> Compression arrows face each other
            # Tension: tail=inner, tip=outer (Points OUT away from center) -> Tension arrows face away
            
            if is_compression:
                dist_tail, dist_tip = outer_gap_distance, inner_gap_distance
            else:
                dist_tail, dist_tip = inner_gap_distance, outer_gap_distance


            # Draw Arrows
            for sign in [1, -1]:
                t_x, t_y = midpoint_x + sign*slope_x*dist_tail, midpoint_y + sign*slope_y*dist_tail
                h_x, h_y = midpoint_x + sign*slope_x*dist_tip, midpoint_y + sign*slope_y*dist_tip
                add_trace_arrow(fig, t_x, t_y, h_x, h_y, arrow_color, "Internal Force", legend_group_arrow)
    # Legend Entries
    for n, c in {"Tension Force": "#22d3ee", "Compression Force": "#fb923c", "Load Force": "#f43f5e", "Reaction Force": "#8b5cf6"}.items():
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(symbol='arrow-bar-up', size=10, color=c), name=n, legendgroup=n))
    


    # 2. Nodes & Supports
    node_plot_x, node_plot_y, node_hover_text = [], [], []
    
    for node_id, node in all_nodes.items():
        node_x, node_y = node['x'], node['y']
        node_plot_x.append(node_x)
        node_plot_y.append(node_y)
        node_hover_text.append(f"Joint {node_id}")
        


        # ---------------------------
        # Layer 1: Support Icons (Structural Base)
        # ---------------------------
        support_type = node.get('type', 'Free Joint')
        markers = {"Pinned Support": ('triangle-up-dot', '#000000'), "Roller Support": ('circle', '#000000'), "Fixed (Rigid)": ('square-dot', '#000000')}
        marker_symbol, marker_color = markers.get(support_type, ('circle', '#1e3d59'))
        
        if support_type != "Free Joint":
             legend_group_support = support_type
             show_legend_support = False
             simulation_results.setdefault('_support_legend', set())
             if legend_group_support not in simulation_results['_support_legend']:
                 show_legend_support = True
                 simulation_results['_support_legend'].add(legend_group_support)

             # Smart Supports: Adaptive scaling (Sleeker integration)
             s_sz = max(22, 55 * visual_scale)
             fig.add_trace(go.Scatter(
                 x=[node_x], y=[node_y - 0.12 * visual_scale], mode='markers',
                 marker=dict(symbol=marker_symbol, size=s_sz, color=marker_color, line_width=2),
                 hoverinfo='text', text=support_type, 
                 name=support_type, legendgroup=support_type, showlegend=show_legend_support
             ))

        # ---------------------------
        # Layer 2: Loads
        # ---------------------------
        load_component_x = node.get('loadX', 0)
        load_component_y = node.get('loadY', 0)
        load_magnitude = np.sqrt(load_component_x**2 + load_component_y**2) / 1000.0
        
        if load_magnitude > 0.001:
            direction_x, direction_y = load_component_x / 1000.0, load_component_y / 1000.0
            norm = np.sqrt(direction_x**2 + direction_y**2)
            unit_dir_x, unit_dir_y = direction_x/norm, direction_y/norm
            
            l_start_x, l_start_y = node_x + unit_dir_x * 0.15 * visual_scale, node_y + unit_dir_y * 0.15 * visual_scale
            l_end_x, l_end_y = node_x + unit_dir_x * 1.6 * visual_scale, node_y + unit_dir_y * 1.6 * visual_scale
            
            add_trace_arrow(fig, l_start_x, l_start_y, l_end_x, l_end_y, '#f43f5e', "Load Force", 
                          "Load Force", f"{load_magnitude:.1f} kN")
        
        # ---------------------------
        # Layer 3: Reactions (Top of Supports)
        # ---------------------------
        if node_id in node_results:
            rx_val, ry_val = node_results[node_id].get('rx', 0) / 1000.0, node_results[node_id].get('ry', 0) / 1000.0
            reaction_magnitude = np.sqrt(rx_val**2 + ry_val**2)
            
            if reaction_magnitude > 0.001:
                norm = np.sqrt(rx_val**2 + ry_val**2)
                unit_rx, unit_ry = rx_val/norm, ry_val/norm
                r_gap, r_len = 0.25 * visual_scale, 1.6 * visual_scale
                r_tail_x, r_tail_y = node_x - unit_rx * (r_len + r_gap), node_y - unit_ry * (r_len + r_gap)
                r_head_x, r_head_y = node_x - unit_rx * r_gap, node_y - unit_ry * r_gap
                
                add_trace_arrow(fig, r_tail_x, r_tail_y, r_head_x, r_head_y, '#8b5cf6', "Reaction Force", 
                              "Reaction Force", f"R: {reaction_magnitude:.1f}")

    # 3. Draw Joints (Top Layer)
    fig.add_trace(go.Scatter(
        x=node_plot_x, y=node_plot_y, mode='markers',
        marker=dict(size=max(10, 12 * visual_scale / visualization_scale_multiplier), color='#1e3d59', line=dict(color='white', width=1)),
        hoverinfo='text', hovertext=node_hover_text, showlegend=False
    ))
                           
    # Joint Labels (Annotations)
    for node_id, node in all_nodes.items():
         fig.add_annotation(
             x=node['x'], y=node['y'], text=str(node_id),
             yshift=10 * complexity_factor, showarrow=False,
             font=dict(color='white', size=min(10, 8+2*complexity_factor), weight='bold'),
             bgcolor='#1e3d59', bordercolor='white', borderwidth=1, borderpad=2, opacity=0.9
         )
                           
    # 4. Beam Labels (Persistent)
    for element in all_elements:
        if element['start'] not in all_nodes or element['end'] not in all_nodes: continue
        node_1 = all_nodes[element['start']]
        node_2 = all_nodes[element['end']]
        
        center_x = (node_1['x'] + node_2['x']) / 2
        center_y = (node_1['y'] + node_2['y']) / 2
        
        # Calculate color based on safety
        label_bg_color = '#3b82f6'
        
        if element['id'] in simulation_results:
            safety_val = simulation_results[element['id']]['safety']
            if safety_val < 1.0: label_bg_color = '#ef4444'
            elif safety_val < 2.0: label_bg_color = '#f59e0b'
            else: label_bg_color = '#10b981'
            
        fig.add_annotation(
            x=center_x, y=center_y, text=f"#{element['id']}", 
            showarrow=False, font=dict(size=min(10, 8+2*complexity_factor), color='white'),
             bgcolor=label_bg_color, bordercolor='white', borderwidth=1, borderpad=1, opacity=0.9
        )

    # Universal Theme: Slate-500 axes for visibility on both
    color_axis = '#64748b'
    color_grid = '#cbd5e1' # Slightly darker grid for visibility

    # Layout
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        margin=dict(l=20, r=20, t=40, b=20),
        
        # Axes
        xaxis=dict(showgrid=True, gridcolor=color_grid, zeroline=True, zerolinecolor=color_grid, 
                  visible=True, scaleanchor="y", scaleratio=1, 
                  tickfont=dict(color=color_axis, size=12, weight='bold'), 
                  title=dict(text="X Position (m)", font=dict(color=color_axis, weight='bold'))),
        
        yaxis=dict(showgrid=True, gridcolor=color_grid, zeroline=True, zerolinecolor=color_grid, 
                  visible=True, 
                  tickfont=dict(color=color_axis, size=12, weight='bold'), 
                  title=dict(text="Y Position (m)", font=dict(color=color_axis, weight='bold'))),
                  
        dragmode='pan',
        width=None, height=None, autosize=True,
        
        # Legend: Adaptive (Let Streamlit Theme handle colors)
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=1.02)
    )
    
    # Final result: figure and recommended height
    return fig, rec_h

# Inject Styles
st.write("""
    <style>
    :root { --bg-main: var(--background-color); --text-main: var(--text-color); --card-bg: var(--secondary-background-color); --card-border: #cbd5e140; --header-bg: var(--primary-color); --header-text: #ffffff; }
    .header-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 2rem; border-radius: 16px; margin-bottom: 2rem; box-shadow: 0 10px 25px rgba(0,0,0,0.15); text-align: center; }
    .header-card h1 { color: white !important; margin: 0; }
    .input-card { background: var(--card-bg); border: 1px solid var(--card-border); padding: 1.5rem; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 1rem; }
    .step-title { font-weight: 600; color: var(--text-main); font-size: 1.3rem; margin-bottom: 0.5rem; }
    * { font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    [data-testid="stMetricLabel"] { color: var(--text-main) !important; font-weight: 600 !important; font-size: 0.85rem !important; opacity: 0.8; }
    [data-testid="stMetricValue"] { color: var(--text-main) !important; font-weight: 800 !important; font-size: 1.6rem !important; }
    [data-testid="stMetric"] div { overflow: visible !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(45deg, #ff6e40, #ff5722) !important; color: white !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important; box-shadow: 0 8px 16px rgba(255, 110, 64, 0.3) !important; transition: all 0.3s ease !important; }
    div.stButton > button[kind="primary"]:hover { box-shadow: 0 12px 20px rgba(255, 110, 64, 0.5) !important; transform: translateY(-2px); }
    div.stButton > button[kind="secondary"] { background: transparent !important; border: 2px solid #ef4444 !important; border-radius: 50px !important; color: #ef4444 !important; font-weight: 600 !important; box-shadow: none !important; opacity: 0.9; transition: all 0.3s ease !important; }
    div.stButton > button[kind="secondary"]:hover { border-color: #dc2626 !important; color: white !important; background: #ef4444 !important; opacity: 1.0; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3) !important; }
    </style>
    """, unsafe_allow_html=True)

# Helper: Render Card Trimming
def render_card_header(emoji, title, stage_num):
    st.markdown(f'<div class="input-card"><div class="step-title">{emoji} Stage {stage_num}: {title}</div></div>', unsafe_allow_html=True)

# --- HEADER SECTION ---
st.markdown('<div class="header-card"><h1>Truss Solver</h1></div>', unsafe_allow_html=True)

# --- WORKFLOW SIDEBAR ---
with st.sidebar:
    st.markdown("### 🛠️ Global Setup")
    
    # Material Presets Logic
    def update_material_defaults():
        defaults = {"Steel": (200.0, 250.0), "Aluminum": (70.0, 95.0), "Wood": (13.0, 40.0)}
        if st.session_state.material_preset in defaults:
            st.session_state.e_val, st.session_state.y_val = defaults[st.session_state.material_preset]
    


    # UI Components
    st.selectbox("📚 Material Preset", ["Custom", "Steel", "Aluminum", "Wood"], 
                 key="material_preset", on_change=update_material_defaults, index=1)
    
    if st.session_state.material_preset == "Custom":
        st.text_input("Name", value="My Custom Material", key="custom_material_name")
    
    input_youngs_modulus_gpa = st.number_input("Young's Modulus (E) [GPa]", key="e_val", min_value=0.0, step=1.0, format="%.1f")
    
    input_yield_strength_mpa = st.number_input("Yield Strength (Y) [MPa]", key="y_val", min_value=0.0, step=5.0, format="%.1f")
    

    input_area_cm2 = st.number_input("📐 Beam Thickness (cm²)", value=15.0, min_value=0.1, step=1.0)
    
    # Global Validation
    if st.session_state.material_preset == "Custom":
        if input_youngs_modulus_gpa <= 0: st.error("⚠️ Young's Modulus must be > 0!")
        if input_yield_strength_mpa <= 0: st.error("⚠️ Yield Strength must be > 0!")
    if input_area_cm2 <= 0: st.error("⚠️ Beam area must be > 0!")

area_in_meters_squared = input_area_cm2 * 1e-4
youngs_modulus_pa = input_youngs_modulus_gpa * 1e9  # Convert GPa to Pa
yield_strength_pa = input_yield_strength_mpa * 1e6  # Convert MPa to Pa



# --- LAYOUT: 3-STEP WORKFLOW ---
st.header("Define Your Bridge Geometry & Physics")
col_joints, col_beams, col_loads = st.columns(3, gap="medium")

with col_joints:
    render_card_header("", "Joints", 1)
    
    node_df_schema = st.session_state.node_data.copy()
    node_df_schema["Support Type"] = node_df_schema["Support Type"].astype("category").cat.set_categories(["Free Joint", "Pinned Support", "Roller Support", "Fixed (Rigid)"])
    
    edited_nodes = st.data_editor(node_df_schema, num_rows="dynamic", key=f"nodes_v{st.session_state.data_key}", use_container_width=True, 
                                 column_config={
                                     "Joint #": st.column_config.NumberColumn("Joint #", min_value=1, step=1),
                                     "Support Type": st.column_config.SelectboxColumn(
                                         "Support Type", 
                                         options=["Free Joint", "Pinned Support", "Roller Support", "Fixed (Rigid)"], 
                                         required=True,
                                         default="Free Joint"
                                     )
                                 })
    valid_joints = sorted(edited_nodes["Joint #"].dropna().unique().tolist())
    # OCD Fix: Prepend existing IDs to options to prevent data_editor crash if a joint is deleted but still referenced
    beam_joints = sorted(list(set(st.session_state.beam_data["From Joint"].dropna().tolist() + st.session_state.beam_data["To Joint"].dropna().tolist())))
    load_joints = sorted(st.session_state.load_data["Target Joint"].dropna().tolist())
    safe_joints = sorted(list(set(valid_joints + beam_joints + load_joints)))
    
    # Validation: Check for overlapping joints & missing data
    if not edited_nodes.empty:
        if edited_nodes["X (m)"].isnull().any() or (edited_nodes["X (m)"] == "").any():
             st.error("⚠️ Error: A joint is missing its X coordinate!")
        elif edited_nodes["Y (m)"].isnull().any() or (edited_nodes["Y (m)"] == "").any():
             st.error("⚠️ Error: A joint is missing its Y coordinate!")
             
        # Check for duplicates based on X and Y columns
        check_df = edited_nodes.copy()
        check_df["X_num"] = pd.to_numeric(check_df["X (m)"], errors='coerce')
        check_df["Y_num"] = pd.to_numeric(check_df["Y (m)"], errors='coerce')
        
        duplicates = check_df.dropna(subset=["X_num", "Y_num"]).duplicated(subset=["X_num", "Y_num"], keep=False)
        if duplicates.any():
            st.error("⚠️ Error: Multiple joints share the same location! Please ensure every joint has unique coordinates.")

with col_beams:
    render_card_header("", "Beams", 2)
    
    edited_beams = st.data_editor(st.session_state.beam_data, num_rows="dynamic", key=f"beams_v{st.session_state.data_key}", use_container_width=True, 
                                column_config={
                                    "From Joint": st.column_config.SelectboxColumn("From Joint", options=safe_joints, required=True),
                                    "To Joint": st.column_config.SelectboxColumn("To Joint", options=safe_joints, required=True),
                                    "Beam #": st.column_config.NumberColumn("Beam #", min_value=1, step=1)
                                })
    
    # Validation Warning
    if not edited_beams.empty:
        if edited_beams["From Joint"].isnull().any():
             st.error("⚠️ Error: A beam is missing its Start Joint!")
        elif edited_beams["To Joint"].isnull().any():
             st.error("⚠️ Error: A beam is missing its End Joint!")
             
        # Check for From == To
        errs = edited_beams[edited_beams["From Joint"] == edited_beams["To Joint"]]
        if len(errs) > 0:
            st.error("⚠️ Error: A beam cannot connect a joint to itself! Please select a different joint.")

with col_loads:
    render_card_header("", "Loads", 3)
    
    edited_loads = st.data_editor(st.session_state.load_data, num_rows="dynamic", key=f"loads_v{st.session_state.data_key}", use_container_width=True, 
                                column_config={
                                    "Target Joint": st.column_config.SelectboxColumn("Target Joint", options=safe_joints, required=True),
                                    "Weight (kN)": st.column_config.NumberColumn("Weight (kN)", min_value=0.0, step=1.0),
                                    "Push Angle": st.column_config.NumberColumn("Push Angle", min_value=0.0, max_value=360.0, step=15.0, default=270.0)
                                })

    # Validation
    if not edited_loads.empty:
        if edited_loads["Target Joint"].isnull().any():
             st.error("⚠️ Error: A load is missing its Target Joint!")

# --- PROCESS INPUTS ---
valid_node_ids = set()
final_nodes_list = []

# Process Nodes
# Use zip for faster iteration than iterrows
for idx, x, y, stype in zip(edited_nodes["Joint #"], edited_nodes["X (m)"], edited_nodes["Y (m)"], edited_nodes["Support Type"]):
    if pd.isna(idx) or pd.isna(x) or pd.isna(y): continue
    
    nid = int(idx)
    valid_node_ids.add(nid)
    
    # 0 = Free, 1 = Pinned, 2 = Roller, 3 = Fixed (Rigid)
    fx = str(stype == "Pinned Support" or stype == "Fixed (Rigid)").lower()
    fy = str(stype != "Free Joint").lower()  # All supports fix Y

    final_nodes_list.append({
        "id": nid, "x": float(x), "y": float(y), 
        "isFixedX": fx, "isFixedY": fy, "loadX": 0.0, "loadY": 0.0, "type": stype
    })

# Process Loads
node_map = {n["id"]: n for n in final_nodes_list}
for tj, mag, ang in zip(edited_loads["Target Joint"], edited_loads["Weight (kN)"], edited_loads["Push Angle"]):
    if pd.isna(tj) or pd.isna(mag) or pd.isna(ang): continue
    if int(tj) in node_map:
        rad = np.radians(float(ang))
        node_map[int(tj)]["loadX"] += float(mag) * np.cos(rad) * 1000.0
        node_map[int(tj)]["loadY"] += float(mag) * np.sin(rad) * 1000.0

final_beams_list = []
for bid, start, end in zip(edited_beams["Beam #"], edited_beams["From Joint"], edited_beams["To Joint"]):
    if pd.isna(bid) or pd.isna(start) or pd.isna(end): continue
    s, e = int(start), int(end)
    if s != e and s in valid_node_ids and e in valid_node_ids:
        final_beams_list.append({"id": int(bid), "start": s, "end": e, "E": youngs_modulus_pa, "A": area_in_meters_squared, "yield": yield_strength_pa})

with open("data/input.json", "w") as f: 
    json.dump({"nodes": final_nodes_list, "elements": final_beams_list}, f, indent=2)

# --- RESULTS ---
st.divider()
col_visualizer, col_results = st.columns([2, 1])

with col_visualizer:
    st.markdown('<div class="input-card"><div class="step-title">Bridge Visualizer</div></div>', unsafe_allow_html=True)
    figure_object, recommended_h = draw_bridge("data/input.json", "data/output.json")
    if figure_object: st.plotly_chart(figure_object, use_container_width=True, height=recommended_h)

with col_results:
    st.markdown('<div class="input-card"><div class="step-title">Analysis Engine</div></div>', unsafe_allow_html=True)
    
    col_buttons_1, col_buttons_2 = st.columns([1.5, 1])
    with col_buttons_1:
        run_btn = st.button("RUN CALCULATION", type="primary", use_container_width=True)
    with col_buttons_2:
        clear_btn = st.button("Clear All", type="secondary", use_container_width=True)

    if clear_btn:
        st.session_state.node_data = pd.DataFrame(columns=["Joint #", "X (m)", "Y (m)", "Support Type"])
        st.session_state.beam_data = pd.DataFrame(columns=["Beam #", "From Joint", "To Joint"])
        st.session_state.load_data = pd.DataFrame(columns=["Target Joint", "Weight (kN)", "Push Angle"])
        st.session_state.data_key += 1
        if os.path.exists("data/output.json"): os.remove("data/output.json")
        st.rerun()

    if run_btn and os.path.exists("truss_engine.exe"):
        # State Sync: Save current edits back to session state before running
        st.session_state.node_data, st.session_state.beam_data, st.session_state.load_data = edited_nodes, edited_beams, edited_loads
        with open("data/input.json") as f: inp = f.read()
        p = subprocess.Popen([os.path.abspath("truss_engine.exe")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate(input=inp)
        if p.returncode == 0:
            with open("data/output.json", "w") as f: f.write(out)
            st.toast("Success! 📊", icon="✅")
            st.rerun()
        else: st.error("Engine Error")

    if os.path.exists("data/output.json"):
        try:
            with open("data/output.json", 'r') as f: results_data = json.load(f)
            
            if results_data.get("status") == "unstable":
                st.warning("⚠️ SYSTEM UNSTABLE: The bridge geometry is incomplete or missing necessary supports (Pinned/Roller).")
                st.stop()
            
            # Metrics Calculation
            total_load_kn = sum(edited_loads["Weight (kN)"].dropna())
            max_stress_mpa = max([abs(e['stress'])/1e6 for e in results_data['elements']]) if results_data['elements'] else 0
            
            # Efficiency Proxy (Load / Total Material Volume)
            vol = sum([np.sqrt((node_map[e['start']]['x']-node_map[e['end']]['x'])**2 + (node_map[e['start']]['y']-node_map[e['end']]['y'])**2) * area_in_meters_squared for e in final_beams_list])
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Load", f"{total_load_kn:.1f} kN")
            m2.metric("Material Usage", f"{vol*1000:.2f} dm³")
            m3.metric("Max Stress", f"{max_stress_mpa:.1f} MPa")

            safety_factors = [e['safety'] for e in results_data['elements']]
            min_safety_factor = min(safety_factors) if safety_factors else 0
            
            if min_safety_factor > 1: bg, tc, txt = ("#d1fae5", "#065f46", "System is SAFE ✅")
            else: bg, tc, txt = ("#fee2e2", "#991b1b", "System is FAILING ❌")
            st.markdown(f'<div style="background:{bg}; color:{tc}; padding:1rem; border-radius:12px; text-align:center; font-weight:800; margin-bottom:1rem; border:1px solid {tc}40;">{txt}</div>', unsafe_allow_html=True)

            # 1. Reaction Forces Table
            st.markdown("#### Support Reactions")
            
            support_ids = set()
            if os.path.exists("data/input.json"):
                try: 
                    with open("data/input.json", 'r') as f_in:
                        nodes_in = json.load(f_in).get('nodes', [])
                        support_ids = {n['id'] for n in nodes_in if n.get('type') in ["Pinned Support", "Roller Support", "Fixed (Rigid)"]}
                except: pass

            reaction_list = [{"Joint": n['id'], "Rx (kN)": f"{n.get('rx',0)/1e3:.2f}", "Ry (kN)": f"{n.get('ry',0)/1e3:.2f}",
                              "Angle (°)": f"{np.degrees(np.arctan2(n.get('ry',0), n.get('rx',0))):.1f}"} 
                           for n in results_data['nodes'] 
                           if abs(n.get('rx',0)) > 10 or abs(n.get('ry',0)) > 10 or n['id'] in support_ids]
            
            if reaction_list: st.dataframe(pd.DataFrame(reaction_list), use_container_width=True, hide_index=True)
            else: st.info("No significant reaction forces.")

            # 2. Beam Report
            st.markdown("#### Beam Report")
            def get_ftype(f): return "Tension 🔵" if f > 0.01 else ("Compression 🟠" if f < -0.01 else "Neutral")
            
            beam_report_list = [{"Beam": f"#{e['id']}", "Force (kN)": f"{e['force']/1e3:.2f}", 
                                 "Type": get_ftype(e['force']/1e3), "FS": f"{e['safety']:.2f}"} 
                                for e in results_data['elements']]
            
            if beam_report_list: st.dataframe(pd.DataFrame(beam_report_list), use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Error reading calculation results: {e}")
