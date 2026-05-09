# Citation Map: External Analysis → MANUSCRIPT_v03.md
# Source document: Стратегия радикальной фальсификации (Deep Research report, April 2026)
# Prepared: 2026-05-09
# Purpose: Ready-to-insert text blocks with citations, mapped to exact manuscript sections
#
# Rights: Third-party links and suggested wording are drafting aids only. Confirm
# copyright, licensing, and publisher terms before reusing or redistributing excerpts.

---

## SECTION 1: Introduction — 3 insertions

---

### 1.1 After paragraph "Each tool answers a narrow question..."
**Insert before:** "Furthermore, existing detectors rarely provide calibrated uncertainty."

**Text to insert:**
```
A parallel problem emerges when LLMs are deployed as data reviewers: 
studies on generative models in scientific contexts warn that such systems 
may function as "digital sophists," generating equally convincing arguments 
for genuine and fabricated claims without signaling epistemic uncertainty 
(Shum & Khashabi, 2026). Epistemic markers that explicitly separate 
empirical facts from inferences and hypotheses are therefore not a 
stylistic choice but a structural safeguard (Nilsson et al., 2025).
```

**Citations to add to References:**
```
Shum, K., & Khashabi, D. (2026). The sophist in the server: Rhetoric, 
reasoning and scientific judgment in the age of LLMs. PMC12979577. 
https://pmc.ncbi.nlm.nih.gov/articles/PMC12979577/

Nilsson, J., et al. (2025). Epistemic markers in the scientific discourse. 
Philosophy of Science. Cambridge Core. 
https://www.cambridge.org/core/journals/philosophy-of-science/article/
epistemic-markers-in-the-scientific-discourse/E256184D590F833A2255790CA9DAFD1A
```

---

### 1.2 In "We propose a shift..." paragraph
**Insert at end of that paragraph, before contributions list:**

**Text to insert:**
```
This shift reflects a Popperian principle: a detection system should not ask 
"can we confirm this anomaly?" but "can this anomaly survive active attempts 
at refutation?" (Popper, 1934). No number of confirmatory observations can 
conclusively verify a fabrication-detection rule; a single counterexample, 
by contrast, immediately invalidates it.
```

**Citations to add:**
```
Popper, K. R. (1934/1959). The Logic of Scientific Discovery. 
Hutchinson & Co., London.
[Wikipedia entry for background: https://en.wikipedia.org/wiki/Falsifiability]
```

**Note:** Popper 1934 is a primary source — cite the book, not Wikipedia. 
Wikipedia can go in footnote or supplementary.

---

### 1.3 Add 5th contribution to the contributions list
**Current list ends at item 4. Add:**

```
5. **Methodological transfer** from intelligence analysis (ACH framework) 
   and adversarial security testing (Red Teaming) to biological data screening, 
   demonstrating domain-agnostic applicability of falsification-first 
   verification pipelines.
```

---

## SECTION 2.4: Adversarial Debate Protocol — 1 insertion

---

### 2.4.1 After the three-agent description (Prosecutor / Defense / Judge)
**Insert before Section 2.5 Datasets:**

**Text to insert:**
```
The closest prior work in NLP is FIRE (Fact-checking using Interactive 
Reasoning and Extraction), which similarly decomposes verification into 
atomic claims and iterates between evidence retrieval and verdict synthesis 
(Guo et al., 2025). Skeptic Engine differs in three respects: (1) it 
operates on structured numerical data rather than free text; (2) it 
explicitly separates Prosecution and Defense as parallel agents with 
independent evidence weights; and (3) it applies isotonic calibration to 
the final confidence score rather than using raw classifier output.

The adversarial structure is also methodologically related to Klein's 
pre-mortem technique (Klein, 2007), in which teams assume a project has 
already failed and reason backwards to identify causes. Both approaches use 
prospective hindsight to overcome confirmation bias in evaluation.
```

**Citations to add:**
```
Guo, Z., et al. (2025). FIRE: Fact-checking with iterative retrieval 
and verification. Findings of NAACL 2025. ACL Anthology. 
https://aclanthology.org/2025.findings-naacl.158.pdf

Klein, G. (2007). Performing a project premortem. 
Harvard Business Review, 85(9), 18-19.
http://homepages.se.edu/cvonbergen/files/2013/01/Performing-a-Project-Premortem.pdf
```

