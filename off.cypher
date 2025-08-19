// 创建或匹配节点
MERGE (:`Entity` {name: '中华人民共和国特种设备安全法'});
MERGE (:`Entity` {name: '事故'});
MERGE (:`Entity` {name: '作业人员'});
MERGE (:`Entity` {name: '依据'});
MERGE (:`Entity` {name: '岗位职责'});
MERGE (:`Entity` {name: '操作规程'});
MERGE (:`Entity` {name: '有关安全规章制度'});
MERGE (:`Entity` {name: '权力'});
MERGE (:`Entity` {name: '检测人员'});
MERGE (:`Entity` {name: '特种设备安全管理人员'});
MERGE (:`Entity` {name: '综合执法支队'});
MERGE (:`Entity` {name: '西安市市场监督管理局'});

CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name);

// 创建或匹配关系
MATCH (h:Entity {name: '特种设备安全管理人员'}), (t:Entity {name: '岗位职责'}) MERGE (h)-[:`不履行`]->(t);
MATCH (h:Entity {name: '特种设备安全管理人员'}), (t:Entity {name: '操作规程'}) MERGE (h)-[:`违反`]->(t);
MATCH (h:Entity {name: '特种设备安全管理人员'}), (t:Entity {name: '有关安全规章制度'}) MERGE (h)-[:`违反`]->(t);
MATCH (h:Entity {name: '特种设备安全管理人员'}), (t:Entity {name: '事故'}) MERGE (h)-[:`造成`]->(t);
MATCH (h:Entity {name: '检测人员'}), (t:Entity {name: '岗位职责'}) MERGE (h)-[:`不履行`]->(t);
MATCH (h:Entity {name: '检测人员'}), (t:Entity {name: '操作规程'}) MERGE (h)-[:`违反`]->(t);
MATCH (h:Entity {name: '检测人员'}), (t:Entity {name: '有关安全规章制度'}) MERGE (h)-[:`违反`]->(t);
MATCH (h:Entity {name: '检测人员'}), (t:Entity {name: '事故'}) MERGE (h)-[:`造成`]->(t);
MATCH (h:Entity {name: '作业人员'}), (t:Entity {name: '岗位职责'}) MERGE (h)-[:`不履行`]->(t);
MATCH (h:Entity {name: '作业人员'}), (t:Entity {name: '操作规程'}) MERGE (h)-[:`违反`]->(t);
MATCH (h:Entity {name: '作业人员'}), (t:Entity {name: '有关安全规章制度'}) MERGE (h)-[:`违反`]->(t);
MATCH (h:Entity {name: '作业人员'}), (t:Entity {name: '事故'}) MERGE (h)-[:`造成`]->(t);
MATCH (h:Entity {name: '西安市市场监督管理局'}), (t:Entity {name: '权力'}) MERGE (h)-[:`行驶`]->(t);
MATCH (h:Entity {name: '西安市市场监督管理局'}), (t:Entity {name: '综合执法支队'}) MERGE (h)-[:`承办机构`]->(t);
MATCH (h:Entity {name: '中华人民共和国特种设备安全法'}), (t:Entity {name: '依据'}) MERGE (h)-[:`第九十二条`]->(t);