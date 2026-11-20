; Build the single-edge SAR macro from the records written by sar_se_def.py.
; Every record comes from the routed DEF; this file adds no geometry of its own.
procedure(seNeed(ok message) unless(ok error("%s\n" message)))
; The T28 technology uses 1000 database units per micron; DEF records sit on the 5 nm grid.
procedure(sePt(x y) list(0.001*round(x/.001) 0.001*round(y/.001)))

; The shared layout library is already bound to tsmcN28; check it and never rebind it.
procedure(seTech(lib)
 let((l)
  l=ddGetObj(lib)
  seNeed(l "Layout library is not defined")
  seNeed(techGetTechFile(l) && techGetTechFile(l)~>libName=="tsmcN28" "Layout library must use the T28 technology")
  t))

procedure(seRect(cv layer purpose net x0 y0 x1 y1)
 let((f)
  seNeed(x0<x1 && y0<y1 "Invalid rectangle")
  f=dbCreateRect(cv list(layer purpose) list(sePt(x0 y0) sePt(x1 y1)))
  seNeed(f sprintf(nil "Cannot draw %L on %L" net layer))
  when(net f~>net=dbFindNetByName(cv net))
  f))

procedure(seBuild(lib cell view records)
 let((cv fp line f kind i term net std name lay dir tm fig w h)
  std="tcbn28hpcplusbwp12t30p140"
  seNeed(!ddGetObj(lib cell view) "Select an unused cell view")
  cv=dbOpenCellViewByType(lib cell view "maskLayout" "w")
  seNeed(cv "Cannot create the macro view")
  dbReplaceProp(cv "generatorOwner" "string" "Layout/design/sar_single_edge.py")
  fp=infile(records) seNeed(fp "Cannot open the build records")
  while(gets(line fp)
   f=parseString(line) kind=car(f)
   cond(
    (kind=="DIE"
     w=atof(cadr(f)) h=atof(caddr(f))
     seRect(cv "prBoundary" "drawing" nil 0.0 0.0 w h))
    (kind=="NET" dbMakeNet(cv cadr(f)))
    (kind=="INST"
     name=nth(1 f)
     i=dbCreateInstByMasterName(cv std nth(2 f) "layout" name sePt(atof(nth(3 f)) atof(nth(4 f))) nth(5 f))
     seNeed(i sprintf(nil "Cannot place %s" name))
     seNeed(length(i~>master~>terminals)==length(nthcdr(6 f)) sprintf(nil "Terminal count of %s" name))
     foreach(binding nthcdr(6 f)
      binding=parseString(binding "=")
      term=dbFindTermByName(i~>master car(binding))
      net=dbFindNetByName(cv cadr(binding))
      seNeed(term && net && dbCreateInstTerm(net i term) sprintf(nil "Pin binding %s.%s" name car(binding)))))
    (kind=="RECT"
     seNeed(dbFindNetByName(cv nth(2 f)) "Unknown route net")
     seRect(cv nth(1 f) "drawing" nth(2 f) atof(nth(3 f)) atof(nth(4 f)) atof(nth(5 f)) atof(nth(6 f))))
    (kind=="PIN"
     name=nth(1 f) lay=nth(2 f)
     net=dbFindNetByName(cv name)
     dir=cond((member(name '("COMP_N" "COMP_P" "SAMPLE")) "input") (member(name '("VDD" "VSS")) "inputOutput") (t "output"))
     tm=dbCreateTerm(net name dir)
     seNeed(tm sprintf(nil "Cannot make terminal %s" name))
     fig=seRect(cv lay "drawing" name atof(nth(3 f)) atof(nth(4 f)) atof(nth(5 f)) atof(nth(6 f)))
     seNeed(dbCreatePin(net fig name tm) sprintf(nil "Cannot make pin %s" name))
     dbCreateLabel(cv list(lay "pin") sePt((atof(nth(3 f))+atof(nth(5 f)))/2 (atof(nth(4 f))+atof(nth(6 f)))/2)
                   name "centerCenter" "R0" "roman" .05))
    (t error("Unknown build record %s\n" kind))))
  close(fp)
  seNeed(dbSave(cv) "Cannot save the macro view")
  dbClose(cv)
  t))

; Native readback of placement, bindings, ports and object counts.
procedure(seAudit(lib cell view out)
 let((cv fp)
  cv=dbOpenCellViewByType(lib cell view "" "r")
  seNeed(cv "Cannot reopen the macro view")
  fp=outfile(out)
  fprintf(fp "VIEW %s %s %s %L\n" lib cell view cv~>bBox)
  foreach(i cv~>instances
   fprintf(fp "INST %s %s %s %s %L %L\n" i~>name i~>libName i~>cellName i~>orient i~>xy i~>bBox)
   foreach(it i~>instTerms fprintf(fp "BIND %s %s %s\n" i~>name it~>term~>name it~>net~>name)))
  foreach(tm cv~>terminals foreach(p tm~>pins foreach(g p~>figs
   fprintf(fp "PORT %s %s %s %L\n" tm~>name tm~>direction car(g~>lpp) g~>bBox))))
  fprintf(fp "COUNT %d %d %d %d\n" length(cv~>instances) length(cv~>terminals) length(cv~>nets) length(cv~>shapes))
  close(fp) dbClose(cv) t))
