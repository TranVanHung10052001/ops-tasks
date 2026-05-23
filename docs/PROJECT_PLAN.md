# Ops-Tasks AI — Master Plan

> **Mục tiêu**: 1 AI agent hiểu trọn vẹn business + org + ops của Truck Ops Ahamove,
> có thể trả lời decision support / RCA / status check / coaching chỉ với 1 câu hỏi.
>
> **Trạng thái**: Foundation đã có (knowledge_loader + smart_agent + 6 tools).
> Document này là cho **bước tiếp**: knowledge thực, data inputs đủ, plan rõ.

---

## TL;DR

| # | Hành động | Output | Thời gian |
|---|-----------|--------|-----------|
| 1 | Fill 8 knowledge templates trong `bot/knowledge/templates/` | AI hiểu 100% business/org/OKR/KPI | 2-3 ngày (anh fill) |
| 2 | Build data ingestion: metrics history, customers, vendors, hubs | Portal có time series + CRM-lite | Week 2 |
| 3 | Thêm 6 tools cho smart_agent: trend, search_knowledge, find_playbook... | AI suy luận sâu hơn | Week 2 |
| 4 | Memory + learning loop (lưu Q&A, feedback ✓✗) | AI tốt dần | Week 3 |
| 5 | Production polish (streaming, monitoring, knowledge admin UI) | Vận hành ổn | Week 4-5 |

**Quan trọng nhất bây giờ**: anh fill 8 templates → AI khôn ngay lập tức, không cần code thêm.

---

## Part 1: Knowledge Backbone — 9 layers AI phải biết

Một AI agent "hiểu task ngay" cần biết 9 lớp context, mỗi lớp 1 nguồn dữ liệu riêng:

| # | Layer | Cái gì | File hiện tại | Status |
|---|-------|--------|---------------|--------|
| **L1** | **Company DNA** | Service, market, unit econ, competitor | Thiếu | ❌ |
| **L2** | **Org & Scope** | Org chart, grade, scope từng người | `member_scopes.json`, `grade_matrix.json` | ✅ Đã có |
| **L3** | **OKR Tree** | O / KR / Action, owner, target | `prompts/okr_truck_ops.md` (markdown) | ⚠️ Cần JSON structured |
| **L4** | **KPI Dictionary** | Mỗi metric: formula, source, target, owner | Thiếu (chỉ có values) | ❌ |
| **L5** | **Customer/Vendor** | Top 20 key accounts, top vendors, SLA | Thiếu | ❌ |
| **L6** | **Network** | Hub/station/KCN, capacity per location | Thiếu | ❌ |
| **L7** | **Operating Rhythm** | Daily/weekly/monthly cadence, meetings | Thiếu | ❌ |
| **L8** | **Risks & Playbooks** | 18 playbook + risk catalog + postmortem | `playbooks.json` (18 ✓), risk catalog ❌ | ⚠️ 1/2 |
| **L9** | **History/Memory** | Task history, decision log, lessons learned | Tasks table có (raw), decision log ❌ | ⚠️ 1/3 |

**Diagnosis**: Layer 2, 8 đã đủ. Layer 3 có nhưng dạng markdown (khó query). **4 layers thiếu hoàn toàn**: L1, L4, L5, L6, L7.

→ **Action**: fill 8 templates ở Part 3.

---

## Part 2: Portal Data Inputs — Audit

### 2.1 Current ingestion channels (data ĐANG vào)

| Source | Tần suất | Destination | Status |
|--------|---------|-------------|--------|
| Telegram bot (chat, forward, /add) | Real-time | `tasks` table | ✅ |
| Telegram bot (registration) | Real-time | `users` table | ✅ |
| Redash SQL query | 30 min | `metrics` table | ✅ |
| Google Sheets (Apps Script fallback) | Daily 8AM | `metrics` table (bulk POST) | ✅ |
| Static JSON (knowledge/) | Khi git push | In-memory cache | ✅ |
| Manual `/api/metrics POST` | Ad-hoc | `metrics` table | ✅ |

