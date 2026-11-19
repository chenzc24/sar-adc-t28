set tech /home/process/tsmc28n/Packages/CLN28HPC+/tf_tluplus_outmap_lef/tn28clpr002e1_1_5a/N28_PRTF_12T/PR_tech/Cadence/LefHeader/HVH/tsmcn28_9lm6X1Z1URDL.tlef
set std /home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/TSMCHOME/digital/Back_End/lef/tcbn28hpcplusbwp12t30p140_170a/lef/tcbn28hpcplusbwp12t30p140.lef
set init_lef_file [list $tech $std fixed.lef]
set init_verilog route.v
set init_top_cell sar_route_overlay
set init_design_settop 1
set init_pwr_net {}
set init_gnd_net {}
setMultiCpuUsage -localCpu 4
init_design
if {[file exists outline.tcl]} {
  source outline.tcl
} else {
  set abstract [open fixed.lef r]
  set found [regexp -line {^[[:blank:]]*SIZE ([0-9.]+) BY ([0-9.]+) ;} [read $abstract] match core_width core_height]
  close $abstract
  if {!$found} {error "ROUTEBASE has no declared footprint"}
}
floorPlan -site core12T -s $core_width $core_height 0 0 0 0
placeInstance u_base 0 0 R0 -fixed
setNanoRouteMode -routeWithTimingDriven false
setNanoRouteMode -routeWithSiDriven false
setNanoRouteMode -routeBottomRoutingLayer 1
setNanoRouteMode -routeTopRoutingLayer 6
setNanoRouteMode -drouteEndIteration 40
routeDesign
verifyConnectivity -type all -report route.conn
verify_drc -report route.drc
defOut -routing routed.def
set map [open route.map w]
for {set i 1} {$i <= 6} {incr i} {
  foreach cat {NET SPNET PIN VIA} {puts $map "M$i $cat [expr {30+$i}] 0"}
  if {$i < 6} {puts $map "VIA$i VIA [expr {50+$i}] 0"}
}
close $map
streamOut overlay.gds -mapFile route.map -libName SAR_ROUTE_OVERLAY -units 1000 -mode ALL
puts "SAR_ROUTER_FINISHED"
exit

