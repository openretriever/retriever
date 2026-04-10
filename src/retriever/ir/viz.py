from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

from retriever.ir.core import IR, IRNode

# --- HTML Template with Cytoscape.js and Dagre ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Retriever Pipeline Visualization</title>
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1, maximum-scale=1">
    __CYTOSCAPE_SCRIPT__
    __DAGRE_SCRIPT__
    __CYTOSCAPE_DAGRE_SCRIPT__
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #333333;
            --header-bg: #f8f9fa;
            --border-color: #ddd;
            --accent-orange: #ff6b35; /* Astro-like Orange */
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-teal: #0f766e;
            --color-source-bg: #fff7ed; --color-source-border: #f97316; /* Orange */
            --color-sink-bg: #faf5ff; --color-sink-border: #9333ea; /* Purple */
            --color-inter-bg: #eff6ff; --color-inter-border: #3b82f6; /* Blue */
            --color-pipeline-bg: #ecfeff; --color-pipeline-border: #0f766e; /* Teal */
            
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
        
        #cy { flex: 1; min-height: 0; background-color: #fafafa; position: relative; }
        #fallback-ascii {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            overflow: auto;
            margin: 0;
            padding: 16px 18px;
            font-family: 'Menlo', 'Monaco', monospace;
            font-size: 12px;
            color: #4b5563;
            white-space: pre;
            background: transparent;
            z-index: 1;
        }
        
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
        <h1><span class="logo-mark"></span>Retriever <span style="font-weight:400; color:#666; font-size:1.1rem; margin-left:8px;" id="pipeline-name">__PIPELINE_NAME__</span></h1>
        <div class="legend">
            <!-- Topology Colors -->
            <div class="legend-item"><div class="dot" style="background:var(--color-source-bg); border:2px solid var(--color-source-border)"></div>Source (Orange)</div>
            <div class="legend-item"><div class="dot" style="background:var(--color-inter-bg); border:2px solid var(--color-inter-border)"></div>Intermediate (Blue)</div>
            <div class="legend-item"><div class="dot" style="background:var(--color-sink-bg); border:2px solid var(--color-sink-border)"></div>Sink (Purple)</div>
            <div class="legend-item"><div class="dot" style="background:var(--color-pipeline-bg); border:3px double var(--color-pipeline-border)"></div>Nested Pipeline</div>
            
            <div style="width:1px; height:15px; background:#ddd; margin:0 5px;"></div>
            
            <!-- Clock Styles -->
            <div class="legend-item"><div class="dot" style="background:#fff; border:2px solid #666"></div>Rate (Solid)</div>
            <div class="legend-item"><div class="dot" style="background:#fff; border:2px dashed #666"></div>Trigger (Dashed)</div>
            <div class="legend-item"><div class="dot" style="background:#fff; border:2px dotted #666"></div>Hybrid (Dotted)</div>
        </div>
    </div>
    <div id="cy"><pre id="fallback-ascii">__ASCII_GRAPH__</pre></div>
    <div id="info-panel">
        <h3 id="panel-title">Node Info</h3>
        <div id="panel-content"></div>
    </div>

    <script>
        const irData = __IR_DATA__;

        const fallback = document.getElementById('fallback-ascii');
        try {
            document.getElementById('pipeline-name').innerText = irData.metadata.name;
        } catch(e) {
            console.error("Failed to set title", e);
        }

        function shortPipelineName(name) {
            if (!name) return "pipeline";
            const parts = String(name).split('.');
            return parts[parts.length - 1] || String(name);
        }

        function previewWrappedPipeline(meta) {
            const nodes = (((meta || {}).internal || {}).nodes || []);
            if (!nodes.length) return "";
            if (nodes.length <= 3) {
                return nodes.map(n => n.id || n.type || "?").join(" -> ");
            }
            return `${nodes.length} inner flows`;
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
        const pipelineGroupIds = new Set();

        function ensurePipelineGroupElements(groups) {
            let parentGroupId = null;
            groups.forEach(group => {
                if (!group || !group.group_id) return;
                if (!pipelineGroupIds.has(group.group_id)) {
                    elements.push({
                        data: {
                            id: group.group_id,
                            parent: parentGroupId || undefined,
                            label: `${group.wrapper_node_id}\n[pipeline: ${shortPipelineName(group.pipeline_name)}]`,
                            wrappedPipeline: {
                                pipeline_name: group.pipeline_name,
                                summary: group.summary,
                                surface: group.surface,
                                internal: group.internal
                            },
                            isPipelineGroup: true
                        },
                        classes: 'pipeline-group'
                    });
                    pipelineGroupIds.add(group.group_id);
                }
                parentGroupId = group.group_id;
            });
            return parentGroupId;
        }
        
        // Nodes
        irData.nodes.forEach(node => {
            const clock = node.config.clock || {};
            const pipelineGroups = node.config.viz && Array.isArray(node.config.viz.pipeline_groups)
                ? node.config.viz.pipeline_groups
                : [];
            const parentGroupId = ensurePipelineGroupElements(pipelineGroups);
            const primaryGroup = pipelineGroups.length ? pipelineGroups[pipelineGroups.length - 1] : null;
            const wrappedPipeline = node.config.viz && node.config.viz.kind === "pipeline"
                ? node.config.viz
                : null;
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
            let label = primaryGroup && primaryGroup.local_node_id ? primaryGroup.local_node_id : node.id;
            if (!primaryGroup && label.includes('__')) {
                label = label.split('__')[0];
            }

            if (wrappedPipeline) {
                label += `\n[pipeline: ${shortPipelineName(wrappedPipeline.pipeline_name)}]`;
                const preview = previewWrappedPipeline(wrappedPipeline);
                if (preview) {
                    label += `\n${preview}`;
                }
            }
            
            // Add clock info to label for visibility
            if (clockType === "Rate" && clockDetail) {
                 label += `\n@ ${clockDetail}`;
            } else if (clockType === "Trigger") {
                 label += `\n@ Trigger`;
            } else if (clockType === "Hybrid" && clockDetail) {
                 // Show detailed Hybrid info: "@ 2.5 Hz & Trigger"
                 const hz = clock.Hybrid ? clock.Hybrid.hz : (clock.Rate ? clock.Rate.hz : "?");
                 label += `\n@ ${hz} Hz & Trigger`;
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
            if (wrappedPipeline) classes.push('wrapped-pipeline');

            elements.push({
                data: {
                    id: node.id,
                    label: label,
                    type: node.type,
                    clock: clockType,
                    clockDetail: clockDetail,
                    inputs: Object.keys(node.inputs),
                    outputs: Object.keys(node.outputs),
                    services: node.service_handlers ? node.service_handlers.map(s => s.service_id) : [],
                    wrappedPipeline: wrappedPipeline,
                    pipelineGroup: primaryGroup,
                    parent: parentGroupId || undefined
                },
                classes: classes.join(' ')
            });
        });

        // Edges
        // Track edge counts between node pairs to calculate offsets for unbundled-bezier
        const pair_counts = {};
        const fanin_counts = {}; // Track fan-in index per (dstNode, logicalPort)


        irData.edges.forEach(edge => {
             const source = edge.source.node;
             const target = edge.destination.node;
             
             // Handle Fan-in Labeling
             let dstPortDisplay = edge.destination.port;
             if (dstPortDisplay.startsWith("_fanin/")) {
                  // Format: _fanin/SourceNode/LogicalPort
                  const parts = dstPortDisplay.split('/');
                  if (parts.length >= 3) {
                      const logicalPort = parts[2];
                      const key = `${target}_${logicalPort}`;
                      if (!fanin_counts[key]) fanin_counts[key] = 0;
                      fanin_counts[key]++;
                      dstPortDisplay = `${logicalPort} (${fanin_counts[key]})`;
                  }
             }
             
             let label = `${edge.source.port} → ${dstPortDisplay}`;
             
             // Extract Adapter Name if present
             if (edge.adapter) {
                 const adapterName = Object.keys(edge.adapter)[0];
                 label += `: ${adapterName}`;
             }
             
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

        function renderWrappedPorts(title, ports) {
            if (!ports || !ports.length) return "";
            let html = `<div style="margin-top:12px"><span class="prop-key">${title}:</span><div style="margin-top:6px; display:flex; flex-direction:column; gap:6px">`;
            ports.forEach(port => {
                html += `<div class="prop"><span class="prop-key">${port.external_name}</span><span class="prop-val">${port.node_id}.${port.port}</span></div>`;
            });
            html += `</div></div>`;
            return html;
        }

        function renderWrappedNodeList(nodes) {
            if (!nodes || !nodes.length) return "";
            let html = `<div style="margin-top:12px"><span class="prop-key">Internal flows:</span><div style="margin-top:6px; display:flex; flex-wrap:wrap; gap:4px">`;
            nodes.forEach(node => {
                html += `<span class="prop-val">${node.id}</span>`;
            });
            html += `</div></div>`;
            return html;
        }

        // CDN Health Check
        if (!window.cytoscape) { alert("Error: Cytoscape.js CDN failed to load."); }
        
        var cy = null;
        try {
            cy = cytoscape({
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
                            'text-justification': 'center',
                            'text-max-width': '220px'
                        }
                    },
                    {
                        selector: 'node.pipeline-group',
                        style: {
                            'background-color': '#ccfbf1',
                            'background-opacity': 0.22,
                            'border-color': '#0f766e',
                            'border-width': 3,
                            'border-style': 'double',
                            'color': '#134e4a',
                            'font-size': '12px',
                            'font-weight': 700,
                            'text-valign': 'top',
                            'text-halign': 'center',
                            'padding': '28px',
                            'compound-sizing-wrt-labels': 'include',
                            'shape': 'round-rectangle'
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
                        selector: 'node.wrapped-pipeline',
                        style: {
                            'background-color': '#ecfeff',
                            'border-color': '#0f766e',
                            'border-width': 5,
                            'border-style': 'double',
                            'color': '#115e59',
                            'padding': '18px'
                        }
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
                    spacingFactor: 1.4,
                    animate: false,
                    nodeSep: 80,
                    rankSep: 220,
                    edgeSep: 100,
                    ranker: 'network-simplex',
                    padding: 80
                }
            });
            if (fallback) { fallback.style.display = 'none'; }

            // Ensure graph fits in view
            cy.ready(function() {
                cy.fit(80); // Add 80px padding
                cy.zoom({ level: Math.min(cy.zoom() * 0.85, 1.2) }); // Zoom out more, cap at 1.2
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

        if (cy) cy.on('tap', 'node', function(evt){
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

            if (data.pipelineGroup) {
                html += `<div style="margin-top:15px; border-top:1px dashed #dbeafe; padding-top:10px"><span class="prop-key">Pipeline group:</span>`;
                html += `<div class="prop"><span class="prop-key">Stage:</span><span class="prop-val">${data.pipelineGroup.wrapper_node_id}</span></div>`;
                html += `<div class="prop"><span class="prop-key">Pipeline:</span><span class="prop-val">${data.pipelineGroup.pipeline_name}</span></div>`;
                html += `</div>`;
            }

            if (data.wrappedPipeline) {
                const wrapped = data.wrappedPipeline;
                html += `<div style="margin-top:15px; border-top:1px dashed #d1fae5; padding-top:10px"><span class="prop-key">Nested pipeline:</span>`;
                html += `<div class="prop"><span class="prop-key">Name:</span><span class="prop-val">${wrapped.pipeline_name}</span></div>`;
                if (wrapped.summary) {
                    html += `<div class="prop"><span class="prop-key">Size:</span><span class="prop-val">${wrapped.summary.node_count} flows / ${wrapped.summary.edge_count} edges</span></div>`;
                }
                html += renderWrappedPorts('Surface inputs', wrapped.surface ? wrapped.surface.inputs : []);
                html += renderWrappedPorts('Surface outputs', wrapped.surface ? wrapped.surface.outputs : []);
                html += renderWrappedNodeList(wrapped.internal ? wrapped.internal.nodes : []);
                html += `</div>`;
            }

            content.innerHTML = html;
            panel.classList.add('visible');
        });

        if (cy) cy.on('tap', function(evt){
            if(evt.target === cy){
                panel.classList.remove('visible');
            }
        });
    </script>
</body>
</html>
"""

_ASSET_DIR = Path(__file__).resolve().parent / "assets"
_CYTOSCAPE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"
_DAGRE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js"
_CYTOSCAPE_DAGRE_CDN = "https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js"


def _load_asset(name: str) -> Optional[str]:
    asset_path = _ASSET_DIR / name
    if not asset_path.exists():
        return None
    text = asset_path.read_text(encoding="utf-8")
    return text.replace("</script>", "<\\/script>")


def _script_tag_inline_or_cdn(asset_name: str, cdn_url: str) -> str:
    inline = _load_asset(asset_name)
    if inline is None:
        return f'<script src="{cdn_url}"></script>'
    return f"<script>\n{inline}\n</script>"


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


def _get_wrapped_pipeline_viz(ir_node: IRNode) -> Optional[Dict[str, Any]]:
    viz = ir_node.config.get("viz")
    if isinstance(viz, dict) and viz.get("kind") == "pipeline":
        return viz
    return None


def _get_pipeline_groups(ir_node: IRNode) -> List[Dict[str, Any]]:
    viz = ir_node.config.get("viz")
    if not isinstance(viz, dict):
        return []
    groups = viz.get("pipeline_groups")
    if isinstance(groups, list):
        return [group for group in groups if isinstance(group, dict)]
    return []


def _format_wrapped_port_bindings(ports: List[Dict[str, Any]]) -> str:
    bindings = []
    for port in ports:
        external = port.get("external_name") or port.get("port") or "port"
        node_id = port.get("node_id") or "node"
        node_port = port.get("port") or "port"
        bindings.append(f"{external}->{node_id}.{node_port}")
    return ", ".join(bindings)


from retriever.ir.core import IR


def generate_ascii_graph(ir: "IR") -> str:
    """
    Generate ASCII representation of the IR graph.

    Args:
        ir: The IR object to visualize

    Returns:
        String containing ASCII graph
    """

    output = []
    output.append(f"Pipeline: {ir.metadata.name}")
    output.append("=" * (len(ir.metadata.name) + 10))

    if ir.topology.has_cycle:
        output.append(
            "NOTE: Cycle detected in graph topology (expected for closed-loop systems)."
        )

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
    seen_pipeline_groups: set[str] = set()

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
        pipeline_groups = _get_pipeline_groups(node)
        primary_group = pipeline_groups[-1] if pipeline_groups else None
        display_name = (
            primary_group.get("local_node_id") or node.id
            if primary_group
            else node.id
        )
        if isinstance(display_name, str) and not primary_group and "__" in display_name:
            display_name = display_name.split("__")[0]

        for group in pipeline_groups:
            group_id = str(group.get("group_id") or "")
            if not group_id or group_id in seen_pipeline_groups:
                continue
            seen_pipeline_groups.add(group_id)
            output.append(
                f"+ Pipeline [{group.get('wrapper_node_id', 'stage')}] "
                f"({group.get('pipeline_name', 'pipeline')})"
            )

        output.append(f"[{display_name}] <{clock_str}>")

        wrapped_pipeline = _get_wrapped_pipeline_viz(node)
        if wrapped_pipeline is not None:
            pipeline_name = wrapped_pipeline.get("pipeline_name", "pipeline")
            output.append(f"   pipeline: {pipeline_name}")

            summary = wrapped_pipeline.get("summary", {})
            if summary:
                output.append(
                    "   contains: "
                    f"{summary.get('node_count', '?')} flows, {summary.get('edge_count', '?')} edges"
                )

            surface = wrapped_pipeline.get("surface", {})
            if surface.get("inputs"):
                output.append(
                    f"   surface in: {_format_wrapped_port_bindings(surface['inputs'])}"
                )
            if surface.get("outputs"):
                output.append(
                    f"   surface out: {_format_wrapped_port_bindings(surface['outputs'])}"
                )

        outgoing = adj[node.id]
        if not outgoing:
            output.append("   (no outputs)")
        else:
            for edge in outgoing:
                dest_id = edge.destination.node
                dest_node = id_to_node.get(dest_id)
                dest_groups = _get_pipeline_groups(dest_node) if dest_node is not None else []
                dest_primary_group = dest_groups[-1] if dest_groups else None
                dest_display = (
                    dest_primary_group.get("local_node_id") or dest_id
                    if dest_primary_group
                    else (dest_id.split("__")[0] if "__" in dest_id else dest_id)
                )

                adapter_info = ""
                if edge.adapter:
                    adapter_name = list(edge.adapter.keys())[0]
                    params = edge.adapter[adapter_name]
                    adapter_info = f": {adapter_name}"

                # Check for cycle/feedback (if dest is earlier in list)
                # Note: this is a heuristic based on print order
                is_feedback = False
                for prev in ordered_nodes[: i + 1]:
                    if prev.id == dest_id:
                        is_feedback = True
                        break

                arrow = "-->"
                note = ""
                if is_feedback:
                    note = " (feedback/cycle)"
                    arrow = "-->"  # Could use different arrow

                output.append(
                    f"   --({edge.source.port} -> {edge.destination.port}{adapter_info}){arrow} [{dest_display}]{note}"
                )
        output.append("")

    return "\n".join(output)


def save_interactive_html(ir: "IR", filename: str = "pipeline_viz.html") -> None:
    """Export the pipeline visualization to a self-contained HTML file using IR."""

    # Serialize IR to JSON
    json_data = ir.to_json(indent=2)

    # Inject into template (inline assets if available)
    html_content = HTML_TEMPLATE
    html_content = html_content.replace(
        "__CYTOSCAPE_SCRIPT__",
        _script_tag_inline_or_cdn("cytoscape.min.js", _CYTOSCAPE_CDN),
    )
    html_content = html_content.replace(
        "__DAGRE_SCRIPT__",
        _script_tag_inline_or_cdn("dagre.min.js", _DAGRE_CDN),
    )
    html_content = html_content.replace(
        "__CYTOSCAPE_DAGRE_SCRIPT__",
        _script_tag_inline_or_cdn("cytoscape-dagre.min.js", _CYTOSCAPE_DAGRE_CDN),
    )
    html_content = html_content.replace("__PIPELINE_NAME__", ir.metadata.name)
    html_content = html_content.replace("__ASCII_GRAPH__", generate_ascii_graph(ir))
    html_content = html_content.replace("__IR_DATA__", json_data)

    with open(filename, "w") as f:
        f.write(html_content)
    print(f"\n[Success] Visualization saved to: {filename}")
    print(f"Open this file in your browser to view the interactive graph.")
