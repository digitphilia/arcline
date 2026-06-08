/*
 * arcline_d3 - NetworkCanvas
 * --------------------------
 *
 * Custom Dash component (plain ES5, no JSX, no build step) that
 * renders an interactive D3 + SVG visualization of an arcline graph.
 *
 * Features:
 *   - Three layout modes: force / tiered / geo (lat-lon projected)
 *   - Per-kind colour and PNG icon rendered inside circular nodes
 *   - Drag a node to reposition (sticks where dropped)
 *   - With `connectMode=true`, drag from one node to another to
 *     emit a `pendingEdge` event back to Dash
 *   - Click   -> writes `clickedElement` prop
 *   - Dbl-clk -> writes `dblClickedElement` prop
 *   - R-click -> writes `contextElement` prop (with viewport x/y)
 *   - Zoom + pan
 *   - Honors `theme` mapping for background / stroke / text colours
 *
 * Globals consumed: window.React, window.d3
 * Exposes:          window.arcline_d3.NetworkCanvas
 */

(function (global) {
    "use strict";

    var React = global.React;
    if (!React) {
        console.error("[arcline_d3] window.React not available");
        return;
    }

    var createElement = React.createElement;
    var useRef = React.useRef;
    var useEffect = React.useEffect;
    var useCallback = React.useCallback;

    var DEFAULT_THEME = {
        bg: "#0f1115",
        surface: "#181b22",
        border: "rgba(255,255,255,0.08)",
        text: "#e6e8ee",
        muted: "#8a93a6",
        accent: "#7aa2ff",
        edge: "rgba(255,255,255,0.32)",
        edgeHighlight: "#7aa2ff",
        nodeStroke: "rgba(255,255,255,0.18)",
        selectionRing: "#ffd166",
        pendingEdge: "#ffd166"
    };

    var TIER_ORDER = ["supplier", "plant", "warehouse", "customer"];

    function ts() { return Date.now(); }

    function mergeTheme(theme) {
        var out = {};
        var k;
        for (k in DEFAULT_THEME) { out[k] = DEFAULT_THEME[k]; }
        if (theme) {
            for (k in theme) {
                if (theme[k]) { out[k] = theme[k]; }
            }
        }
        return out;
    }

    function tierIndex(kind) {
        var idx = TIER_ORDER.indexOf((kind || "").toLowerCase());
        return idx < 0 ? TIER_ORDER.length : idx;
    }

    /*
     * Project geo coords (lat, lng) -> SVG x/y inside `[w, h]` using
     * a simple equirectangular projection. Falls back to a centred
     * dot when coords are missing.
     */
    function geoProject(node, w, h, bounds) {
        if (node.lat == null || node.lng == null) {
            return { x: w / 2, y: h / 2 };
        }
        var spanLng = (bounds.maxLng - bounds.minLng) || 1;
        var spanLat = (bounds.maxLat - bounds.minLat) || 1;
        var x = ((node.lng - bounds.minLng) / spanLng) * (w - 80) + 40;
        var y = h - (((node.lat - bounds.minLat) / spanLat) * (h - 80) + 40);
        return { x: x, y: y };
    }

    function computeGeoBounds(nodes) {
        var minLat = +Infinity, maxLat = -Infinity;
        var minLng = +Infinity, maxLng = -Infinity;
        var anyCoords = false;
        nodes.forEach(function (n) {
            if (n.lat != null && n.lng != null) {
                anyCoords = true;
                if (n.lat < minLat) minLat = n.lat;
                if (n.lat > maxLat) maxLat = n.lat;
                if (n.lng < minLng) minLng = n.lng;
                if (n.lng > maxLng) maxLng = n.lng;
            }
        });
        if (!anyCoords) {
            return { minLat: 0, maxLat: 1, minLng: 0, maxLng: 1 };
        }
        if (minLat === maxLat) { minLat -= 0.5; maxLat += 0.5; }
        if (minLng === maxLng) { minLng -= 0.5; maxLng += 0.5; }
        return { minLat: minLat, maxLat: maxLat, minLng: minLng, maxLng: maxLng };
    }

    function NetworkCanvas(props) {
        var nodes = props.nodes || [];
        var edges = props.edges || [];
        var layoutMode = props.layoutMode || "force";
        var theme = mergeTheme(props.theme);
        var iconBase = props.iconBase || "/assets/icons/";
        var selectedId = props.selectedId || null;
        var connectMode = !!props.connectMode;
        var tsTick = props.ts || 0;

        var containerRef = useRef(null);
        var svgRef = useRef(null);
        var simRef = useRef(null);
        var dragSourceRef = useRef(null);

        var setProps = props.setProps || function () {};

        var emit = useCallback(function (key, payload) {
            var patch = {};
            patch[key] = Object.assign({}, payload, { ts: ts() });
            setProps(patch);
        }, [setProps]);

        useEffect(function () {
            var d3 = global.d3;
            if (!d3) {
                console.error("[arcline_d3] window.d3 not available");
                return;
            }
            var container = containerRef.current;
            if (!container) { return; }

            // teardown previous render
            d3.select(container).selectAll("svg").remove();
            if (simRef.current) {
                simRef.current.stop();
                simRef.current = null;
            }

            var rect = container.getBoundingClientRect();
            var width = Math.max(rect.width, 320);
            var height = Math.max(rect.height, 320);

            var svg = d3.select(container)
                .append("svg")
                .attr("width", "100%")
                .attr("height", "100%")
                .attr("viewBox", "0 0 " + width + " " + height)
                .style("background", theme.bg)
                .style("border-radius", "16px")
                .style("display", "block");
            svgRef.current = svg.node();

            // arrow marker
            var defs = svg.append("defs");
            defs.append("marker")
                .attr("id", "arc-arrow")
                .attr("viewBox", "0 -5 10 10")
                .attr("refX", 22)
                .attr("refY", 0)
                .attr("markerWidth", 10)
                .attr("markerHeight", 10)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M0,-5L10,0L0,5")
                .attr("fill", theme.edge);

            // dotted grid background
            var grid = defs.append("pattern")
                .attr("id", "arc-grid")
                .attr("width", 24).attr("height", 24)
                .attr("patternUnits", "userSpaceOnUse");
            grid.append("circle")
                .attr("cx", 1).attr("cy", 1).attr("r", 1)
                .attr("fill", theme.border);
            svg.append("rect")
                .attr("width", width).attr("height", height)
                .attr("fill", "url(#arc-grid)");

            var zoomLayer = svg.append("g").attr("class", "arc-zoom");

            svg.call(d3.zoom()
                .scaleExtent([0.25, 4])
                .filter(function (event) {
                    // disable zoom-on-drag for left button (we use it
                    // for node drag); allow wheel + middle / right
                    return !event.button || event.type === "wheel";
                })
                .on("zoom", function (event) {
                    zoomLayer.attr("transform", event.transform);
                }));

            var edgeLayer = zoomLayer.append("g").attr("class", "arc-edges");
            var nodeLayer = zoomLayer.append("g").attr("class", "arc-nodes");
            var pendingLayer = zoomLayer.append("g").attr("class", "arc-pending");

            // working copies (we mutate x/y)
            var simNodes = nodes.map(function (n) {
                return Object.assign({}, n);
            });
            var byKey = {};
            simNodes.forEach(function (n) { byKey[n.hashKey] = n; });
            var simEdges = edges
                .filter(function (e) { return byKey[e.srcKey] && byKey[e.dstKey]; })
                .map(function (e) {
                    return Object.assign({}, e, {
                        source: byKey[e.srcKey],
                        target: byKey[e.dstKey]
                    });
                });

            // seed positions based on layout mode
            if (layoutMode === "tiered") {
                var tiers = {};
                simNodes.forEach(function (n) {
                    var t = tierIndex(n.kind);
                    if (!tiers[t]) tiers[t] = [];
                    tiers[t].push(n);
                });
                var tierKeys = Object.keys(tiers).map(Number).sort(function (a, b) { return a - b; });
                var dx = width / (tierKeys.length + 1);
                tierKeys.forEach(function (t, i) {
                    var col = tiers[t];
                    var dy = height / (col.length + 1);
                    col.forEach(function (n, j) {
                        n.x = dx * (i + 1);
                        n.y = dy * (j + 1);
                        n.fx = n.x; n.fy = n.y;
                    });
                });
            } else if (layoutMode === "geo") {
                var bounds = computeGeoBounds(simNodes);
                simNodes.forEach(function (n) {
                    var p = geoProject(n, width, height, bounds);
                    n.x = p.x; n.y = p.y;
                    n.fx = p.x; n.fy = p.y;
                });
            } else {
                // force layout
                simNodes.forEach(function (n) {
                    if (n.x == null) n.x = width / 2 + (Math.random() - 0.5) * 200;
                    if (n.y == null) n.y = height / 2 + (Math.random() - 0.5) * 200;
                });
            }

            var edgeSel = edgeLayer.selectAll("line")
                .data(simEdges, function (d) { return d.hashKey; })
                .enter()
                .append("line")
                .attr("stroke", function (d) { return d.color || theme.edge; })
                .attr("stroke-width", function (d) { return d.width || 1.5; })
                .attr("stroke-linecap", "round")
                .attr("marker-end", "url(#arc-arrow)")
                .style("cursor", "pointer")
                .on("click", function (event, d) {
                    event.stopPropagation();
                    emit("clickedElement", { kind: "edge", hashKey: d.hashKey });
                })
                .on("dblclick", function (event, d) {
                    event.stopPropagation();
                    emit("dblClickedElement", { kind: "edge", hashKey: d.hashKey });
                })
                .on("contextmenu", function (event, d) {
                    event.preventDefault();
                    event.stopPropagation();
                    emit("contextElement", {
                        kind: "edge", hashKey: d.hashKey,
                        x: event.clientX, y: event.clientY
                    });
                });

            var nodeRadius = 22;

            var nodeSel = nodeLayer.selectAll("g.arc-node")
                .data(simNodes, function (d) { return d.hashKey; })
                .enter()
                .append("g")
                .attr("class", "arc-node")
                .style("cursor", "grab");

            // selection halo
            nodeSel.append("circle")
                .attr("class", "halo")
                .attr("r", nodeRadius + 6)
                .attr("fill", "none")
                .attr("stroke", theme.selectionRing)
                .attr("stroke-width", 2.5)
                .attr("opacity", function (d) {
                    return d.hashKey === selectedId ? 1 : 0;
                });

            // colored disk
            nodeSel.append("circle")
                .attr("class", "disk")
                .attr("r", nodeRadius)
                .attr("fill", function (d) { return d.color || theme.accent; })
                .attr("stroke", theme.nodeStroke)
                .attr("stroke-width", 2)
                .attr("filter", "drop-shadow(0 4px 10px rgba(0,0,0,0.45))");

            // icon
            nodeSel.append("image")
                .attr("xlink:href", function (d) {
                    if (!d.icon) return null;
                    if (d.icon.indexOf("http") === 0 || d.icon.indexOf("/") === 0) return d.icon;
                    return iconBase + d.icon;
                })
                .attr("x", -16).attr("y", -16)
                .attr("width", 32).attr("height", 32)
                .attr("pointer-events", "none")
                .attr("opacity", 0.92);

            // label
            nodeSel.append("text")
                .attr("y", nodeRadius + 16)
                .attr("text-anchor", "middle")
                .attr("font-family", "Inter, system-ui, sans-serif")
                .attr("font-size", 11)
                .attr("font-weight", 500)
                .attr("fill", theme.text)
                .attr("paint-order", "stroke")
                .attr("stroke", theme.bg)
                .attr("stroke-width", 3)
                .text(function (d) { return d.name || d.hashKey; });

            // interactions
            nodeSel
                .on("click", function (event, d) {
                    event.stopPropagation();
                    emit("clickedElement", { kind: "node", hashKey: d.hashKey });
                })
                .on("dblclick", function (event, d) {
                    event.stopPropagation();
                    emit("dblClickedElement", { kind: "node", hashKey: d.hashKey });
                })
                .on("contextmenu", function (event, d) {
                    event.preventDefault();
                    event.stopPropagation();
                    emit("contextElement", {
                        kind: "node", hashKey: d.hashKey,
                        x: event.clientX, y: event.clientY
                    });
                });

            // drag behaviour - either reposition or pending-edge
            var drag = d3.drag()
                .on("start", function (event, d) {
                    d3.select(this).style("cursor", "grabbing");
                    if (connectMode) {
                        dragSourceRef.current = d;
                        pendingLayer.selectAll("*").remove();
                        pendingLayer.append("line")
                            .attr("class", "pending")
                            .attr("x1", d.x).attr("y1", d.y)
                            .attr("x2", d.x).attr("y2", d.y)
                            .attr("stroke", theme.pendingEdge)
                            .attr("stroke-width", 2.5)
                            .attr("stroke-dasharray", "6 4")
                            .attr("pointer-events", "none");
                    } else {
                        if (simRef.current) simRef.current.alphaTarget(0.2).restart();
                        d.fx = d.x; d.fy = d.y;
                    }
                })
                .on("drag", function (event, d) {
                    if (connectMode) {
                        var pt = d3.pointer(event, zoomLayer.node());
                        pendingLayer.select("line.pending")
                            .attr("x2", pt[0]).attr("y2", pt[1]);
                    } else {
                        d.fx = event.x; d.fy = event.y;
                    }
                })
                .on("end", function (event, d) {
                    d3.select(this).style("cursor", "grab");
                    if (connectMode) {
                        var pt = d3.pointer(event, zoomLayer.node());
                        var dropTarget = null;
                        simNodes.forEach(function (n) {
                            if (n === d) return;
                            var dx = n.x - pt[0], dy = n.y - pt[1];
                            if (dx * dx + dy * dy < (nodeRadius + 6) * (nodeRadius + 6)) {
                                dropTarget = n;
                            }
                        });
                        pendingLayer.selectAll("*").remove();
                        if (dropTarget) {
                            emit("pendingEdge", {
                                srcKey: d.hashKey, dstKey: dropTarget.hashKey
                            });
                        }
                        dragSourceRef.current = null;
                    } else {
                        if (simRef.current) simRef.current.alphaTarget(0);
                        // remember position for read-back
                        var positions = {};
                        simNodes.forEach(function (n) {
                            positions[n.hashKey] = { x: n.x, y: n.y };
                        });
                        setProps({ positions: positions });
                    }
                });
            nodeSel.call(drag);

            function ticked() {
                edgeSel
                    .attr("x1", function (d) { return d.source.x; })
                    .attr("y1", function (d) { return d.source.y; })
                    .attr("x2", function (d) { return d.target.x; })
                    .attr("y2", function (d) { return d.target.y; });
                nodeSel.attr("transform", function (d) {
                    return "translate(" + d.x + "," + d.y + ")";
                });
            }

            if (layoutMode === "force") {
                var sim = d3.forceSimulation(simNodes)
                    .force("link", d3.forceLink(simEdges)
                        .id(function (d) { return d.hashKey; })
                        .distance(110).strength(0.6))
                    .force("charge", d3.forceManyBody().strength(-360))
                    .force("center", d3.forceCenter(width / 2, height / 2))
                    .force("collide", d3.forceCollide().radius(nodeRadius + 8))
                    .alphaDecay(0.05)
                    .on("tick", ticked)
                    .on("end", function () {
                        var positions = {};
                        simNodes.forEach(function (n) {
                            positions[n.hashKey] = { x: n.x, y: n.y };
                        });
                        setProps({ positions: positions });
                    });
                simRef.current = sim;
            } else {
                ticked();
            }

            // background click clears selection
            svg.on("click", function () {
                emit("clickedElement", { kind: null, hashKey: null });
            });
            svg.on("contextmenu", function (event) {
                event.preventDefault();
                emit("contextElement", {
                    kind: null, hashKey: null,
                    x: event.clientX, y: event.clientY
                });
            });

            return function () {
                if (simRef.current) {
                    simRef.current.stop();
                    simRef.current = null;
                }
            };
        }, [nodes, edges, layoutMode, theme.bg, theme.accent, theme.edge,
            selectedId, connectMode, iconBase, tsTick, emit, setProps]);

        var style = Object.assign({
            width: "100%",
            height: "calc(100vh - 220px)",
            minHeight: "520px",
            borderRadius: "16px",
            background: theme.bg,
            border: "1px solid " + theme.border,
            boxShadow: "0 10px 40px rgba(0,0,0,0.35)",
            overflow: "hidden",
            position: "relative"
        }, props.style || {});

        return createElement("div", {
            ref: containerRef,
            id: props.id,
            className: props.className || "arcline-network-canvas",
            style: style
        });
    }

    NetworkCanvas.defaultProps = {};

    global.arcline_d3 = global.arcline_d3 || {};
    global.arcline_d3.NetworkCanvas = NetworkCanvas;
})(window);
