# Project Agent Rules

This project is the new shadcn/Next/FastAPI implementation. Do not edit the older Streamlit project when working here.

## Scope

- Keep changes small and tied to the requested feature.
- Prefer existing shadcn components and local feature folders.
- Preserve the public/private data boundary.

## Public/Private Data

- Public examples live in `storage/templates`.
- Private runtime data lives in `storage/local` and must stay gitignored.
- Do not commit real portfolio data, trading logs, account identifiers, API keys, cookies, exported broker files, or local SQLite databases.

## Frontend

- Use shadcn/ui components before custom markup.
- Use semantic CSS variables and Tailwind tokens.
- Use `gap-*`, not `space-*`.
- Client components that use browser APIs must include `"use client"`.
- Chart code belongs under `apps/web/src/features/charts`.

## Backend

- Keep the FastAPI API local-first.
- External market providers must degrade to deterministic sample data so the UI remains usable.
- Runtime writes must target `storage/local` by default.
