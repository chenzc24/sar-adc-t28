; SAR/timing placement helpers. sar_timing.py emits calls using the electrical binding.
procedure(stNeed(ok message) unless(ok error("%s\n" message)))
procedure(stPt(x y) list(0.005*round(x/.005) 0.005*round(y/.005)))
procedure(stRect(cv layer net x0 y0 x1 y1)
 let((f)
  stNeed(x0<x1 && y0<y1 "Invalid rectangle")
  f=dbCreateRect(cv list(layer "drawing") list(stPt(x0 y0) stPt(x1 y1)))
  when(net!="" f~>net=dbFindNetByName(cv net)) f))

procedure(stVia(cv lower net x y horizontal)
 let((def v e1 e2)
  lower=round(lower)
  def=techFindViaDefByName(techGetTechFile(cv) sprintf(nil "M%d_M%d" lower+1 lower))
  e1=case(lower (1 '(0.0 .03)) (2 if(horizontal>0 '(.03 .01) '(.01 .03))) (3 '(.03 .005)))
  e2=case(lower (1 if(horizontal>0 '(.03 .01) '(.01 .03))) (2 '(.03 .01)) (3 '(.01 .03)))
  v=dbCreateVia(cv def stPt(x y) "R0" list(list("layer1Enc" e1) list("layer2Enc" e2)))
  stNeed(v sprintf(nil "Cannot place via on %s" net))
  v~>net=dbFindNetByName(cv net) v))

procedure(stPowerVia(cv lower net x y @optional (rows 2))
 let((def v)
  lower=round(lower)
  def=techFindViaDefByName(techGetTechFile(cv) sprintf(nil "M%d_M%d" lower+1 lower))
  v=dbCreateVia(cv def stPt(x y) "R0" list(list("cutRows" round(rows)) list("cutColumns" 2)))
  stNeed(v sprintf(nil "Cannot place power via array for %s" net))
  v~>net=dbFindNetByName(cv net) v))

; Import the geometry emitted by sar_overlay into a fresh private review view.
procedure(stApplyDetailedRoute(view expectedCount @optional (rects "route-rects.txt"))
 let((lib cell src cv fp line fields name)
  lib="SAR_PLACEMENT_WORK" cell="sar8_sar_timing_core"
  stNeed(view && view!="layout" && !ddGetObj(lib cell view) "Select an unused private view")
  src=dbOpenCellViewByType(lib cell "layout" "" "r")
  stNeed(src && length(src~>instances)==expectedCount && length(src~>terminals)==26 "Route seed differs")
  fp=infile(rects) stNeed(fp "Cannot open the verified detailed route")
  cv=dbCopyCellView(src lib cell view) stNeed(cv "Cannot copy the private seed")
  while(gets(line fp)
   fields=parseString(line) stNeed(length(fields)==6 "Invalid detailed route rectangle")
   name=cadr(fields) stNeed(dbFindNetByName(cv name) "Unknown detailed route net")
   stRect(cv car(fields) name atoi(nth(2 fields))/1000.0 atoi(nth(3 fields))/1000.0
         atoi(nth(4 fields))/1000.0 atoi(nth(5 fields))/1000.0))
  close(fp) stNeed(dbSave(cv) "Cannot save detailed route")
  dbClose(cv) dbClose(src) stAudit(lib cell view) t))

