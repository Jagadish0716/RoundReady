# RoundReady frontend

Next.js App Router foundation using strict TypeScript, Tailwind CSS, shadcn/ui conventions, ESLint, Prettier, and Vitest.

## Local development

```bash
cp .env.example .env.local
npm install
npm run dev
```

`NEXT_PUBLIC_API_BASE_URL` must point to the RoundReady API gateway (locally, `http://127.0.0.1:8000`). Browser code must never call an individual microservice.

Public routes are `/`, `/login`, and `/register`. `/candidate`, `/interviewer`, and `/admin` are protected role placeholders.

## Authentication design

The current backend returns access and refresh tokens in JSON. Until a server-managed HttpOnly cookie contract exists, tokens are held only in React memory: they are not written to local storage, session storage, cookies, or logs. This minimizes persistent XSS exposure, with the intentional tradeoff that a page reload signs the user out. The provider supports login, refresh-token rotation, logout, authenticated identity loading, and role guards.

Run quality checks with:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```
