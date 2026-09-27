"""
Spatial 3D & Layered Pipeline Architecture Visualization
Futuristic AI Lab visual architecture with animated particles, glowing conduits,
and interactive stage inspector.
"""

import streamlit as st
import streamlit.components.v1 as components

# Technical stage dossiers with real project statistics
STAGE_DETAILS = {
    "source_inputs": {
        "title": "Data Sources (S1, S2, S3)",
        "badge": "Input Layer",
        "category": "data",
        "what": "Ingests heterogeneous enterprise records from three independent catalogs: Source 1 (query entities), and Source 2 & Source 3 (multilingual target entity repositories).",
        "why": "Different vendors, data providers, and business units catalog identical real-world entities under conflicting naming conventions, localized abbreviations, and noisy address schemas.",
        "inputs": "• S1 Test Queries: 1,732,544 records\n• S2 & S3 Target Knowledge Base: 9,969,589 records (S2: 4,964,258 | S3: 5,005,331)",
        "outputs": "Tabular streaming batches with fields: entity_id, name, address, country.",
        "stats": {
            "Total Query Scale": "1,732,544 queries",
            "Target Pool Scale": "9,969,589 targets",
            "Full Pairwise Space": "~17.27 Trillion potential pairs",
            "Geographic Footprint": "International (India, US, EU, etc.)"
        }
    },
    "preprocessing": {
        "title": "Normalization & Preprocessing",
        "badge": "Processing Layer",
        "category": "process",
        "what": "Executes character-level sanitization, Unicode casefolding, punctuation stripping, legal suffix removal ('pvt', 'ltd', 'inc', 'corp', 'gmbh'), tokenization, and numerical sequence isolation.",
        "why": "Eliminates superficial syntactic variations, corporate acronym noise, and casing artifacts so comparison algorithms focus on core entity identity.",
        "inputs": "Raw strings: name, address, country.",
        "outputs": "Clean core name, alpha-tokens (len >= 5), address tokens (len >= 4), digit tuples, and character bigram sets.",
        "stats": {
            "Regex Engine": "Compiled C-level regex ([^a-z0-9])",
            "Legal Stopwords": "27 canonical corporate identifiers",
            "Char N-grams": "Character bigrams on core name",
            "Processing Mode": "Zero-copy streaming string transforms"
        }
    },
    "blocking": {
        "title": "Multi-Channel Blocking & Inverted Indexing",
        "badge": "Reduction Layer",
        "category": "process",
        "what": "Applies a 3-channel inverted index over target records partitioned strictly by country: Channel A (Country + Exact Core Name), Channel B (Country + Significant Token + 2-char Prefix), and Channel C (Country + Address Digits).",
        "why": "Comparing 1.73M queries against 9.97M targets requires 17.27 trillion comparisons ($O(N \\times M)$), which is computationally intractable. Blocking reduces candidate comparisons by >99.9999% without sacrificing true recall.",
        "inputs": "Normalized tokens, address digits, and country partitions.",
        "outputs": "Sparse candidate index mapping each S1 query to a compact candidate target list.",
        "stats": {
            "Pairwise Search Space": "17,272,624,374,416 pairs",
            "Candidate Pairs Evaluated": "5,148,829 pairs",
            "Candidate Reduction Ratio": "99.99997% space eliminated",
            "Avg Candidates / Query": "2.97 targets per S1 query"
        }
    },
    "candidate_set": {
        "title": "Candidate Subspace & Prioritization",
        "badge": "Candidate Pool",
        "category": "data",
        "what": "Deduplicates candidate identifiers from all active blocking channels and constructs the prioritized candidate pool for machine learning verification.",
        "why": "Supplies high-recall potential matches to the classifier while bounding memory usage to ensure streaming stability on commodity hardware.",
        "inputs": "Multi-channel blocking hits from S2 and S3 targets.",
        "outputs": "Ordered candidate pairs (S1_ID, Target_ID) prepared for pairwise vectorization.",
        "stats": {
            "Max Candidate Cap": "Configurable (K=1000 per query)",
            "Candidate Ingestion": "Streaming generator (RAM-safe)",
            "Peak Memory RSS": "4.8 GB during test inference",
            "Zero-Candidate Queries": "Emitted with empty match list"
        }
    },
    "feature_eng": {
        "title": "Pairwise Feature Engineering (11 Signals)",
        "badge": "Feature Layer",
        "category": "feature",
        "what": "Computes an 11-dimensional feature vector quantifying lexical string similarity, token overlap, numerical alignment, length ratios, and address proximity.",
        "why": "Converts heterogeneous text comparison into dense numerical features that machine learning trees can split on with optimal decision boundaries.",
        "inputs": "Pairs of normalized query and candidate records.",
        "outputs": "11-dimensional floating-point feature vector for each candidate pair.",
        "features": [
            ("exact_match", "Binary (1.0/0.0)", "Identical normalized core names"),
            ("tok_jaccard", "Float [0.0, 1.0]", "Jaccard coefficient on significant name tokens"),
            ("has_shared_dig", "Binary (1.0/0.0)", "Presence of at least one common numeric sequence"),
            ("exact_dig", "Binary (1.0/0.0)", "Exact equality of extracted digit sets"),
            ("dig_jaccard", "Float [0.0, 1.0]", "Jaccard overlap on numerical identifier tokens"),
            ("pref4_match", "Binary (1.0/0.0)", "Equality of leading 4-character string prefixes"),
            ("len_diff", "Float >= 0.0", "Absolute string length difference"),
            ("len_ratio", "Float [0.0, 1.0]", "Length ratio min(L1, L2) / max(L1, L2)"),
            ("addr_tok_jaccard", "Float [0.0, 1.0]", "Jaccard similarity on address token sets"),
            ("first_dig_match", "Binary (1.0/0.0)", "Match on leading digit sequence (street/unit)"),
            ("char_dice", "Float [0.0, 1.0]", "Sørensen-Dice coefficient on character bigrams")
        ],
        "stats": {
            "Feature Vector Dim": "11 dense numerical features",
            "Top Feature by Splits": "char_dice (787 splits) & addr_tok_jaccard (621 splits)",
            "Computation Overhead": "< 1.2 microseconds per pair",
            "Missing Value Handling": "Zero-imputed, strictly bounded"
        }
    },
    "lgbm_model": {
        "title": "LightGBM Gradient Boosted Decision Forest",
        "badge": "Model Layer",
        "category": "model",
        "what": "LightGBM binary classifier (Model V2) trained using binary logloss objective to predict the posterior probability $P(\\text{Match} = 1 \\mid \\mathbf{x})$.",
        "why": "Gradient boosted trees excel at non-linear interactions among heterogeneous tabular features, are resilient to scale disparities, and provide ultra-fast inference throughput.",
        "inputs": "11-dimensional feature matrix $\\mathbf{X} \\in \\mathbb{R}^{M \\times 11}$.",
        "outputs": "Continuous calibrated match probability $p \\in [0.0, 1.0]$.",
        "stats": {
            "Model Size on Disk": "342 KB (ultra-compact)",
            "Number of Trees": "100 estimators",
            "Inference Speed": "~850 queries/second (end-to-end)",
            "License": "MIT Open Source"
        }
    },
    "decision_gate": {
        "title": "Calibrated Decision Thresholding (0.40)",
        "badge": "Calibration Gate",
        "category": "model",
        "what": "Applies a precision-calibrated cutoff ($P \\ge 0.40$) optimized via grid sweep over out-of-fold holdout splits to maximize the competition metric Macro $F_{0.5}$.",
        "why": "Macro $F_{0.5}$ weights precision twice as heavily as recall ($\\beta = 0.5$). Standard 0.50 probability cutoff does not account for class imbalance; threshold 0.40 balances high precision (90.54%) with robust recall (68.06%).",
        "inputs": "LightGBM predicted probabilities.",
        "outputs": "Binary classification: MATCH ($P \\ge 0.40$) vs REJECT ($P < 0.40$).",
        "stats": {
            "Calibrated Cutoff": "0.40",
            "Validation Precision": "90.54%",
            "Validation Recall": "68.06%",
            "Validation Macro F0.5": "0.8237"
        }
    },
    "resolution_output": {
        "title": "Final Entity Resolution & Leaderboard TSVs",
        "badge": "Output Layer",
        "category": "output",
        "what": "Groups predicted matched target IDs per query into comma-separated lists and generates the final formatted competition TSV files conforming to official validation schemas.",
        "why": "Provides the final resolved knowledge graph linkages required for downstream catalog deduplication and leaderboard ranking.",
        "inputs": "Qualified matched target entities per S1 query.",
        "outputs": "• matching_results.tsv (80.11 MB, 1,732,544 rows)\n• candidate_pairs.tsv (421 MB, 1,732,544 rows)",
        "stats": {
            "Resolved S1 Entities": "712,042 queries matched",
            "S1 IDs with 0 Matches": "1,020,502 queries (valid singletons)",
            "Official Validator": "PASS (0 errors, 100% containment)",
            "Formatting": "TSV with exact headers"
        }
    }
}


