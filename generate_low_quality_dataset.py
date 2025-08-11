''' 
通用文本数据退化脚本  (适用于任何领域的数据集)
退化策略示例：
1. 世界知识或实体错误 (China→USA 等)
2. 年份/数字扰动 (2023→3023, 数字±10%)
3. 动词缺失
4. 短语顺序打乱
5. 标点删除
6. 字符重复或错别字
'''

import argparse
import os
import random
import re
from typing import List

# ------------------ 质量退化策略 ------------------

# 1. 世界知识错误映射（简单规则）
WORLD_KNOWLEDGE_SWAP = [
    (r"中国", "美国"), (r"美国", "火星"),
    (r"北京", "纽约"), (r"上海", "巴黎"), (r"广州", "柏林"),
    (r"苹果公司", "香蕉公司"), (r"微软", "火狐"),
]

# 2. 常见动词列表（用于删除动词制造动词缺失）
COMMON_VERBS = [
    "是", "在", "位于", "拥有", "获得", "参加", "赢得", "击败", "抵达", "宣布"
]

# 3. 随机打乱短语顺序

def shuffle_phrases(sentence: str) -> str:
    phrases = re.split(r"[，,。.!?]", sentence)
    phrases = [p for p in phrases if p.strip()]
    random.shuffle(phrases)
    return "，".join(phrases) + "。"

# ------------------ 退化函数 ------------------

def apply_degradation(sentence: str) -> str:
    """随机选择一种或多种方式退化句子质量"""
    operations = [introduce_factual_error, distort_year_number, remove_random_verb, shuffle_phrases, remove_punctuation, duplicate_random_char]
    # 至少应用一种退化，可能应用多种
    random_ops = random.sample(operations, k=random.randint(1, len(operations)))
    for op in random_ops:
        sentence = op(sentence)
    return sentence


def introduce_factual_error(sentence: str) -> str:
    for pattern, replacement in WORLD_KNOWLEDGE_SWAP:
        if re.search(pattern, sentence):
            return re.sub(pattern, replacement, sentence, count=1)
    return sentence  # 若未命中则返回原句


def remove_random_verb(sentence: str) -> str:
    verbs_in_sentence = [v for v in COMMON_VERBS if v in sentence]
    if verbs_in_sentence:
        verb_to_remove = random.choice(verbs_in_sentence)
        return sentence.replace(verb_to_remove, "")
    return sentence

def distort_year_number(sentence:str)->str:
    # 找四位数字年份或一般数字
    def repl(match):
        num = match.group()
        if len(num)==4: # 可能是年份
            return str(int(num)+100)  # 偏移100年
        else:
            try:
                val=int(num)
                return str(int(val*1.1))
            except:
                return num
    return re.sub(r"\d{2,4}", repl, sentence, count=1)

def remove_punctuation(sentence:str)->str:
    PUNCTUATIONS = "，。,！？!?,."
    return sentence.translate(str.maketrans('', '', PUNCTUATIONS))

def duplicate_random_char(sentence:str)->str:
    if not sentence:
        return sentence
    idx=random.randint(0,len(sentence)-1)
    return sentence[:idx]+sentence[idx]*2+sentence[idx+1:]

# ------------------ 主脚本 ------------------

def process_file(input_path: str, output_path: str):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    with open(input_path, "r", encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            try:
                idx, text = line.strip().split("\t", 1)
            except ValueError:
                # 若格式不对，跳过
                continue
            degraded = apply_degradation(text)
            fout.write(f"{idx}\t{degraded}\n")

    print(f"✅ 已生成低质量版本: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="生成低质量文本数据集")
    parser.add_argument("input", help="输入 txt 文件路径 (如 data/processed_dataset/news_sports.txt)")
    parser.add_argument("--output", help="输出文件路径，如果未提供则自动在输入文件名后加 _low_quality.txt", default=None)
    args = parser.parse_args()

    output_path = args.output or (os.path.splitext(args.input)[0]+"_low_quality.txt")
    process_file(args.input, output_path)


if __name__ == "__main__":
    main() 