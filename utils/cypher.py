# File: utils/cypher.py
# ── Full‐text search by name or code ───────────────────────────
STRING_SEARCH_CYPHER = """
MATCH (d:DRUG)
WHERE ANY(val IN [v IN keys(d) | toString(d[v])] 
    WHERE toLower(val) CONTAINS $q)
RETURN d.`TMTID(SUBS)_LIST` AS subs_codes
LIMIT 1
"""


DRUGSEARCH_CYPHER = """
UNWIND $qs AS q
WITH q WHERE trim(q) <> ""
CALL db.index.fulltext.queryNodes("DrugSearch", q) YIELD node, score
WITH q, node, score,
  CASE
    WHEN node.`TMTID(TPU)` = q OR toLower(node.`TPUNAME`) CONTAINS toLower(q) THEN "TPU"
    WHEN node.`TMTID(TP)`  = q OR toLower(node.`TPNAME`)  CONTAINS toLower(q) THEN "TP"
    WHEN node.`TMTID(GPU)` = q OR toLower(node.`GPUNAME`) CONTAINS toLower(q) THEN "GPU"
    WHEN node.`TMTID(GP)`  = q OR toLower(node.`GPNAME`)  CONTAINS toLower(q) THEN "GP"
    WHEN node.`TMTID(VTM)` = q OR toLower(node.`VTMNAME`) CONTAINS toLower(q) THEN "VTM"
    WHEN node.`TMTID(SUBS)_LIST` CONTAINS q
         OR toLower(node.`SUBSNAME_LIST`) CONTAINS toLower(q) THEN "SUBS"
    ELSE "UNKNOWN"
  END AS level
WITH *
WITH q,
     collect({
        level:level,
        tpu_code:node.`TMTID(TPU)`, tpu_name:node.`TPUNAME`,
        tp_code:node.`TMTID(TP)`,   tp_name:node.`TPNAME`,
        gpu_code:node.`TMTID(GPU)`, gpu_name:node.`GPUNAME`,
        gp_code:node.`TMTID(GP)`,   gp_name:node.`GPNAME`,
        vtm_code:node.`TMTID(VTM)`, vtm_name:node.`VTMNAME`,
        subs_codes:node.`TMTID(SUBS)_LIST`,
        subs_names:node.`SUBSNAME_LIST`,
        score:score
     })[0] AS best
RETURN q AS code, best
"""

# ── Fallback: resolve SUBS IDs by matching any code directly ────
RESOLVE_SUBS_FALLBACK = """
UNWIND $codes AS code
MATCH (n)
WHERE   (n:SUBS AND n.`TMTID(SUBS)` = code)
    OR  (n:TPU  AND n.`TMTID(TPU)`  = code)
    OR  (n:TP   AND n.`TMTID(TP)`   = code)
    OR  (n:GPU  AND n.`TMTID(GPU)`  = code)
    OR  (n:GP   AND n.`TMTID(GP)`   = code)
    OR  (n:VTM  AND n.`TMTID(VTM)`  = code)
OPTIONAL MATCH (n)<-[:TP_TO_TPU|GPU_TO_TPU|GP_TO_TP|GP_TO_GPU|VTM_TO_GP|SUBS_TO_VTM*0..5]-(subs:SUBS)
RETURN DISTINCT subs.`TMTID(SUBS)` AS sid
"""


# ── Search all SUBS IDs for given codes (used in allergy) ───────
SEARCHSUBS_CYPHER = """
UNWIND $codes AS code
MATCH (n)
  WHERE (n:TPU  AND n.`TMTID(TPU)`  = code)
     OR (n:TP   AND n.`TMTID(TP)`   = code)
     OR (n:GPU  AND n.`TMTID(GPU)`  = code)
     OR (n:GP   AND n.`TMTID(GP)`   = code)
     OR (n:VTM  AND n.`TMTID(VTM)`  = code)
     OR (n:SUBS AND n.`TMTID(SUBS)` = code)
OPTIONAL MATCH (n)<-[:TP_TO_TPU|GPU_TO_TPU|GP_TO_TP|GP_TO_GPU|VTM_TO_GP|SUBS_TO_VTM*0..5]-(subs:SUBS)
WITH code, collect(DISTINCT COALESCE(subs.`TMTID(SUBS)`, n.`TMTID(SUBS)`)) AS subs_ids
RETURN code AS raw_code, subs_ids
"""

# ── Fetch interaction contrasts between SUBS ID pairs ────────────
CONTRAST_CYPHER = """
UNWIND $pairs AS p
MATCH (s1:SUBS {`TMTID(SUBS)`: p[0]})-[r:CONTRAST_WITH]-
      (s2:SUBS {`TMTID(SUBS)`: p[1]})
RETURN
  s1.`TMTID(SUBS)` AS sub1_id,
  s1.SUBSNAME      AS sub1_name,
  s2.`TMTID(SUBS)` AS sub2_id,
  s2.SUBSNAME      AS sub2_name,
  COALESCE(r.SEVERITY,"")        AS severity,
  COALESCE(r.DOCUMENTATION,"")   AS documentation,
  COALESCE(r.SUMMARY,"")         AS interaction_detail_en,
  COALESCE(r.SUMMARY_TH,"")      AS interaction_detail_th,
  COALESCE(r.ONSET,"")           AS onset,
  COALESCE(r.SIGNIFICANCE,"")    AS significance,
  COALESCE(r.MANAGEMENT,"")      AS management,
  COALESCE(r.DISCUSSION,"")      AS discussion,
  COALESCE(r.REFERENCE,"")       AS reference
"""

# ── Map SUBS IDs to human‐readable names ────────────────────────
SUBS_NAME_CYPHER = """
UNWIND $subs_ids AS sid
MATCH (s:SUBS {`TMTID(SUBS)`: sid})
RETURN sid AS code, s.SUBSNAME AS name
"""

# ── Fetch external status from TPU nodes ─────────────────────────
FETCH_EXTERNAL_STATUS_CYPHER = """
MATCH (tpu:TPU)
WHERE tpu.`TMTID(TPU)` IN $tpu_codes
RETURN tpu.`TMTID(TPU)` as tpu_code, 
       COALESCE(tpu.external, "false") as external
"""