def render_architecture_visualization():
    """Renders the spatial 3D interactive pipeline visualization with stage selection."""
    
    st.markdown("### 🌐 End-to-End System Pipeline")
    st.caption("Interactive spatial pipeline: click any node below to inspect its operational mechanics, mathematical formulation, and verified telemetry.")

    # Control layout options
    col_ctrl1, col_ctrl2 = st.columns([3, 1])
    with col_ctrl1:
        view_mode = st.radio(
            "Perspective Viewport Mode:",
            ["3D Spatial Perspective", "2D Layered Architecture"],
            horizontal=True,
            key="arch_view_mode"
        )
    with col_ctrl2:
        particles_active = st.checkbox("Particle Conduits", value=True, help="Toggle animated data particle flows")

    is_3d = (view_mode == "3D Spatial Perspective")
    transform_css = "transform: perspective(1000px) rotateX(7deg) scale(0.97);" if is_3d else "transform: none;"

    # Interactive Stage Node HTML/CSS/JS Component
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #f8fafc;
            overflow: hidden;
            padding: 4px 0;
        }}
        
        .viewport {{
            width: 100%;
            perspective: 1000px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}

        .pipeline-container {{
            width: 100%;
            max-width: 900px;
            background: radial-gradient(circle at 50% 50%, rgba(30, 41, 59, 0.45) 0%, rgba(15, 23, 42, 0.7) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 12px 18px 8px 18px;
            position: relative;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            transition: transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
            {transform_css}
        }}

        .pipeline-grid {{
            display: flex;
            flex-direction: column;
            gap: 5px;
            position: relative;
            z-index: 2;
        }}

        .pipeline-row {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            position: relative;
        }}

        .node {{
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 6px 14px;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 240px;
            position: relative;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }}

        .node:hover {{
            transform: translateY(-2px) scale(1.015);
            box-shadow: 0 6px 18px rgba(56, 189, 248, 0.25);
            border-color: rgba(56, 189, 248, 0.6);
        }}

        .node-active {{
            border-color: #38bdf8 !important;
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.4) !important;
            background: rgba(30, 58, 138, 0.4) !important;
        }}

        .node-icon {{
            width: 26px;
            height: 26px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.95rem;
            flex-shrink: 0;
        }}

        /* Category accent colors */
        .cat-data .node-icon {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
        .cat-process .node-icon {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}
        .cat-feature .node-icon {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
        .cat-model .node-icon {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .cat-output .node-icon {{ background: rgba(0, 242, 254, 0.15); color: #00f2fe; border: 1px solid rgba(0, 242, 254, 0.3); }}

        .node-content {{
            display: flex;
            flex-direction: column;
            text-align: left;
        }}

        .node-title {{
            font-size: 0.78rem;
            font-weight: 700;
            color: #f1f5f9;
            letter-spacing: -0.01em;
            line-height: 1.2;
        }}

        .node-sub {{
            font-size: 0.65rem;
            color: #94a3b8;
            font-family: monospace;
            margin-top: 1px;
            line-height: 1.1;
        }}

        /* Connecting conduit lines */
        .conduit-vertical {{
            width: 2px;
            height: 8px;
            background: linear-gradient(180deg, rgba(56, 189, 248, 0.5), rgba(168, 85, 247, 0.5));
            margin: 0 auto;
            position: relative;
        }}

        .particle {{
            position: absolute;
            width: 3px;
            height: 3px;
            border-radius: 50%;
            background: #00f2fe;
            box-shadow: 0 0 5px #00f2fe;
            animation: flow 1.2s infinite linear;
            display: {"block" if particles_active else "none"};
        }}

        @keyframes flow {{
            0% {{ top: 0; opacity: 0; }}
            30% {{ opacity: 1; }}
            80% {{ opacity: 1; }}
            100% {{ top: 100%; opacity: 0; }}
        }}

        .aux-source {{
            border-style: dashed !important;
            background: rgba(15, 23, 42, 0.5) !important;
        }}

        /* Instructions banner */
        .banner {{
            text-align: center;
            font-size: 0.72rem;
            color: #64748b;
            margin-top: 6px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}

        @media (max-width: 768px) {{
            .pipeline-container {{
                padding: 10px 10px 6px 10px;
                transform: none !important;
            }}
            .node {{
                padding: 5px 10px;
                min-width: 200px;
                gap: 8px;
            }}
            .node-title {{
                font-size: 0.72rem;
            }}
            .node-sub {{
                font-size: 0.60rem;
            }}
            .conduit-vertical {{
                height: 6px;
            }}
        }}
    </style>
    </head>
    <body>
    <div class="viewport">
        <div class="pipeline-container">
            <div class="pipeline-grid">
                
                <!-- Stage 1: Dual Data Ingestion -->
                <div class="pipeline-row">
                    <div class="node cat-data" onclick="selectStage('source_inputs')">
                        <div class="node-icon">📦</div>
                        <div class="node-content">
                            <span class="node-title">SOURCE 1 (Queries)</span>
                            <span class="node-sub">1,732,544 Entities</span>
                        </div>
                    </div>
                    <div style="color: #64748b; font-size: 0.9rem;">+</div>
                    <div class="node cat-data aux-source" onclick="selectStage('source_inputs')">
                        <div class="node-icon">📚</div>
                        <div class="node-content">
                            <span class="node-title">SOURCE 2 & 3 (Targets)</span>
                            <span class="node-sub">9,969,589 Records</span>
                        </div>
                    </div>
                </div>

                <div class="conduit-vertical"><div class="particle"></div></div>

                <!-- Stage 2: Normalization -->
                <div class="pipeline-row">
                    <div class="node cat-process" onclick="selectStage('preprocessing')">
                        <div class="node-icon">⚙️</div>
                        <div class="node-content">
                            <span class="node-title">NORMALIZATION / PREPROCESSING</span>
                            <span class="node-sub">Unicode • Legal Suffixes • Bigrams</span>
                        </div>
                    </div>
                </div>

                <div class="conduit-vertical"><div class="particle"></div></div>

                <!-- Stage 3: Multi-Channel Blocking -->
                <div class="pipeline-row">
                    <div class="node cat-process" onclick="selectStage('blocking')">
                        <div class="node-icon">⚡</div>
                        <div class="node-content">
                            <span class="node-title">BLOCKING / CANDIDATE GENERATION</span>
                            <span class="node-sub">3 Inverted Channels • Country Partitioned</span>
                        </div>
                    </div>
                </div>

                <div class="conduit-vertical"><div class="particle"></div></div>

                <!-- Stage 4: Candidate Set -->
                <div class="pipeline-row">
                    <div class="node cat-data" onclick="selectStage('candidate_set')">
                        <div class="node-icon">🎯</div>
                        <div class="node-content">
                            <span class="node-title">CANDIDATE SET (5.15M Pairs)</span>
                            <span class="node-sub">99.99997% Space Pruning</span>
                        </div>
                    </div>
                </div>

                <div class="conduit-vertical"><div class="particle"></div></div>

                <!-- Stage 5: Feature Engineering -->
                <div class="pipeline-row">
                    <div class="node cat-feature" onclick="selectStage('feature_eng')">
                        <div class="node-icon">🔬</div>
                        <div class="node-content">
                            <span class="node-title">FEATURE ENGINEERING</span>
                            <span class="node-sub">11-Dimensional Pairwise Signals</span>
                        </div>
                    </div>
                </div>

                <div class="conduit-vertical"><div class="particle"></div></div>

                <!-- Stage 6: LightGBM Model -->
                <div class="pipeline-row">
                    <div class="node cat-model" onclick="selectStage('lgbm_model')">
                        <div class="node-icon">🧠</div>
                        <div class="node-content">
                            <span class="node-title">LIGHTGBM MATCHING MODEL</span>
                            <span class="node-sub">Model V2 • Binary Logloss Trees</span>
                        </div>
                    </div>
                </div>

                <div class="conduit-vertical"><div class="particle"></div></div>

                <!-- Stage 7: Decision Calibration -->
                <div class="pipeline-row">
                    <div class="node cat-model" onclick="selectStage('decision_gate')">
                        <div class="node-icon">⚖️</div>
                        <div class="node-content">
                            <span class="node-title">MATCH / NO MATCH GATE</span>
                            <span class="node-sub">Precision-Calibrated Threshold 0.40</span>
                        </div>
                    </div>
                </div>

                <div class="conduit-vertical"><div class="particle"></div></div>

                <!-- Stage 8: Output Resolution -->
                <div class="pipeline-row">
                    <div class="node cat-output" onclick="selectStage('resolution_output')">
                        <div class="node-icon">🏆</div>
                        <div class="node-content">
                            <span class="node-title">FINAL ENTITY RESOLUTION</span>
                            <span class="node-sub">712,042 Matches • Official TSVs</span>
                        </div>
                    </div>
                </div>

            </div>
            <div class="banner">Click any stage above to inspect details & telemetry below</div>
        </div>
    </div>

    <script>
        function selectStage(stageKey) {{
            // Dispatch custom event to parent window if supported
            const nodes = document.querySelectorAll('.node');
            nodes.forEach(n => n.classList.remove('node-active'));
            event.currentTarget.classList.add('node-active');
            
            // Send selected stage key to parent via hash or direct query
            window.parent.postMessage({{type: 'STAGE_SELECTED', stage: stageKey}}, '*');
        }}
    </script>
    </body>
    </html>
    """

    components.html(html_code, height=560, scrolling=False)

    # Stage Selection Selector
    st.markdown("---")
    st.markdown("#### 🔍 Stage Deep-Dive Inspector")
    
    stage_keys = list(STAGE_DETAILS.keys())
    stage_labels = [f"{STAGE_DETAILS[k]['title']} ({STAGE_DETAILS[k]['badge']})" for k in stage_keys]
    
    selected_idx = st.selectbox(
        "Select Pipeline Stage to Inspect:",
        range(len(stage_keys)),
        format_func=lambda i: stage_labels[i],
        key="stage_inspector_select"
    )
    
    selected_stage_key = stage_keys[selected_idx]
    stage_info = STAGE_DETAILS[selected_stage_key]

    # Render detailed dossier
    st.markdown(f"### {stage_info['title']}")
    
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown(f"**What happens at this stage:**\n\n{stage_info['what']}")
        st.markdown(f"**Why this stage exists:**\n\n{stage_info['why']}")
        st.markdown(f"**Inputs:**\n`{stage_info['inputs']}`")
        st.markdown(f"**Outputs:**\n`{stage_info['outputs']}`")

        # If feature engineering, show the 11 verified features table
        if "features" in stage_info:
            st.markdown("##### 📐 Validated 11 Model Features")
            feat_table = "| Feature | Type | Operational Rationale |\n| :--- | :--- | :--- |\n"
            for fn, ft, fr in stage_info["features"]:
                feat_table += f"| `{fn}` | {ft} | {fr} |\n"
            st.markdown(feat_table)

    with col_b:
        st.markdown("##### 📊 Verified Stage Telemetry")
        for stat_name, stat_val in stage_info["stats"].items():
            st.markdown(
                f"""
                <div class="glass-card" style="padding: 0.8rem 1rem; margin-bottom: 0.6rem;">
                    <div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase;">{stat_name}</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #38bdf8; font-family: monospace;">{stat_val}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
