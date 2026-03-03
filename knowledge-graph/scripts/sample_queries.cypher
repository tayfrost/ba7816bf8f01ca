// ==============================================
// SentinelAI Knowledge Graph - Sample Cypher Queries
// ==============================================

// 1. Get all advice for workplace stress, ranked by confidence
MATCH (a:Advice)-[:SOURCED_FROM]->(p:Paper)-[:COVERS]->(t:Topic {id: 'workplace_stress'})
OPTIONAL MATCH (a)-[:USES_TECHNIQUE]->(tc:Technique)
RETURN a.text AS advice, a.confidence AS confidence, p.title AS paper, tc.name AS technique
ORDER BY a.confidence DESC
LIMIT 10;

// 2. Find breathing exercises for anger management
MATCH (a:Advice)-[:USES_TECHNIQUE]->(tc:Technique {id: 'deep_breathing'})
MATCH (a)-[:SOURCED_FROM]->(p:Paper)-[:COVERS]->(t:Topic {id: 'anger_management'})
RETURN a.text AS advice, p.title AS source, p.citations AS citations
ORDER BY p.citations DESC;

// 3. Most cited papers in the knowledge graph
MATCH (p:Paper)
RETURN p.title AS paper, p.citations AS citations, p.year AS year, p.arxiv_id AS arxiv
ORDER BY p.citations DESC
LIMIT 10;

// 4. All techniques that address a given topic
MATCH (tc:Technique)-[:ADDRESSES]->(t:Topic {id: 'anxiety'})
RETURN tc.name AS technique, t.name AS topic;

// 5. Papers covering multiple topics (intersection)
MATCH (p:Paper)-[:COVERS]->(t:Topic)
WITH p, collect(t.name) AS topics, count(t) AS topic_count
WHERE topic_count >= 3
RETURN p.title AS paper, topics, topic_count
ORDER BY topic_count DESC;

// 6. Advice using CBT techniques across all topics
MATCH (a:Advice)-[:USES_TECHNIQUE]->(tc:Technique {id: 'cbt_restructuring'})
MATCH (a)-[:SOURCED_FROM]->(p:Paper)
RETURN a.text AS advice, a.confidence AS confidence, p.title AS paper
ORDER BY a.confidence DESC;

// 7. Full path: Topic -> Technique -> Advice -> Paper
MATCH (t:Topic {id: 'sleep_issues'})<-[:COVERS]-(p:Paper)<-[:SOURCED_FROM]-(a:Advice)-[:USES_TECHNIQUE]->(tc:Technique)
RETURN t.name AS topic, tc.name AS technique, a.text AS advice, p.title AS paper, a.confidence AS confidence
ORDER BY a.confidence DESC;

// 8. Graph statistics
MATCH (p:Paper) WITH count(p) AS papers
MATCH (a:Advice) WITH papers, count(a) AS advice
MATCH (t:Topic) WITH papers, advice, count(t) AS topics
MATCH (tc:Technique) WITH papers, advice, topics, count(tc) AS techniques
RETURN papers, advice, topics, techniques;

// 9. Find advice for multiple simultaneous concerns
MATCH (a:Advice)-[:SOURCED_FROM]->(p:Paper)-[:COVERS]->(t:Topic)
WHERE t.id IN ['workplace_stress', 'anxiety', 'sleep_issues']
OPTIONAL MATCH (a)-[:USES_TECHNIQUE]->(tc:Technique)
RETURN DISTINCT a.text AS advice, a.confidence AS confidence, 
       collect(DISTINCT t.name) AS related_topics, tc.name AS technique, p.title AS paper
ORDER BY a.confidence DESC
LIMIT 10;

// 10. Topic connectivity - which topics are most interconnected through papers
MATCH (t1:Topic)<-[:COVERS]-(p:Paper)-[:COVERS]->(t2:Topic)
WHERE t1.id < t2.id
RETURN t1.name AS topic1, t2.name AS topic2, count(p) AS shared_papers
ORDER BY shared_papers DESC
LIMIT 15;
