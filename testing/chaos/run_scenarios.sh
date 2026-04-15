#!/bin/bash
# SentinelAI — Resilience & Chaos Testing with Toxiproxy
# Usage: ./chaos/run_scenarios.sh [scenario]
# Scenarios: latency | bandwidth | timeout | down | all

TOXI_API="http://localhost:8474"
BASE_URL="http://localhost:8000"
RESULTS_DIR="./results"
mkdir -p "$RESULTS_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()    { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()     { echo -e "${GREEN}[PASS]${NC} $1"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()   { echo -e "${RED}[FAIL]${NC} $1"; }
header() { echo -e "\n${CYAN}══════════════════════════════════════${NC}"; echo -e "${CYAN} $1${NC}"; echo -e "${CYAN}══════════════════════════════════════${NC}"; }

# ── Helper: check if service responds ────────────────────────────────────────
check_service() {
  local url=$1
  local label=$2
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url/health" 2>/dev/null)
  if [ "$status" = "200" ]; then
    ok "$label is UP (HTTP $status)"
    return 0
  else
    fail "$label is DOWN or degraded (HTTP $status)"
    return 1
  fi
}

# ── Helper: add toxic ─────────────────────────────────────────────────────────
add_toxic() {
  local proxy=$1 name=$2 type=$3 attrs=$4
  curl -s -X POST "$TOXI_API/proxies/$proxy/toxics" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$name\",\"type\":\"$type\",\"stream\":\"downstream\",\"toxicity\":1.0,\"attributes\":$attrs}" \
    > /dev/null
  log "Injected toxic: $name ($type) on $proxy"
}

# ── Helper: remove toxic ──────────────────────────────────────────────────────
remove_toxic() {
  local proxy=$1 name=$2
  curl -s -X DELETE "$TOXI_API/proxies/$proxy/toxics/$name" > /dev/null
  log "Removed toxic: $name from $proxy"
}

# ── Helper: enable/disable proxy ─────────────────────────────────────────────
set_proxy_enabled() {
  local proxy=$1 enabled=$2
  curl -s -X POST "$TOXI_API/proxies/$proxy" \
    -H "Content-Type: application/json" \
    -d "{\"enabled\":$enabled}" > /dev/null
}

# ── Scenario 1: High latency ──────────────────────────────────────────────────
scenario_latency() {
  header "Scenario 1: High Latency (500ms delay on API)"

  add_toxic "api_proxy" "high_latency" "latency" '{"latency":500,"jitter":100}'

  log "Running requests through degraded proxy..."
  for i in $(seq 1 5); do
    start=$(date +%s%3N)
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:18000/health")
    end=$(date +%s%3N)
    elapsed=$((end - start))
    echo "  Request $i: HTTP $status — ${elapsed}ms"
  done

  remove_toxic "api_proxy" "high_latency"
  ok "Scenario 1 complete"
}

# ── Scenario 2: Bandwidth throttle ───────────────────────────────────────────
scenario_bandwidth() {
  header "Scenario 2: Bandwidth Throttle (100KB/s on API)"

  add_toxic "api_proxy" "slow_bandwidth" "bandwidth" '{"rate":100}'

  log "Fetching /plans through throttled proxy..."
  time curl -s "http://localhost:18000/plans" > /dev/null

  remove_toxic "api_proxy" "slow_bandwidth"
  ok "Scenario 2 complete"
}

# ── Scenario 3: Connection timeout ───────────────────────────────────────────
scenario_timeout() {
  header "Scenario 3: Connection Timeout (payments service)"

  add_toxic "payments_proxy" "timeout" "timeout" '{"timeout":1000}'

  log "Attempting payments endpoint through toxic proxy..."
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:18004/health" 2>/dev/null)
  if [ "$status" = "200" ]; then
    warn "Service still responded — timeout may not have triggered"
  else
    ok "Timeout injected correctly (HTTP $status or connection refused)"
  fi

  remove_toxic "payments_proxy" "timeout"
  ok "Scenario 3 complete"
}

# ── Scenario 4: Service down ──────────────────────────────────────────────────
scenario_down() {
  header "Scenario 4: Service Outage (API proxy disabled)"

  log "Disabling API proxy..."
  set_proxy_enabled "api_proxy" "false"

  log "Testing system behaviour during API outage..."
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://localhost:18000/health" 2>/dev/null)
  if [ "$status" != "200" ]; then
    ok "API correctly unreachable through proxy (HTTP $status)"
  else
    fail "API still reachable — proxy disable may have failed"
  fi

  log "Verifying direct API still works (bypassing proxy)..."
  check_service "$BASE_URL" "Direct API"

  log "Re-enabling API proxy..."
  set_proxy_enabled "api_proxy" "true"
  sleep 2
  check_service "http://localhost:18000" "API via proxy"

  ok "Scenario 4 complete"
}

# ── Scenario 5: Container failure ────────────────────────────────────────────
scenario_container_failure() {
  header "Scenario 5: Container Failure (pgvector restart)"

  log "Current API health..."
  check_service "$BASE_URL" "API"

  log "Stopping pgvector container..."
  docker stop sentinelai-pgvector 2>/dev/null || docker stop $(docker ps -q --filter name=pgvector) 2>/dev/null

  sleep 3
  log "Testing API during DB outage..."
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE_URL/health")
  echo "  API health during DB outage: HTTP $status"

  log "Restarting pgvector..."
  docker start sentinelai-pgvector 2>/dev/null || docker start $(docker ps -aq --filter name=pgvector) 2>/dev/null

  log "Waiting for DB to recover (15s)..."
  sleep 15
  check_service "$BASE_URL" "API after recovery"

  ok "Scenario 5 complete"
}

# ── Scenario 6: Packet loss ───────────────────────────────────────────────────
scenario_packet_loss() {
  header "Scenario 6: Packet Loss (30% on webhooks)"

  add_toxic "webhooks_proxy" "packet_loss" "slice" '{"average_size":1,"size_variation":0,"delay":0}'

  log "Sending 10 requests through lossy proxy..."
  success=0
  for i in $(seq 1 10); do
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:19000/health" 2>/dev/null)
    [ "$status" = "200" ] && ((success++))
    echo "  Request $i: HTTP $status"
  done
  echo "  Success rate: $success/10"

  remove_toxic "webhooks_proxy" "packet_loss"
  ok "Scenario 6 complete"
}

# ── Run all / specific ────────────────────────────────────────────────────────
SCENARIO=${1:-all}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$RESULTS_DIR/resilience_${TIMESTAMP}.log"

{
  echo "SentinelAI Resilience Test Report — $(date)"
  echo "Scenario: $SCENARIO"
  echo ""

  case "$SCENARIO" in
    latency)           scenario_latency ;;
    bandwidth)         scenario_bandwidth ;;
    timeout)           scenario_timeout ;;
    down)              scenario_down ;;
    container_failure) scenario_container_failure ;;
    packet_loss)       scenario_packet_loss ;;
    all)
      scenario_latency
      scenario_bandwidth
      scenario_timeout
      scenario_down
      scenario_packet_loss
      scenario_container_failure
      ;;
    *)
      echo "Unknown scenario: $SCENARIO"
      echo "Available: latency | bandwidth | timeout | down | packet_loss | container_failure | all"
      exit 1
      ;;
  esac

  echo ""
  echo "All scenarios complete. Report saved to $REPORT"
} | tee "$REPORT"