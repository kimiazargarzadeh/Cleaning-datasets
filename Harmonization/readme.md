# Parish–Registration District Harmonisation (1851 Anchor)

**Goal**  
Assess whether UKBMD Registration District parish lists can be linked to a spatial parish backbone.

**Reference geography**  
1851 England & Wales civil parish polygons (earliest complete, open parish boundary dataset).

**Temporal filter**  
Parishes retained if their existence overlaps 1851  
(`From ≤ 1851 ≤ To`, using UKBMD dates).

**Data construction**  
- Scraped UKBMD Table 1 (parish composition) for all Registration Districts  
- Built a national parish↔Registration District concordance for 1851

**Matching approach**  
Deterministic name normalisation only:
- case folding and whitespace normalisation  
- punctuation, bracket, and parenthesis removal  
- St/St./Saint harmonisation  
- `&` → `and`, `cum` → `with`  
- hyphen and slash treated as word separators  
- handling of urban prefixes (e.g. `DOVER, …`)  
- explicit one-to-many matches for subdivided urban parishes (e.g. Bermondsey) still working on it..

**Results**  
- Total parish–district rows: **15,976**  
- Matched to 1851 parish polygons: **14,264** (**≈89%**)  



**Known exceptions**  
Some unmatched cases reflect genuine historical differences, including parishes not distinct in 1851 (e.g. Temple Ewell), urban sub-districts, and complex naming variants.

**Conclusion**  
Linking UKBMD Registration District parish lists to the 1851 parish geography is feasible at national scale using light, transparent normalisation, providing a stable spatial anchor for subsequent harmonisation.
