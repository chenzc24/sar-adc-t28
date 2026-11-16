; Native OA generator for the two disposable SAR8 MOM fixtures.
; The runner sets pilotCell, pilotB1Extension and pilotOpenB1 before loading.

procedure(pilotRequire(ok message)
  unless(ok error("%s\n" message))
)

procedure(pilotPinBox(inst terminal)
  let((hits)
    foreach(term inst~>master~>terminals
      when(equal(term~>name terminal)
        foreach(pin term~>pins
          foreach(fig pin~>figs
            when(equal(fig~>lpp list("M3" "drawing"))
              hits = cons(dbTransformBBox(fig~>bBox inst~>transform) hits)
            )
          )
        )
      )
    )
    pilotRequire(length(hits) == 1 "Expected one M3 landing per MOM terminal")
    car(hits)
  )
)

procedure(pilotCenter(box)
  list((caar(box)+caadr(box))/2.0 (cadar(box)+cadadr(box))/2.0)
)

procedure(pilotWire(cv net p q)
  let((half fig)
    half = 0.08
    pilotRequire(car(p)==car(q) || cadr(p)==cadr(q) "Expected a Manhattan wire")
    fig = dbCreateRect(cv list("M3" "drawing")
      list(list(min(car(p) car(q))-half min(cadr(p) cadr(q))-half)
           list(max(car(p) car(q))+half max(cadr(p) cadr(q))+half)))
    pilotRequire(fig "Cannot create wire")
    fig~>net = net
    fig
  )
)

procedure(pilotPort(cv net p half)
  let((name term fig label)
    name = net~>name
    term = dbCreateTerm(net name "inputOutput")
    fig = dbCreateRect(cv list("M3" "drawing")
      list(list(car(p)-half cadr(p)-half) list(car(p)+half cadr(p)+half)))
    pilotRequire(term && fig && dbCreatePin(net fig name term) "Cannot create OA port")
    label = dbCreateLabel(cv list("M3" "pin") p name "centerCenter" "R0" "roman" 0.1)
    pilotRequire(label "Cannot create stream port label")
  )
)

procedure(pilotReadback(cellName ratio openB1 ext)
  let((cv n expected routeTerms)
    cv = dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" cellName "layout" "" "r")
    pilotRequire(cv "Cannot reopen saved layout")
    n = if(ratio then 3 else 1)
    pilotRequire(length(cv~>instances)==n "Unexpected number of saved MOMs")
    routeTerms = if(ratio then list("TOP" "B0" "B1") else list("TOP" "B0"))
    pilotRequire(length(cv~>terminals)==length(routeTerms) "Unexpected number of saved ports")
    foreach(term cv~>terminals
      pilotRequire(member(term~>name routeTerms) && length(term~>pins)==1 "Unexpected OA terminal")
      printf("PILOT_PORT %s %L\n" term~>name car(car(term~>pins)~>figs)~>bBox)
    )
    expected = list(list("Nfinger" "8") list("Lfinger" "2u") list("Wfinger" "50n")
                    list("Sfinger" "50n") list("StartMn" "1") list("StopMn" "3"))
    foreach(inst cv~>instances
      pilotRequire(equal(inst~>master~>libName "tsmcN28") &&
                   equal(inst~>master~>cellName "cfmom_2t") "Unexpected PCell master")
      foreach(item expected
        let((match)
          foreach(prop inst~>master~>parameters~>value
            when(equal(prop~>name car(item)) match=prop~>value))
          pilotRequire(equal(match cadr(item)) "PCell parameter did not survive save")
        )
      )
      printf("PILOT_MOM %s %L PLUS_M3=%L MINUS_M3=%L\n"
        inst~>name inst~>bBox pilotPinBox(inst "PLUS") pilotPinBox(inst "MINUS"))
    )
    printf("PILOT_OA_OK %s instances=%d ports=%d openB1=%L extension=%L\n"
      cellName n length(routeTerms) openB1 ext)
    dbClose(cv)
    t
  )
)

procedure(pilotBuild(cellName ext openB1)
  let((lib cv ratio n top b0 b1 dangling topLand lowLand plus minus inst
       plusBox minusBox pTop pLow b1End i origin portHalf)
    pilotRequire(member(cellName list("sar8_mom_unit" "sar8_mom_ratio")) "Unexpected target cell")
    pilotRequire(member(ext list(0.5 3.5)) "Unexpected B1 extension")
    ratio = equal(cellName "sar8_mom_ratio")
    ; In the ratio fixture TOP enters a rail; match the rail width to avoid
    ; a small jog at the port. The standalone unit retains its landing pad.
    portHalf = if(ratio then 0.08 else 0.12)
    pilotRequire(ratio || !openB1 "Open control requires ratio fixture")
    lib = ddGetObj("SAR_ADC_T28_LAYOUT")
    unless(lib
      lib = ddCreateLib("SAR_ADC_T28_LAYOUT" "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_LAYOUT")
      pilotRequire(lib && techBindTechFile(lib "tsmcN28") "Cannot bind the private library")
    )
    pilotRequire(lib && equal(lib~>readPath "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_LAYOUT") "Not the unified layout library")
    cv = dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" cellName "layout" "maskLayout" "w")
    pilotRequire(cv "Cannot open work cell")
    pilotRequire(!cv~>instances && !cv~>shapes && !cv~>nets "Expected empty regeneration buffer")
    top = dbCreateNet(cv "TOP")
    b0 = dbCreateNet(cv "B0")
    when(ratio b1 = dbCreateNet(cv "B1"))
    when(openB1 dangling = dbCreateNet(cv "CONTROL_OPEN"))
    n = if(ratio then 3 else 1)
    for(i 0 n-1
      origin = list(2.0*i 0.0)
      inst = dbCreateParamInstByMasterName(cv "tsmcN28" "cfmom_2t" "layout"
        sprintf(nil "C%d" i) origin "R0" 1
        list(list("Nfinger" "string" "8") list("Lfinger" "string" "2u")
             list("Wfinger" "string" "50n") list("Sfinger" "string" "50n")
             list("StartMn" "string" "1") list("StopMn" "string" "3")))
      pilotRequire(inst "Cannot instantiate cfmom_2t")
      plusBox = pilotPinBox(inst "PLUS")
      minusBox = pilotPinBox(inst "MINUS")
      plus = list(car(pilotCenter(plusBox)) cadadr(plusBox))
      minus = list(car(pilotCenter(minusBox)) cadar(minusBox))
      pTop = list(car(plus) 3.20)
      pLow = list(car(minus) -0.80)
      pilotWire(cv top plus pTop)
      pilotWire(cv cond((i==0 b0) (i==1 && openB1 dangling) (t b1)) minus pLow)
      topLand = append(topLand list(pTop))
      lowLand = append(lowLand list(pLow))
    )
    when(ratio
      pilotWire(cv top car(topLand) caddr(topLand))
      unless(openB1 pilotWire(cv b1 cadr(lowLand) caddr(lowLand)))
      b1End = list(car(caddr(lowLand))+ext -0.80)
      pilotWire(cv b1 caddr(lowLand) b1End)
      pilotPort(cv b1 b1End portHalf)
    )
    pilotPort(cv top car(topLand) portHalf)
    pilotPort(cv b0 car(lowLand) portHalf)
    pilotRequire(dbSave(cv) "Cannot save work cell")
    dbClose(cv)
    pilotReadback(cellName ratio openB1 ext)
  )
)

if(errset(pilotBuild(pilotCell pilotB1Extension pilotOpenB1) t) then exit(0) else exit(1))
