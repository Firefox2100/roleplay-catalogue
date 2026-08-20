# Roleplay Catalogue frontend

The React frontend uses Vitest, jsdom, and React Testing Library. Tests are colocated with the
code they exercise so ownership and refactoring impact remain obvious.

## Test layers

- **Unit tests** cover pure utilities and API request contracts. They should not render React or
  make network requests.
- **Component and hook tests** render one shared component or hook and exercise behavior through
  accessible user interactions.
- **Page integration tests** render a page inside a memory router while mocking only the API
  boundary. They verify loading, errors, filtering, navigation, and composed UI behavior.
- Backend function tests remain responsible for the real HTTP API. Browser end-to-end tests can
  be added later for a small set of deployment-critical journeys.

## Commands

```sh
npm test                 # deterministic one-shot test run
npm run test:watch       # interactive development mode
npm run test:coverage    # enforced baseline plus HTML and LCOV reports
npm run lint
npm run build
```

Coverage includes the whole application. The initial global threshold deliberately reflects the
existing editor pages that do not yet have integration tests while preventing regression; increase it as each editor receives a
page integration suite. High-risk utilities, auth state, conflict handling, shared components,
and the catalogue page already have substantially higher focused coverage.
