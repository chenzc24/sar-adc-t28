; Native placement and integration helpers for the CDAC gate driver.
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



procedure(refOpen(cell view)
  let((cv)
    stNeed(!ddGetObj("SAR_ADC_T28_LAYOUT" cell view) "Reference driver target already exists")
    cv=dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" cell view "maskLayout" "a")
    stNeed(cv "Cannot create the reference driver view")
    cv))

procedure(refPinBox(cv name layer box direction)
  let((net tm fig)
    net=dbFindNetByName(cv name)
    tm=dbCreateTerm(net name direction)
    fig=dbCreateRect(cv list(layer "drawing") box)
    stNeed(tm && fig && dbCreatePin(net fig name tm) sprintf(nil "Cannot make terminal %s" name))
    dbCreateLabel(cv list(layer "pin")
      stPt((caar(box)+caadr(box))/2 (cadar(box)+cadadr(box))/2)
      name "centerCenter" "R0" "roman" .05)))

procedure(refPin(cv name layer x y w h direction)
  refPinBox(cv name layer list(stPt(x-w/2 y-h/2) stPt(x+w/2 y+h/2)) direction))

procedure(refChild(cv cell view name wiring)
  let((master inst tm)
    master=dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" cell view "" "r")
    stNeed(master && length(master~>terminals)==length(wiring) sprintf(nil "Interface changed on %s" cell))
    inst=dbCreateInst(cv master name 0:0 "R0")
    foreach(pair wiring
      tm=dbFindTermByName(master car(pair))
      stNeed(tm && dbCreateInstTerm(dbFindNetByName(cv cadr(pair)) inst tm)
        sprintf(nil "Cannot bind %s.%s" name car(pair))))
    dbClose(master)
    inst))

procedure(refCopyPin(cv instName name direction)
  let((inst tm figs)
    inst=dbFindAnyInstByName(cv instName)
    tm=dbFindTermByName(inst~>master name)
    figs=nil
    foreach(pin tm~>pins figs=append(figs pin~>figs))
    stNeed(length(figs)==1 sprintf(nil "Expected one landing for %s.%s" instName name))
    refPinBox(cv name car(car(figs)~>lpp) dbTransformBBox(car(figs)~>bBox inst~>transform) direction)))

procedure(refUpperVia(cv lower name x y)
  let((def via)
    def=techFindViaDefByName(techGetTechFile(cv) sprintf(nil "M%d_M%d" round(lower)+1 round(lower)))
    stNeed(def "Missing upper-metal via definition")
    via=dbCreateVia(cv def stPt(x y) "R0")
    stNeed(via "Cannot create upper-metal via")
    via~>net=dbFindNetByName(cv name)))

procedure(refSave(cv)
  dbReplaceProp(cv "generatorOwner" "string" "Layout/design/reference_driver.py")
  stNeed(dbSave(cv) "Cannot save reference driver layout")
  dbClose(cv))
