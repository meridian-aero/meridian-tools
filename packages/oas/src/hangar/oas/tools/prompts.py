"""MCP prompts: guided multi-step analysis and optimization workflows.

Migrated from: OpenAeroStruct/oas_mcp/tools/prompts.py
"""

from __future__ import annotations


def prompt_analyze_wing(
    wing_type: str = "CRM",
    span: str = "default",
    target_CL: str = "0.5",
    Mach: str = "0.84",
) -> str:
    span_note = "" if span == "default" else f" with a span of {span} m"
    span_param = "" if span == "default" else f"\n   Set span={span}."
    return f"""\
Analyse a {wing_type} wing{span_note} at Mach {Mach} and find the operating point \
that achieves CL ≈ {target_CL}.

Follow these steps using the OpenAeroStruct tools:

0. Call start_session(notes="Analyse {wing_type} wing at Mach {Mach}, target CL={target_CL}").

1. Call create_surface to define the wing geometry.
   Use wing_type="{wing_type}", num_x=2, num_y=7, symmetry=True, with_viscous=True, CD0=0.015.{span_param}
   Use wing_type="CRM" for a realistic transport wing; "rect" for a clean rectangular planform.
   Then call log_decision(decision_type="mesh_resolution",
     reasoning="<why this wing_type and mesh density>",
     selected_action="wing_type={wing_type}, num_x=2, num_y=7").

2. Call run_aero_analysis at alpha=5.0 (default cruise: velocity=248.136, Mach_number={Mach}, density=0.38).
   Read envelope.summary.narrative and check validation.passed.
   Note any flags in summary.flags (e.g. tip_loaded, induced_drag_dominant).
   Then call log_decision(decision_type="result_interpretation",
     reasoning="<summarise CL, CD, L/D and any flags>",
     selected_action="<next step based on results>",
     prior_call_id=<_provenance.call_id from the analysis result>).

3. Call visualize(run_id, "lift_distribution") to see the spanwise Cl distribution.

4. Call compute_drag_polar with alpha_start=-5.0, alpha_end=15.0, num_alpha=21
   to map out the full polar and find the alpha that gives CL ≈ {target_CL}.
   Check results.best_L_over_D for the optimum operating point.

5. Call compute_stability_derivatives at the operating alpha.
   Set cg to approximately 25% of the mean chord ahead of the aerodynamic centre
   to check whether the configuration is statically stable.
   Then call log_decision(decision_type="result_interpretation",
     reasoning="<summarise stability: CL_alpha, static margin, stable/unstable>",
     selected_action="<design recommendation>",
     prior_call_id=<_provenance.call_id from the stability result>).

6. Report results:
   - Operating point: alpha, CL, CD, L/D at the target CL
   - Best L/D point: alpha, CL, L/D from the drag polar
   - Lift distribution balance (from summary.derived_metrics)
   - Drag breakdown: CDi%, CDv%, CDw% (from summary.derived_metrics.drag_breakdown_pct)
   - Stability: CL_alpha, static margin, and whether the configuration is statically stable
   - Any validation warnings

7. Call export_session_graph(output_path="analyze_wing_provenance.json") to save the audit trail.
"""