---

## SECTION 4.1: From "Flagging" to "Explaining" — 1 insertion

---

### 4.1.1 After "they see why (e.g., 'p-value clustering is suspicious...')"
**Insert at end of section 4.1:**

**Text to insert:**
```
The structured verdict format aligns with epistemological principles of 
calibrated uncertainty disclosure (Nilsson et al., 2025). By labeling 
each inference as <fact>, <inference>, or <hypothesis>, the Debate 
Protocol prevents the collapse of speculative signals into empirical claims 
— the same conflation that enables scientific misconduct to survive 
peer review in the first place.
```

*Note: Nilsson et al. already added in Section 1.1 — no new reference needed.*

---

## SECTION 4.2: Comparison with Existing Tools — 1 insertion

---

### 4.2.1 After paragraph on complementary error profiles
**Insert before Section 4.3:**

**Text to insert:**
```
Beyond bioinformatics, analogous adversarial review frameworks have been 
validated in clinical AI (PIEE cycle for red-teaming diagnostic LLMs; 
Park et al., 2025) and legal risk assessment (legal red-teaming of 
generative AI models; DLA Piper, 2024). These applications confirm that 
the core mechanism — an independent agent actively searching for 
counterexamples — generalizes across domains where undetected errors 
carry high-stakes consequences.
```

**Citations to add:**
```
Park, Y. J., et al. (2025). The PIEE cycle: A structured framework for 
red teaming large language models in clinical decision-making. 
PMC12292938. https://pmc.ncbi.nlm.nih.gov/articles/PMC12292938/

DLA Piper. (2024). Legal red teaming: A systematic approach to assessing 
legal risk of generative AI models. 
https://www.dlapiper.com/insights/publications/2024/05/legal-red-teaming-a-systematic-approach-to-assessing-legal-risk-of-generative-ai-models
```

---

## SECTION 4.4: Practical Implications — 1 insertion

---

### 4.4.1 After "scores above 0.7 trigger detailed investigation"
**Insert before Section 4.5:**

**Text to insert:**
```
These thresholds function as operationalized kill criteria: pre-defined 
conditions that automatically trigger escalation rather than leaving 
judgment to individual reviewers (Dutta, 2024). The Stage-Gate framing 
(Cooper, 2001) maps naturally to editorial workflow: Stage 1 = automated 
screening (Skeptic Engine), Stage 2 = human expert review of flagged 
items, Stage 3 = editorial decision with audit trail.
```

**Citations to add:**
```
Dutta, R. (2024). Kill criteria: The uncomfortable pill to swallow for 
product managers. Medium. 
https://medium.com/@rajeshdutta/kill-criteria-the-uncomfortable-pill-to-swallow-for-product-managers-5f130b3a28a5

Cooper, R. G. (2001). Winning at New Products: Accelerating the Process 
from Idea to Launch (3rd ed.). Perseus Books.
[Stage-Gate overview: https://www.stage-gate.com/blog/the-stage-gate-model-an-overview/]
```

*Note: Cooper 2001 is the canonical Stage-Gate reference — prefer the book over the blog.*

---

## SECTION 4.5: Future Work — 1 insertion

---

### 4.5.1 After "Instinct Memory (H37)" item
**Insert as new bullet point:**

**Text to insert:**
```
- **Autonomous Verification Agents (H39):** Current Skeptic Engine 
  operates on submitted datasets; a natural extension is real-time 
  cross-referencing of flagged datasets against external databases 
  (GEO, ProteomicsDB, ClinicalTrials.gov) via Level-3 autonomous agents 
  (MIT AI Agent Index 2025). The FIRE architecture (Guo et al., 2025) 
  provides a technical blueprint: each suspicious claim triggers an 
  automated search query, reducing the gap the external evaluation 
  identified as the primary limitation of the current framework.
```

**Citations to add:**
```
Sager, E., et al. (2025). The 2025 AI Agent Index: Documenting technical 
and safety features of deployed agentic AI systems. arXiv:2602.17753. 
https://arxiv.org/html/2602.17753v1
```

