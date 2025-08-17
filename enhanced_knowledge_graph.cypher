// 创建或匹配节点
MERGE (:`Entity` {name: 'E06FCBC8B4E263C04595AD197B9A8718'});
MERGE (:`Entity` {name: '《中华人民共和国消防法》'});
MERGE (:`Entity` {name: '实施依据'});
MERGE (:`Entity` {name: '对擅自停用、拆除消防设施、器材的处罚'});
MERGE (:`Entity` {name: '市公安局'});
MERGE (:`Entity` {name: '承办机构'});
MERGE (:`Entity` {name: '服务事项'});
MERGE (:`Entity` {name: '权力类型'});
MERGE (:`Entity` {name: '消防支队、大队'});
MERGE (:`Entity` {name: '统一发布平台'});
MERGE (:`Entity` {name: '行政处罚'});
MERGE (:`Entity` {name: '行驶主体'});

CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name);

// 创建或匹配关系
MATCH (h:Entity {name: '权力类型'}), (t:Entity {name: '行政处罚'}) MERGE (h)-[:`类型`]->(t);
MATCH (h:Entity {name: '行驶主体'}), (t:Entity {name: '市公安局'}) MERGE (h)-[:`主体`]->(t);
MATCH (h:Entity {name: '承办机构'}), (t:Entity {name: '消防支队、大队'}) MERGE (h)-[:`机构`]->(t);
MATCH (h:Entity {name: '实施依据'}), (t:Entity {name: '《中华人民共和国消防法》'}) MERGE (h)-[:`依据`]->(t);
MATCH (h:Entity {name: '统一发布平台'}), (t:Entity {name: 'E06FCBC8B4E263C04595AD197B9A8718'}) MERGE (h)-[:`ID`]->(t);
MATCH (h:Entity {name: '服务事项'}), (t:Entity {name: '对擅自停用、拆除消防设施、器材的处罚'}) MERGE (h)-[:`名称`]->(t);