def prompt_aerostructural_design(
    W0_kg: str = "120000",
    load_factor: str = "2.5",
    material: str = "aluminum",
) -> str:
    material_props = {
        "aluminum":   "E=70e9, G=30e9, yield_stress=500e6, mrho=3000.0",
        "titanium":   "E=114e9, G=42e9, yield_stress=950e6, mrho=4430.0",
        "composite":  "E=70e9, G=30e9, yield_stress=900e6, mrho=1600.0",
    }.get(material, "E=70e9, G=30e9, yield_stress=500e6, mrho=3000.0")

    return f"""\
Size a wing structure for an aircraft with empty weight W0={W0_kg} kg using \
{material} material properties, at a load factor of {load_factor}.

Follow these steps:

0. Call start_session(notes="Aerostruct design: W0={W0_kg} kg, {material}, LF={load_factor}").

1. Call create_surface with fem_model_type="tube" and material properties:
   {material_props}, safety_factor=2.5
   Use wing_type="CRM", num_x=2, num_y=7, symmetry=True, with_viscous=True, CD0=0.015.
   Then call log_decision(decision_type="mesh_resolution",
     reasoning="<why this mesh and material choice>",
     selected_action="CRM tube, num_y=7, {material}").

2. Call run_aerostruct_analysis with:
   W0={W0_kg}, load_factor={load_factor}, Mach_number=0.84, density=0.38,
   velocity=248.136, R=11.165e6, speed_of_sound=295.4

3. Interpret the results:
   - failure < 0  ->  structure is safe (report the margin)
   - failure > 0  ->  structure has failed; the design needs thicker skins
   - L_equals_W residual: if |L_equals_W| > 0.1, note that alpha or W0 may need adjustment
   - Report structural_mass, fuelburn, and the failure metric.
   Then call log_decision(decision_type="result_interpretation",
     reasoning="<summarise failure metric, structural_mass, fuelburn, L_equals_W>",
     selected_action="<proceed to optimisation / design is adequate>",
     prior_call_id=<_provenance.call_id from the aerostruct result>).

4. If failure > 0, first log the optimisation setup:
   Call log_decision(decision_type="dv_selection",
     reasoning="thickness, alpha, twist needed to find feasible minimum-weight structure",
     selected_action="thickness (0.003-0.25), alpha, twist").
   Call log_decision(decision_type="constraint_choice",
     reasoning="L=W for trim, failure<=0 for structural feasibility, no spar intersection",
     selected_action="L_equals_W=0, failure<=0, thickness_intersects<=0").
   Then call run_optimization with objective="fuelburn",
   design_variables=[thickness (lower=0.003, upper=0.25), alpha, twist],
   constraints=[L_equals_W=0, failure<=0, thickness_intersects<=0]
   to find the minimum-weight feasible structure.
   After optimisation, call log_decision(decision_type="convergence_assessment",
     reasoning="<did it converge, final objective, constraint satisfaction>",
     selected_action="<accept result / re-run with changes>",
     prior_call_id=<_provenance.call_id from the optimisation result>).

5. Call export_session_graph(output_path="aerostruct_design_provenance.json") to save the audit trail.
"""


def prompt_optimize_wing(
    objective: str = "CD",
    target_CL: str = "0.5",
    analysis_type: str = "aero",
) -> str:
    struct_note = ""
    dv_list = '[{"name":"twist","lower":-10,"upper":15}, {"name":"alpha","lower":-5,"upper":10}]'
    con_list = f'[{{"name":"CL","equals":{target_CL}}}]'

    if analysis_type == "aerostruct":
        struct_note = (
            "Use fem_model_type='tube', E=70e9, G=30e9, yield_stress=500e6, "
            "safety_factor=2.5, mrho=3000.0 in create_surface.\n   "
        )
        dv_list = (
            '[{"name":"twist","lower":-10,"upper":15},'
            '{"name":"thickness","lower":0.003,"upper":0.25,"scaler":100},'
            '{"name":"alpha","lower":-5,"upper":10}]'
        )
        con_list = (
            '[{"name":"L_equals_W","equals":0},'
            '{"name":"failure","upper":0},'
            '{"name":"thickness_intersects","upper":0}]'
        )

    final_metric = "fuelburn" if objective == "fuelburn" else "L/D"

    return f"""\
Optimise a wing for minimum {objective} subject to CL={target_CL} \
using a {analysis_type} analysis.

Follow these steps:

0. Call start_session(notes="Optimise {analysis_type} wing: min {objective}, CL={target_CL}").

1. Call create_surface:
   {struct_note}Use wing_type="CRM", num_x=2, num_y=7, symmetry=True, \
with_viscous=True, CD0=0.015.
   Then call log_decision(decision_type="mesh_resolution",
     reasoning="<why this mesh density and wing configuration>",
     selected_action="CRM, num_x=2, num_y=7").

2. Call run_aero_analysis (or run_aerostruct_analysis) at alpha=5.0 to establish a baseline.
   Note baseline CL, CD, L/D from summary.narrative.
   Save the baseline run_id for later comparison.
   Then call log_decision(decision_type="result_interpretation",
     reasoning="<summarise baseline CL, CD, L/D>",
     selected_action="proceed to optimisation",
     prior_call_id=<_provenance.call_id from the baseline result>).

3. Log the optimisation setup:
   Call log_decision(decision_type="dv_selection",
     reasoning="<why these design variables and bounds>",
     selected_action="{dv_list}").
   Call log_decision(decision_type="constraint_choice",
     reasoning="<why these constraints and targets>",
     selected_action="{con_list}").
   Then call run_optimization with:
   analysis_type="{analysis_type}"
   objective="{objective}"
   design_variables={dv_list}
   constraints={con_list}
   Mach_number=0.84, density=0.38, velocity=248.136
   After optimisation, call log_decision(decision_type="convergence_assessment",
     reasoning="<did it converge, iterations, objective improvement>",
     selected_action="<accept / re-run>",
     prior_call_id=<_provenance.call_id from the optimisation result>).

4. Call visualize(run_id, "opt_history") to see objective convergence.
   If design variables changed significantly, also call visualize(run_id, "opt_dv_evolution").
   Call visualize(run_id, "opt_comparison") for a side-by-side DV comparison.

5. Report results:
   - Convergence: success (True/False), number of iterations
   - Objective improvement: summary.derived_metrics.objective_improvement_pct
   - Optimised DV values: results.optimized_design_variables (root-to-tip ordering)
   - Final performance: CL, CD, {final_metric} from results.final_results
   - Constraint satisfaction: CL residual, failure margin
   - Any validation warnings

6. Call export_session_graph(output_path="optimize_wing_provenance.json") to save the audit trail.

Decision guide:
- Minimize drag (aero-only): objective="CD", DVs=[twist, alpha], constraints=[CL=target]
- Minimize fuel burn (aerostruct): objective="fuelburn", DVs=[twist, thickness, alpha],
  constraints=[L_equals_W=0, failure<=0, thickness_intersects<=0]
- Minimize structural mass: objective="structural_mass", same DVs/constraints as fuelburn
"""


