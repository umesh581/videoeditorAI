# Technical Specification — Constituency Dashboard
## Port Target: Lovable (React + Supabase)

**Project:** Manikonda–Neknampur Constituency Accountability Dashboard
**Candidate:** Jithender Merugu (@JITHUINC) — Congress Corporator candidate
**Source repo:** `constituency_dashboard/` (Streamlit + SQLite + APScheduler)
**Target:** Lovable.dev — React frontend, Supabase (Postgres) backend, Supabase Edge Functions for scheduled scrapers.

---

## 1. Database Schema (Supabase / Postgres)

Migration from SQLite. All tables use `uuid` primary keys, `timestamptz` for time fields, and `text` over `varchar`. Enable Row Level Security (RLS) on every table — auth model in §1.5.

### 1.1 `grievances`

Core table — every civic issue we have a citable source for.

```sql
create table grievances (
  id                  uuid primary key default gen_random_uuid(),
  location            text not null,            -- e.g. "Manikonda Village"
  lat                 double precision,
  lon                 double precision,
  category            text,                     -- CPGRAMS category label
  category_code       text,                     -- "001"–"015" (see §1.6)
  description         text,
  reported_date       date not null default current_date,
  status              text not null default 'Pending'
                       check (status in ('Pending','InProgress','Resolved','Closed')),
  era                 text default 'Congress Era (2024–Present)'
                       check (era in ('BRS Era (Pre-2023)','Congress Era (2024–Present)')),
  families_affected   integer default 0,
  petition_no         text,
  agency              text,                     -- "GHMC", "HMWSSB", etc.
  source_url          text,                     -- MUST be http(s) — see §1.7
  source_type         text default 'scraped',   -- "google_form" | "firecrawl/<domain>" | "news_rss" | "manual"
  days_pending        integer generated always as
                       (greatest(0, current_date - reported_date)) stored,
  escalation_tier     text,                     -- see §2 — computed by trigger
  opportunity_score   numeric(5,1),             -- see §3 — computed by trigger
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

create index on grievances (location);
create index on grievances (escalation_tier);
create index on grievances (opportunity_score desc);
create index on grievances (reported_date desc);
```

### 1.2 `voters`

**New** in the Supabase port (not in the Streamlit version). Captures opt-in voters from the Google Form + door-to-door intake.

```sql
create table voters (
  id                uuid primary key default gen_random_uuid(),
  name              text,
  phone             text,                       -- E.164 — index for SMS outreach
  ward_number       text,                       -- GHMC ward 100–139
  location          text,                       -- one of the 19 micro-locations
  household_size    integer,
  registered_voter  boolean default true,
  voter_id_epic     text,                       -- EPIC number (encrypted at rest)
  preferred_lang    text default 'te'
                     check (preferred_lang in ('te','en','hi','ur')),
  opt_in_sms        boolean default false,
  opt_in_whatsapp   boolean default false,
  source            text default 'field_form',  -- "field_form" | "google_form" | "manual"
  notes             text,
  created_at        timestamptz default now(),
  updated_at        timestamptz default now(),
  unique (phone)
);

create index on voters (ward_number);
create index on voters (location);
create index on voters (phone) where phone is not null;

-- Link a voter to grievances they filed
create table voter_grievances (
  voter_id     uuid references voters(id) on delete cascade,
  grievance_id uuid references grievances(id) on delete cascade,
  primary key (voter_id, grievance_id)
);
```

### 1.3 `news_articles`

```sql
create table news_articles (
  id          uuid primary key default gen_random_uuid(),
  title       text not null,
  source      text,                             -- "Google News" | "Firecrawl · eenadu.net" | "X/@JITHUINC"
  url         text unique,                      -- dedup key
  published   date,
  keyword     text,                             -- which query found it
  sentiment   text check (sentiment in ('Angry / Frustrated','Neutral','Hopeful')),
  summary     text,
  era         text,                             -- "BRS Era" | "Congress Era" | null
  scraped_at  timestamptz default now()
);

create index on news_articles (sentiment);
create index on news_articles (scraped_at desc);
create index on news_articles (keyword);
```

### 1.4 `sentiment_records`, `scrape_log`

```sql
create table sentiment_records (
  id          uuid primary key default gen_random_uuid(),
  text        text not null unique,
  location    text,
  lat         double precision,
  lon         double precision,
  sentiment   text check (sentiment in ('Angry / Frustrated','Neutral','Hopeful')),
  source      text,
  scraped_at  timestamptz default now()
);

create table scrape_log (
  id        uuid primary key default gen_random_uuid(),
  source    text not null,
  status    text check (status in ('ok','error','skip')),
  records   integer default 0,
  error     text,
  ran_at    timestamptz default now()
);

create index on scrape_log (source, ran_at desc);
```