*Note: Guo et al. 2025 (FIRE) already added in Section 2.4 — no duplicate needed.*

---

## CONSOLIDATED NEW REFERENCES (add to Section 5 References)

```
[Current refs: 1-10, keep all]

11. Shum, K., & Khashabi, D. (2026). The sophist in the server: Rhetoric, 
    reasoning and scientific judgment in the age of LLMs. 
    PMC12979577. Retrieved from https://pmc.ncbi.nlm.nih.gov/articles/PMC12979577/

12. Nilsson, J., et al. (2025). Epistemic markers in the scientific discourse. 
    Philosophy of Science. Cambridge Core. DOI pending.

13. Popper, K. R. (1934/1959). The Logic of Scientific Discovery. 
    Hutchinson & Co., London.

14. Guo, Z., et al. (2025). FIRE: Fact-checking with iterative retrieval 
    and verification. Findings of NAACL 2025. 
    https://aclanthology.org/2025.findings-naacl.158.pdf

15. Klein, G. (2007). Performing a project premortem. 
    Harvard Business Review, 85(9), 18–19.

16. Park, Y. J., et al. (2025). The PIEE cycle: A structured framework for 
    red teaming large language models in clinical decision-making. 
    PMC12292938. https://pmc.ncbi.nlm.nih.gov/articles/PMC12292938/

17. DLA Piper. (2024). Legal red teaming: A systematic approach to assessing 
    legal risk of generative AI models.
    https://www.dlapiper.com/insights/publications/2024/05/legal-red-teaming

18. Cooper, R. G. (2001). Winning at New Products: Accelerating the Process 
    from Idea to Launch (3rd ed.). Perseus Books.

19. Sager, E., et al. (2025). The 2025 AI Agent Index. arXiv:2602.17753.
    https://arxiv.org/html/2602.17753v1
```

---

## VERIFICATION CHECKLIST (before inserting)

| Citation | Status | Action needed |
|----------|--------|---------------|
| Shum & Khashabi 2026 (PMC12979577) | [UNKNOWN] | Verify PMC ID resolves and authors correct |
| Nilsson et al. 2025 (Cambridge Core) | [UNKNOWN] | Verify DOI + actual author names |
| Popper 1934/1959 | [VERIFIED-MEMORY] | Standard primary source — OK |
| Guo et al. FIRE 2025 (NAACL) | [UNKNOWN] | Verify ACL Anthology URL active |
| Klein 2007 HBR pre-mortem | [UNKNOWN] | Verify volume/page/year |
| Park et al. PIEE 2025 (PMC12292938) | [UNKNOWN] | Verify PMC ID + authors |
| DLA Piper 2024 | [UNKNOWN] | Verify URL active |
| Cooper 2001 Stage-Gate | [VERIFIED-MEMORY] | Classic reference — OK |
| Sager et al. 2025 AI Agent Index | [UNKNOWN] | Verify arXiv ID |

**Rule:** All [UNKNOWN] must be spot-checked before manuscript submission.
Use WebFetch on each URL. Budget: 20 min.

---

## IMPACT SUMMARY

| Insertion | Section | Effect |
|-----------|---------|--------|
| Digital sophists (Shum) | 1 | Strengthens WHY epistemic markers matter |
| Popper 1934 | 1 | Anchors philosophical lineage |
| 5th contribution (ACH/Red Team) | 1 | Broadens stated contribution scope |
| FIRE comparison (Guo) | 2.4 | Positions vs. closest NLP analog |
| Pre-mortem lineage (Klein) | 2.4 | Intellectual heritage of debate protocol |
| Epistemic markers (Nilsson) | 4.1 | Deepens "from flagging to explaining" |
| PIEE + Legal red team | 4.2 | Demonstrates cross-domain generalization |
| Kill criteria + Stage-Gate | 4.4 | Operationalizes practical implications |
| Autonomous agents (H39) | 4.5 | Closes the gap identified by external evaluators |

**Before:** 10 references, all biological/statistical
**After:** 19 references, spanning philosophy, NLP, clinical AI, legal, product management
**Effect:** Manuscript positions Skeptic Engine not as a bioinformatics tool but as an instance of a general falsification-first verification paradigm
