; Compact B1-B0-B1 array and the frozen B0/B1 reference switches.
; Run in the private pilot library through run_physical.py compact.

procedure(cmpRequire(ok message)
  unless(ok error("%s\n" message))
)

procedure(cmpGrid(x)
  0.005 * round(x / 0.005)
)

procedure(cmpPoint(x y)
  list(cmpGrid(x) cmpGrid(y))
)

procedure(cmpCenter(box)
  cmpPoint((caar(box) + caadr(box))/2.0 (cadar(box) + cadadr(box))/2.0)
)

procedure(cmpRect(cv layer x0 y0 x1 y1)
  let((shape)
    shape = dbCreateRect(cv list(layer "drawing") list(cmpPoint(x0 y0) cmpPoint(x1 y1)))
    cmpRequire(shape "Cannot create rectangle")
    shape
  )
)

procedure(cmpSquare(cv layer p width)
  let((x y half)
    x = car(p)
    y = cadr(p)
    half = width / 2.0
    cmpRect(cv layer x-half y-half x+half y+half)
  )
)

procedure(cmpWire(cv net layer p q width)
  let((shape half)
    cmpRequire(abs(car(p)-car(q)) < 0.001 || abs(cadr(p)-cadr(q)) < 0.001
               "Expected a Manhattan segment")
    half = width / 2.0
    shape = cmpRect(cv layer min(car(p) car(q))-half min(cadr(p) cadr(q))-half
                             max(car(p) car(q))+half max(cadr(p) cadr(q))+half)
    shape~>net = net
    shape
  )
)

procedure(cmpPort(cv net layer p width)
  let((name shape term)
    name = net~>name
    shape = cmpSquare(cv layer p width)
    term = dbCreateTerm(net name "inputOutput")
    cmpRequire(term && dbCreatePin(net shape name term) "Cannot create compact fixture port")
    cmpRequire(dbCreateLabel(cv list(layer "pin") p name "centerCenter" "R0" "roman" 0.095)
               "Cannot create stream port label")
  )
)

procedure(cmpVia(cv name p)
  let((def)
    def = techFindViaDefByName(techGetTechFile(cv) name)
    cmpRequire(def && dbCreateVia(cv def p "R0") "Cannot create native via")
  )
)

procedure(cmpPinBoxes(inst prefix layer)
  let((boxes)
    foreach(term inst~>master~>terminals
      when(equal(term~>name prefix) ||
           (strlen(term~>name) > strlen(prefix) &&
            equal(substring(term~>name 1 strlen(prefix)+1) strcat(prefix "_")))
        foreach(pin term~>pins
          foreach(fig pin~>figs
            when(equal(fig~>lpp list(layer "drawing"))
              boxes = cons(dbTransformBBox(fig~>bBox inst~>transform) boxes)
            )
          )
        )
      )
    )
    cmpRequire(boxes "Missing native device pin landing")
    boxes
  )
)

procedure(cmpMOM(cv name x)
  let((inst)
    inst = dbCreateParamInstByMasterName(cv "tsmcN28" "cfmom_2t" "layout" name cmpPoint(x 0) "R0" 1
      list(list("Nfinger" "string" "8") list("Lfinger" "string" "2u")
           list("Wfinger" "string" "50n") list("Sfinger" "string" "50n")
           list("StartMn" "string" "1") list("StopMn" "string" "3")))
    cmpRequire(inst "Cannot create native MOM")
    inst
  )
)

procedure(cmpLanding(inst pin layer upper)
  let((boxes box)
    boxes = cmpPinBoxes(inst pin layer)
    cmpRequire(length(boxes) == 1 "Expected one MOM landing on the selected metal")
    box = car(boxes)
    cmpPoint(car(cmpCenter(box)) if(upper then cadadr(box) else cadar(box)))
  )
)

procedure(cmpMOS(cv model width fingers name x y)
  let((inst box)
    inst = dbCreateParamInstByMasterName(cv "tsmcN28" model "layout" name cmpPoint(x y) "R0" 1
      list(list("l" "string" "90n") list("Wfg" "string" width)
           list("fingers" "string" fingers)
           list("dummyPolyWidth" "string" "60n") list("dummyPolyWidth2" "string" "60n")))
    cmpRequire(inst "Cannot create folded reference switch")
    box = inst~>bBox
    cmpRequire(caadr(box)-caar(box) < 2.0 && cadadr(box)-cadar(box) < 0.8
               "Unexpected native switch PCell bounding box")
    inst
  )
)

procedure(cmpXRange(points)
  let((lo hi)
    lo = caar(points)
    hi = lo
    foreach(p points
      lo = min(lo car(p))
      hi = max(hi car(p))
    )
    list(lo hi)
  )
)

procedure(cmpImplantExtension(cv inst layer upperY)
  let((figures box)
    figures = setof(shape inst~>master~>shapes
                    shape~>objType == "rect" && equal(shape~>lpp list(layer "drawing")))
    cmpRequire(length(figures) == 1 "Expected one native implant rectangle")
    box = dbTransformBBox(car(figures)~>bBox inst~>transform)
    cmpRect(cv layer caar(box) cadadr(box)-0.10 caadr(box) upperY)
  )
)

