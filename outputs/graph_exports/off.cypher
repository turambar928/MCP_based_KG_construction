// 创建或匹配节点
MERGE (:`Entity` {name: '《陕西省艾滋病防治条例》'});
MERGE (:`Entity` {name: '免费发放安全套'});
MERGE (:`Entity` {name: '其他需要采取行为干预措施的人群免费发放安全套'});
MERGE (:`Entity` {name: '卫生和计划生育行政部门'});
MERGE (:`Entity` {name: '县级以上人民政府及其有关行政主管部门'});
MERGE (:`Entity` {name: '安全套产品质量的监督管理工作'});
MERGE (:`Entity` {name: '安全套等预防艾滋病传播的措施'});
MERGE (:`Entity` {name: '安全套营销、供应网络'});
MERGE (:`Entity` {name: '工商行政管理'});
MERGE (:`Entity` {name: '推广使用安全套工作'});
MERGE (:`Entity` {name: '疾病预防控制处'});
MERGE (:`Entity` {name: '育龄人群免费发放安全套'});
MERGE (:`Entity` {name: '艾滋病病毒感染者和艾滋病病人免费发放安全套'});
MERGE (:`Entity` {name: '西安市卫生健康委员会'});
MERGE (:`Entity` {name: '质量技术监督'});
MERGE (:`Entity` {name: '预防艾滋病'});
MERGE (:`Entity` {name: '食品药品监督'});

CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name);

// 创建或匹配关系
MATCH (h:Entity {name: '西安市卫生健康委员会'}), (t:Entity {name: '免费发放安全套'}) MERGE (h)-[:`行使主体`]->(t);
MATCH (h:Entity {name: '西安市卫生健康委员会'}), (t:Entity {name: '《陕西省艾滋病防治条例》'}) MERGE (h)-[:`行驶依据`]->(t);
MATCH (h:Entity {name: '疾病预防控制处'}), (t:Entity {name: '免费发放安全套'}) MERGE (h)-[:`承办机构`]->(t);
MATCH (h:Entity {name: '县级以上人民政府及其有关行政主管部门'}), (t:Entity {name: '预防艾滋病'}) MERGE (h)-[:`做好`]->(t);
MATCH (h:Entity {name: '县级以上人民政府及其有关行政主管部门'}), (t:Entity {name: '推广使用安全套工作'}) MERGE (h)-[:`做好`]->(t);
MATCH (h:Entity {name: '县级以上人民政府及其有关行政主管部门'}), (t:Entity {name: '安全套营销、供应网络'}) MERGE (h)-[:`建立完善`]->(t);
MATCH (h:Entity {name: '卫生和计划生育行政部门'}), (t:Entity {name: '安全套等预防艾滋病传播的措施'}) MERGE (h)-[:`加强推广使用`]->(t);
MATCH (h:Entity {name: '卫生和计划生育行政部门'}), (t:Entity {name: '育龄人群免费发放安全套'}) MERGE (h)-[:`向`]->(t);
MATCH (h:Entity {name: '卫生和计划生育行政部门'}), (t:Entity {name: '艾滋病病毒感染者和艾滋病病人免费发放安全套'}) MERGE (h)-[:`向`]->(t);
MATCH (h:Entity {name: '卫生和计划生育行政部门'}), (t:Entity {name: '其他需要采取行为干预措施的人群免费发放安全套'}) MERGE (h)-[:`向`]->(t);
MATCH (h:Entity {name: '质量技术监督'}), (t:Entity {name: '安全套产品质量的监督管理工作'}) MERGE (h)-[:`加强对`]->(t);
MATCH (h:Entity {name: '工商行政管理'}), (t:Entity {name: '安全套产品质量的监督管理工作'}) MERGE (h)-[:`加强对`]->(t);
MATCH (h:Entity {name: '食品药品监督'}), (t:Entity {name: '安全套产品质量的监督管理工作'}) MERGE (h)-[:`加强对`]->(t);