### 1.5 Row Level Security

```sql
-- Public read for the dashboard (anon key)
alter table grievances        enable row level security;
alter table news_articles     enable row level security;
alter table sentiment_records enable row level security;
alter table scrape_log        enable row level security;
alter table voters            enable row level security;
alter table voter_grievances  enable row level security;

create policy "public read grievances"    on grievances        for select using (true);
create policy "public read news"          on news_articles     for select using (true);
create policy "public read sentiment"     on sentiment_records for select using (true);
create policy "public read scrape_log"    on scrape_log        for select using (true);

-- Voters PII — restrict to authenticated campaign-team members only
create policy "team read voters"          on voters
  for select using (auth.jwt() ->> 'role' = 'campaign_team');

create policy "team write voters"         on voters
  for insert with check (auth.jwt() ->> 'role' = 'campaign_team');

-- Inserts to grievances/news happen via service role from Edge Functions only.
```

### 1.6 Reference: CPGRAMS Category Codes

| code | label                                | default agency                |
|------|--------------------------------------|-------------------------------|
| 001  | Delay in decision / implementation   | District Collector / RDO      |
| 002  | Civic amenities / Quality of service | GHMC / Municipal Commissioner |
| 003  | Law & Order                          | Police / Commissioner         |
| 004  | Revenue / Land / Tax                 | Revenue Dept / Tahsildar      |
| 005  | Compensations / Refunds              | Relevant Dept                 |
| 006  | Social Evils                         | Police / Social Welfare       |
| 007  | Retirement dues                      | AG Office / Treasury          |
| 008  | Service matters (Govt employees)     | Dept of Personnel             |
| 009  | Requests / Permissions               | Relevant Dept                 |
| 010  | Corruption / Malpractices            | District Collector            |
| 011  | Harassment / Misbehaviour            | District Collector            |
| 012  | SC / ST / Backward class issues      | SC/ST Welfare Dept            |
| 013  | Central Govt miscellaneous           | Central Govt Office           |
| 014  | State Govt miscellaneous             | State Govt Office             |
| 015  | Legal Redress                        | District Legal Services       |

### 1.7 Zero-hallucination invariant

Every `grievances` row used to generate published content **must** satisfy
`source_url ~ '^https?://'`. Enforce at the application layer (drafts page
filters out rows without URLs) AND in the database:

```sql
alter table grievances add constraint grievance_must_have_source
  check (source_url is null or source_url ~ '^https?://');
```

---

## 2. Grievance Aging — Escalation Logic

`days_pending` is the **Postgres-generated** column:

```
days_pending = greatest(0, current_date - reported_date)
```

### 2.1 Tier thresholds (config constants — port these unchanged)

```ts
export const ESCALATION = {
  URGENT:    15,   // ≥ 15 days  → Call RDO today
  POLITICAL: 30,   // ≥ 30 days  → Raise at next Prajavani camp
  CRITICAL:  60,   // ≥ 60 days  → Escalate to District Collector
};
```

### 2.2 Classification (port from `modules/grievance_engine.py`)

```ts
function classifyEscalation(daysPending: number): Tier {
  if (daysPending >= 60) return 'CRITICAL';
  if (daysPending >= 30) return 'POLITICAL';
  if (daysPending >= 15) return 'URGENT';
  return 'MONITOR';
}
```

### 2.3 Recommended action by tier

| Tier      | Action template                                                                                       |
|-----------|--------------------------------------------------------------------------------------------------------|
| CRITICAL  | "Escalate to District Collector with written representation. Demand written response within 7 days. Copy: {agency}, MLA office." |
| POLITICAL | "Raise at next Prajavani camp. Publish status publicly. File RTI with {agency} if no response in 5 days." |
| URGENT    | "Call {agency} helpline today. Visit RDO office with petition copy. Post update on ward WhatsApp group." |
| MONITOR   | "Monitor — no action required yet."                                                                    |

### 2.4 Postgres trigger — keep `escalation_tier` and `opportunity_score` in sync

```sql
create or replace function update_grievance_derived()
returns trigger language plpgsql as $$
begin
  new.escalation_tier :=
    case
      when new.days_pending >= 60 then 'CRITICAL'
      when new.days_pending >= 30 then 'POLITICAL'
      when new.days_pending >= 15 then 'URGENT'
      else 'MONITOR'
    end;

  -- See §3 for the formula
  new.opportunity_score :=
    round(
      least(new.days_pending::numeric / 100, 1.0) * 50
      + least(coalesce(new.families_affected,0)::numeric / 300, 1.0) * 30
      + case when new.era = 'BRS Era (Pre-2023)' then 20 else 0 end,
      1
    );

  new.updated_at := now();
  return new;
end;
$$;

create trigger trg_grievance_derived
before insert or update of reported_date, families_affected, era
on grievances
for each row execute function update_grievance_derived();

-- Re-classify every night at midnight IST so aging stays current
-- (use Supabase pg_cron)
select cron.schedule(
  'reclassify-grievances',
  '30 18 * * *',  -- 00:00 IST = 18:30 UTC
  $$ update grievances set updated_at = now() where status = 'Pending'; $$
);
```

