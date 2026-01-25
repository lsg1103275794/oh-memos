# Memory Content Examples

## Milestone Memory

```
[MILESTONE] Project: my-app | Date: 2025-01-25

## Summary
User authentication system fully implemented and tested

## Context
- Part of Phase 1 security requirements
- Needed before public launch

## Details
- JWT-based authentication with refresh tokens
- Files: src/auth/jwt.ts, src/middleware/auth.ts
- Used bcrypt for password hashing
- Token expiry: access=15min, refresh=7days

## Outcome
- All auth tests passing (15/15)
- Ready for integration testing
- Next: implement rate limiting

Tags: milestone, auth, security, phase1
```

## Bugfix Memory

```
[BUGFIX] Project: api-server | Date: 2025-01-25

## Summary
Fixed race condition in database connection pool

## Context
- Users reported intermittent 503 errors
- Happened under high load (>100 req/s)

## Details
- Root cause: connection checkout not atomic
- Fix: wrapped in mutex lock
- File: src/db/pool.ts:142-156
- Added connection timeout fallback

## Outcome
- Load test passed at 500 req/s
- No 503 errors in 24h monitoring

Tags: bugfix, database, performance, race-condition
```

## Decision Memory

```
[DECISION] Project: frontend | Date: 2025-01-25

## Summary
Chose TanStack Query over Redux for server state management

## Context
- Needed to manage API data caching
- Team debated Redux vs React Query vs SWR

## Options Considered
1. Redux + RTK Query - familiar but verbose
2. TanStack Query - modern, built-in caching
3. SWR - simpler but fewer features

## Decision
TanStack Query because:
- Automatic cache invalidation
- Better DevTools
- Smaller bundle size
- Team agreed it fits our use case

## Outcome
- Migration plan created
- Will implement in Sprint 7

Tags: decision, architecture, state-management, frontend
```

## Gotcha Memory

```
[GOTCHA] Project: deploy | Date: 2025-01-25

## Summary
Docker build fails silently when .env is missing

## Context
- CI/CD pipeline was hanging without error
- Took 2 hours to debug

## Details
- Docker COPY fails if source doesn't exist (in certain modes)
- Our Dockerfile had: COPY .env* ./
- When no .env files exist, build continues but app crashes at runtime

## Solution
```dockerfile
# Use explicit file or create empty
RUN touch .env
COPY .env* ./
```

## Outcome
- Added to CI check: verify .env.example exists
- Documented in deployment guide

Tags: gotcha, docker, ci-cd, debugging
```

## Progress Memory

```
[PROGRESS] Project: refactor | Date: 2025-01-25

## Summary
Database migration 50% complete - users table done

## Context
- Migrating from MongoDB to PostgreSQL
- Sprint 5 of 8-sprint migration

## Completed
- [x] Users table with all constraints
- [x] Sessions table
- [x] Data migration script for users
- [x] Read path switched to Postgres

## In Progress
- [ ] Orders table (complex, many relations)
- [ ] Write path still on MongoDB

## Blockers
- Need DBA review for orders table indexes
- Waiting on test environment with 10GB dataset

## Next Steps
1. Complete orders table schema
2. Run migration on staging
3. Performance comparison

Tags: progress, migration, database, sprint5
```

## Feature Memory

```
[FEATURE] Project: dashboard | Date: 2025-01-25

## Summary
Implemented real-time notifications using WebSocket

## Context
- User feedback: want instant updates
- Previously polling every 30s

## Details
- Socket.io for WebSocket connection
- Redis pub/sub for scaling across instances
- Files:
  - src/socket/server.ts (main handler)
  - src/socket/events.ts (event types)
  - src/hooks/useNotifications.ts (React hook)

## Usage
```typescript
const { notifications, markRead } = useNotifications();
```

## Outcome
- Latency reduced from 30s to <100ms
- CPU usage down 40% (no polling)

Tags: feature, websocket, real-time, notifications
```

## Config Memory

```
[CONFIG] Project: infra | Date: 2025-01-25

## Summary
Updated production rate limits after traffic spike

## Context
- Black Friday traffic 10x normal
- Original limits causing user drops

## Changes
- API rate limit: 100/min → 500/min per user
- WebSocket connections: 1000 → 5000 per instance
- Redis: increased maxmemory to 4GB

## Files Modified
- k8s/production/rate-limit.yaml
- redis/redis.conf
- nginx/nginx.conf

## Rollback
```bash
kubectl rollout undo deployment/api -n production
```

## Outcome
- Handled 50k concurrent users
- Will review limits post-holiday

Tags: config, production, scaling, rate-limit
```
