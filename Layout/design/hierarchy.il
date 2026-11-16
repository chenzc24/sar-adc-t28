; Shared functional core plus a thin verification wrapper. Requires cmp helpers.
; This file defines procedures only; loading it does not modify OA.
procedure(cdacWrapCore(withFill)
  let((lib core top inst net term fig shape p master)
    lib=ddGetObj("SAR_ADC_T28_LAYOUT")
    cmpRequire(lib && equal(lib~>readPath "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_LAYOUT") "Wrong layout library")
    core=dbOpenCellViewByType(lib~>name "sar8j_r1_cdac_core" "layout" "" "r")
    cmpRequire(core && length(core~>terminals)==38 "Invalid functional core")
    cmpRequire(!setof(i core~>instances member(i~>name list("FILL_ODPO" "FILL_METAL"))) "Fill must not be in the core")
    top=dbOpenCellViewByType(lib~>name "sar8j_r1_cdac" "layout" "maskLayout" "w")
    cmpRequire(top && !top~>instances && !top~>shapes "Cannot rebuild wrapper")
    inst=dbCreateInst(top core "XCORE" list(0 0) "R0")
    cmpRequire(inst "Cannot instantiate shared core")
    foreach(ct core~>terminals
      net=dbCreateNet(top ct~>name)
      term=dbCreateTerm(net ct~>name ct~>direction)
      cmpRequire(term && dbCreateInstTerm(net inst ct) "Cannot connect core terminal")
      foreach(cp ct~>pins
        fig=cp~>fig
        cmpRequire(equal(fig~>objType "rect") "Expected rectangular interface pin")
        shape=dbCreateRect(top fig~>lpp fig~>bBox)
        cmpRequire(shape && dbCreatePin(net shape ct~>name term) "Cannot expose core pin")
        p=cmpCenter(fig~>bBox)
        cmpRequire(dbCreateLabel(top list(fig~>layerName "pin") p ct~>name "centerCenter" "R0" "roman" 0.095) "Cannot label wrapper pin")))
    when(withFill
      foreach(pair list(list("FILL_ODPO" "sar8_cdac_fill_odpo") list("FILL_METAL" "sar8_cdac_fill_metal"))
        master=dbOpenCellViewByType(lib~>name cadr(pair) "layout" "" "r")
        cmpRequire(master && dbCreateInst(top master car(pair) list(0 0) "R0") "Cannot attach fill")
        dbClose(master)))
    cmpRequire(length(top~>terminals)==38 && length(top~>instances)==if(withFill then 3 else 1) "Invalid wrapper structure")
    cmpRequire(dbSave(top) "Cannot save wrapper")
    printf("CDAC_WRAPPER_OK fill=%L ports=%d instances=%d\n" withFill length(top~>terminals) length(top~>instances))
    dbClose(top) dbClose(core) t))
