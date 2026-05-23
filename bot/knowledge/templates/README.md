# Knowledge Templates — Fill Guide

Đây là 8 file template anh fill vào để AI agent hiểu Ahamove business sâu nhất.

## Thứ tự ưu tiên fill

| Order | File | ETA | Priority |
|-------|------|-----|----------|
| 1 | `01_company_dna.yaml` | 30 phút | 🔴 P0 |
| 2 | `04_kpi_dictionary.yaml` | 1h | 🔴 P0 |
| 3 | `03_okr_tree.yaml` | 30 phút | 🔴 P0 |
| 4 | `07_operating_rhythm.yaml` | 30 phút | 🟠 P1 |
| 5 | `05_customers.yaml` | 1-2h | 🟠 P1 |
| 6 | `06_vendors.yaml` | 1h | 🟡 P2 |
| 7 | `08_network.yaml` | 1h | 🟡 P2 |
| 8 | `09_risks_postmortems.yaml` | 1h | 🟡 P2 |

**Tổng**: ~6-8h. Có thể delegate cho team:
- KPI dictionary → Data Analyst
- Customers → BD Lead
- Vendors → Vendor Manager
- Network → Ops Expansion Lead

## Cách fill

1. Copy file `XX_*.yaml` → `bot/knowledge/XX_*.yaml` (bỏ folder `templates/`)
2. Replace `(điền)` placeholders + `# EXAMPLE` entries
3. Giữ structure (keys, indentation) — chỉ thay values
4. Test bằng cách chạy:
   ```bash
   cd bot && python -c "import yaml; yaml.safe_load(open('knowledge/01_company_dna.yaml'))"
   ```
5. Restart bot → AI tự pick up

## Lưu ý

- **PII/Sensitive**: Vendor contract value, customer revenue — file nằm trong git, không push lên public repo nếu nhạy cảm. Có thể tách secrets ra `.gitignore`.
- **Updates**: Anh assign owner cho mỗi file → mỗi cadence (weekly/monthly) review
- **Validation**: Sau khi fill, AI Ask thử:
  - "AI biết KFM là ai không?"
  - "OKR O1.1 owner ai?"
  - "Vendor V001 SLA gì?"
  → Nếu AI trả đúng → knowledge load thành công.

## Cấu trúc 9 layers (đầy đủ)

| Layer | File | Status |
|-------|------|--------|
| L1 — Company DNA | `01_company_dna.yaml` | 🔴 Cần fill |
| L2 — Org & Scope | `../grade_matrix.json`, `../member_scopes.json` | ✅ Đã có |
| L3 — OKR Tree | `03_okr_tree.yaml` | 🔴 Convert từ markdown |
| L4 — KPI Dictionary | `04_kpi_dictionary.yaml` | 🔴 Cần fill |
| L5a — Customers | `05_customers.yaml` | 🔴 Cần fill |
| L5b — Vendors | `06_vendors.yaml` | 🔴 Cần fill |
| L6 — Network | `08_network.yaml` | 🔴 Cần fill |
| L7 — Operating Rhythm | `07_operating_rhythm.yaml` | 🔴 Cần fill |
| L8 — Risks | `09_risks_postmortems.yaml` (risks section) | 🔴 Cần fill |
| L9 — Postmortem/Decision | `09_risks_postmortems.yaml` (postmortems + decisions) | 🟡 Fill khi có |

## Auto-loaded vs manual

Sau khi fill, các file được auto-load vào `knowledge_loader.py` ở Week 1 work:
- Static YAML → cached in-memory at bot startup
- Reload via `kn.reload()` (sẽ build trong week 1)
- Smart agent sẽ tự inject vào system prompt + tool responses
