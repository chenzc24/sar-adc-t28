; Standalone fill evaluation. XCORE retains the exact routed functional view.
procedure(stFillWrapper(@optional (lib "SAR_ADC_T28_LAYOUT") (view "layout")
 (coreView "layout_compact") (odpo "sar8_timing_fill_odpo_final") (metal "sar8_timing_fill_metal") (headerPins nil))
 let((core cv inst net term fig2 master bounds best candidate center)
  stNeed(!ddGetObj(lib "sar8_sar_timing" view) "Wrapper view already exists")
  core=dbOpenCellViewByType(lib "sar8_sar_timing_core" coreView "" "r")
  stNeed(core && length(core~>terminals)==26 && core~>instances "Unexpected functional core")
  cv=dbOpenCellViewByType(lib "sar8_sar_timing" view "maskLayout" "a")
  stNeed(cv "Cannot open fill wrapper")
  inst=dbCreateInst(cv core "XCORE" 0:0 "R0")
  stNeed(inst "Cannot instance the routed core")
  foreach(ct core~>terminals
   net=dbCreateNet(cv ct~>name)
   term=dbCreateTerm(net ct~>name ct~>direction)
   stNeed(dbCreateInstTerm(net inst ct) "Cannot bind core terminal")
   foreach(pin ct~>pins foreach(fig pin~>figs
    stNeed(equal(fig~>objType "rect") "Expected rectangular port")
    bounds=fig~>bBox
    center=list((caar(bounds)+caadr(bounds))/2.0 (cadar(bounds)+cadadr(bounds))/2.0)
    when(headerPins && member(ct~>name '("VDD" "VSS"))
     best=0.0
     foreach(s ct~>net~>figs
      when(s~>objType=="rect" && s~>layerName==fig~>layerName && s~>purpose=="drawing"
           && caar(s~>bBox)<=car(center) && caadr(s~>bBox)>=car(center)
           && cadar(s~>bBox)<=cadr(center) && cadadr(s~>bBox)>=cadr(center)
       candidate=caadr(s~>bBox)-caar(s~>bBox)
       when(candidate>best best=candidate bounds=s~>bBox)))
     stNeed(best>caadr(fig~>bBox)-caar(fig~>bBox) "Continuous power header was not found"))
    fig2=dbCreateRect(cv fig~>lpp bounds)
    dbCreatePin(net fig2 ct~>name term)
    dbCreateLabel(cv list(fig~>layerName "pin")
     center
     ct~>name "centerCenter" "R0" "roman" 0.1))))
  foreach(pair list(list("FILL_ODPO" odpo) list("FILL_METAL" metal))
   master=dbOpenCellViewByType(lib cadr(pair) "layout" "" "r")
   stNeed(master && dbCreateInst(cv master car(pair) 0:0 "R0") "Missing native fill")
   dbClose(master))
  dbReplaceProp(cv "generatorOwner" "string" "Layout/design/sar-timing-wrapper.il")
  stNeed(dbSave(cv) "Cannot save fill wrapper")
  dbClose(cv) dbClose(core)
  stAudit(lib "sar8_sar_timing" view)
  printf("SAR_FILL_WRAPPER_OK\n")
  t))