### 2.2 Critical gaps (xếp theo ưu tiên)

| # | Gap | Tại sao quan trọng | Effort | Priority |
|---|-----|-------------------|--------|----------|
| 1 | **Metrics time series** | Chỉ có current value → AI không thấy được trend ("FR HAN giảm từ 75% → 60% trong 3 tuần") | Low (thêm cột `recorded_at`, lưu mỗi sync) | 🔴 P0 |
| 2 | **Customer/Vendor table** | AI không biết KFM, Shopee, vendor Truck là ai → mỗi lần phải hỏi lại | Medium (CRUD table + admin UI) | 🔴 P0 |
| 3 | **Decision log** | Manager hỏi đã trả lời rồi → AI quên → câu sau lại dò từ đầu | Low (`ask_log` table + retrieval) | 🟠 P1 |
| 4 | **Network/Hub data** | "Mở rộng KCN Bình Dương" → AI không biết hub gần nhất là gì | Medium | 🟠 P1 |
| 5 | **Driver pool detail** | Chỉ có total count → không biết Station/Core/Hub/Mass breakdown | Low (4 metrics có sẵn, cần ingest) | 🟠 P1 |
| 6 | **Incident/issue log** | AI không học được từ failures cũ | Medium | 🟡 P2 |
| 7 | **Meeting notes / action items** | Quyết định trong meeting không tracked → drift | High (cần workflow mới) | 🟡 P2 |
| 8 | **Document references** | Living docs ở Google Drive, AI không đọc được | High (cần Drive integration) | 🟢 P3 |
| 9 | **Competitor signals** | "Be Delivery promo mới, ảnh hưởng FR?" → AI không biết | High (cần ingest manual hoặc scraping) | 🟢 P3 |
| 10 | **Customer satisfaction signals** | NPS, complaints — feedback loop từ thị trường | High | 🟢 P3 |

### 2.3 Integration roadmap — đề xuất theo phase

**Phase 1 (Week 1-2)**: Fix P0 — biggest bang/buck
- Thêm `metrics_history` table (timestamp + key + value) → AI thấy trend
- Thêm `customers` + `vendors` tables → AI biết "KFM là ai"
- Thêm `ask_log` table → AI có memory

**Phase 2 (Week 3-4)**: P1 — operational depth
- `network` table (hubs/stations/KCN với capacity)
- Driver tier metrics expanded
- `incidents` table

**Phase 3 (Week 5+)**: P2/P3 — strategic depth
- Google Drive integration cho living docs
- Competitor monitoring (manual ingest UI)
- Customer feedback aggregator

---

## Part 3: Templates anh cần fill

8 file YAML đã tạo sẵn ở `bot/knowledge/templates/`. Mỗi file có:
- Block comments giải thích structure
- Example entries marked `EXAMPLE`
- Anh chỉ cần thay nội dung, giữ structure

### Thứ tự ưu tiên fill

| Order | File | Layer | ETA fill | Tại sao priority |
|-------|------|-------|----------|------------------|
| 1 | `01_company_dna.yaml` | L1 | 30ph | AI cần biết business basics đầu tiên |
| 2 | `04_kpi_dictionary.yaml` | L4 | 1h | Mỗi câu hỏi metrics đều cần |
| 3 | `03_okr_tree.yaml` | L3 | 30ph | Convert từ markdown → structured |
| 4 | `07_operating_rhythm.yaml` | L7 | 30ph | Định nghĩa cadence (daily 8AM, weekly Fri 5PM...) |
| 5 | `05_customers.yaml` | L5 | 1-2h | Top 20 KH (KFM, Shopee, TikTok Shop, key Bulky) |
| 6 | `06_vendors.yaml` | L5 | 1h | Top vendor (truck, fuel, insurance) |
| 7 | `08_network.yaml` | L6 | 1h | Hubs + stations + KCN coverage |
| 8 | `09_risks_postmortems.yaml` | L8/L9 | 1h | Top 10 risk + 3-5 postmortem |

