; Native 11-MOS StrongARM core in three diffusion-shared rows inside N+/P+ guard rings.
; Every finger is its own nf=1 PCell instance (W=0.5u, L=30n) with D/G/S/B bound to the
; schematic nets and S/D sides oriented to them; MNINP, MNINN and MNTAIL are two parallel
; fingers each (instances _1 and _2) of their W=1u schematic devices. Neighbouring
; instances share diffusion through the PDK abutment shapes; the generator adds the
; contacts the PDK leaves out of shared diffusions. Loaded only by the locked physical
; runner; a scratch run may preset saLib.
;
; Gate columns on a 0.13 um pitch, rows from top to bottom:
;   P  (NW, N+ ring to VDD)  Y|RSTY|VDD|PLATN|OUTN|RSTN|VDD|RSTP|OUTP|PLATP|VDD|RSTX|X
;   N1 (P+ ring to VSS)      OUTN|LATN|Y|INP|TAIL|INN|X|LATP|OUTP
;   N2 (same P+ ring)        Y|INP|TAIL|TL|VSS|TL|TAIL|INN|X
; PLATN/LATN and PLATP/LATP share gate columns x=-/+0.195. Routing: M1 for contacts,
; diffusion columns and rings; M2 horizontal straps; M3 vertical trunks at x=0 (CLK),
; -/+0.195 (OUTP/OUTN) and -/+0.39 (Y/X). Inputs leave sideways on M2 from the N1/N2
; channel, CLK enters from the south and the outputs leave north. VDD and VSS pins are
; 0.07 um M2 straps over the top N+ and bottom P+ ring sides, tied to the rings by a via
; every 0.13 um. Latch-gate, tail-gate CLK, input, tail, Y/X stack and supply connections
; use two or three cuts. The output and Y/X straps, the N1 TAIL drop and the reset-gate CLK
; stack keep one cut: the M2 track pitch or mirror symmetry leaves no room for a second.
unless(boundp('saLib) saLib="SAR_ADC_T28_LAYOUT")
procedure(saRequire(ok message)
 unless(ok error("%s\n" message))
)
procedure(saPoint(x y) list(0.005*round(x/0.005) 0.005*round(y/0.005)))
procedure(saRect(cv layer x0 y0 x1 y1 @optional netName)
 let((s)
  s=dbCreateRect(cv list(layer "drawing") list(saPoint(min(x0 x1) min(y0 y1)) saPoint(max(x0 x1) max(y0 y1))))
  when(netName s~>net=dbFindNetByName(cv netName))
  s
 )
)
; Horizontal / vertical wire of width w centred on a track.
procedure(saH(cv layer net y x0 x1 @optional (w 0.05))
 saRect(cv layer x0 y-w/2.0 x1 y+w/2.0 net))
procedure(saV(cv layer net x y0 y1 @optional (w 0.05))
 saRect(cv layer x-w/2.0 y0 x+w/2.0 y1 net))
; Single-cut native via between M(lower) and M(lower+1); e1/e2 are the (x y) enclosures.
; Enclosures match the wire they sit on, so via pads never stick out of a wire.
procedure(saVia(cv lower x y e1 e2)
 let((def)
  def=techFindViaDefByName(techGetTechFile(cv) sprintf(nil "M%d_M%d" lower+1 lower))
  saRequire(def && dbCreateVia(cv def saPoint(x y) "R0" list(list("layer1Enc" e1) list("layer2Enc" e2)))
   "Missing native via")
 )
)
procedure(saCo(cv x y) saRect(cv "CO" x-0.02 y-0.02 x+0.02 y+0.02))
procedure(saPoly(cv x y0 y1) saRect(cv "PO" x-0.015 y0 x+0.015 y1))
; Gate contact: gate poly extended from its OD edge to 0.07 past the contact, 0.20 M1 bar.
procedure(saGate(cv net x yEdge yCo)
 saPoly(cv x yEdge yCo+if(yCo>yEdge 0.07 -0.07))
 saCo(cv x yCo)
 saH(cv "M1" net yCo x-0.10 x+0.10 0.07))
; Contacted shared diffusion: same contact rows and 0.05 M1 column as the PCell's own ends.
procedure(saDiff(cv net x yb w)
 foreach(dy if(w<0.75 list(0.05 0.185 0.32 0.45) list(0.05 0.165 0.28 0.395 0.51 0.62 0.73 0.84 0.95))
  saCo(cv x yb+dy))
 saV(cv "M1" net x yb yb+w)
)
; Guard ring on centre lines x0..x1, y0..y1: 0.10 OD, 0.07 M1, implant enclosure enc.
procedure(saRing(cv net implant x0 y0 x1 y1 enc)
 let((h)
  h=0.05+enc
  foreach(seg list(list(x0 y0 x1 y0) list(x0 y1 x1 y1) list(x0 y0 x0 y1) list(x1 y0 x1 y1))
   let((ax ay bx by)
    ax=nth(0 seg) ay=nth(1 seg) bx=nth(2 seg) by=nth(3 seg)
    saRect(cv "OD" ax-0.05 ay-0.05 bx+0.05 by+0.05)
    saRect(cv implant ax-h ay-h bx+h by+h)
    saRect(cv "M1" ax-0.035 ay-0.035 bx+0.035 by+0.035 net)))
  ; Contacts at >= 0.12 um pitch, corners shared.
  foreach(span list(list(x0 x1 y0 t) list(x0 x1 y1 t) list(y0+0.12 y1-0.12 x0 nil) list(y0+0.12 y1-0.12 x1 nil))
   let((a b c n step p)
    a=nth(0 span) b=nth(1 span) c=nth(2 span)
    n=floor((b-a)/0.12+0.001) step=(b-a)/n
    for(k 0 n
     p=if(nth(3 span) saPoint(a+k*step c) saPoint(c a+k*step))
     saRect(cv "CO" car(p)-0.02 cadr(p)-0.02 car(p)+0.02 cadr(p)+0.02))))
 )
)
procedure(saPin(cv name layer x0 y0 x1 y1)
 let((net fig term)
  net=dbFindNetByName(cv name)
  fig=saRect(cv layer x0 y0 x1 y1 name)
  term=dbCreateTerm(net name "inputOutput")
  saRequire(dbCreatePin(net fig name term) "Cannot create port")
  dbCreateLabel(cv list(layer "pin") saPoint((x0+x1)/2.0 (y0+y1)/2.0) name "centerCenter" "R0" "roman" 0.05)
 )
)
; Native MOS PCell whose first gate is centred on gx, OD bottom at yb. physL/physR are the
; abutment shapes of the drawn left/right sides; nets maps every master terminal to a net.
procedure(saMOS(cv name model w fingers gx yb orient physL physR nets gates)
 let((inst left right got b)
  left=if(equal(orient "R0") physL physR)
  right=if(equal(orient "R0") physR physL)
  inst=dbCreateParamInstByMasterName(cv "tsmcN28" model "layout" name
   saPoint(gx+if(equal(orient "MY") 0.015 -0.015) yb) orient 1
   list(list("l" "string" "30n") list("Wfg" "string" w) list("fingers" "string" sprintf(nil "%d" fingers))
        list("dummyPolyWidth" "string" "30n") list("dummyPolyWidth2" "string" "30n")
        list("leftShape" "string" left) list("rightShape" "string" right)))
  saRequire(inst && caadr(inst~>bBox)-caar(inst~>bBox)<2.0 sprintf(nil "PCell evaluation failed: %s" name))
  foreach(term inst~>master~>terminals
   saRequire(assoc(term~>name nets) sprintf(nil "Unmapped terminal %s.%s" name term~>name))
   dbCreateInstTerm(dbFindNetByName(cv cadr(assoc(term~>name nets))) inst term)
   when(rexMatchp("^G" term~>name)
    foreach(pin term~>pins foreach(fig pin~>figs
     b=dbTransformBBox(fig~>bBox inst~>transform)
     unless(member(0.005*round((caar(b)+caadr(b))/0.01) got)
      got=cons(0.005*round((caar(b)+caadr(b))/0.01) got))))))
  got=sort(got 'lessp)
  saRequire(length(got)==length(gates) && forall(p mapcar('list got gates) abs(car(p)-cadr(p))<0.003)
   sprintf(nil "%s gates at %L, expected %L" name got gates))
  saRequire(length(inst~>instTerms)==length(inst~>master~>terminals) sprintf(nil "%s terminals unbound" name))
  printf("COMPARATOR_DEVICE %s %s W=%s L=30n fingers=%d orient=%s shapes=%s/%s gates=%L nets=%L\n"
   name model w fingers orient left right got nets)
  inst
 )
)
; M1 -> M3 at one point onto a vertical M3 trunk through a 0.11 x 0.13 M2 pad (M2.A.2);
; e1 is the M1 enclosure of the wire the stack sits on.
procedure(saStack(cv net x y e1)
 saVia(cv 1 x y e1 list(0.03 0.03))
 saRect(cv "M2" x-0.055 y-0.065 x+0.055 y+0.065 net)
 saVia(cv 2 x y list(0.03 0.03) list(0.0 0.03))
)
; Diffusion column xd (via1) to the vertical M3 trunk xm (via2) along one M2 track y.
procedure(saStrap(cv net y xd xm @optional (w 0.05))
 let((e)
  e=if(w>0.06 list(0.03 0.01) list(0.03 0.0))
  saVia(cv 1 xd y list(0.0 0.03) e)
  saH(cv "M2" net y min(xd xm)-0.055 max(xd xm)+0.055 w)
  saVia(cv 2 xm y e list(0.0 0.03))
 )
)
; Latch gate stack with two via1 cuts along the gate bar (s points away from the core
; centre) and two via2 cuts along the output trunk.
procedure(saLatchStack(cv net x y s ePad)
 saH(cv "M1" net y x x+s*0.185 0.07)
 foreach(xc list(x x+s*0.13) saVia(cv 1 xc y list(0.03 0.01) ePad))
 saRect(cv "M2" min(x x+s*0.13)-0.055 y-0.065 max(x x+s*0.13)+0.055 y+0.065 net)
 saRect(cv "M2" x-0.055 y-0.065 x+0.055 y+0.185 net)
 foreach(yc list(y y+0.13) saVia(cv 2 x yc ePad list(0.0 0.03)))
)
procedure(saBuild()
 let((cv lib owner eCol eRow eBar eTall ePad yRt yRb yGt yN1 yN2 yGb yBot)
  ; Via enclosures (x y) matching a 0.05 column, a 0.05 row wire, a 0.07 bar, a 0.07 column.
  eCol=list(0.0 0.03) eRow=list(0.03 0.0) eBar=list(0.03 0.01) eTall=list(0.01 0.03)
  ePad=list(0.03 0.03)
  ; Floorplan: P OD 0..0.5 inside the N+ ring yRb..yRt; N1 OD yN1-0.5..yN1 and N2 OD
  ; yN2-0.5..yN2 inside the P+ ring yGb..yGt. Both rings share the same left/right edges.
  yRt=0.76 yRb=-0.44 yGt=-0.67 yN1=-0.93 yN2=-1.77 yGb=-2.53 yBot=yGb-0.115
  lib=ddGetObj(saLib)
  saRequire(lib "Missing layout library")
  when(equal(saLib "SAR_ADC_T28_LAYOUT")
   saRequire(equal(lib~>readPath "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_LAYOUT") "Wrong library"))
  cv=dbOpenCellViewByType(saLib "sar_strongarm_t28_core" "layout" "maskLayout" "a")
  saRequire(cv "Cannot open comparator")
  owner=dbFindProp(cv "generatorOwner")
  saRequire((!cv~>instances && !cv~>shapes) || (owner && equal(owner~>value "Layout/design/comparator.il"))
   "Existing comparator is not owned by this generator")
  foreach(obj cv~>instances dbDeleteObject(obj))
  foreach(obj cv~>shapes dbDeleteObject(obj))
  foreach(obj cv~>vias dbDeleteObject(obj))
  foreach(obj cv~>nets dbDeleteObject(obj))
  dbReplaceProp(cv "generatorOwner" "string" "Layout/design/comparator.il")
  foreach(name list("CLK" "OUTN" "OUTP" "VDD" "VINN" "VINP" "VSS" "X" "Y" "TAIL") dbCreateNet(cv name))

  ; ---- P row: name gx orient left right D G (S and B are VDD)
  foreach(d list(list("MPRSTY" -0.325 "MY" "normal" "same" "Y" "CLK")
                 list("MPLATN" -0.195 "R0" "same" "same" "OUTN" "OUTP")
                 list("MPRSTN" -0.065 "MY" "same" "same" "OUTN" "CLK")
                 list("MPRSTP" 0.065 "R0" "same" "same" "OUTP" "CLK")
                 list("MPLATP" 0.195 "MY" "same" "same" "OUTP" "OUTN")
                 list("MPRSTX" 0.325 "R0" "same" "normal" "X" "CLK"))
   saMOS(cv nth(0 d) "pch_mac" "500n" 1 nth(1 d) 0 nth(2 d) nth(3 d) nth(4 d)
    list(list("D" nth(5 d)) list("G" nth(6 d)) list("S" "VDD") list("B" "VDD")) list(nth(1 d))))
  ; ---- N1 and N2 rows: name gx yBottom orient left right D G S (B is VSS)
  foreach(d list(list("MNLATN" -0.195 yN1-0.5 "MY" "normal" "same" "OUTN" "OUTP" "Y")
                 list("MNINP_1" -0.065 yN1-0.5 "MY" "same" "same" "Y" "VINP" "TAIL")
                 list("MNINN_1" 0.065 yN1-0.5 "R0" "same" "same" "X" "VINN" "TAIL")
                 list("MNLATP" 0.195 yN1-0.5 "R0" "same" "normal" "OUTP" "OUTN" "X")
                 list("MNINP_2" -0.195 yN2-0.5 "MY" "normal" "same" "Y" "VINP" "TAIL")
                 list("MNTAIL_1" -0.065 yN2-0.5 "MY" "same" "same" "TAIL" "CLK" "VSS")
                 list("MNTAIL_2" 0.065 yN2-0.5 "R0" "same" "same" "TAIL" "CLK" "VSS")
                 list("MNINN_2" 0.195 yN2-0.5 "R0" "same" "normal" "X" "VINN" "TAIL"))
   saMOS(cv nth(0 d) "nch_mac" "500n" 1 nth(1 d) nth(2 d) nth(3 d) nth(4 d) nth(5 d)
    list(list("D" nth(6 d)) list("G" nth(7 d)) list("S" nth(8 d)) list("B" "VSS")) list(nth(1 d))))

  ; ---- wells, implants and guard rings
  saRect(cv "NW" -0.815 yRb-0.115 0.815 yRt+0.115)
  saRect(cv "PP" -0.45 yRb+0.115 0.45 yRt-0.115)
  saRing(cv "VDD" "NP" -0.70 yRb 0.70 yRt 0.065)
  saRect(cv "NP" -0.40 yGb+0.115 0.40 yGt-0.115)
  saRing(cv "VSS" "PP" -0.70 yGb 0.70 yGt 0.065)

  ; ---- contacted shared diffusions; the P-row VDD columns run straight into the ring in M1
  foreach(c list(list("VDD" -0.26) list("OUTN" -0.13) list("VDD" 0) list("OUTP" 0.13) list("VDD" 0.26))
   saDiff(cv car(c) cadr(c) 0 0.5))
  foreach(x list(-0.26 0 0.26) saV(cv "M1" "VDD" x 0.5 yRt))
  foreach(c list(list("Y" -0.13 yN1) list("TAIL" 0 yN1) list("X" 0.13 yN1)
                 list("TAIL" -0.13 yN2) list("VSS" 0 yN2) list("TAIL" 0.13 yN2))
   saDiff(cv car(c) cadr(c) caddr(c)-0.5 0.5))

  ; ---- latch gates: P contacted below its row, N1 above its row, both on the output trunk
  ; of their shared column.
  foreach(g list(list("OUTP" -0.195) list("OUTN" 0.195))
   saGate(cv car(g) cadr(g) 0 -0.15)
   saLatchStack(cv car(g) cadr(g) -0.15 if(cadr(g)<0 -1 1) ePad)
   saGate(cv car(g) cadr(g) yN1 yN1+0.10)
   saLatchStack(cv car(g) cadr(g) yN1+0.10 if(cadr(g)<0 -1 1) ePad)
   saV(cv "M3" car(g) cadr(g) yN1-0.345 yRt+0.115))
  ; ---- CLK: P reset gates on one M1 bus below the P row, tail gates on one M1 bar below
  ; N2, joined by the centre M3 trunk that also leaves the core at the south edge.
  foreach(x list(-0.325 -0.065 0.065 0.325) saPoly(cv x 0 -0.35) saCo(cv x -0.28))
  saH(cv "M1" "CLK" -0.28 -0.36 0.36 0.07)
  ; Top CLK stack stays single-cut: a second cut has no mirror-symmetric spot and would sit
  ; nearer the OUTP strap than the OUTN strap.
  saStack(cv "CLK" 0 -0.28 eBar)
  ; Bottom CLK stack: three cuts along the tail gate bar and a local M3 widening.
  foreach(x list(-0.065 0.065) saPoly(cv x yN2-0.5 yN2-0.67) saCo(cv x yN2-0.60))
  saH(cv "M1" "CLK" yN2-0.60 -0.185 0.185 0.07)
  saRect(cv "M2" -0.185 yN2-0.665 0.185 yN2-0.535 "CLK")
  saRect(cv "M3" -0.185 yN2-0.66 0.185 yN2-0.54 "CLK")
  foreach(x list(-0.13 0 0.13)
   saVia(cv 1 x yN2-0.60 eBar ePad)
   saVia(cv 2 x yN2-0.60 ePad ePad))
  saV(cv "M3" "CLK" 0 yBot -0.225)

  ; ---- cross-coupling: drain straps in M2 to the opposite output trunk. In each row the
  ; Y/X strap or stack sits between the two output straps.
  saStrap(cv "OUTP" 0.125 0.13 -0.195)
  saStrap(cv "OUTN" 0.375 -0.13 0.195)
  saStrap(cv "OUTN" yN1-0.06 -0.26 0.195)
  saStrap(cv "OUTP" yN1-0.29 0.26 -0.195)
  ; ---- Y / X: P reset drain stacked onto its trunk; N1 and N2 straps from their columns.
  foreach(s list(list("Y" -1) list("X" 1))
   ; three cuts, pad grown both ways so the OUTP strap end (low) and the OUTN strap end
   ; (high) each face one of the Y/X pads
   saRect(cv "M2" 0.39*cadr(s)-0.055 0.065 0.39*cadr(s)+0.055 0.435 car(s))
   foreach(yc list(0.12 0.25 0.38)
    saVia(cv 1 0.39*cadr(s) yc eCol ePad)
    saVia(cv 2 0.39*cadr(s) yc ePad eCol))
   saStrap(cv car(s) yN1-0.175 0.13*cadr(s) 0.39*cadr(s))
   saStrap(cv car(s) yN2-0.25 0.26*cadr(s) 0.39*cadr(s) 0.07)
   ; second via2 on the trunk above the N2 strap
   saV(cv "M2" car(s) 0.39*cadr(s) yN2-0.25 yN2-0.065)
   saVia(cv 2 0.39*cadr(s) yN2-0.12 eCol eCol)
   saV(cv "M3" car(s) 0.39*cadr(s) yN2-0.305 0.435))
  ; ---- TAIL: N1 shared diffusion down the centre in M2 to both N2 TAIL diffusions
  saVia(cv 1 0 yN1-0.445 eCol eCol)
  saV(cv "M2" "TAIL" 0 yN1-0.5 yN2-0.085)
  saH(cv "M2" "TAIL" yN2-0.06 -0.185 0.185)
  foreach(x list(-0.13 0.13)
   saVia(cv 1 x yN2-0.06 eCol eRow)
   saV(cv "M2" "TAIL" x yN2-0.245 yN2-0.06)
   saVia(cv 1 x yN2-0.19 eCol eCol))
  ; ---- VSS: tail source column (two cuts) to both P+ ring sides on one M2 bar, which
  ; drops along the ring sides to the bottom VSS strap.
  saVia(cv 1 0 yN2-0.44 eCol eRow)
  saVia(cv 1 0 yN2-0.31 eCol eCol)
  saV(cv "M2" "VSS" 0 yN2-0.44 yN2-0.255)
  saH(cv "M2" "VSS" yN2-0.44 -0.755 0.755)
  foreach(x list(-0.70 0.70)
   saVia(cv 1 x yN2-0.44 eTall eRow)
   saV(cv "M2" "VSS" x yGb yN2-0.44 0.07)
   saVia(cv 1 x yN2-0.57 eTall eTall))
  ; ---- inputs: both fingers' gates contacted in the N1/N2 channel, joined by one M1 L,
  ; and taken sideways on M2 to the west (VINP) and east (VINN) edges.
  foreach(s list(list("VINP" -1) list("VINN" 1))
   saPoly(cv 0.065*cadr(s) yN1-0.5 yN1-0.67)
   saCo(cv 0.065*cadr(s) yN1-0.60)
   saPoly(cv 0.195*cadr(s) yN2 yN2+0.17)
   saCo(cv 0.195*cadr(s) yN2+0.10)
   saH(cv "M1" car(s) yN1-0.60 0.03*cadr(s) 0.23*cadr(s) 0.07)
   saV(cv "M1" car(s) 0.195*cadr(s) yN2+0.065 yN1-0.565 0.07)
   saVia(cv 1 0.195*cadr(s) yN2+0.17 eTall eRow)
   saH(cv "M1" car(s) yN2+0.17 0.195*cadr(s) 0.38*cadr(s) 0.07)
   saVia(cv 1 0.325*cadr(s) yN2+0.17 eBar eRow)
   saH(cv "M2" car(s) yN2+0.17 0.14*cadr(s) 0.815*cadr(s)))

  ; ---- ports
  saPin(cv "OUTP" "M3" -0.22 yRt+0.015 -0.17 yRt+0.115)
  saPin(cv "OUTN" "M3" 0.17 yRt+0.015 0.22 yRt+0.115)
  saPin(cv "CLK" "M3" -0.025 yBot 0.025 yBot+0.10)
  saPin(cv "VINP" "M2" -0.815 yN2+0.145 -0.715 yN2+0.195)
  saPin(cv "VINN" "M2" 0.715 yN2+0.145 0.815 yN2+0.195)
  ; Supply pins: M2 straps over the top N+ and bottom P+ ring sides, one via per 0.13 um.
  saPin(cv "VDD" "M2" -0.735 yRt-0.035 0.735 yRt+0.035)
  saPin(cv "VSS" "M2" -0.735 yGb-0.035 0.735 yGb+0.035)
  for(k 0 9
   saVia(cv 1 -0.585+0.13*k yRt eBar eBar)
   saVia(cv 1 -0.585+0.13*k yGb eBar eBar))
  saRequire(dbSave(cv) "Cannot save comparator")
  dbClose(cv)
  cv=dbOpenCellViewByType(saLib "sar_strongarm_t28_core" "layout" "" "r")
  saRequire(length(cv~>instances)==14 && length(cv~>terminals)==7 "Saved comparator count mismatch")
  saRequire(forall(i cv~>instances length(i~>instTerms)==length(i~>master~>terminals)) "Saved terminals unbound")
  printf("PILOT_OA_OK sar_strongarm_t28_core instances=14 ports=7 bbox=%L\n" cv~>bBox)
  dbClose(cv)
  t
 )
)
if(errset(saBuild() t) then exit(0) else exit(1))