procedure(stPin(cv name layer x y w h)
 let((n tm f direction lay)
  n=dbFindNetByName(cv name)
  direction=cond((member(name '("COMP_N" "COMP_P" "SAMPLE")) "input")
                 (member(name '("VSS" "VDD")) "inputOutput") (t "output"))
  tm=dbCreateTerm(n name direction)
  lay=sprintf(nil "M%d" round(layer))
  f=stRect(cv lay name x-w/2 y-h/2 x+w/2 y+h/2)
  stNeed(dbCreatePin(n f name tm) "Cannot make port")
  dbCreateLabel(cv list(lay "pin") stPt(x y) name "centerCenter" "R0" "roman" .05)))

procedure(stDevice(cv name lib master x y orient options wiring)
 let((i term expected real)
  i=if(options then dbCreateParamInstByMasterName(cv lib master "layout" name stPt(x y) orient 1 options)
               else dbCreateInstByMasterName(cv lib master "layout" name stPt(x y) orient))
  stNeed(i sprintf(nil "Cannot place %s" name))
  stNeed(length(i~>master~>terminals)==length(wiring) sprintf(nil "Terminal count %s" name))
  foreach(w wiring
   term=dbFindTermByName(i~>master car(w))
   stNeed(term && dbCreateInstTerm(dbFindNetByName(cv cadr(w)) i term) sprintf(nil "Pin binding %s.%s" name car(w))))
  foreach(opt options
   real=dbFindProp(i~>master~>parameters car(opt))~>value
   stNeed(equal(real caddr(opt)) sprintf(nil "PCell effective parameter %s.%s = %L" name car(opt) real)))
  i))

procedure(stCheckPin(cv name term layer x y)
 let((i tm found box lay)
  i=dbFindAnyInstByName(cv name)
  tm=dbFindTermByName(i~>master term)
  lay=sprintf(nil "M%d" round(layer))
  foreach(p tm~>pins foreach(f p~>figs when(equal(f~>lpp list(lay "drawing"))
   box=dbTransformBBox(f~>bBox i~>transform)
   when(caar(box)-.0001<=x && caadr(box)+.0001>=x &&
        cadar(box)-.0001<=y && cadadr(box)+.0001>=y found=t))))
  stNeed(found sprintf(nil "Missing native %s.%s %s access at %g %g" name term lay x y))))

; The two adjacent devices use the PDK's leftShape=same on their common source.
; It omits the contacts on this seam. Use one contact column and one metal bar.
procedure(stBody(cv net sourceX tapX y w shared)
 let((n py bodyPol)
  bodyPol=if(net=="VSS" "PP" "NP")
  when(net=="VDD"
    stRect(cv "NW" "" sourceX-.42 y-.42 tapX+.20 y+w+.42))
  stRect(cv "OD" "" tapX-.05 y tapX+.05 y+w)
  stRect(cv bodyPol "" tapX-.115 y-.065 tapX+.115 y+w+.065)
  stRect(cv "M1" net tapX-.035 y tapX+.035 y+w)
  when(shared>0 stRect(cv "M1" net sourceX-.025 y sourceX+.025 y+w))
  n=ceiling((w-.10)/.135)
  for(k 0 n
   py=y+.05+(w-.10)*k/n
   stRect(cv "CO" "" tapX-.02 py-.02 tapX+.02 py+.02)
   when(shared>0 stRect(cv "CO" "" sourceX-.02 py-.02 sourceX+.02 py+.02)))))

procedure(stGate(cv net x y sign implant)
 let((yc)
  yc=y+sign*.19
  stRect(cv implant "" x-.12 min(y-.065 yc+sign*.07-.065) x+.12 max(y+.065 yc+sign*.07+.065))
  stRect(cv "PO" "" x-.015 min(y yc+sign*.07) x+.015 max(y yc+sign*.07))
  stRect(cv "CO" "" x-.02 yc-.02 x+.02 yc+.02)
  stRect(cv "M1" net x-.105 yc-.04 x+.105 yc+.04)))

procedure(stAudit(lib cell @optional (view "layout"))
 let((cv fp)
  cv=dbOpenCellViewByType(lib cell view "" "r")
  stNeed(cv "Cannot reopen SAR floorplan")
  fp=outfile("sar-readback.txt")
  fprintf(fp "VIEW %s %s %L\n" lib cell cv~>bBox)
  foreach(i cv~>instances
   fprintf(fp "INST %s %s %s %s %L %L\n" i~>name i~>libName i~>cellName i~>orient i~>xy i~>bBox)
   foreach(it i~>instTerms
    fprintf(fp "BIND %s %s %s\n" i~>name it~>term~>name it~>net~>name)
    foreach(p it~>term~>pins foreach(f p~>figs
     when(member(car(f~>lpp) '("M1" "M2" "M3" "OD" "PO")) && equal(cadr(f~>lpp) "drawing")
      fprintf(fp "LAND %s %s %s %L\n" i~>name it~>term~>name car(f~>lpp) dbTransformBBox(f~>bBox i~>transform)))))))
  foreach(tm cv~>terminals foreach(p tm~>pins foreach(f p~>figs
   fprintf(fp "PORT %s %s %L\n" tm~>name car(f~>lpp) f~>bBox))))
  fprintf(fp "COUNT %d %d %d %d\n" length(cv~>instances) length(cv~>terminals) length(cv~>vias) length(cv~>shapes))
  close(fp) dbClose(cv) t))