**Tổng**: ~6-8h fill. Có thể delegate cho team members fill từng phần (vd: KPI cho data analyst, customer cho BD).

---

## Part 4: Roadmap chi tiết (5 weeks)

### Week 1 — Knowledge backbone (NOW)

**Deliverable**: AI hiểu 100% business/org/OKR/KPI

**Tasks:**
- [x] Smart agent foundation (DONE)
- [ ] **Fill 8 templates** ← anh làm
- [ ] Build `knowledge_loader_v2.py`: load YAML + JSON + cache + reload
- [ ] Inject knowledge into smart_agent system prompt
- [ ] Test: 10 câu hỏi sample, đo accuracy

**Success criteria**:
- AI trả lời câu "Vì sao FR HAN giảm?" có cite được metric trend + OKR ref + member nào responsible
- AI trả lời "Task X giao ai" có match scope + check workload + grade alignment

### Week 2 — More tools + Time series

**Deliverable**: AI suy luận sâu (trend, RCA, knowledge search)

**Tasks:**
- [ ] Add `metrics_history` table + cron lưu snapshot mỗi 30min
- [ ] Add 6 tools mới cho smart_agent:
  - `get_metrics_trend(metric, days)` — time series
  - `search_knowledge(query)` — RAG over all knowledge files
  - `find_playbook(task_text)` — match SOP
  - `get_okr_burndown(okr_id)` — % done over time
  - `get_member_history(name, days)` — past task patterns
  - `get_customer_info(name)` — key account detail
- [ ] Update `_PLAN_PROMPT` để AI biết chọn tools mới
- [ ] Update web `/ask` tool inspector với 12 tools

**Success criteria**:
- "Trend FR HAN 4 tuần qua" → AI plot text chart
- "Vendor X có vấn đề không" → AI search past incidents

### Week 3 — Memory + Learning loop

**Deliverable**: AI tốt dần qua usage

**Tasks:**
- [ ] `ask_log` table: lưu mọi Q&A + tools_used + tool_results
- [ ] `/ask` API trả về `ask_id` → user feedback ✓/✗ qua endpoint
- [ ] `prompt_feedback.md` aggregate: top câu sai → manager review
- [ ] Conversation memory: thread context giữa các câu trong cùng session (chat_id)
- [ ] Weekly: AI tự review past Q&A, đề xuất prompt updates

**Success criteria**:
- User trả lời /ask → next /ask trong cùng session có nhớ context
- Feedback ✓ rate > 70% sau 2 tuần usage

### Week 4 — UX + Automation

**Deliverable**: Trải nghiệm production-grade

**Tasks:**
- [ ] Web `/ask` streaming SSE (response từng chunk, không phải đợi full)
- [ ] Knowledge admin page: `/admin/knowledge` edit YAML inline
- [ ] Scheduled brief: 8AM mỗi ngày bot tự /ask "team status hôm nay" → DM manager
- [ ] Monitoring: cost per query (Gemini token count), P95 latency, success rate
- [ ] Health check: `/api/agent/health` show all tools functional

**Success criteria**:
- Streaming response < 2s đến chunk đầu
- Daily auto-brief có insight, không phải dump số

### Week 5 — Production polish

**Deliverable**: Sẵn sàng team rollout

**Tasks:**
- [ ] Google Drive integration: living docs (`/03 OKR`, `/04 KPI`) auto-sync
- [ ] CRM-lite admin UI: customer/vendor table với add/edit/delete
- [ ] Postmortem template + library
- [ ] Slash commands cho web: `/ask <q>` từ task page anywhere
- [ ] Docs: ONBOARDING.md cho TL/manager mới
- [ ] Failover: nếu Gemini down → fallback to Claude

**Success criteria**:
- New TL onboard trong 30 phút
- Bot uptime > 99% trong 1 tuần

