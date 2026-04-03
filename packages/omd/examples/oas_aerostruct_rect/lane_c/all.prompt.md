# OAS Rectangular Wing: Aerostructural Workflow

Run the aerostructural analysis, then verify results and provenance.

## Analysis

1. `omd-cli assemble packages/omd/examples/oas_aerostruct_rect/lane_b/aerostruct_analysis/`
2. `omd-cli run .../plan.yaml --mode analysis`
3. `omd-cli results <run_id> --summary`

## Verification

4. `omd-cli provenance ex-oas-aerostruct-analysis --format text`

Report: CL, CD, L/D, structural mass, failure index, and the provenance chain.
