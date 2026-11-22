# Ripple Frontend

React + Vite + TypeScript + Tailwind scaffold for the Ripple operations dashboard. This batch uses local mock data only; it does not call the API or Adaption.

## Start locally

From this directory:

```bash
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://127.0.0.1:5173`). To verify a production bundle, run `npm run build`.

## Structure

- `src/layout/`: desktop sidebar, mobile navigation, and top bar.
- `src/pages/`: overview, system map, scenario creator, simulation, intervention center, and analyst sections.
- `src/components/`: shared metric and section-heading components.
- `src/data/mockData.ts`: UI-only sample metrics and event data.
- `@xyflow/react` is installed for the next network visualization batch; no graph UI is implemented here.
