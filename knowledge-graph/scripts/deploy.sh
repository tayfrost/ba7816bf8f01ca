#!/bin/bash
# SentinelAI Knowledge Graph - Deploy Script
# Usage: ./deploy.sh [start|import|export|test|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NEO4J_CONTAINER="sentinelai-neo4j"
NEO4J_USER="neo4j"
NEO4J_PASS="sentinelai2025"

start() {
    echo "Starting Neo4j..."
    cd "$SCRIPT_DIR"
    docker-compose up -d
    echo "Waiting for Neo4j to be ready..."
    sleep 10
    until docker exec $NEO4J_CONTAINER wget --spider -q http://localhost:7474 2>/dev/null; do
        echo "  Still waiting..."
        sleep 5
    done
    echo "Neo4j is ready at http://localhost:7474"
}

build() {
    echo "Building knowledge graph..."
    cd "$SCRIPT_DIR"
    pip install -r requirements.txt -q
    python build_graph.py
    echo "Graph built. Cypher exported to import.cypher"
}

import_graph() {
    echo "Importing graph to Neo4j..."
    cat "$SCRIPT_DIR/import.cypher" | docker exec -i $NEO4J_CONTAINER cypher-shell -u $NEO4J_USER -p $NEO4J_PASS
    echo "Import complete."
}

export_db() {
    echo "Exporting Neo4j database volume..."
    VOLUME_NAME=$(docker volume ls -q | grep neo4j_data)
    if [ -z "$VOLUME_NAME" ]; then
        echo "ERROR: Neo4j data volume not found"
        exit 1
    fi
    docker run --rm -v ${VOLUME_NAME}:/data -v "$SCRIPT_DIR":/backup alpine \
        tar czf /backup/knowledge-graph-db.tar.gz -C /data .
    echo "Exported to: $SCRIPT_DIR/knowledge-graph-db.tar.gz"
    echo "Upload this file to a public file sharing service and link in README."
}

run_tests() {
    echo "Running tests..."
    cd "$SCRIPT_DIR"
    python -m pytest test_knowledge_graph.py -v
}

case "${1:-all}" in
    start)   start ;;
    build)   build ;;
    import)  import_graph ;;
    export)  export_db ;;
    test)    run_tests ;;
    all)
        start
        build
        import_graph
        run_tests
        echo ""
        echo "Knowledge graph deployed successfully!"
        echo "  Neo4j Browser: http://localhost:7474"
        echo "  API: uvicorn api:app --port 8000"
        ;;
    *)
        echo "Usage: $0 [start|build|import|export|test|all]"
        exit 1
        ;;
esac