---

## 3. Sentiment & Opportunity Scoring

### 3.1 Sentiment classifier (news articles)

Three-class output: `Angry / Frustrated` | `Neutral` | `Hopeful`.

**Pipeline (port from `modules/data_ingestion.py:classify_sentiment`):**

```ts
const POSITIVE_BOOST = new Set([
  'prajavani', 'resolved', 'inaugurated', 'camp', 'hopeful', 'progress'
]);

const NEGATIVE_BOOST = new Set([
  'encroachment', 'flooding', 'pending', 'ignored', 'delayed',
  'crisis', 'overload', 'contamination', 'unresolved', 'abandoned'
]);

function classifySentiment(text: string): Sentiment {
  const lower = text.toLowerCase();
  const negHits = [...NEGATIVE_BOOST].filter(w => lower.includes(w)).length;
  const posHits = [...POSITIVE_BOOST].filter(w => lower.includes(w)).length;

  if (negHits > posHits) return 'Angry / Frustrated';
  if (posHits > negHits) return 'Hopeful';

  // Tie-break: TextBlob polarity (use `sentiment` npm pkg or a JS port)
  const polarity = computePolarity(text);   // returns -1..1
  if (polarity < -0.1) return 'Angry / Frustrated';
  if (polarity >  0.1) return 'Hopeful';
  return 'Neutral';
}
```

**Why a custom lexicon overrides polarity:** generic libraries miss
Telangana-specific civic vocabulary. *"Prajavani"* is positive locally
but neutral in TextBlob; *"encroachment"* is uniformly negative in
constituency context regardless of phrasing.

### 3.2 Opportunity Score (0–100)

A grievance's tweet-worthiness — composite of aging, scale, and political
contrast value.

```
score = age_component + family_component + era_bonus

age_component    = min(days_pending / 100, 1.0) × 50
family_component = min(families_affected / 300, 1.0) × 30
era_bonus        = 20  if era = "BRS Era (Pre-2023)"
                 = 0   otherwise

score is rounded to 1 decimal, capped at 100.
```

**Interpretation:**
- `≥ 80` — top-priority post / personal field visit
- `60–79` — weekly content slot
- `40–59` — monitor; bundle into thematic threads
- `< 40` — background tracking only

### 3.3 Tweet-source guarantee

A tweet/thread draft can be generated **only** for grievances where:
- `source_url ~ '^https?://'`
- `source_type` is not `'manual_test'`

The React UI must render the source URL alongside every draft (port the
`📎 Reference: ...` pattern from `app.py`).

---

## 4. Manikonda / Neknampur Boundary & Map Points

### 4.1 Map defaults

```ts
export const MAP_CONFIG = {
  center: [17.4065, 78.3772],   // Manikonda geometric center
  zoom:   14,
  // Approximate bounding box for the constituency
  bounds: {
    south: 17.3900,
    north: 17.4280,
    west:  78.3450,
    east:  78.3900,
  },
};
```

### 4.2 Canonical micro-locations (lat, lon)

Use these as the **authoritative** point list for markers, heatmap centroids,
and the location dropdown in the field-intake form. Port from
`modules/google_sheets.py:_location_coords` and `modules/form_config.py:LOCATIONS`.

| # | Location               | Latitude  | Longitude |
|---|------------------------|-----------|-----------|
| 1 | Manikonda Village      | 17.4071   | 78.3765   |
| 2 | Neknampur              | 17.4123   | 78.3689   |
| 3 | Puppalguda             | 17.3934   | 78.3798   |
| 4 | Lanco Hills            | 17.4089   | 78.3812   |
| 5 | Khajaguda              | 17.3985   | 78.3841   |
| 6 | Nallagandla            | 17.4245   | 78.3456   |
| 7 | Raj Bhavan Colony      | 17.4102   | 78.3829   |
| 8 | Alkapur Township       | 17.4050   | 78.3720   |
| 9 | Fairfield Colony       | 17.4090   | 78.3700   |
| 10| Lakshmi Nagar Colony   | 17.4060   | 78.3755   |
| 11| YSR Colony             | 17.4010   | 78.3780   |
| 12| Byouth Colony          | 17.4030   | 78.3800   |
| 13| Pioneer Estate         | 17.4080   | 78.3720   |
| 14| EVV Colony             | 17.4100   | 78.3690   |
| 15| EIPL Tamarind          | 17.4115   | 78.3672   |
| 16| Manikonda Basti        | 17.4055   | 78.3740   |
| 17| Neknampur Layout       | 17.4138   | 78.3701   |
| 18| Puppalguda Extension   | *(reuse Puppalguda)* | |

