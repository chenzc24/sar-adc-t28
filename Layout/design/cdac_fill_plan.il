; Planned-fill primitive for the paired-row CDAC (Layout/specs/fill-policy.md).
; Draws one rectangle on an explicit layer-purpose pair: dummy OD/PO, ODBLK/POBLK
; and DMEXCL dummy1..dummy9. Loaded only when the generator emits the fill cell.
procedure(rdLpp(cv layer purpose x0 y0 x1 y1)
  cmpRequire(dbCreateRect(cv list(layer purpose) list(cmpPoint(x0 y0) cmpPoint(x1 y1)))
    "Cannot create fill-plan rectangle"))
