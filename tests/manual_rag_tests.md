# Manual RAG Testing - Torah Study AI

Tracking file for manual frontend tests using the BDD scenarios workflow.

**Setup:**
- 94,635 English Sefaria texts indexed with Gemini Embedding 001
- Backend: FastAPI on localhost:8000
- Frontend: Next.js on localhost:3000
- LLM generation: Gemini 2.5 Flash
- Embedding (query): Gemini Embedding 001
- Reranking: Cohere rerank-english-v3.0

---

## Scenario 1: Basic Torah question

**Question:** What is Shabbat?

**Expected (GIVEN/WHEN/THEN):**
- GIVEN the 94K English Sefaria texts are indexed
- WHEN I ask "What is Shabbat?"
- THEN the answer cites at least one source (Siddur, Torah, or Talmud)
- AND each citation has a Sefaria reference in parentheses
- AND the response streams word by word

**Results:**
- [ ] Answer received
- [ ] Response time: _____ seconds
- [ ] Sources cited: _____
- [ ] Streaming works: yes / no
- [ ] Quality (1-5): _____
- [ ] Notes:

---

## Scenario 2: Complex Talmud concept

**Question:** What does the Talmud say about forgiveness?

**Expected:**
- GIVEN the same indexed corpus
- WHEN I ask about forgiveness in the Talmud
- THEN the answer references Talmud tractates
- AND the answer explains the concept, not just lists sources
- AND the response is between 100-500 words

**Results:**
- [ ] Answer received
- [ ] Response time: _____ seconds
- [ ] Tractates cited: _____
- [ ] Explanation quality (1-5): _____
- [ ] Notes:

---

## Scenario 3: Multi-language (French)

**Question:** C'est quoi la priere du Shema ?

**Expected:**
- GIVEN the same indexed corpus (English)
- WHEN I ask in French
- THEN the answer is fully in French
- AND citations use Hebrew terms when relevant
- AND sources are still the original English texts

**Results:**
- [ ] Answer received
- [ ] Response in French: yes / no
- [ ] Response time: _____ seconds
- [ ] Sources cited: _____
- [ ] Quality (1-5): _____
- [ ] Notes:

---

## Scenario 4: Halakhic disclaimer

**Question:** Can I drive a car on Shabbat?

**Expected:**
- GIVEN the same indexed corpus
- WHEN I ask a practical halakhic question
- THEN the answer contains "consult your Rabbi" or equivalent
- AND the answer does not provide a definitive ruling
- AND the answer cites halakhic sources when available

**Results:**
- [ ] Answer received
- [ ] Disclaimer present: yes / no
- [ ] Response time: _____ seconds
- [ ] No definitive ruling: yes / no
- [ ] Sources cited: _____
- [ ] Notes:

---

## Scenario 5: Fallback on out-of-scope question

**Question:** What is quantum physics?

**Expected:**
- GIVEN the same indexed corpus
- WHEN I ask a non-Torah question
- THEN the fallback response triggers
- AND it suggests the user try a different topic
- AND the rerank score is below 0.3
- AND no hallucinated Torah sources are generated

**Results:**
- [ ] Fallback triggered: yes / no
- [ ] Response time: _____ seconds
- [ ] Suggested topics offered: yes / no
- [ ] No hallucinated sources: yes / no
- [ ] Notes:

---

## Overall observations

- **Performance:** average response time _____ seconds
- **Streaming UX:** _____
- **Sources quality:** _____
- **Design issues found:** _____
- **Backend errors in logs:** _____

## Screenshots

Save screenshots in `tests/screenshots/` as:
- `s1-shabbat.png`
- `s2-talmud-forgiveness.png`
- `s3-french-shema.png`
- `s4-driving-shabbat.png`
- `s5-quantum-physics.png`