procedure(cmpSwitchRoutes(cv inst gate bot ref trunkX yRef yGate fingers)
  let((gates drains sources xs yDrain gateX gateY polyHigh pmos)
    pmos = equal(inst~>master~>cellName "pch_mac")
    drains = mapcar('cmpCenter cmpPinBoxes(inst "D" "M1"))
    sources = mapcar('cmpCenter cmpPinBoxes(inst "S" "M1"))
    ; Continue the native gate stripe at its channel width and put CO above
    ; diffusion. This gives both ends of the contact 50 nm poly enclosure.
    foreach(box cmpPinBoxes(inst "G" "PO")
      when(cadar(box) > cadar(drains)
        gateX = car(cmpCenter(box))
        gateY = cadar(box) + 0.105
        ; PMOS poly extends beyond the existing PMET edge before it ends.
        polyHigh = gateY + if(pmos then 0.135 else 0.075)
        cmpRect(cv "PO" caar(box) cadar(box)-0.005 caadr(box) polyHigh)
        cmpSquare(cv "CO" cmpPoint(gateX gateY) 0.04)
        gates = cons(cmpPoint(gateX gateY) gates)
      )
    )
    cmpRequire(length(gates) == fingers && length(drains) + length(sources) == fingers+1
               "Unexpected folded switch contacts")
    cmpImplantExtension(cv inst if(pmos then "PP" else "NP") polyHigh+0.075)

    foreach(p gates
      cmpWire(cv gate "M1" p cmpPoint(car(p) yGate) 0.08)
    )
    xs = cmpXRange(gates)
    cmpWire(cv gate "M1" cmpPoint(car(xs) yGate) cmpPoint(cadr(xs) yGate) 0.08)
    cmpPort(cv gate "M1" cmpPoint((car(xs)+cadr(xs))/2.0 yGate) 0.08)

    ; Place the drain via on the M1 escape, away from the gate contact.
    yDrain = yRef + 0.21
    foreach(p drains
      cmpWire(cv bot "M1" p cmpPoint(car(p) yDrain) 0.05)
      cmpVia(cv "M2_M1" cmpPoint(car(p) yDrain))
    )
    xs = cmpXRange(drains)
    cmpRequire(trunkX > car(xs) && trunkX < cadr(xs) "Drain feed outside its landing rail")
    cmpWire(cv bot "M2" cmpPoint(car(xs) yDrain) cmpPoint(cadr(xs) yDrain) 0.11)
    cmpVia(cv "M3_M2" cmpPoint(trunkX yDrain))

    foreach(p sources
      cmpWire(cv ref "M1" p cmpPoint(car(p) yRef) 0.05)
      cmpVia(cv "M2_M1" cmpPoint(car(p) yRef))
    )
    list(yDrain cmpXRange(sources))
  )
)

procedure(cmpRefRail(cv ref y l r)
  let((edge)
    edge = cmpPoint(2.96 y)
    cmpWire(cv ref "M2" cmpPoint(min(car(cadr(l)) car(cadr(r))) y) edge 0.12)
    cmpPort(cv ref "M2" edge 0.12)
  )
)

procedure(cmpTap(cv net implant p)
  cmpSquare(cv "OD" p 0.18)
  cmpSquare(cv implant p 0.33)
  cmpSquare(cv "CO" p 0.04)
  cmpPort(cv net "M1" p 0.16)
)

procedure(cmpReadback()
  let((cv names)
    cv = dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" "sar8_mom_ratio" "layout" "" "r")
    cmpRequire(cv && length(cv~>instances) == 7 && length(cv~>terminals) == 11
               "Unexpected saved compact view")
    names = cv~>terminals~>name
    foreach(name list("TOP" "B0" "B1" "GN0" "GP0" "GN1" "GP1" "VDD" "VSS" "VREFN" "VREFP")
      cmpRequire(member(name names) "Missing saved port")
    )
    foreach(inst cv~>instances
      printf("COMPACT_DEVICE %s %s %L\n" inst~>name inst~>master~>cellName inst~>bBox)
    )
    printf("PILOT_OA_OK sar8_mom_ratio compact instances=7 ports=11 bbox=%L\n" cv~>bBox)
    dbClose(cv)
    t
  )
)

procedure(cmpBuild()
  let((lib cv top b0 b1 vdd vss refn refp gn0 gn1 gp0 gp1
       left middle right pL pC pR xL xC xR pitch
       n0 n1 p0 p1 nr0 nr1 pr0 pr1 xBot0 xBot1)
    lib = ddGetObj("SAR_ADC_T28_LAYOUT")
    cmpRequire(lib && equal(lib~>readPath "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_LAYOUT") &&
               ddGetObj("SAR_ADC_T28_LAYOUT" "sar8_mom_ratio" "layout")
               "The existing private working view is required")
    cv = dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" "sar8_mom_ratio" "layout" "maskLayout" "w")
    cmpRequire(cv && !cv~>instances && !cv~>shapes "Cannot regenerate the private working view")

    top = dbCreateNet(cv "TOP")
    b0 = dbCreateNet(cv "B0")
    b1 = dbCreateNet(cv "B1")
    vdd = dbCreateNet(cv "VDD")
    vss = dbCreateNet(cv "VSS")
    refn = dbCreateNet(cv "VREFN")
    refp = dbCreateNet(cv "VREFP")
    gn0 = dbCreateNet(cv "GN0")
    gn1 = dbCreateNet(cv "GN1")
    gp0 = dbCreateNet(cv "GP0")
    gp1 = dbCreateNet(cv "GP1")

    pitch = 0.96
    left = cmpMOM(cv "MOM_B1L" 0)
    middle = cmpMOM(cv "MOM_B0" pitch)
    right = cmpMOM(cv "MOM_B1R" 2*pitch)
    pL = cmpLanding(left "PLUS" "M3" t)
    pC = cmpLanding(middle "PLUS" "M3" t)
    pR = cmpLanding(right "PLUS" "M3" t)
    xL = car(pL)
    xC = car(pC)
    xR = car(pR)
    foreach(p list(pL pC pR) cmpWire(cv top "M3" p cmpPoint(car(p) 2.70) 0.12))
    cmpWire(cv top "M3" cmpPoint(xL 2.70) cmpPoint(xR 2.70) 0.12)
    cmpPort(cv top "M3" cmpPoint(xC 2.70) 0.12)

    ; Match the two outer B1 drops to the midpoint. B0 crosses underneath on M2.
    cmpWire(cv b1 "M3" cmpLanding(left "MINUS" "M3" nil) cmpPoint(xL -0.25) 0.12)
    cmpWire(cv b1 "M3" cmpLanding(right "MINUS" "M3" nil) cmpPoint(xR -0.25) 0.12)
    cmpWire(cv b1 "M3" cmpPoint(xL -0.25) cmpPoint(xR -0.25) 0.12)
    xBot1 = 2.20
    cmpWire(cv b1 "M3" cmpPoint(xC -0.25) cmpPoint(xC -0.56) 0.12)
    cmpWire(cv b1 "M3" cmpPoint(xC -0.56) cmpPoint(xBot1 -0.56) 0.12)

    xBot0 = 0.58
    cmpWire(cv b0 "M2" cmpLanding(middle "MINUS" "M2" nil) cmpPoint(xC -0.46) 0.12)
    cmpWire(cv b0 "M2" cmpPoint(xC -0.46) cmpPoint(xBot0 -0.46) 0.12)
    cmpVia(cv "M3_M2" cmpPoint(xBot0 -0.46))

    ; Frozen B uses three and six parallel units, respectively, in each leg.
    n0 = cmpMOS(cv "nch_mac" "150n" "3" "N0_REFN" 0.25 -1.05)
    n1 = cmpMOS(cv "nch_mac" "150n" "6" "N1_REFN" 1.53 -1.05)
    p0 = cmpMOS(cv "pch_mac" "175n" "3" "P0_REFP" 0.25 -2.05)
    p1 = cmpMOS(cv "pch_mac" "175n" "6" "P1_REFP" 1.53 -2.05)
    nr0 = cmpSwitchRoutes(cv n0 gn0 b0 refn xBot0 -1.38 -0.72 3)
    nr1 = cmpSwitchRoutes(cv n1 gn1 b1 refn xBot1 -1.38 -0.72 6)
    pr0 = cmpSwitchRoutes(cv p0 gp0 b0 refp xBot0 -2.38 -1.70 3)
    pr1 = cmpSwitchRoutes(cv p1 gp1 b1 refp xBot1 -2.38 -1.70 6)
    cmpRefRail(cv refn -1.38 nr0 nr1)
    cmpRefRail(cv refp -2.38 pr0 pr1)
    cmpWire(cv b0 "M3" cmpPoint(xBot0 -0.46) cmpPoint(xBot0 car(pr0)) 0.12)
    cmpWire(cv b1 "M3" cmpPoint(xBot1 -0.56) cmpPoint(xBot1 car(pr1)) 0.12)
    cmpPort(cv b0 "M3" cmpPoint(xBot0 -0.63) 0.12)
    cmpPort(cv b1 "M3" cmpPoint(xBot1 -0.63) 0.12)

    ; The two PMOS devices share a contacted n-well. The NMOS share substrate.
    cmpRect(cv "NW" -0.64 -2.28 2.92 -1.50)
    cmpTap(cv vdd "NP" cmpPoint(-0.36 -1.96))
    cmpTap(cv vss "PP" cmpPoint(-0.36 -0.975))

    cmpRequire(dbSave(cv) "Cannot save compact working view")
    dbClose(cv)
    cmpReadback()
  )
)

if(errset(cmpBuild() t) then exit(0) else exit(1))
