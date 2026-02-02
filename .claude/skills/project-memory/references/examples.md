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

---

## Enhanced Memory Types (New)

### Error Pattern Memory

```
[ERROR_PATTERN] Project: my-api | Date: 2025-01-25

## Error Signature
- Type: ConnectionRefusedError
- Message: ConnectionRefusedError: [Errno 111] Connection refused
- Context: Connecting to Redis on container startup

## Environment
- OS: Linux (Docker Alpine)
- Python: 3.11
- Key packages: redis==4.5.0, FastAPI

## Root Cause
Redis container not ready when app container starts. Docker Compose `depends_on` only waits for container start, not service readiness.

## Solution
1. Add health check to Redis in docker-compose.yml:
   ```yaml
   redis:
     healthcheck:
       test: ["CMD", "redis-cli", "ping"]
       interval: 5s
       timeout: 3s
       retries: 5
   ```
2. Add `condition: service_healthy` to depends_on:
   ```yaml
   app:
     depends_on:
       redis:
         condition: service_healthy
   ```
3. Alternative: Add retry logic in app code

## Verification
```bash
docker-compose down && docker-compose up -d
docker logs app-container  # Should show successful Redis connection
```

## Prevention
- Always use health checks for service dependencies
- Add retry logic for external connections
- Consider using wait-for-it.sh script

Tags: error, ConnectionRefusedError, docker, redis, startup
```

### Code Pattern Memory

```
[CODE_PATTERN] Project: my-api | Pattern: Async Retry Decorator

## Purpose
Generic retry decorator for async functions with exponential backoff

## Usage Context
- External API calls that may fail temporarily
- Database connections during startup
- Any operation that benefits from retry

## Template
```python
import asyncio
from functools import wraps
from typing import Type
import logging

logger = logging.getLogger(__name__)

def async_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,)
):
    """
    Retry decorator with exponential backoff for async functions.

    Args:
        retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{retries + 1}): {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} failed after {retries + 1} attempts: {e}")

            raise last_exception
        return wrapper
    return decorator
```

## Parameters
- `retries`: Number of retry attempts (default: 3)
- `delay`: Initial delay in seconds (default: 1.0)
- `backoff`: Backoff multiplier (default: 2.0)
- `exceptions`: Exception types to catch (default: all)

## Example Usage
```python
@async_retry(retries=5, delay=0.5, exceptions=(ConnectionError, TimeoutError))
async def fetch_external_api(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10)
        return response.json()
```

## Used In
- src/services/external_api.py:25
- src/db/connection.py:42
- src/integrations/payment.py:18

## Notes
- Always specify exception types to avoid masking bugs
- Consider adding jitter for distributed systems
- Log all retries for debugging

Tags: pattern, retry, async, decorator, python, error-handling
```

### Decision Chain Memory

```
[DECISION_CHAIN] Project: e-commerce | Topic: Database Architecture

## Current Decision
PostgreSQL with read replicas + Redis cache (implemented 2025-01-25)

## Evolution Timeline
| Date | Decision | Rationale | Supersedes |
|------|----------|-----------|------------|
| 2024-06-01 | SQLite | Quick prototype, simple setup | - |
| 2024-09-15 | PostgreSQL single | Production ready, ACID | SQLite |
| 2024-12-01 | PostgreSQL + Redis | Cache frequently accessed data | Single PG |
| 2025-01-25 | PG + read replicas + Redis | Scale read operations | PG + Redis |

## Context
E-commerce platform with:
- 100k daily active users
- 80% read, 20% write operations
- Product catalog with 1M+ items
- Real-time inventory updates needed

## Alternatives Considered
1. **Vertical scaling**: Bigger DB instance
   - Pros: Simple, no code changes
   - Cons: Cost ceiling, single point of failure

2. **Read replicas only**: No caching layer
   - Pros: Simpler architecture
   - Cons: Still hit DB for every read

3. **PG + Redis + Read replicas** (chosen)
   - Pros: Best performance, fault tolerant
   - Cons: More complex, eventual consistency for cache

## Impact
- Affected files: src/db/*, src/cache/*, docker-compose.yml
- Dependencies: asyncpg, redis, sqlalchemy
- Migration needed: Yes, connection pooling changes

## Links
- Previous: [DECISION-DB-002]
- Related: [CONFIG-REDIS-001], [FEATURE-CACHING-001]
- Caused: [GOTCHA-CACHE-INVALIDATION-001]

Tags: decision, database, architecture, scaling, postgresql, redis
```

### Knowledge Memory

```
[KNOWLEDGE] Project: my-api | Topic: Rate Limiting Strategy

## Summary
Documentation of our rate limiting approach and configuration

## Key Information

### Rate Limit Tiers
| Tier | Requests/min | Burst | Use Case |
|------|--------------|-------|----------|
| Anonymous | 20 | 30 | Public endpoints |
| Authenticated | 100 | 150 | Logged in users |
| Premium | 500 | 750 | Paid accounts |
| Internal | unlimited | - | Service-to-service |

### Implementation
- Using Redis sliding window algorithm
- Key format: `ratelimit:{user_id}:{endpoint}:{window}`
- Window size: 60 seconds
- Burst uses token bucket on top of sliding window

### Headers Returned
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706234567
```

### When Exceeded
- Returns 429 Too Many Requests
- Retry-After header with seconds to wait
- Does NOT count failed requests against limit

## Related Files
- src/middleware/rate_limit.py
- src/config/rate_limits.yaml
- tests/test_rate_limiting.py

## Common Pitfalls
1. Don't forget to exclude health check endpoints
2. Internal services must use service tokens
3. Reset time is Unix timestamp, not seconds

Tags: knowledge, rate-limiting, api, security, redis
```

---

## Memory Relationship Examples

### Linking Memories

When saving a memory that relates to others, include links:

```
[BUGFIX] Project: my-api | Date: 2025-01-25

## Summary
Fixed cache invalidation race condition

## Context
Users seeing stale data after updates

## Details
- Redis cache not invalidated atomically with DB write
- Added distributed lock using Redlock

## Related Memories
- Relates to: [FEATURE-CACHING-001]
- Caused by: [DECISION-DB-003] (the caching decision)
- Similar to: [ERROR_PATTERN-RACE-001]
- Updates: [KNOWLEDGE-CACHING-001]

Tags: bugfix, cache, race-condition, redis
```
