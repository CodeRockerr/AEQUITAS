/**
 * AEQUITAS: Site-wide product stats shown on Home, About, and the Sidebar.
 *
 * Single source of truth so these numbers can't drift out of sync across
 * pages. Update here when the underlying count actually changes:
 *   - unitTests: `python -m pytest --collect-only -q` in backend/ (last line)
 *   - apiRouters: count of `app.include_router(...)` calls in backend/app/main.py
 *   - version: latest git tag
 */
export const SITE_STATS = {
  unitTests: "222",
  algorithms: "13",
  agentNodes: "4",
  mlModels: "2",
  apiRouters: "13",
  version: "v0.14.0",
} as const;
