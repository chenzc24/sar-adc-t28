; Single-channel Bootstrap prefill core, with physical VDD/VSS for schematic VDD!/0.
unless(boundp('bsLib) bsLib="SAR_ADC_T28_LAYOUT")
; Main-switch fingers beside Msin, and the target view. The defaults build the
; adopted four-finger design into the published layout view; a sampler
; candidate goes to its own view layout_mmain<N>.
unless(boundp('bsMainFingers) bsMainFingers=4)
unless(boundp('bsView) bsView="layout")
procedure(bsRequire(ok message) unless(ok error("%s\n" message)))
bsRequire(evenp(bsMainFingers) && bsMainFingers>=2 "bsMainFingers must be even")
procedure(bsPoint(x y) list(0.005*round(x/0.005) 0.005*round(y/0.005)))
; Evaluate the installed CDF callbacks just as the instance form does. The 1.8 V
; MOS generator uses the resulting contact/via enclosures to build its routes.
procedure(bsMosParams(cv model fingers gateSide sdRoute left right)
 let((seed master cdfgData cdfgForm baseline field actual values)
  seed=dbCreateInstByMasterName(cv "tsmcN28" model "symbol" "__cdf_seed" 0:0 "R0")
  master=dbOpenCellViewByType("tsmcN28" model "layout" "" "r")
  cdfgData=cdfGetInstCDF(seed)
  baseline=mapcar(lambda((p) list(p~>name p~>value)) cdfgData~>parameters)
  foreach(option list(list("Wfg" "1u") list("fingers" sprintf(nil "%d" fingers)) list("custom_style" "ON")
                      list("polyContacts" t) list("polyContactsEnh" gateSide)
                      list("routePolydir" gateSide) list("routeSD" sdRoute))
   field=cdfFindParamByName(cdfgData car(option))
   field~>value=cadr(option)
   bsRequire(errset(evalstring(field~>callback) t) strcat("CDF callback failed: " car(option))))
  foreach(p master~>parameters~>value
   field=cdfFindParamByName(cdfgData p~>name)
   when(field && !equal(cadr(assoc(p~>name baseline)) field~>value)
    actual=cond((field~>value==t "TRUE") (!field~>value "FALSE") (t field~>value))
    values=cons(list(p~>name "string" actual) values)))
  dbDeleteObject(seed)
  dbClose(master)
  append(values list(list("leftShape" "string" left) list("rightShape" "string" right)))))

procedure(bsRect(cv layer net x0 y0 x1 y1)
 let((shape)
  shape=dbCreateRect(cv list(layer "drawing") list(bsPoint(min(x0 x1) min(y0 y1)) bsPoint(max(x0 x1) max(y0 y1))))
  when(net shape~>net=dbFindNetByName(cv net))
  shape))
procedure(bsH(cv layer net y x0 x1 w)
 bsRect(cv layer net min(x0 x1)-w/2 y-w/2 max(x0 x1)+w/2 y+w/2))
procedure(bsV(cv layer net x y0 y1 w)
 bsRect(cv layer net x-w/2 min(y0 y1)-w/2 x+w/2 max(y0 y1)+w/2))
procedure(bsVia(cv lower x y @optional (enc1 '(0.025 0.025)) (enc2 '(0.025 0.025)))
 let((def)
  def=techFindViaDefByName(techGetTechFile(cv) sprintf(nil "M%d_M%d" lower+1 lower))
  bsRequire(dbCreateVia(cv def bsPoint(x y) "R0" list(list("layer1Enc" enc1) list("layer2Enc" enc2))) "Missing via")))
procedure(bsStack(cv net x y lo hi)
 for(k lo hi-1
  bsVia(cv k x y if(k==1 then '(0.0 0.03) else '(0.025 0.025)) '(0.025 0.025)))
 for(k lo+1 hi-1 bsRect(cv sprintf(nil "M%d" k) net x-0.070 y-0.080 x+0.070 y+0.080)))
; A row of n cuts at 0.14 um pitch, vertical unless horiz, centred on x y.
procedure(bsCuts(cv lower x y n horiz enc1)
 for(k 0 n-1
  let((d) d=(k-(n-1)/2.0)*0.14
   if(horiz bsVia(cv lower x+d y enc1) bsVia(cv lower x y+d enc1)))))
; Multi-cut transition with landings on both layers that cover every cut.
; On M1 the device column, or the ring, carries the lower enclosure.
procedure(bsPair(cv net lower x y n horiz @optional (enc1 '(0.0 0.03)))
 let((half hx hy)
  half=(n-1)*0.07+0.055
  hx=if(horiz half 0.055) hy=if(horiz 0.055 half)
  bsCuts(cv lower x y n horiz if(lower==1 enc1 '(0.025 0.025)))
  ; On a 0.07 um ring the per-cut M1 pads leave notches: cover the row.
  when(lower==1 && !equal(enc1 '(0.0 0.03))
   bsRect(cv "M1" net x-hx-0.005 y-hy-0.005 x+hx+0.005 y+hy+0.005))
  unless(lower==1 bsRect(cv sprintf(nil "M%d" lower) net x-hx y-hy x+hx y+hy))
  bsRect(cv sprintf(nil "M%d" lower+1) net x-hx y-hy x+hx y+hy)))
procedure(bsTower(cv net x y lo hi n horiz)
 for(k lo hi-1 bsPair(cv net k x y n horiz)))
procedure(bsPinRect(cv name layer x0 y0 x1 y1)
 let((net term fig)
  net=dbFindNetByName(cv name)
  term=dbCreateTerm(net name "inputOutput")
  fig=bsRect(cv layer name x0 y0 x1 y1)
  bsRequire(dbCreatePin(net fig name term) "Cannot create core terminal")
  dbCreateLabel(cv list(layer "pin") bsPoint((x0+x1)/2 (y0+y1)/2) name "centerCenter" "R0" "roman" 0.05)))
procedure(bsPin(cv name layer x y)
 bsPinRect(cv name layer x-0.060 y-0.060 x+0.060 y+0.060))
procedure(bsPins(inst name layer)
 let((boxes)
  foreach(tm inst~>master~>terminals when(equal(name tm~>name)
   foreach(p tm~>pins foreach(f p~>figs when(equal(f~>lpp list(layer "drawing"))
    boxes=cons(dbTransformBBox(f~>bBox inst~>transform) boxes))))))
  boxes))
procedure(bsBind(cv inst wiring)
 foreach(tm inst~>master~>terminals
  let((entry)
   entry=assoc(tm~>name wiring)
   bsRequire(entry sprintf(nil "%s.%s has no mapping" inst~>name tm~>name))
   bsRequire(dbCreateInstTerm(dbFindNetByName(cv cadr(entry)) inst tm) "Cannot bind native terminal")))
 bsRequire(length(inst~>instTerms)==length(wiring) sprintf(nil "Terminal count changed: %s" inst~>name)))
procedure(bsMos(cv name model gx y nf orientation left right side sd wiring)
 let((inst x gateBox gateNet gxPin cy)
  x=gx+if(equal(orientation "MY") 0.075 -0.075)
  inst=dbCreateParamInstByMasterName(cv "tsmcN28" model "layout" name bsPoint(x y) orientation 1
       bsMosParams(cv model nf side sd if(equal(orientation "MY") right left) if(equal(orientation "MY") left right)))
  bsRequire(inst && caadr(inst~>bBox)-caar(inst~>bBox)<2.3+0.33*max(nf-3 0) sprintf(nil "Invalid native MOS %s" name))
  ; A symbol names a procedure that maps the placed terminals to nets.
  when(symbolp(wiring) wiring=funcall(wiring inst))
  bsBind(cv inst wiring)
  gateBox=car(bsPins(inst "G" "M2"))
  bsRequire(gateBox && abs((cadar(gateBox)+cadadr(gateBox))/2-y-if(side=="Top" 1.115 -0.115))<0.002
    sprintf(nil "%s native gate strap has moved" name))
  gateNet=cadr(assoc("G" wiring))
  foreach(b bsPins(inst "G" "M1")
   gxPin=(caar(b)+caadr(b))/2 cy=(cadar(b)+cadadr(b))/2
   bsRect(cv "M1" gateNet gxPin-0.085 cy-0.055 gxPin+0.085 cy+0.055))
  printf("BS_MOS %s model=%s fingers=%d body=%s gate=%L\n" name model nf cadr(assoc("B" wiring)) gateBox)
  inst))
; Main group: sources are VIN; the rightmost drain column is Msin's BBOT side
; and every other drain is VOUT.
procedure(bsMainWiring(inst)
 let((drains right fig box)
  foreach(tm inst~>master~>terminals
   when(equal(substring(tm~>name 1 1) "D")
    fig=car(car(tm~>pins)~>figs)
    bsRequire(fig sprintf(nil "No pin figure on %s" tm~>name))
    box=dbTransformBBox(fig~>bBox inst~>transform)
    drains=cons(list(tm~>name (caar(box)+caadr(box))/2) drains)))
  bsRequire(length(drains)==bsMainFingers/2+1 "Unexpected main-group drain terminals")
  ; sort is destructive: keep its result.
  drains=sort(drains lambda((a b) cadr(a)>cadr(b)))
  right=car(car(drains))
  append(list(list("S" "VIN") list("G" "G") list("B" "VSS"))
   mapcar(lambda((d) list(car(d) if(equal(car(d) right) "BBOT" "VOUT"))) drains))))
; Contact a shared S/D seam on the same nine rows as the 1 um PCell end.
procedure(bsSeam(cv net x y)
 foreach(dy '(0.05 0.165 0.28 0.395 0.51 0.62 0.73 0.84 0.95)
  bsRect(cv "CO" nil x-0.02 y+dy-0.02 x+0.02 y+dy+0.02))
 bsRect(cv "M1" net x-0.025 y x+0.025 y+1.0))
procedure(bsRing(cv net implant x0 y0 x1 y1)
 let((a b c n p)
  foreach(seg list(list(x0 y0 x1 y0) list(x1 y0 x1 y1) list(x0 y1 x1 y1) list(x0 y0 x0 y1))
   foreach(l list(list("OD" 0.050) list(implant 0.115) list("M1" 0.035))
    let((half)
     half=cadr(l)
     bsRect(cv car(l) if(car(l)=="M1" net nil) car(seg)-half cadr(seg)-half caddr(seg)+half nth(3 seg)+half))))
  foreach(s list(list(x0 x1 y0 t) list(x0 x1 y1 t) list(y0+0.14 y1-0.14 x0 nil) list(y0+0.14 y1-0.14 x1 nil))
   a=car(s) b=cadr(s) c=caddr(s) n=ceiling((b-a)/0.17)
   for(k 0 n
    p=if(nth(3 s) bsPoint(a+k*(b-a)/n c) bsPoint(c a+k*(b-a)/n))
    bsRect(cv "CO" nil car(p)-0.02 cadr(p)-0.02 car(p)+0.02 cadr(p)+0.02)))))

; Left notched-row spine x for BTOP and BBOT. A wider main switch needs a
; 12-site notch; 28 columns then keep the 200 units (28*8-24).
procedure(bsWing() if(bsMainFingers>2 '(-6.99 -7.41) '(-3.47 -3.89)))
; Each unit is the electrical 2.5 um, eight-finger, M1..M3 MOM. The
; lower two rows leave eight central sites each for the switches (27*8-16).
; Rows face like terminals across the inter-row gap. Their M3 landings are
; collinear. Metal is added only in the gaps. M4 spines feed the array.
procedure(bsArray(cv)
 let((inst x y origin orient plus minus pY mY prevLeft count cols notch0 wing)
  count=0 wing=bsWing()
  cols=if(bsMainFingers>2 27 26) notch0=if(bsMainFingers>2 6 10)
  for(r 0 7
   y=0.0+3.14*r
   orient=if(evenp(r) "R0" "MX")
   origin=if(evenp(r) y y+2.92)
   pY=if(evenp(r) y+2.865 y+0.055) mY=if(evenp(r) y+0.055 y+2.865)
   prevLeft=nil
   for(c 0 cols
    if(r<2 && c>=notch0 && c<=17 then prevLeft=nil
    else
     x=(c-13)*0.88-0.38
     inst=dbCreateParamInstByMasterName(cv "tsmcN28" "cfmom_2t" "layout" sprintf(nil "Cboot_%02d_%02d" r c)
       bsPoint(x origin) orient 1 list(list("Nfinger" "string" "8") list("Lfinger" "string" "2.5u")
       list("Wfinger" "string" "50n") list("Sfinger" "string" "50n") list("StartMn" "string" "1") list("StopMn" "string" "3")))
     bsBind(cv inst '(("PLUS" "BTOP") ("MINUS" "BBOT")))
     plus=car(bsPins(inst "PLUS" "M3")) minus=car(bsPins(inst "MINUS" "M3"))
     bsRequire(plus && minus && abs((cadar(plus)+cadadr(plus))/2-pY)<0.002
        && abs((cadar(minus)+cadadr(minus))/2-mY)<0.002 "MOM pin geometry changed")
     when(prevLeft
      bsRect(cv "M3" "BTOP" prevLeft-0.01 cadar(plus) caar(plus)+0.01 cadadr(plus))
      bsRect(cv "M3" "BBOT" prevLeft-0.01 cadar(minus) caar(minus)+0.01 cadadr(minus)))
     prevLeft=caadr(plus)
     count=count+1))
   foreach(item list(list("BTOP" pY -1.01 car(wing) 4.39) list("BBOT" mY -0.515 cadr(wing) 4.81))
    foreach(bx if(r<2 list(nth(3 item) nth(4 item)) if(r==2 cddr(item) list(nth(2 item))))
     foreach(dx '(-0.070 0.070) bsVia(cv 3 bx+dx cadr(item) '(0.03 0.005) '(0.005 0.03))))))
  ; Edge spines on the two notched rows tie into the first continuous row.
  foreach(x list(car(wing) 4.39) bsV(cv "M4" "BTOP" x 2.865 9.145 0.20))
  foreach(x list(cadr(wing) 4.81) bsV(cv "M4" "BBOT" x 0.055 6.335 0.20))
  bsRect(cv "M4" "BTOP" -1.16 4.00 -0.86 22.135)
  bsRect(cv "M4" "BBOT" -0.665 1.54 -0.365 24.945)
  bsH(cv "M4" "BTOP" 4.10 car(wing) -1.01 0.20)
  ; At the NMOS pickup height all BTOP rails end above this M4 crossbar.
  bsH(cv "M4" "BBOT" 1.64 cadr(wing) 4.81 0.20)
  ; The right BTOP feed crosses BBOT on a short M3 section above the wells.
  bsH(cv "M3" "BTOP" 5.31 -1.07 0.10 0.13)
  foreach(x '(-1.01 0.04)
   foreach(dx '(-0.070 0.070) bsVia(cv 3 x+dx 5.31 '(0.03 0.005) '(0.005 0.03))))
  bsH(cv "M4" "BTOP" 5.31 -0.005 4.39 0.20)
  bsRequire(count==200 "Invalid Cboot unit count")))

procedure(bsSwitches(cv)
 let((ny py main vin s vinX voutX)
  ny=0.80 py=3.80
  ; Extra main fingers extend the group, its guard ring and the rails leftwards.
  s=0.33*(bsMainFingers-2)
  vinX=nil voutX=nil
  for(k 0 bsMainFingers/2 vinX=cons(-1.505-0.66*k vinX))
  for(k 0 bsMainFingers/2-1 voutX=cons(-1.835-0.66*k voutX))
  ; Native S-only strap joins the VIN diffusions. Drain terminals stay
  ; distinct. From left: VIN | VOUT | ... | VIN | BBOT.
  main=bsMos(cv if(bsMainFingers==2 "Mmain_Mmain_U1_Msin" "Mmain_group_Msin") "nch_18_mac" -2.00-s ny
        bsMainFingers+1 "R0" "normal" "same" "Top" "Source" 'bsMainWiring)
  vin=setof(b bsPins(main "S" "M1") caadr(b)-caar(b)>0.65)
  bsRequire(length(vin)==1 && abs(caar(car(vin))+2.19+s)<0.002 "Native VIN strap missing")
  foreach(d '(("M4A" -1.01 "R0" "same" "same" "Top" "CTRL" "G" "BBOT")
              ("M4C" -0.68 "MY" "same" "same" "Bottom" "CTRL" "CLKS" "BBOT")
              ("M8" -0.35 "MY" "same" "normal" "Top" "BBOT" "CLKSB" "VSS")
              ("Maux" 1.80 "MY" "normal" "same" "Bottom" "G" "VDD" "GRESET")
              ("MRSTG" 2.13 "MY" "same" "same" "Top" "GRESET" "CLKSB" "VSS")
              ("MNCLK" 2.46 "R0" "same" "normal" "Bottom" "CLKSB" "CLKS" "VSS"))
   bsMos(cv car(d) "nch_18_mac" cadr(d) ny 1 nth(2 d) nth(3 d) nth(4 d) nth(5 d) "None"
    list(list("D" nth(6 d)) list("G" nth(7 d)) list("S" nth(8 d)) list("B" "VSS"))))
  foreach(d '(("M2" -1.175 "R0" "normal" "same" "Bottom" "BTOP" "G" "VDD" "BTOP")
              ("M4" -0.845 "R0" "same" "normal" "Top" "G" "CTRL" "BTOP" "BTOP")
              ("M4B" 2.13 "MY" "normal" "same" "Bottom" "CTRL" "CLKS" "VDD" "VDD")
              ("MPCLK" 2.46 "R0" "same" "normal" "Bottom" "CLKSB" "CLKS" "VDD" "VDD"))
   bsMos(cv car(d) "pch_18_mac" cadr(d) py 1 nth(2 d) nth(3 d) nth(4 d) nth(5 d) "None"
    list(list("D" nth(6 d)) list("G" nth(7 d)) list("S" nth(8 d)) list("B" nth(9 d)))))
  ; GRESET connects only Maux and MRSTG, by diffusion alone.
  foreach(s '(("BBOT" -1.175) ("CTRL" -0.845) ("BBOT" -0.515) ("VSS" 2.295))
   bsSeam(cv car(s) cadr(s) ny))
  foreach(s '(("BTOP" -1.01) ("VDD" 2.295)) bsSeam(cv car(s) cadr(s) py))
  ; One thick-oxide region for the whole bank. Extraction takes 1.8 V NMOS
  ; well proximity from the OD_18 NOT NW boundary, so per-device OD_18
  ; boxes 0.2 um from each gate raise the threshold. Here the nearest edges
  ; are 0.7 um or more from every NMOS gate; the PMOS see their N-well edges.
  ; OD2.EX.2: the region encloses both N-wells (3.13..5.47) by 0.25 um.
  bsRect(cv "OD_18" nil -3.10-s 0.10 3.72 5.72)
  ; Substrate guard; boosted and static PMOS each have a contacted well.
  bsRing(cv "VSS" "PP" -2.86-s 0.36 3.32 2.37)
  bsRect(cv "NP" nil -2.745-s 0.475 3.205 2.255)
  foreach(w '(("BTOP" -1.98 -0.04) ("VDD" 1.30 3.31))
   bsRect(cv "NW" nil cadr(w)-0.16 3.13 caddr(w)+0.16 5.47)
   bsRect(cv "PP" nil cadr(w)+0.115 3.405 caddr(w)-0.115 5.195)
   bsRing(cv car(w) "NP" cadr(w) 3.29 caddr(w) 5.31))
  bsV(cv "M1" "BTOP" -1.01 py+0.97 5.31 0.05)
  bsV(cv "M1" "VDD" 2.295 3.29 py+0.03 0.05)
  foreach(x '(-0.185 2.295) bsV(cv "M1" "VSS" x 0.36 ny+0.03 0.05))
  ; Held output: three cuts on every drain column and a 0.20 um M2 exit at
  ; the lower edge, facing the CDAC. Further drains join on a 0.20 um M2 bar
  ; below the VIN landings.
  foreach(x voutX bsPair(cv "VOUT" 1 x 1.02 3 nil))
  bsV(cv "M2" "VOUT" -1.835 0.07 1.02 0.20)
  foreach(x setof(x voutX x<-1.84) bsV(cv "M2" "VOUT" x 0.62 1.02 0.20))
  when(bsMainFingers>2 bsH(cv "M2" "VOUT" 0.62 car(voutX) -1.835 0.20))
  bsPinRect(cv "VOUT" "M2" -1.935 -0.03 -1.735 0.17)
  ; Analogue input: every source column, three cuts each, rises on paired cuts
  ; to a 0.30 um M5 trunk that leaves the north edge, away from VOUT.
  foreach(x vinX
   bsPair(cv "VIN" 1 x 1.16 3 nil)
   bsTower(cv "VIN" x 1.23 2 5 2 nil))
  bsH(cv "M5" "VIN" 1.33 car(vinX) -1.505 0.14)
  bsRect(cv "M5" "VIN" -2.315 1.26 -2.015 24.945)
  bsPinRect(cv "VIN" "M5" -2.315 24.705 -2.015 24.945)
  ; BBOT feed from the two diffusion seams.
  ; Collect the BTOP switching current at the shared PMOS diffusion.
  ; The well contact remains a branch of the same net.
  foreach(x '(-1.175 -0.515)
   foreach(dy '(-0.07 0.07)
    bsVia(cv 1 x 1.64+dy '(0.0 0.03) '(0.025 0.025))))
  bsH(cv "M2" "BBOT" 1.64 -1.175 -0.515 0.09)
  bsRect(cv "M2" "BBOT" -1.225 1.515 -1.125 1.765)
  foreach(feed '(("BBOT" -0.515 1.64) ("BTOP" -1.01 4.10))
   let((net x y)
    net=car(feed) x=cadr(feed) y=caddr(feed)
    bsRect(cv "M2" net x-0.060 y-0.145 x+0.060 y+0.145)
    bsRect(cv "M3" net x-0.055 y-0.15 x+0.055 y+0.15)
    foreach(dy '(-0.07 0.07)
     when(equal(net "BTOP") bsVia(cv 1 x y+dy '(0.0 0.03) '(0.025 0.025)))
     bsVia(cv 2 x y+dy '(0.025 0.025) '(0.025 0.025))
     bsVia(cv 3 x y+dy '(0.005 0.03) '(0.03 0.005)))))
  ; The boosted gate and CTRL rise beside their actual device terminals.
  ; Cut pairs run along each M3 riser or M2 bar.
  bsH(cv "M2" "G" 1.915 -1.34 -0.68 0.11)
  bsPair(cv "G" 2 -0.68 1.985 2 nil)
  bsV(cv "M3" "G" -0.68 1.18 4.08 0.08)
  bsH(cv "M2" "G" 1.18 -0.68 1.635 0.10)
  bsPair(cv "G" 2 -0.61 1.18 2 t) bsPair(cv "G" 1 1.635 1.25 2 nil)
  ; Upper G riser end: one M2/M3 landing, three VIA2 and two VIA1 cuts.
  bsH(cv "M2" "G" 3.685 -1.175 -0.68 0.11)
  foreach(layer '("M2" "M3") bsRect(cv layer "G" -0.735 3.63 -0.625 4.135))
  bsCuts(cv 2 -0.68 3.825 3 nil '(0.025 0.025))
  bsCuts(cv 1 -0.68 4.01 2 nil '(0.0 0.03))
  ; CTRL's lower pickup sits between G and the BBOT bar: one cut per layer.
  bsStack(cv "CTRL" -0.845 1.38 1 3)
  bsV(cv "M3" "CTRL" -0.845 1.38 4.915 0.08)
  bsRect(cv "M2" "CTRL" -0.935 4.86 -0.755 4.97) bsPair(cv "CTRL" 2 -0.775 4.915 2 t)
  bsH(cv "M2" "CTRL" 4.32 -0.845 1.965 0.10)
  bsPair(cv "CTRL" 2 -0.775 4.32 2 t) bsPair(cv "CTRL" 1 1.965 4.25 2 nil)
  ; Power and clock are on the outside of the switch chain.
  bsH(cv "M2" "VDD" 4.55 -1.34 1.30 0.10)
  bsPair(cv "VDD" 1 -1.34 4.48 2 nil) bsPair(cv "VDD" 1 1.30 4.62 2 nil '(0.025 0.025))
  bsV(cv "M3" "VDD" 1.80 0.07 3.29 0.12)
  bsRect(cv "M2" "VDD" 1.71 0.63 1.89 0.74)
  bsPair(cv "VDD" 1 1.80 3.29 2 t '(0.025 0.025)) bsPair(cv "VDD" 2 1.80 3.29 2 t)
  bsPair(cv "VDD" 2 1.80 0.685 2 t)
  ; Supply rails on M5 span the switch bank for the top-level grid.
  bsPinRect(cv "VSS" "M5" -2.86-s 0.24 3.32 0.48)
  bsPinRect(cv "VDD" "M5" -2.86-s 0.62 3.32 0.82)
  bsTower(cv "VDD" 1.80 0.72 3 5 2 nil)
  foreach(x list(-2.55-s 3.08)
   bsPair(cv "VSS" 1 x 0.36 2 t '(0.025 0.025))
   bsTower(cv "VSS" x 0.36 2 5 2 t))
  bsH(cv "M2" "CLKS" 0.49 -0.68 2.46 0.11)
  bsV(cv "M2" "CLKS" -0.68 0.49 0.685 0.11)
  bsV(cv "M2" "CLKS" 2.46 0.07 0.685 0.11) bsPin(cv "CLKS" "M2" 2.46 0.07)
  bsPair(cv "CLKS" 2 2.46 0.755 2 nil) bsV(cv "M3" "CLKS" 2.46 0.685 3.685 0.08)
  bsPair(cv "CLKS" 2 2.46 3.615 2 nil) bsH(cv "M2" "CLKS" 3.685 2.13 2.46 0.11)
  bsH(cv "M2" "CLKSB" 1.915 -0.35 2.625 0.11)
  bsPair(cv "CLKSB" 2 2.625 1.985 2 nil) bsTower(cv "CLKSB" 2.625 1.47 1 3 2 nil)
  bsV(cv "M3" "CLKSB" 2.625 1.54 4.08 0.08) bsTower(cv "CLKSB" 2.625 4.15 1 3 2 nil)))

procedure(bsBuild()
 let((lib cv owner cell)
  cell="sar_bootstrap_flat_8b_p_core"
  lib=ddGetObj(bsLib)
  bsRequire(lib && techGetTechFile(lib)~>libName=="tsmcN28" "Missing T28 technology")
  cv=dbOpenCellViewByType(bsLib cell bsView "maskLayout" "a")
  bsRequire(cv "Cannot open Bootstrap core")
  owner=dbFindProp(cv "generatorOwner")
  bsRequire((!cv~>instances && !cv~>shapes && !cv~>nets && !cv~>vias) ||
     (owner && owner~>value=="Layout/design/bootstrap.il") "Existing view has a different owner")
  foreach(obj cv~>instances dbDeleteObject(obj))
  foreach(obj cv~>vias dbDeleteObject(obj))
  foreach(obj cv~>shapes dbDeleteObject(obj))
  foreach(obj cv~>nets dbDeleteObject(obj))
  dbReplaceProp(cv "generatorOwner" "string" "Layout/design/bootstrap.il")
  foreach(net '("CLKS" "VIN" "VOUT" "VDD" "VSS" "G" "BBOT" "BTOP" "CTRL" "GRESET" "CLKSB") dbCreateNet(cv net))
  bsArray(cv) bsSwitches(cv)
  bsRequire(dbSave(cv) "Cannot save")
  dbClose(cv)
  cv=dbOpenCellViewByType(bsLib cell bsView "" "r")
  bsRequire(cv && length(cv~>instances)==211 && length(cv~>terminals)==5 "Saved placement or ports differ")
  bsRequire(forall(i cv~>instances length(i~>instTerms)==length(i~>master~>terminals)) "Unbound device terminal")
  foreach(port cv~>terminals
   let((fig) fig=car(car(port~>pins)~>figs) printf("BS_PORT %s %s %L\n" port~>name car(fig~>lpp) fig~>bBox)))
  printf("PILOT_OA_OK %s instances=%d ports=%d bbox=%L\n" cell length(cv~>instances) length(cv~>terminals) cv~>bBox)
  dbClose(cv) printf("BS_DONE\n") t))
if(errset(bsBuild() t) then exit(0) else exit(1))

