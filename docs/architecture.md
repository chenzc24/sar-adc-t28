# Current Architecture

The design specification gives the complete definition and identifies the machine-readable source. Verify the behavioral views and transistor implementation separately. [Design specification](specification.md) · [specs/arch.json](../specs/arch.json) · [Behavioral views](../design/behav/README.md)

An 8-bit, 10 MS/s, fully differential asynchronous SAR ADC. The Bootstrap sampler drives the differential top plates. Eighteen MOM capacitors form the CDAC. The asynchronous SAR consumes the StrongARM outputs and updates the reference controls bit by bit.

The external clock period is 100 ns. It starts low for 60 ns; each period then has a 45 ns high sampling phase and a 55 ns low conversion phase. Internal decisions, writes, and reference updates follow the comparator handshake and a DEL250 settling chain with registered per-bit taps. [ADC top](../design/top/adc_top.scs) · [Modules and ports](../design/README.md)

Digital logic uses native standard cells. The Bootstrap, CDAC switches, and comparator use transistor implementations. The PDK, standard-cell library, and OA are stored separately. Record netlist and OA synchronization evidence for each view.