Fallback for unknown / "Other (specify)" submissions: `(17.4065, 78.3772)`.

### 4.3 Administrative metadata

```ts
export const ADMIN_CODES = {
  district:     'Rangareddy',
  district_code:'DARRD',
  district_num: '151',
  dept_code:    'MCMKONDA',          // CPGRAMS Manikonda department
  ward_numbers: range(100, 140),     // GHMC wards in Manikonda area
  mandals: {
    '21/151': 'SAROORNAGAR',
    '25/151': 'SRILINGAMPALLE',      // primary mandal for Manikonda
    '20/151': 'RAJENDRANAGAR',
    '7/151':  'GANDIPET',
    '3/151':  'BALAPUR',
  },
};
```

### 4.4 Recommended map library

`react-leaflet` + `leaflet.heat` for the heatmap (matches Streamlit's
`folium` + `HeatMap` plugin). Use **OpenStreetMap** tiles (no API key needed).
For polygon overlay of ward boundaries, source the GeoJSON from
[GHMC Open Data](https://data.telangana.gov.in/) — not included here as
it's a separate dataset acquisition step.

---

## 5. Scraper Architecture in Supabase

Replace the APScheduler `BackgroundScheduler` with **Supabase Edge Functions
+ pg_cron triggers**. One function per source:

| Edge Function           | Cron schedule    | Source module ported from              |
|-------------------------|------------------|----------------------------------------|
| `scrape-google-news`    | every 30 min     | `modules/scrapers/news_rss.py`         |
| `scrape-news-sites`     | every 35 min     | `modules/scrapers/news_sites.py`       |
| `scrape-firecrawl`      | every 60 min     | `modules/scrapers/firecrawl_news.py`   |
| `scrape-twitter-nitter` | every 40 min     | `modules/scrapers/twitter_scanner.py`  |
| `scrape-telugu-news`    | every 45 min     | `modules/scrapers/telugu_news.py`      |
| `scrape-brs-congress`   | every 90 min     | `modules/scrapers/brs_congress_live.py`|
| `sync-google-sheets`    | every 10 min     | `modules/google_sheets.py`             |

Edge Functions write via the **service role key** (bypasses RLS), then
the React frontend reads via the anon key (RLS-protected).

### Secrets (Supabase project settings)

```
FIRECRAWL_API_KEY          fc-…
GOOGLE_SHEET_ID            (from Apps Script create_form.gs)
GOOGLE_API_KEY             (Sheets API read key)
REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET   (optional)
```

---

## 6. React Frontend — Page Map

Direct port of the 9 Streamlit pages to React routes:

| Streamlit page                       | Route                       | Primary table reads        |
|--------------------------------------|-----------------------------|----------------------------|
| Executive Summary                    | `/`                         | grievances (aggregates)    |
| Voter Pain Heatmap                   | `/heatmap`                  | grievances + sentiment     |
| Escalation Engine                    | `/escalation`               | grievances (tier filter)   |
| BRS vs Congress Tracker              | `/accountability`           | news_articles (era filter) |
| Voter Sentiment                      | `/sentiment`                | sentiment_records          |
| News Intelligence                    | `/news`                     | news_articles              |
| Smart Outreach                       | `/outreach`                 | grievances                 |
| Content Opportunities (Jithender)    | `/content`                  | grievances + news_articles |
| Field Intake Form                    | `/intake`                   | writes grievances + voters |
| Data Sources                         | `/admin/sources`            | scrape_log                 |

Every page must render the **Data Status Badge** (port from `app.py:data_badge`):
🟢 LIVE / 🟡 PARTIAL LIVE / 🔴 SAMPLE — driven by row counts and
`scrape_log.ran_at` recency.

---

## 7. Open Items / Acquisition Required

1. **GHMC ward boundary GeoJSON** — needed for polygon overlay on the heatmap.
2. **Paid X API key** OR a reliable Nitter-equivalent — current Nitter mirrors are unreliable.
3. **Telegu newspaper API access** — currently scraped via Google News RSS site-filter; direct feeds would be faster.
4. **Voter roll cross-reference** — link `voters.voter_id_epic` to EC public rolls (manual data load).
