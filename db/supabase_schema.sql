-- ════════════════════════════════════════════════════════════════════════
-- HoloacademIA · Índice de conocimiento en Supabase (Postgres + pgvector)
-- Fuente única para el Sinodal y el Motor Terapéutico.
-- Búsqueda HÍBRIDA: semántica (pgvector) + palabra clave (full-text español).
-- Ejecutar una sola vez en el SQL Editor de Supabase.
-- ════════════════════════════════════════════════════════════════════════

create extension if not exists vector;

create table if not exists holos_chunks (
  chunk_id       text primary key,
  course_id      text,
  course_name    text,
  linea          text,
  tipo           text,
  audiencia      text,
  idioma         text default 'es',
  source_id      text,
  source_type    text,
  source_file    text,
  heading        text,
  text           text not null,
  char_count     integer,
  embedding      vector(1536),
  -- Vector de texto para búsqueda por palabra clave (español).
  tsv            tsvector generated always as (
                   to_tsvector('spanish', coalesce(heading,'') || ' ' || coalesce(text,''))
                 ) stored,
  created_at     timestamptz default now()
);

-- Índice semántico (coseno). HNSW: rápido y de alta calidad para este tamaño.
create index if not exists holos_chunks_embedding_idx
  on holos_chunks using hnsw (embedding vector_cosine_ops);

-- Índice de palabra clave.
create index if not exists holos_chunks_tsv_idx
  on holos_chunks using gin (tsv);

-- Filtro por curso.
create index if not exists holos_chunks_course_idx
  on holos_chunks (course_id);

-- ────────────────────────────────────────────────────────────────────────
-- Búsqueda híbrida con Reciprocal Rank Fusion (RRF).
-- Combina el ranking semántico y el de palabra clave en un solo puntaje,
-- sin que una escala aplaste a la otra. full_text_weight da más peso a las
-- coincidencias literales (útil para términos técnicos del material).
-- ────────────────────────────────────────────────────────────────────────
create or replace function match_holos(
  query_embedding   vector(1536),
  query_text        text,
  match_count       int  default 6,
  full_text_weight  float default 1.0,
  semantic_weight   float default 1.0,
  rrf_k             int  default 50,
  filter_course_ids text[] default null
)
returns table (
  chunk_id    text,
  course_name text,
  source_file text,
  heading     text,
  text        text,
  score       float
)
language sql
as $$
with fts as (
  select c.chunk_id,
         row_number() over (
           order by ts_rank_cd(c.tsv, websearch_to_tsquery('spanish', query_text)) desc
         ) as rank
  from holos_chunks c
  where query_text is not null
    and c.tsv @@ websearch_to_tsquery('spanish', query_text)
    and (filter_course_ids is null or c.course_id = any(filter_course_ids))
  limit least(match_count * 4, 100)
),
sem as (
  select c.chunk_id,
         row_number() over (order by c.embedding <=> query_embedding) as rank
  from holos_chunks c
  where query_embedding is not null
    and (filter_course_ids is null or c.course_id = any(filter_course_ids))
  order by c.embedding <=> query_embedding
  limit least(match_count * 4, 100)
),
fused as (
  select coalesce(fts.chunk_id, sem.chunk_id) as chunk_id,
         coalesce(full_text_weight / (rrf_k + fts.rank), 0.0)
       + coalesce(semantic_weight  / (rrf_k + sem.rank), 0.0) as score
  from fts
  full outer join sem on fts.chunk_id = sem.chunk_id
)
select c.chunk_id, c.course_name, c.source_file, c.heading, c.text, f.score
from fused f
join holos_chunks c on c.chunk_id = f.chunk_id
order by f.score desc
limit match_count;
$$;
