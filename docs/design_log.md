# Design Log

## 2026-08-30

- Adopted a 10-bit, 10 MS/s, 0.9 V fully differential default specification.
- Selected a 5+5 split CDAC, StrongARM comparator, and synchronous SAR baseline.
- Assigned text sources and verification automation to the local Git repository.
- Assigned all OA data to the remote `SAR_ADC_T28` Virtuoso library.
- Kept capacitor-cell selection and non-TT model section names unresolved until verified from the PDK.
- Created the empty remote `SAR_ADC_T28` OA library at `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28` and verified its `tsmcN28` technology binding.
- Completed the stage-1 input-referred error budget. The initial allocations
  project 56.784 dB SNDR and 9.140 bit ENOB at -1 dBFS, retaining 0.844 dB
  margin over the 9-bit ENOB target.
- Established the stage-2 bit-accurate golden model using the ideal binary
  equivalent of the 5+5 split CDAC. Bridge ratio error, parasitics, switching,
  and settling remain explicit later-stage CDAC work.