---

## Part 5: Success Metrics — đo cái gì?

### Adoption
- Số câu `/ask` per day (target: > 20 sau 4 tuần)
- Số distinct user dùng (target: 5+/11 members)
- Telegram /ask vs Web /ask ratio (cho biết surface nào tốt hơn)

### Quality
- User feedback ✓ rate (target: > 70%)
- Tool selection accuracy (đúng tool / total) — measure qua human review 50 query sample
- Hallucination rate (số liệu sai) — < 5%

### Performance
- P50 latency (target: < 8s)
- P95 latency (target: < 20s)
- Token cost per query (target: < $0.05)

### Business impact
- % decisions trên `/ask` thay vì gọi họp ad-hoc
- Time saved per manager (anecdotal survey)
- OKR action throughput trước/sau (proxy metric)

---

## Part 6: Open questions cho anh trả lời

Trước khi anh fill templates, em cần biết:

1. **Customer scope**: Top 20 KH hay top 50? Có exclude C2C không?
2. **Vendor scope**: Truck rental + fuel + insurance + tech vendor? Hay chỉ truck?
3. **Network granularity**: Tới hub level (5-10 hubs) hay đến station level (50+ stations)?
4. **OKR access**: AI có quyền xem cả OKR Q1/Q3 của các quarter khác không, hay chỉ Q2?
5. **Memory privacy**: Decision log lưu plain text — có cần PII redaction không?
6. **Google Drive**: Có access service account hay personal account để integrate?
7. **Cost ceiling**: Limit token/tháng là bao nhiêu? (để decide cache strategy)
8. **Multi-language**: AI chỉ tiếng Việt hay support cả tiếng Anh (cho expat)?

---

## Appendix A: File map

```
bot/
├── knowledge/
│   ├── grade_matrix.json          ✅ existing
│   ├── member_scopes.json         ✅ existing
│   ├── playbooks.json             ✅ existing
│   ├── templates/                 ← anh fill 8 file ở đây
│   │   ├── 01_company_dna.yaml
│   │   ├── 03_okr_tree.yaml
│   │   ├── 04_kpi_dictionary.yaml
│   │   ├── 05_customers.yaml
│   │   ├── 06_vendors.yaml
│   │   ├── 07_operating_rhythm.yaml
│   │   ├── 08_network.yaml
│   │   └── 09_risks_postmortems.yaml
│   └── (filled YAML files sẽ sống cùng level với JSON sau khi fill)
├── knowledge_loader.py            ✅ (cần extend YAML support week 1)
├── models.py                      ✅
├── agents.py                      ✅ (delegation coach, crisis commander)
├── smart_agent.py                 ✅ (6 tools, two-pass)
└── classifier.py                  ✅ (NL intent, route, classify)

web/src/app/
├── ask/page.tsx                   ✅
├── api/ask/route.ts               ✅
└── admin/knowledge/page.tsx       ⏳ week 4

docs/
├── PROJECT_PLAN.md                ← document này
└── ONBOARDING.md                  ⏳ week 5
```

## Appendix B: Decision authority cho knowledge admin

Ai update knowledge file nào:

| File | Owner | Cadence update |
|------|-------|----------------|
| `company_dna.yaml` | CEO / Head of Strategy | Yearly |
| `okr_tree.yaml` | OKR owner (anh) | Quarterly |
| `kpi_dictionary.yaml` | Data Lead | Monthly review |
| `customers.yaml` | BD Lead | Weekly add new |
| `vendors.yaml` | Ops Lead | Monthly review |
| `operating_rhythm.yaml` | Manager | Quarterly review |
| `network.yaml` | Ops + Expansion | Monthly |
| `risks_postmortems.yaml` | Manager | Sau mỗi postmortem |
| `member_scopes.json` | Manager | Khi có thay đổi role |
| `playbooks.json` | TL theo playbook | Khi update SOP |
