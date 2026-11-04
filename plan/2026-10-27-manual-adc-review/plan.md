# Manual SAR8 topology review

User authorizes read-only audit of SAR_ADC_T28_manual at /home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_manual, then module TB before joined verification. Preserve intended bidirectional first-up/later-down SAR algorithm and topology unless an actual error is demonstrated. Sizes/timing not optimized; L1 intentionally incomplete. External sources ideal. Target8bit10MS/s; retain prior spec as reference, verify range/LSB against actual switching scheme.

Local ownership: this plan, verification/manual_adc_review/ (audit/report/reader), output/manual_adc_review/ (live snapshots and exports), append plan/log.md. Remote OA ownership:none; library, all user unsaved windows, PDK and shared libraries read-only. No save/check/edit/netlist mutation of user OA. No simulation in initial topology review; any later simulation uses managed process and separate frozen inputs. No commit/push/adoption.

Dirty state: unrelated Obsidian,10bit,management and old SAR8 module work retained. This isolated subtree does not overlap other module ownership. Existing automation remains separate; do not attribute old performance to manual design.

Preflight: T28_IO bridge on thu-wei, UIDuser chenzc_intern25, workdir llm_IO healthy. User open L2_CDAC_8bit and L1_SAR_ADC_8bit; L1 has unsaved asterisk. Read live in-memory connectivity without saving; disk export may differ and will be labelled, not silently used as latest.

Steps: inventory exact library/path/views; supported read-only schematic reader for hierarchy/ports/parameters; inspect weighting, SAR polarity/control truth tables, reset/handshake/load interfaces and missing top-level nets; report demonstrated errors separately from unfinished work and unknown margins. Produce concise module TB matrix and next steps. Validation: actual connectivity/instance evidence, no simulation claims, scoped diff check. Preserve raw readbacks and provenance.


Review complete (2026-10-27): six cells read; compact connectivity and SHA256 provenance saved. Confirmed CDN/CLKS phase conflict using same-cell native Liberty; derived required first-step cross-mapping, MSB output recoding and >=75ns eighth-evaluate lower bound for current 5ns feedback delay. Ideal 256-centre charge arithmetic validates intended algorithm only. L1 connectivity readback empty and unsaved window preserved; screenshot returned zero bytes, visual wiring not verified. No OA mutation/save/check, export or simulation. Report: verification/manual_adc_review/README.md. Next work is independent netlist TBs with explicit Cunit and corrected interfaces, not automatic topology redesign. No commit/push.