def prompt_compare_designs(
    run_id_1: str = "",
    run_id_2: str = "",
) -> str:
    if run_id_1 and run_id_2:
        run_spec = f"Compare run_id_1={run_id_1!r} and run_id_2={run_id_2!r}."
    else:
        run_spec = (
            "No run_ids were specified. Call list_artifacts() and use the two most "
            "recent run_ids, or ask the user to provide them."
        )

    return f"""\
Compare two OAS analysis runs side by side. {run_spec}

Follow these steps:

0. Call start_session(notes="Compare designs") if no session is active.

1. Identify the two runs -- accept any of:
   - Two explicit run_ids provided above
   - "last two runs" -> call list_artifacts() and use the two most recent run_ids
   - "before and after" -> use the run_id from before and after an optimization

2. Retrieve both artifacts in parallel -- call get_artifact(run_id_1) and
   get_artifact(run_id_2) simultaneously.
   Extract metadata.analysis_type, results, and metadata.parameters from each.

3. Build a comparison table -- create a markdown table with these metrics (where applicable):

   | Metric               | Run 1 | Run 2 | Change | Change % |
   |----------------------|-------|-------|--------|----------|
   | CL                   | ...   | ...   | ...    | ...      |
   | CD                   | ...   | ...   | ...    | ...      |
   | L/D                  | ...   | ...   | ...    | ...      |
   | CM                   | ...   | ...   | ...    | ...      |
   | fuelburn (kg)        | ...   | ...   | ...    | ...      |
   | structural_mass (kg) | ...   | ...   | ...    | ...      |
   | failure              | ...   | ...   | ...    | ...      |

   Highlight rows with >5% change in bold or with a * marker.

4. Compare design variables -- if both runs have results.optimized_design_variables
   (optimization runs) or different input parameters, note what changed.

5. Spanwise distribution qualitative comparison -- call get_detailed_results(run_id, "standard")
   for each run (in parallel), then describe:
   - Whether the lift distribution became more/less elliptical
   - Whether the stress distribution changed significantly

6. Summarize in 3-5 sentences: what changed, by how much, and what it means for the
   design. Reference the analysis_type context (aero vs aerostruct, cruise vs polar)
   and make a design recommendation.
   Then call log_decision(decision_type="result_interpretation",
     reasoning="<your 3-5 sentence summary and design recommendation>",
     selected_action="<recommended design choice>").

7. Call export_session_graph(output_path="compare_designs_provenance.json") to save the audit trail.

Output format:
- Markdown table for quantitative metrics
- Bullet list for qualitative observations
- Final 3-5 sentence summary with design recommendation
"""
