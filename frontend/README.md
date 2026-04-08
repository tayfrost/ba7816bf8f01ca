# SentinelAI Frontend

React + TypeScript + Vite frontend for SentinelAI.

## Stack

- React 19
- TypeScript 5
- Vite 7
- ESLint 9

## Scripts

From the `frontend/` directory:

```bash
npm install
npm run dev
npm run lint
npm run build
npm run preview
```

## Docker

The production image is served via Nginx and built from [frontend/Dockerfile](Dockerfile).

In the repository root compose stack, the frontend service is `sentinel-frontend`.

## Notes

- The CI gate for frontend currently runs `lint` and `build` only.
- End-to-end and resilience tests live under [testing/](../testing/README.md).
