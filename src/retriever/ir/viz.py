from typing import Dict, List, Any, Tuple

from retriever.ir.struct import IRStruct, IRNode

# --- HTML Template with Cytoscape.js and Dagre ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Retriever Pipeline Visualization</title>
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1, maximum-scale=1">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js"></script>
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #333333;
            --header-bg: #f8f9fa;
            --border-color: #ddd;
            --accent-orange: #ff6b35; /* Astro-like Orange */
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --color-source-bg: #fff7ed; --color-source-border: #f97316; /* Orange */
            --color-sink-bg: #faf5ff; --color-sink-border: #9333ea; /* Purple */
            --color-inter-bg: #eff6ff; --color-inter-border: #3b82f6; /* Blue */
            
            --text-main: #374151;
        }
        body { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; background-color: var(--bg-color); color: var(--text-color); margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column; }
        
        #header {
            padding: 15px 25px;
            background-color: var(--header-bg);
            border-bottom: 2px solid var(--border-color);
            display: flex; justify-content: space-between; align-items: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        h1 { margin: 0; font-size: 1.4rem; font-weight: 700; color: #1f2937; display: flex; align-items: center; gap: 10px; }
        .logo-mark { width: 12px; height: 12px; background: var(--color-inter-border); border-radius: 50%; display: inline-block; }
        
        #cy { flex: 1; min-height: 0; background-color: #fafafa; }
        
        #info-panel {
            position: absolute; top: 80px; right: 25px; width: 320px;
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid var(--border-color);
            padding: 20px; border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            backdrop-filter: blur(8px);
            transform: translateX(120%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 100;
        }
        #info-panel.visible { transform: translateX(0); }
        #info-panel h3 { margin-top: 0; color: #111; border-bottom: 2px solid var(--border-color); padding-bottom: 10px; font-size: 1.1rem; }
        
        .prop { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.9rem; align-items: baseline; }
        .prop-key { color: #666; font-weight: 500; }
        .prop-val { color: #111; font-family: 'Menlo', 'Monaco', monospace; font-size: 0.85rem; background: #f3f4f6; padding: 2px 5px; border-radius: 4px; }
        
        .badge { padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
        .badge.rate { background: #f3f4f6; color: #333; border: 1px solid #ccc; }
        .badge.trigger { background: #f3f4f6; color: #333; border: 1px dashed #ccc; }
        
        .legend { display: flex; gap: 15px; font-size: 0.85rem; color: #555; font-weight: 500; }
        .legend-item { display: flex; align-items: center; gap: 6px; }
        .dot { width: 12px; height: 12px; border-radius: 4px; }
        
        .service-badge {
             background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0;
             font-size: 0.7rem; padding: 2px 6px; border-radius: 4px;
             margin-left: 5px; vertical-align: middle; font-family: monospace;
        }
    </style>
</head>
<body>
    <div id="header">
        <h1><span class="logo-mark"></span>Retriever <span style="font-weight:400; color:#666; font-size:1.1rem; margin-left:8px;" id="pipeline-name">Loading...</span></h1>
        <div class="legend">
            <!-- Topology Colors -->
            <div class="legend-item"><div class="dot" style="background:var(--color-source-bg); border:2px solid var(--color-source-border)"></div>Source (Orange)</div>
            <div class="legend-item"><div class="dot" style="background:var(--color-inter-bg); border:2px solid var(--color-inter-border)"></div>Intermediate (Blue)</div>
            <div class="legend-item"><div class="dot" style="background:var(--color-sink-bg); border:2px solid var(--color-sink-border)"></div>Sink (Purple)</div>
            
            <div style="width:1px; height:15px; background:#ddd; margin:0 5px;"></div>
            
            <!-- Clock Styles -->
            <div class="legend-item"><div class="dot" style="background:#fff; border:2px solid #666"></div>Rate (Solid)</div>
            <div class="legend-item"><div class="dot" style="background:#fff; border:2px dashed #666"></div>Trigger (Dashed)</div>
            <div class="legend-item"><div class="dot" style="background:#fff; border:2px dotted #666"></div>Hybrid (Dotted)</div>
        </div>
    </div>
    <div id="cy"></div>
    <div id="info-panel">
        <h3 id="panel-title">Node Info</h3>
        <div id="panel-content"></div>
    </div>

    <script>
        const irData = __IR_DATA__;

        try {
            document.getElementById('pipeline-name').innerText = irData.metadata.name;
        } catch(e) {
            console.error("Failed to set title", e);
        }
        
        // Helper to check for sources/sinks based on edges
        const sourceNodes = new Set(irData.nodes.map(n => n.id));
        const sinkNodes = new Set(irData.nodes.map(n => n.id));
        
        irData.edges.forEach(edge => {
            sinkNodes.delete(edge.source.node);
            sourceNodes.delete(edge.destination.node);
        });

        // Transform IR to Cytoscape elements
        const elements = [];
        
        // Nodes
        irData.nodes.forEach(node => {
            const clock = node.config.clock || {};
            let clockType = "Unknown";
            let clockDetail = "";
            
            // Check for IR structure which is key-based: {'Rate': {...}} or {'Trigger': {...}}
            // Hybrid Detection: Check if explicitly Hybrid OR both are present
            if (clock.Hybrid) {
                clockType = "Hybrid";
                const hz = clock.Hybrid.hz;
                const fields = clock.Hybrid.trigger_fields || clock.Hybrid.trigger;
                clockDetail = `${hz} Hz + on ${fields}`;
            } else if (clock.Rate && clock.Trigger) {
                clockType = "Hybrid";
                const hz = clock.Rate.hz;
                const fields = clock.Trigger.fields || clock.Trigger.ports;
                clockDetail = `${hz} Hz + on ${fields}`;
            } else if (clock.Rate) {
                clockType = "Rate";
                clockDetail = `${clock.Rate.hz} Hz`;
            } else if (clock.Trigger) {
                clockType = "Trigger";
                const fields = clock.Trigger.fields || clock.Trigger.ports;
                clockDetail = `on ${fields}`;
            } else if (clock.type) {
                // Fallback for flat config if strictly typed
                clockType = clock.type;
                clockDetail = clock.hz ? `${clock.hz} Hz` : (clock.ports ? `on ${clock.ports}` : "");
            }

            // Label shows just the class/name part of the ID
            let label = node.id;
            if (label.includes('_')) {
                label = label.split('_')[0];
            }
            
            // Add clock info to label for visibility
            if (clockType === "Rate" && clockDetail) {
                 label += `\n@ ${clockDetail}`;
            } else if (clockType === "Trigger") {
                 label += `\n@ Trigger`;
            } else if (clockType === "Hybrid") {
                 label += `\n@ Hybrid`;
            } else {
                 label += `\n@ ${clockType}`;
            }
            
            const classes = [];
            // Topology Classes
            let isIntermediate = true;
            if (sourceNodes.has(node.id)) { classes.push('source'); isIntermediate = false; }
            if (sinkNodes.has(node.id)) { classes.push('sink'); isIntermediate = false; }
            if (isIntermediate) classes.push('intermediate');
            
            // Clock Classes
            classes.push(clockType.toLowerCase());

            elements.push({
                data: {
                    id: node.id,
                    label: label,
                    type: node.type,
                    clock: clockType,
                    clockDetail: clockDetail,
                    inputs: Object.keys(node.inputs),
                    outputs: Object.keys(node.outputs),
                    services: node.service_handlers ? node.service_handlers.map(s => s.service_id) : []
                },
                classes: classes.join(' ')
            });
        });

        // Edges
        // Edges
        // Track edge counts between node pairs to calculate offsets for unbundled-bezier
        const pair_counts = {};

        irData.edges.forEach(edge => {
             const source = edge.source.node;
             const target = edge.destination.node;
             const label = `${edge.source.port} → ${edge.destination.port}`;
             
             // Group by sorted pair to handle parallel edges in either direction
             // Using sorted IDs ensures A->B and B->A share the same "lane set"
             const sorted_ids = [source, target].sort();
             const pairKey = sorted_ids.join('_');
             
             // Determine direction relative to sort order
             // If source is first in sort, we are "Forward". If source is second, "Backward".
             const isForward = (source === sorted_ids[0]);
             
             if (!pair_counts[pairKey]) { pair_counts[pairKey] = 0; }
             const count = pair_counts[pairKey];
             pair_counts[pairKey] += 1;
             
             // Calculate Curvature Offset (C-Curve Arch)
             // To avoid overlap between A->B and B->A, we need them to arc into DIFFERENT spaces.
             // Strategy:
             // Lane 0: Dist 20.
             // Lane 1: Dist -20.
             // Lane 2: Dist 40. ...
             
             const laneIndex = Math.floor(count / 2);
             const laneSide = (count % 2 === 0) ? 1 : -1;
             
             // Base magnitude + step
             const magnitude = 25 + (laneIndex * 25);
             const absDist = magnitude;
             
             // Algorithm:
             // 1. Assign unique integer slot to edge: 0, 1, 2...
             // 2. Map slot to Spatial Side: Even=East (+), Odd=West (-)
             // 3. Logic: dist = absDist * side * (isForward ? 1 : -1)
             
             const side = (count % 2 === 0) ? 1 : -1; // 1=East, -1=West
             const dist = absDist * side * (isForward ? 1 : -1);
             
             // Cytoscape expected format for single control point
             const curveDist = dist.toString();
             
             elements.push({
                 data: {
                     source: source,
                     target: target,
                     label: label,
                     id: edge.id,
                     qsize: edge.qsize,
                     curveDist: curveDist
                 }
             });
        });

        // CDN Health Check
        if (!window.cytoscape) { alert("Error: Cytoscape.js CDN failed to load."); }
        
        try {
            var cy = cytoscape({
                container: document.getElementById('cy'),
                elements: elements,
                style: [
                    {
                        selector: 'node',
                        style: {
                            'label': 'data(label)',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'background-color': '#f3f4f6',
                            'border-width': 3,
                            'border-style': 'solid', /* Default */
                            'border-color': '#9ca3af',
                            'color': '#374151',
                            'font-size': '13px',
                            'font-weight': 600,
                            'width': 'label',
                            'height': 'label',
                            'padding': '14px',
                            'shape': 'round-rectangle',
                            'text-wrap': 'wrap',
                            'text-justification': 'center'
                        }
                    },
                    /* Clock Styles -> Border Style */
                    {
                        selector: 'node.rate',
                        style: { 'border-style': 'solid' }
                    },
                    {
                        selector: 'node.trigger',
                        style: { 'border-style': 'dashed' }
                    },
                    {
                        selector: 'node.hybrid',
                        style: { 'border-style': 'dotted' }
                    },
                    
                    /* Topology Styles -> Colors */
                    {
                         selector: 'node.source',
                         style: {
                             'background-color': '#fff7ed',
                             'border-color': '#f97316',
                             'color': '#9a3412'
                         }
                    },
                    {
                         selector: 'node.sink',
                         style: {
                             'background-color': '#faf5ff',
                             'border-color': '#9333ea',
                             'color': '#6b21a8'
                         }
                    },
                    {
                         selector: 'node.intermediate',
                         style: {
                             'background-color': '#eff6ff',
                             'border-color': '#3b82f6',
                             'color': '#1e40af'
                         }
                    },
                    
                    {
                        selector: ':selected',
                        style: { 'border-width': 4, 'border-color': '#1f2937', 'background-color': '#ffffff', 'shadow-blur': 10, 'shadow-color': 'rgba(0,0,0,0.2)' }
                    },
                    {
                        selector: ':selected',
                        style: { 'border-width': 4, 'border-color': '#1f2937', 'background-color': '#ffffff', 'shadow-blur': 10, 'shadow-color': 'rgba(0,0,0,0.2)' }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 3,
                            'line-color': '#94a3b8',
                            'line-fill': 'linear-gradient',
                            'line-gradient-stop-colors': '#10b981 #ef4444', /* Green to Red */
                            'line-gradient-stop-positions': '0 100',
                            'target-arrow-color': '#ef4444',
                            'target-arrow-shape': 'triangle',
                            'target-arrow-shape': 'triangle',
                            'target-arrow-shape': 'triangle',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'unbundled-bezier',
                            'control-point-distances': 'data(curveDist)',
                            'control-point-weights': '0.5', 
                            'label': 'data(label)',
                            'font-size': '9px',
                            'color': '#64748b',
                            'text-rotation': 'autorotate',
                            'text-margin-y': -10,
                            'text-background-opacity': 1,
                            'text-background-color': '#ffffff',
                            'text-background-padding': '2px',
                            'text-border-width': 1,
                            'text-border-color': '#e2e8f0',
                            'text-border-style': 'solid',
                            'text-border-opacity': 1,
                            'ghost': 'yes',
                            'ghost-offset-x': 0,
                            'ghost-offset-y': 1,
                            'ghost-opacity': 0.1
                        }
                    },
                     {
                        selector: 'edge:selected',
                        style: { 'line-color': '#ff6b35', 'target-arrow-color': '#ff6b35', 'color': '#ff6b35', 'width': 3, 'z-index': 99 }
                    }
                ],
                layout: {
                    name: 'dagre',
                    rankDir: 'LR',
                    spacingFactor: 1.2,
                    animate: false,
                    nodeSep: 60,
                    rankSep: 180,
                    edgeSep: 80,
                    ranker: 'network-simplex'
                }
            });

            // Ensure graph fits in view
            cy.ready(function() {
                cy.fit();
                cy.zoom({ level: cy.zoom() * 0.95 }); // Zoom out slightly for breathing room
                cy.center();
                console.log("Cytoscape ready and fitted.");
            });
            
        } catch (err) {
            console.error(err);
            alert("Error initializing Visualization: " + err.message);
        }

        const panel = document.getElementById('info-panel');
        const title = document.getElementById('panel-title');
        const content = document.getElementById('panel-content');

        cy.on('tap', 'node', function(evt){
            const node = evt.target;
            const data = node.data();
            
            title.innerText = data.label.replace('\\n', ' '); // Remove newline for title
            
            let html = `<div class="prop"><span class="badge ${data.clock.toLowerCase()}">${data.clock}</span></div>`;
            if (data.clockDetail) html += `<div class="prop"><span class="prop-key">Config:</span><span class="prop-val">${data.clockDetail}</span></div>`;
            
            html += `<hr style="border:0; border-bottom:1px solid #eee; margin:15px 0"/>`;
            
            html += `<div class="prop"><span class="prop-key">Type:</span><span class="prop-val">${data.type}</span></div>`;
            html += `<div class="prop"><span class="prop-key">ID:</span><span class="prop-val" style="font-size:0.75rem">${data.id}</span></div>`;
            
            if (data.inputs && data.inputs.length) {
                 html += `<div style="margin-top:10px"><span class="prop-key">Inputs:</span><div style="margin-top:4px; display:flex; flex-wrap:wrap; gap:4px">`;
                 data.inputs.forEach(i => html += `<span class="prop-val">${i}</span>`);
                 html += `</div></div>`;
            }
            if (data.outputs && data.outputs.length) {
                 html += `<div style="margin-top:10px"><span class="prop-key">Outputs:</span><div style="margin-top:4px; display:flex; flex-wrap:wrap; gap:4px">`;
                 data.outputs.forEach(o => html += `<span class="prop-val">${o}</span>`);
                 html += `</div></div>`;
            }
            
            if (data.services && data.services.length) {
                html += `<div style="margin-top:15px; border-top:1px dashed #eee; padding-top:10px"><span class="prop-key">Services:</span>`;
                data.services.forEach(s => html += `<span class="service-badge">${s}</span>`);
                html += `</div>`;
            }

            content.innerHTML = html;
            panel.classList.add('visible');
        });

        cy.on('tap', function(evt){
            if(evt.target === cy){
                panel.classList.remove('visible');
            }
        });
    </script>
</body>
</html>
"""

def get_node_clock_info(ir_node: IRNode) -> Tuple[str, str]:
    """Extract readable clock info from IR node config."""
    clock_cfg = ir_node.config.get("clock", {})
    if not clock_cfg:
        return "Unknown", ""
    
    # In IR, clock config is usually a dict with the clock type as the key
    # e.g. {'Rate': {'hz': 10}} or {'Trigger': {'fields': ['obs']}}
    
    if "Rate" in clock_cfg:
        c_type = "Rate"
        params = clock_cfg["Rate"]
        hz = params.get("hz")
        detail = f"{hz} Hz" if hz else ""
    elif "Trigger" in clock_cfg:
        c_type = "Trigger"
        params = clock_cfg["Trigger"]
        # 'fields' is the key in the JSON output we saw
        fields = params.get("fields") or params.get("ports")
        detail = f"on {fields}" if fields else ""
    elif "Hybrid" in clock_cfg:
        c_type = "Hybrid"
        params = clock_cfg["Hybrid"]
        hz = params.get("hz")
        fields = params.get("trigger_fields") or params.get("trigger")
        detail = f"{hz} Hz + on {fields}"
    else:
        # Fallback if structure is different
        c_type = clock_cfg.get("type", "Unknown")
        detail = str(clock_cfg)
            
    return c_type, detail

def generate_ascii_graph(ir: IRStruct) -> str:
    """ASCII Tree View using IR Structure, topologically sorted."""
    
    output = []
    output.append(f"Pipeline: {ir.metadata.name}")
    output.append("=" * (len(ir.metadata.name) + 10))
    
    if ir.topology.has_cycle:
        output.append("NOTE: Cycle detected in graph topology (expected for closed-loop systems).")
    
    # 1. Build Adjacency
    adj: Dict[str, List[Any]] = {node.id: [] for node in ir.nodes}
    for edge in ir.edges:
        src_id = edge.source.node
        if src_id in adj:
            adj[src_id].append(edge)

    # 2. Topological Sort (Kahn's algorithm approx/DFS)
    # Since we have cycles, standard topo sort fails. Use DFS with visited set.
    # But for display, we want "Sources first".
    # Calculate in-degrees
    in_degree = {n.id: 0 for n in ir.nodes}
    for edge in ir.edges:
        in_degree[edge.destination.node] += 1
        
    ordered_nodes = []
    # Simple heuristic: Start with 0 in-degree, then BFS
    queue = [n for n in ir.nodes if in_degree[n.id] == 0]
    visited = set(n.id for n in queue)
    
    # If no 0 in-degree (pure cycle), pick arbitrary (e.g. first definition)
    if not queue and ir.nodes:
        queue = [ir.nodes[0]]
        visited.add(ir.nodes[0].id)
        
    # Mapping id -> node
    id_to_node = {n.id: n for n in ir.nodes}
    
    while queue:
        n = queue.pop(0)
        ordered_nodes.append(n)
        
        # Add neighbors not visited
        # Sort neighbors for deterministic output
        neighbors = sorted([e.destination.node for e in adj[n.id]])
        for neigh_id in neighbors:
            if neigh_id not in visited:
                visited.add(neigh_id)
                queue.append(id_to_node[neigh_id])
    
    # Add any remaining nodes (disconnected components or unreachable in this simple BFS)
    for n in ir.nodes:
        if n.id not in visited:
            ordered_nodes.append(n)
            
    # 3. Print
    for i, node in enumerate(ordered_nodes):
        c_type, c_detail = get_node_clock_info(node)
        clock_str = f"{c_type}({c_detail})" if c_detail else c_type
        
        # Simplify ID for display (NodeClass_123 -> NodeClass)
        display_name = node.id
        if "_" in display_name:
            display_name = display_name.split("_")[0]
            
        output.append(f"[{display_name}] <{clock_str}>")
        
        outgoing = adj[node.id]
        if not outgoing:
            output.append("   (no outputs)")
        else:
            for edge in outgoing:
                dest_id = edge.destination.node
                dest_display = dest_id.split("_")[0] if "_" in dest_id else dest_id
                
                adapter_info = ""
                if edge.adapter:
                     adapter_name = list(edge.adapter.keys())[0]
                     adapter_info = f" via {adapter_name}"
                
                # Check for cycle/feedback (if dest is earlier in list)
                # Note: this is a heuristic based on print order
                is_feedback = False
                for prev in ordered_nodes[:i+1]:
                    if prev.id == dest_id:
                        is_feedback = True
                        break
                
                arrow = "-->"
                note = ""
                if is_feedback:
                    note = " (feedback/cycle)"
                    arrow = "-->" # Could use different arrow
                
                output.append(f"   --({edge.source.port} -> {edge.destination.port}{adapter_info}){arrow} [{dest_display}]{note}")
        output.append("")
        
    return "\n".join(output)

def save_interactive_html(ir: IRStruct, filename: str = "pipeline_viz.html") -> None:
    """Export the pipeline visualization to a self-contained HTML file using IR."""
    
    # Serialize IR to JSON
    json_data = ir.to_json(indent=2)
    
    # Inject into template
    html_content = HTML_TEMPLATE.replace("__IR_DATA__", json_data)
    
    with open(filename, "w") as f:
        f.write(html_content)
    print(f"\n[Success] Visualization saved to: {filename}")
    print(f"Open this file in your browser to view the interactive graph.")
