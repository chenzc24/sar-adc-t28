# Dummy and Density Fill Policy

Use this policy for the CDAC, comparator, Bootstrap, reference switch drive, SAR and timing, and top-level integration. The 2026-11-16 decision calls for completing placement and routing first, retaining required matching dummies with the core, managing density fill separately, and closing density at the top level.

## Core and Fill Ownership

| Structure | Ownership and handling |
| --- | --- |
| Matching dummies, array boundary dummies, and required device-row end structures | Retain in the functional core. Use the PDK and actual connectivity for LVS and extraction. |
| Taps, well and body contacts, guard rings, required isolation, and functional shielding | Treat as functional or process-required structures and retain them. |
| OD, PO, and multilevel metal used only for density | Put in a hierarchy that can be hidden and regenerated independently of the core. |

Classify shapes by purpose and the native rules. Use the original definitions for required dummies and boundaries inside native standard cells and PDK PCells.

Maintain one functional core. For filled evaluation, use a fixed wrapper that references that core and separate fill. Reuse the CDAC's XCORE, FILL_ODPO, and FILL_METAL structure and the comparator's existing hierarchy. For routine review, open the core or hide its fill instances so that actual devices on OD and PO remain visible.

## Module Delivery

1. Complete device placement for matching, pin access, internal routing, required isolation, and power connections. Feed the actual bounding box, pin locations and layers, and sensitive regions back into top-level planning.
2. Complete the applicable local geometry and connectivity checks, LVS, prefill PEX, and interface measurements. Record deferred density, density gradient, and top-level boundary rules by rule ID and retain the raw reports. Keep other modules progressing and report those open rules when reporting DRC status.
3. Treat module density as a feasibility check during routine iteration. If space, exclusion regions, or rules make top-level closure infeasible, raise it during placement.
4. For sensitive modules such as the comparator, run a filled parasitic sensitivity evaluation when needed. Label that evidence as standalone evaluation. Include its fill in final integration only through the agreed fill ownership and top-level flow. Use the planned-fill process below for gain-sensitive modules.

## Planned Fill for Gain-Sensitive Modules

CDAC gain depends on TOP capacitance to fixed potentials. Fill placement changes gain and bit weights. The CDAC therefore owns TOP-related fill inside its outline and includes it in acceptance. [Gain and linearity budgets](../../docs/specification.md#full-scale-and-gain-error) · [Layout constraints](constraints.json)

| Rule | Window | Handling |
| --- | --- | --- |
| OD ≥20% (OD.DN.3), PO ≥10% (PO.DN.3), and 10 µm maximum OD spacing (OD.S.14) | 20 × 20 µm with 10 µm steps | Windows can fit entirely in the MOM array, so meet the rules in the array. PO.DN.3.1 exempts the MOM region. PO.DN.3 still applies. |
| M1–M9 minimum density (Mn.DN.1, M9.DN.3) | 125 × 125 µm | The window is larger than the CDAC. Exclude fill above the array and meet density in surrounding regions as needed. Check the adjacent-window gradient (Mn.DN.3) at the top level. |
| Three consecutive metal layers cannot all be below 5% (Mx.DN.7) | 30 × 30 µm with 15 µm steps | A window can fit inside the array. Plan shapes on at least one of M5, M6, and M7 above the array at module level. |

ODBLK, POBLK, and DM1EXCL–DM9EXCL block placement by the fill tool. The density checks still apply.

1. **Generate OD and PO fill inside the array.** Use OD and PO dummy datatypes and align the shapes to unit pitch. Use the same pattern around every active unit and matching dummy, mirrored between the N and P sides. Target density slightly above the minimum and prefer areas clear of TOP conductors. This preserves relative bit weights while changing overall gain. Use extraction to quantify the cost of lateral spacing between dummy OD and M1 TOP fingers.
2. **Exclude tool-generated metal fill above the array and TOP leads.** Cover those areas with DM1EXCL–DM9EXCL. Floating fill, including M7–M9, can reduce coupling from wide bottom-plate trunks to TOP by different amounts for each bit and degrade DNL. Place the deterministic M7 dummy stripes needed for Mx.DN.7 above matching-dummy rows.
3. **Use default fill in the switch and bottom-plate routing regions outside the array as appropriate.** Use ODBLK and POBLK over the array and TOP regions to preserve the planned OD/PO pattern.
4. **Assign ownership.** Place planned fill and exclusion layers in a separate fill cell referenced by the fixed wrapper. Apply top-level fill outside those exclusion regions.
5. **Verify the filled module.** Close local OD/PO density inside the array. Close metal minimum-density and gradient checks at the top level as specified above. Extract with planned fill and default peripheral fill. Remove one fill category at a time to measure its TOP load and check linearity from extracted bit weights.

## Top-Level Closure

Plan top-level fill after module adjacency, main routing, power, and isolation are established. Verify the planned regions of gain-sensitive modules. Assign a single owner to each region, even when fill is hierarchical. Exclude reused, verified module fill from regeneration and check module boundaries. Retain required matching and device structures when regenerating fill. Use PDK-supported exclusions and symmetry constraints, and apply all relevant density rules.

Final delivery includes full top-level density and geometry DRC, LVS, PEX matching the final fill state, and the relevant ADC post-layout simulations. Label prefill, standalone filled, and top-level filled evidence according to its actual scope.

Bind fill provenance to core or top-level input digests, boundaries, constraints, rule and tool identity, and outputs. Reassess fill, extraction, and electrical evidence after changes to the core, its neighbors, or routing. Retain dated results.

## Existing Layouts

Continue in-flight verification as planned. Existing fill can support review and diagnosis after it is isolated in its own hierarchy. Before writing OA, follow the ownership and recovery procedure. Protect other modules, unsaved user edits, and existing failure evidence. [Recovery and in-place iteration](../docs/workflow.md#recovery-and-in-place-iteration)
