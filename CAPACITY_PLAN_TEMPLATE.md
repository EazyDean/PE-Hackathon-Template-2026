# Capacity Plan Template

## Scope

- Date:
- Commit / branch:
- Environment:
- Public endpoints under test:
- Cache enabled:

## Expected Workload

- Expected peak users:
- Expected steady-state users:
- Read/write ratio:
- Hot endpoint:
- Expected request rate:

## Service Targets

- Availability target:
- p95 latency target:
- Error-rate target:
- Recovery objective:

## Current Capacity

- App instances:
- App CPU / memory per instance:
- PostgreSQL host / container sizing:
- Redis sizing:
- Nginx sizing:

## Test Evidence

- 50-user result:
- 200-user result:
- 500-user result:
- Highest stable throughput observed:
- Failure point observed:

## Scale Triggers

- Add app instances when:
- Investigate DB tuning when:
- Increase cache TTL or Redis resources when:
- Reduce load or roll back when:

## Risks

- Primary bottleneck risk:
- Secondary bottleneck risk:
- Data-safety concern:

## Next Capacity Step

- Next improvement:
- Expected gain:
- Validation plan:
