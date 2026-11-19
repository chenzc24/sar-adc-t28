; Primitives for the paired-row CDAC. The caller supplies the target library
; and view. Only a fresh view can be populated. All PCells use their layout view.
procedure(rdOpen(cell)
  let((cv)
    when(ddGetObj(rdLib cell rdView) error("Target already exists: %s/%s/%s\n" rdLib cell rdView))
    cv=dbOpenCellViewByType(rdLib cell rdView "maskLayout" "a")
    cmpRequire(cv && !cv~>shapes && !cv~>instances "Expected an empty maskLayout")
    cv))

procedure(rdNet(cv name)
  or(dbFindNetByName(cv name) dbCreateNet(cv name)))

procedure(rdStack(cv lo hi x y)
  let((p)
    p=cmpPoint(x y)
    for(k lo hi-1 cmpVia(cv sprintf(nil "M%d_M%d" k+1 k) p))
    for(k max(2 lo) hi cmpSquare(cv sprintf(nil "M%d" k) p 0.14))))

procedure(rdMom(cv name x base flip top bot)
  let((inst plus minus expectedTop expectedBot)
    inst=dbCreateParamInstByMasterName(cv "tsmcN28" "cfmom_2t" "layout" name
      cmpPoint(x if(flip then base+2.42 else base)) if(flip then "MX" else "R0") 1
      list(list("Nfinger" "string" "8") list("Lfinger" "string" "2u")
           list("Wfinger" "string" "50n") list("Sfinger" "string" "50n")
           list("StartMn" "string" "1") list("StopMn" "string" "3")))
    cmpRequire(inst "Missing native MOM")
    plus=cmpCenter(car(cmpPinBoxes(inst "PLUS" "M3")))
    minus=cmpCenter(car(cmpPinBoxes(inst "MINUS" "M3")))
    expectedTop=cmpPoint(x+0.38 if(flip then base+0.055 else base+2.365))
    expectedBot=cmpPoint(x+0.38 if(flip then base+2.365 else base+0.055))
    cmpRequire(equal(plus expectedTop) && equal(minus expectedBot) "MOM plate landing changed")
    foreach(term inst~>master~>terminals
      cmpRequire(member(term~>name list("PLUS" "MINUS")) "Unknown MOM terminal")
      dbCreateInstTerm(rdNet(cv if(equal(term~>name "PLUS") then top else bot)) inst term))))

procedure(rdSwitch(cv name model fingers x y bot gate ref body drains feeds)
  let((inst width pm gates d s xs yg yd yr polyHigh gateY p)
    pm=equal(model "pch_mac")
    width=if(pm then "175n" else "150n")
    inst=dbCreateParamInstByMasterName(cv "tsmcN28" model "layout" name cmpPoint(x y) "R0" 1
      list(list("l" "string" "90n") list("Wfg" "string" width)
           list("fingers" "string" sprintf(nil "%d" fingers))
           list("dummyPolyWidth" "string" "60n") list("dummyPolyWidth2" "string" "60n")))
    cmpRequire(inst "Missing reference switch")
    foreach(term inst~>master~>terminals
      dbCreateInstTerm(rdNet(cv case(substring(term~>name 1 1)
        ("D" bot) ("S" ref) ("G" gate) ("B" body) (t error("Unknown MOS terminal\n")))) inst term))
    d=mapcar('cmpCenter cmpPinBoxes(inst "D" "M1"))
    s=mapcar('cmpCenter cmpPinBoxes(inst "S" "M1"))
    yg=y+0.33 yd=y-0.12 yr=y-0.40
    foreach(box cmpPinBoxes(inst "G" "PO")
      when(cadar(box)>cadar(d)
        gateY=cadar(box)+0.105
        polyHigh=gateY+if(pm then 0.135 else 0.075)
        p=cmpPoint(car(cmpCenter(box)) gateY)
        cmpRect(cv "PO" caar(box) cadar(box)-0.005 caadr(box) polyHigh)
        cmpSquare(cv "CO" p 0.04)
        cmpWire(cv rdNet(cv gate) "M1" p cmpPoint(car(p) yg) 0.08)
        gates=cons(p gates)))
    cmpRequire(length(gates)==fingers && length(d)+length(s)==fingers+1 "Native MOS fingers/landings changed")
    cmpImplantExtension(cv inst if(pm then "PP" else "NP") polyHigh+0.075)
    xs=cmpXRange(gates)
    cmpWire(cv rdNet(cv gate) "M1" cmpPoint(car(xs)-0.10 yg) cmpPoint(cadr(xs)+0.10 yg) 0.12)
    foreach(g feeds
      cmpRequire(g>=car(xs)-0.003 && g<=cadr(xs)+0.003 "Gate feed outside native strap")
      rdStack(cv 1 4 g yg))
    foreach(p d
      cmpWire(cv rdNet(cv bot) "M1" p cmpPoint(car(p) yd) 0.05)
      cmpVia(cv "M2_M1" cmpPoint(car(p) yd)))
    xs=cmpXRange(d)
    cmpWire(cv rdNet(cv bot) "M2" cmpPoint(car(xs) yd) cmpPoint(cadr(xs) yd) 0.11)
    foreach(g drains
      cmpRequire(g>=car(xs)-0.003 && g<=cadr(xs)+0.003 "Drain feed outside native strap")
      rdStack(cv 2 3 g yd))
    foreach(p s
      cmpWire(cv rdNet(cv ref) "M1" p cmpPoint(car(p) yr) 0.05)
      cmpVia(cv "M2_M1" cmpPoint(car(p) yr)))))

procedure(rdTap(cv implant x y)
  let((p) p=cmpPoint(x y)
    cmpSquare(cv "OD" p 0.18) cmpSquare(cv implant p 0.33)
    cmpSquare(cv "CO" p 0.04) cmpSquare(cv "M1" p 0.16)
    rdStack(cv 1 4 x y)))

procedure(rdRing(cv x0 y0 x1 y1)
  let((net)
    net=rdNet(cv "VSS")
    foreach(edge list(list(x0 y0 x1 y0) list(x0 y1 x1 y1) list(x0 y0 x0 y1) list(x1 y0 x1 y1))
      foreach(spec list(list("OD" 0.09) list("PP" 0.165))
        cmpRect(cv car(spec) min(car(edge) caddr(edge))-cadr(spec) min(cadr(edge) cadddr(edge))-cadr(spec)
          max(car(edge) caddr(edge))+cadr(spec) max(cadr(edge) cadddr(edge))+cadr(spec)))
      cmpWire(cv net "M1" cmpPoint(car(edge) cadr(edge)) cmpPoint(caddr(edge) cadddr(edge)) 0.24))
    for(k 1 floor((x1-x0)/0.5)-1
      foreach(y list(y0 y1) cmpSquare(cv "CO" cmpPoint(x0+k*0.5 y) 0.04)))
    for(k 1 floor((y1-y0)/0.5)-1
      foreach(x list(x0 x1) cmpSquare(cv "CO" cmpPoint(x y0+k*0.5) 0.04)))))

procedure(rdChild(cv cell name x orient)
  let((master i)
    master=dbOpenCellViewByType(rdLib cell rdView "" "r")
    cmpRequire(master "Missing newly built master")
    i=dbCreateInst(cv master name cmpPoint(x 0) orient)
    cmpRequire(i "Cannot place child") i))
