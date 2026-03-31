# Hangar VPS Operations

## Update a tool after code changes

```bash
cd ~/hangar/repo && git pull
cp ~/hangar/repo/deploy/docker-compose.prod.yml ~/hangar/
cd ~/hangar
docker compose -f docker-compose.prod.yml build --no-cache oas-mcp
docker compose -f docker-compose.prod.yml up -d oas-mcp
```

Replace `oas-mcp` with `ocp-mcp` or `pyc-mcp` as needed. Build multiple at once:

```bash
docker compose -f docker-compose.prod.yml build --no-cache oas-mcp ocp-mcp pyc-mcp
docker compose -f docker-compose.prod.yml up -d oas-mcp ocp-mcp pyc-mcp
```

## Update Caddy routing

After editing `~/caddy/Caddyfile`:

```bash
cd ~/caddy && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Check status

```bash
cd ~/hangar
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs oas-mcp --tail 10
docker compose -f docker-compose.prod.yml logs ocp-mcp --tail 10
docker compose -f docker-compose.prod.yml logs pyc-mcp --tail 10
```

## Restart a single tool

```bash
cd ~/hangar
docker compose -f docker-compose.prod.yml restart oas-mcp
```

## Stop a single tool

```bash
cd ~/hangar
docker compose -f docker-compose.prod.yml stop oas-mcp
```

## Stop everything

```bash
cd ~/hangar
docker compose -f docker-compose.prod.yml down
```

Note: `down` removes containers but preserves volumes (`postgres_data`) and bind mounts (`hangar_data/`).

## Start everything

```bash
cd ~/hangar
docker compose -f docker-compose.prod.yml up -d
```

## View real-time logs

```bash
cd ~/hangar
docker compose -f docker-compose.prod.yml logs -f oas-mcp
```

## Keycloak admin console

```bash
# 1. Comment out @admin block in ~/caddy/Caddyfile
# 2. Reload Caddy
cd ~/caddy && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
# 3. Open https://auth.lakesideai.dev/admin/
# 4. Uncomment @admin block and reload when done
```

## Fix data directory permissions

If a tool fails with `unable to open database file`:

```bash
sudo chown -R 999:999 ~/hangar/hangar_data/oas/
sudo chown -R 999:999 ~/hangar/hangar_data/ocp/
sudo chown -R 999:999 ~/hangar/hangar_data/pyc/
```

## Back up

```bash
# Keycloak DB
cd ~/hangar
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U keycloak keycloak > ~/keycloak_backup_$(date +%Y%m%d).sql

# Artifacts
cp -r ~/hangar/hangar_data ~/hangar_data_backup_$(date +%Y%m%d)
```

## Landing page

The landing page at `mcp.lakesideai.dev/` is served by Caddy from static files.
The Caddy container must mount the landing directory from the repo:

```yaml
# In ~/caddy/docker-compose.yml, add to caddy volumes:
- ~/hangar/repo/deploy/landing:/srv/landing:ro
```

After adding the volume:

```bash
cd ~/caddy && docker compose up -d caddy
```

To update the landing page after a `git pull`, no action is needed &mdash;
Caddy serves directly from the repo directory.

### Health endpoints

Each MCP server exposes `GET /healthz` (unauthenticated) returning:

```json
{"status": "ok", "server": "oas", "version": "0.1.0"}
```

The landing page JS polls these at `/oas/healthz`, `/ocp/healthz`, `/pyc/healthz`
every 30 seconds to show live status indicators.

## Nuclear restart (rebuild everything from scratch)

```bash
cd ~/hangar
docker compose -f docker-compose.prod.yml down
cd ~/hangar/repo && git pull
cp ~/hangar/repo/deploy/docker-compose.prod.yml ~/hangar/
cd ~/hangar
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```
